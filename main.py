import logging
import sys
import time
from typing import Any

import elasticapm
from elasticsearch import Elasticsearch

import config
from api import authenticate_sensorpush, authorize_sensorpush, fetch_sensor_data
from database import create_db_and_tables, get_sensor_timestamp, update_sensor_timestamp
from es import send_to_elasticsearch
from logger import configure_logging
from utils import format_sensor_data

# Configure logging at module level
configure_logging()
logger = logging.getLogger()


def main():
    create_db_and_tables()
    loader = config.ConfigLoader()
    loader.load_config()

    # Define required settings and secrets
    REQUIRED_SETTINGS = [
        "INDEX_NAME",
        "AUTHENTICATE_URL",
        "AUTHORIZATION_URL",
        "DATA_URL",
        "DEFAULT_START_TIME",
        "SLEEP_DURATION",
        "SENSORS",
        "MEASURES",
    ]

    REQUIRED_SECRETS = ["ES_USERNAME", "ES_PASSWORD", "ES_URL", "SENSORPUSH_EMAIL", "SENSORPUSH_PASSWORD"]

    # Validate required keys
    loader.validate_config(REQUIRED_SETTINGS, REQUIRED_SECRETS)

    es_client = Elasticsearch(
        loader.get("ES_URL", "secrets"),
        basic_auth=(loader.get("ES_USERNAME", "secrets"), loader.get("ES_PASSWORD", "secrets")),
        timeout=15,
        max_retries=5,
        retry_on_timeout=True,
    )

    # Validate the Elasticsearch connection
    try:
        if not es_client.ping():
            logger.error("Failed to connect to Elasticsearch. Please check the configuration.")
            sys.exit(1)
        else:
            logger.info("Successfully connected to Elasticsearch.")
    except ConnectionError as e:
        logger.error(f"Elasticsearch connection error: {e}")
        sys.exit(1)

    # Create Elastic APM client
    apm_client = elasticapm.Client(
        {
            "SERVER_URL": loader.get("APM_SERVER_URL", "secrets"),
            "SERVICE_NAME": loader.get("APM_SERVICE_NAME"),
            "SECRET_TOKEN": loader.get("APM_SECRET_TOKEN", "secrets"),
            "ENVIRONMENT": loader.get("APM_ENVIRONMENT"),
            "SERVICE_VERSION": loader.get("APM_SERVICE_VERSION"),
        }
    )

    elasticapm.instrument()  # type: ignore

    while True:
        apm_client.begin_transaction("sensorpush script")
        with elasticapm.capture_span("authentication"):  # type: ignore
            authentication = authenticate_sensorpush(
                loader.get("AUTHENTICATE_URL", "settings"), loader.get("SENSORPUSH_EMAIL", "secrets"), loader.get("SENSORPUSH_PASSWORD", "secrets")
            )

        with elasticapm.capture_span("authorization"):  # type: ignore
            authorization = authorize_sensorpush(loader.get("AUTHORIZATION_URL", "settings"), authentication)

        if authorization:
            sensors: list[dict[str, Any]] = loader.get("SENSORS", "settings")
            for sensor in sensors:
                if isinstance(sensor, dict) and "id" in sensor:
                    logger.info(f"Processing data for sensor_id: [{sensor['id']}] sensor_name: [{sensor['name']}].")
                    timestamp = get_sensor_timestamp(sensor["id"]) or loader.get("DEFAULT_START_TIME", "settings")
                    logger.info(f"Last timestamp for sensor {sensor['id']}: {timestamp}")

                    with elasticapm.capture_span("fetch_sensor_data"):  # type: ignore
                        raw_data = fetch_sensor_data(
                            url=loader.get("DATA_URL", "settings"),
                            access_token=authorization,
                            sensor_id=sensor["id"],
                            measures=list(loader.get("MEASURES", "settings")),
                            start_time=timestamp,
                            limit=int(loader.get("DATA_LIMIT", "settings")),
                        )

                    if raw_data:
                        with elasticapm.capture_span("format_sensor_data"):  # type: ignore
                            formatted_data = format_sensor_data(sensor, raw_data)

                        if formatted_data:
                            with elasticapm.capture_span("update_sensor_timestamp"):  # type: ignore
                                update_sensor_timestamp(sensor_id=sensor["id"], timestamp=formatted_data[0]["sensor.observed"])
                            with elasticapm.capture_span("send_to_elasticsearch"):  # type: ignore
                                send_to_elasticsearch(es_client, formatted_data, loader.get("INDEX_NAME", "settings"))
                        else:
                            logger.error(f"No formated data found for sensor_id: [{sensor['id']}].")
                    else:
                        logger.error(f"No raw data found for sensor_id: [{sensor['id']}].")
        else:
            logger.error("Failed to authenticate with SensorPush API.")

        apm_client.end_transaction("sensorpush script", "success")
        logger.info(f"Sleeping for {loader.get('SLEEP_DURATION', 'settings')} seconds.")
        time.sleep(int(loader.get("SLEEP_DURATION", "settings")))


if __name__ == "__main__":
    main()
