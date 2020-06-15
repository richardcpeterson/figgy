from typing import Set

import boto3
import logging

from lib.data.ssm import SsmDao
from lib.svcs.slack import SlackService
from lib.utils.utils import Utils
from config.constants import *
from lib.data.dynamo.config_cache_dao import ConfigCacheDao, ConfigItem

log = Utils.get_logger(__name__, logging.INFO)

dynamo_resource = boto3.resource("dynamodb")
ssm_client = boto3.client('ssm')
ssm = SsmDao(ssm_client)
webhook_url = ssm.get_parameter_value(FIGGY_WEBHOOK_URL_PATH)
slack: SlackService = SlackService(webhook_url=webhook_url)
ACCOUNT_ID = ssm.get_parameter_value(ACCOUNT_ID_PS_PATH)


def handle(event, context):
    # Don't process other account's events.
    originating_account = event.get('account')
    if originating_account != ACCOUNT_ID:
        log.info(f"Received event from different account with id: {ACCOUNT_ID}. Skipping this event.")
        return

    try:
        log.info(f"Event: {event}")
        cache_dao: ConfigCacheDao = ConfigCacheDao(dynamo_resource)

        detail = event["detail"]
        action = detail["eventName"]
        params = detail.get('requestParameters', {})
        ps_name = params.get('name') if params else None

        if not ps_name:
            log.info(f"Received an event missing parameterStore path: {event}")
            return

        if action == DELETE_PARAM_ACTION or action == DELETE_PARAMS_ACTION:
            log.info(f"Deleting from cache: {ps_name}")
            items: Set[ConfigItem] = cache_dao.get_items(ps_name)
            sorted_items = sorted(items)
            [cache_dao.delete(item) for item in sorted_items[:-1]]  # Delete all but the most recent item.
            cache_dao.mark_deleted(sorted_items[-1])
        elif action == PUT_PARAM_ACTION:
            items: Set[ConfigItem] = cache_dao.get_items(ps_name)
            [cache_dao.delete(item) for item in items]  # If any stragglers exist, get rid of em
            log.info(f"Putting in cache: {ps_name}")
            cache_dao.put_in_cache(ps_name)
        else:
            log.info(f"Unsupported action type found! --> {action}")
    except Exception as e:
        log.error(e)
        slack.send_error(title=f"Figgy experienced an irrecoverable error! In account: {ACCOUNT_ID[0:5]}[REDACTED]",
                         message=f"The following error occurred in an the figgy-config-cache-manager lambda. "
                                 f"If this appears to be a bug with figgy, please tell us by submitting a GitHub issue!"
                                 f" \n\n{Utils.printable_exception(e)}")
        raise e


if __name__ == "__main__":
    handle(None, None)
