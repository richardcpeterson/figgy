import boto3
import logging
from config.constants import *
from lib.models.replication_config import ReplicationConfig
from lib.data.dynamo.replication_dao import ReplicationDao
from lib.data.ssm.ssm import SsmDao
from lib.models.slack import SlackMessage, SlackColor
from lib.svcs.replication import ReplicationService
from lib.svcs.slack import SlackService
from lib.utils.utils import Utils

repl_dao: ReplicationDao = ReplicationDao(boto3.resource('dynamodb'))
ssm: SsmDao = SsmDao(boto3.client('ssm'))
repl_svc: ReplicationService = ReplicationService(repl_dao, ssm)
webhook_url = ssm.get_parameter_value(FIGGY_WEBHOOK_URL_PATH)
slack: SlackService = SlackService(webhook_url=webhook_url)
log = Utils.get_logger(__name__, logging.INFO)


def notify_slack(config: ReplicationConfig):
    message = SlackMessage(
        color=SlackColor.GREEN,
        title="Figgy Event: Replication configured successfully.",
        message=f"Replication updated: `{config.source}` -> `{config.destination}`. \n"
                f"*{config.user}* configured this replication.\n"
                f"Replication to `{config.destination}` was successful."
    )

    slack.send_message(message)


def handle(event, context):
    log.info(f"Got Event: {event} with context {context}")
    try:
        records = event.get('Records', [])
        for record in records:
            event_name = record.get("eventName")
            # Only resync on adds / updates, never on deletes.
            if event_name != 'REMOVE':
                ddb_record = record.get("dynamodb", {})
                keys = ddb_record.get("Keys", {})
                destination = keys.get(REPL_DEST_KEY_NAME, {}).get("S", None)
                run_env = keys.get(REPL_RUN_ENV_KEY_NAME, {}).get("S", None)
                if destination and run_env:
                    log.info(f"Record updated with key: {destination} and run_env: {run_env}")
                    config: ReplicationConfig = repl_dao.get_config_repl(destination, run_env)
                    if config:
                        log.info(f"Got config: {config}, syncing...")
                        repl_svc.sync_config(config) and notify_slack(config)
                    else:
                        log.warning(f"Unable to find record with destination: {destination} and {run_env}. This *could* "
                                    f"indicate a serious issue with replication. If you see lots of these, please pay "
                                    f"attention.")
            else:
                log.info("Event is a delete event, skipping!")
    except Exception as e:
        log.error(e)
        slack.send_error(title="Figgy Dynamo Stream Replicator experienced and irrecoverable error!",
                         message=f"The following error occurred in an the *figgy-dynamo-stream-replicator* lambda.\n"
                                 f"Figgy is designed to continually backoff and retry in the face of error. \n```{Utils.printable_exception(e)}```")
        raise e


if __name__ == '__main__':
    handle(None, None)