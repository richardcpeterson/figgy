import time
import logging
from dataclasses import dataclass, field
import requests
from typing import List, Dict
from svcs.cache_manager import CacheManager
from utils.utils import Utils
from concurrent.futures import ThreadPoolExecutor
from config import *
from threading import Thread
log = logging.getLogger(__name__)


@dataclass
class FiggyMetrics:
    COUNT_KEY = 'count'
    metrics: Dict[str, Dict] = field(default_factory=dict)
    last_report: int = Utils.millis_since_epoch()

    def increment_count(self, command: str) -> None:
        metric = self.metrics.get(command, {})
        metric[FiggyMetrics.COUNT_KEY] = metric.get(FiggyMetrics.COUNT_KEY, 0) + 1
        self.metrics[command] = metric


class UsageTracker:
    """
        We want to track the usage counts of various commands and the version of Figgy people are currently using.
        This data will be valuable for informing future decisions & when considering upgrade paths or potentially
        introducing breaking changes and their impacts.
    """
    _CACHE_NAME = 'usage-metrics'
    _METRICS_KEY = 'metrics'
    REPORT_FREQUENCY = 1000 * 60 * 60 * 24  # Report daily

    @staticmethod
    def report_usage(metrics: FiggyMetrics):
        metrics_json = {UsageTracker._METRICS_KEY: {}}
        for key, val in metrics.metrics.items():
            metrics_json[UsageTracker._METRICS_KEY][key] = val.get(FiggyMetrics.COUNT_KEY, 0)

        requests.post(url=FIGGY_LOG_METRICS_URL, json=metrics_json)


    @staticmethod
    def track_command_usage(function):
        """
        Tracks user command usage locally. This will be intermittently reported in aggregate.
        """

        def inner(self, *args, **kwargs):
            command = getattr(self, 'type', None)
            if command:
                command = Utils.get_first(command)
                cache = CacheManager(UsageTracker._CACHE_NAME)
                last_write, metrics = cache.get(UsageTracker._METRICS_KEY, default=FiggyMetrics())
                metrics.increment_count(command)
                if Utils.millis_since_epoch() - metrics.last_report > UsageTracker.REPORT_FREQUENCY:
                    # Ship it async. If it don't worky, oh well :shruggie:
                    with ThreadPoolExecutor(max_workers=1) as pool:
                        pool.submit(UsageTracker.report_usage, metrics)
                        cache.write(UsageTracker._METRICS_KEY, FiggyMetrics())
                        return function(self, *args, **kwargs)
                else:
                    cache.write(UsageTracker._METRICS_KEY, metrics)

            return function(self, *args, **kwargs)

        return inner
