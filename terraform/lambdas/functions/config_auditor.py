import random
import time
from datetime import datetime

import boto3
import time
import logging
from config.constants import *
from lib.models.replication_config import ReplicationConfig
from lib.data.dynamo.audit_dao import AuditDao
from lib.data.ssm import SsmDao
from lib.models.slack import FigDeletedMessage, SlackColor, SimpleSlackMessage
from lib.svcs.slack import SlackService
from lib.utils.utils import Utils

log = Utils.get_logger(__name__, logging.INFO)

dynamo_resource = boto3.resource("dynamodb")
audit: AuditDao = AuditDao(dynamo_resource)
ssm_client = boto3.client('ssm')
ssm = SsmDao(ssm_client)
webhook_url = ssm.get_parameter_value(FIGGY_WEBHOOK_URL_PATH)
slack: SlackService = SlackService(webhook_url=webhook_url)

ACCOUNT_ID = ssm.get_parameter_value(ACCOUNT_ID_PS_PATH)
ACCOUNT_ENV = ssm.get_parameter_value(ACCOUNT_ENV_PS_PATH)
NOTIFY_DELETES = ssm.get_parameter_value(NOTIFY_DELETES_PS_PATH)
NOTIFY_DELETES = NOTIFY_DELETES.lower() == "true" if NOTIFY_DELETES else False

FIGGY_NAMESPACES = ssm.get_parameter_value(FIGGY_NAMESPACES_PATH)
CLEANUP_INTERVAL = 60 * 60  # Cleanup hourly
LAST_CLEANUP = 0


def notify_delete(ps_name: str, user: str):
    if NOTIFY_DELETES:
        slack.send_message(
            FigDeletedMessage(name=ps_name, user=user, environment=ACCOUNT_ENV)
        )


def handle(event, context):
    global LAST_CLEANUP

    # Don't process other account's events.
    originating_account = event.get('account')
    if originating_account != ACCOUNT_ID:
        log.info(f"Received event from different account with id: {ACCOUNT_ID}. Skipping this event.")
        return

    try:
        log.info(f"Event: {event}")
        detail = event["detail"]
        user_arn = detail.get("userIdentity", {}).get("arn", "UserArnUnknown")
        user = user_arn.split("/")[-1:][0]
        action = detail.get("eventName")

        if 'errorMessage' in detail:
            log.info(f'Not processing event due to this being an error event with message: {detail["errorMessage"]}')
            return

        request_params = detail.get('requestParameters', {})
        ps_names = request_params.get('names', [])
        ps_name = [request_params['name']] if 'name' in request_params else []
        ps_names = ps_names + ps_name
        event_time = detail.get('eventTime')

        # Convert to millis since epoch
        if event_time:
            event_time = int(datetime.strptime(event_time, "%Y-%m-%dT%H:%M:%SZ").timestamp() * 1000)
        else:
            event_time = int(time.time() * 1000)

        log.info(f"Got user: {user}, action: {action} for parameter(s) {ps_names}")

        for ps_name in ps_names:
            ps_name = f'/{ps_name}' if not ps_name.startswith('/') else ps_name

            if action == DELETE_PARAM_ACTION or action == DELETE_PARAMS_ACTION:
                audit.put_delete_log(user, action, ps_name, timestamp=event_time)
                notify_delete(ps_name, user)
            elif action == PUT_PARAM_ACTION:
                ps_value = request_params.get("value")
                ps_type = request_params.get("type")
                ps_description = request_params.get("description")
                ps_version = detail.get("responseElements", {}).get("version", 1)
                ps_key_id = request_params.get("keyId")

                if not ps_value:
                    ps_value = ssm.get_parameter_value(ps_name)

                audit.put_audit_log(
                    user,
                    action,
                    ps_name,
                    ps_value,
                    ps_type,
                    ps_key_id,
                    ps_description,
                    ps_version,
                    timestamp=event_time,
                )
            else:
                log.info(f"Unsupported action type found! --> {action}")

        # This will occassionally cleanup parameters with the explict value of DELETE_ME.
        # Great for testing and adding PS parameters
        # you don't want to be restored later on.
        if time.time() - CLEANUP_INTERVAL > LAST_CLEANUP:
            log.info("Cleaning up.")
            audit.cleanup_test_logs()
            LAST_CLEANUP = time.time()

    except Exception as e:
        log.error(e)
        message = f"The following error occurred in an the figgy-ssm-stream-replicator lambda. " \
                  f"If this appears to be a bug with Figgy, please tell us by submitting a GitHub issue!" \
                  f" \n\n{Utils.printable_exception(e)}"

        title = "Figgy experienced an irrecoverable error!"
        message = SimpleSlackMessage(
            title=title,
            message=message,
            color=SlackColor.RED
        )
        slack.send_message(message)
        raise e


if __name__ == "__main__":
    handle(None, None)
