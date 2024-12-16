import datetime
import hashlib
import json
import logging
import logging.config
import sys
import time
from typing import Any, Dict, Generator, List, Optional

import ecs_logging
import elasticapm
import requests
from config import config as CFG
from database import create_db_and_tables, engine
from elasticsearch.exceptions import (ConnectionError, RequestError,
                                      TransportError)
from elasticsearch.helpers import streaming_bulk
from models import Sensor
from sqlmodel import Session, select

from elasticsearch import Elasticsearch


# Logging configuration and initialization
def configure_logging():
    """
    Configures structured logging with ECS (Elastic Common Schema) formatting.

    This function sets up the logging configuration for the application, enabling
    structured log output in ECS format. Logs are output to the console using
    the `ecs_logging.StdlibFormatter`. The configuration includes a root logger
    and an application-specific logger.

    Logging Configuration:
        - **Formatters**: Uses the ECS formatter (`ecs_logging.StdlibFormatter`) for structured logs.
        - **Handlers**: Configures a console handler to output logs to `stdout`.
        - **Root Logger**: Logs messages at the `INFO` level and outputs them to the console.
        - **Application Logger**: Configures a logger named `python-sensorpush` with the same console handler,
          set to `INFO` level, and prevents propagation to the root logger.

    Dependencies:
        - `ecs_logging`: A library that provides an ECS-compatible formatter for Python logging.
        - `logging.config.dictConfig`: Used to apply the logging configuration.

    Notes:
        - This setup ensures that all logs are consistent with ECS, making them compatible
          with tools like Elastic Observability for centralized monitoring and analysis.
        - The `python-sensorpush` logger can be used for application-specific logging needs.

    """
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "ecs": {  # ECS formatter for structured logs
                "()": ecs_logging.StdlibFormatter,
            }
        },
        "handlers": {
            "console": {  # Console handler with ECS formatter
                "class": "logging.StreamHandler",
                "formatter": "ecs",
                "stream": "ext://sys.stdout",
            }
        },
        "root": {  # Root logger
            "level": "INFO",
            "handlers": ["console"],
        },
        "loggers": {
            "python-sensorpush": {  # Application-specific logger
                "level": "INFO",
                "handlers": ["console"],
                "propagate": False,
            }
        },
    }

    logging.config.dictConfig(logging_config)


# Helper functions
def create_headers(auth_token: Optional[str] = None) -> Dict[str, str]:
    """
    Create standard headers for API requests.

    Args:
        auth_token (Optional[str]): Authorization token to include in the headers.

    Returns:
        Dict[str, str]: Headers dictionary for API requests.
    """
    headers = {"content-type": "application/json", "accept": "application/json"}
    if auth_token:
        headers["Authorization"] = auth_token
    return headers


def make_api_request(
    url: str, headers: Dict[str, str], body: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Make a POST API request and handle errors.

    Args:
        url (str): API endpoint.
        headers (Dict[str, str]): Request headers.
        body (Dict[str, Any]): Request body.

    Returns:
        Dict[str, Any]: Response JSON as a dictionary, or an empty dictionary on failure.
    """
    with elasticapm.capture_span(name="make_api_request"):  # type: ignore
        try:
            response = requests.post(url=url, json=body, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Request to {url} failed: {e}")
            return {}


def authenticate_sensorpush(url: str, email: str, password: str) -> Optional[str]:
    """
    Authenticate with the SensorPush API and retrieve an authorization token.

    Args:
        url (str): API endpoint for authentication.
        email (str): User email for authentication.
        password (str): User password for authentication.

    Returns:
        Optional[str]: Authorization token, or None on failure.
    """
    with elasticapm.capture_span(name="authenticate"):  # type: ignore
        logger.info("Authenticating with SensorPush API.")
        headers = create_headers()
        body = {"email": email, "password": password}
        response = make_api_request(url, headers, body)
        return response.get("authorization")


def authorize_sensorpush(url: str, authentication: Optional[str]) -> Optional[str]:
    """
    Authorize with the SensorPush API and retrieve an access token.

    Args:
        url (str): API endpoint for authorization.
        authentication (Optional[str]): Authentication token from initial login.

    Returns:
        Optional[str]: Access token, or None on failure.
    """
    with elasticapm.capture_span(name="authenticate"):  # type: ignore
        if not authentication:
            logger.error("Invalid authentication!")
            return None

        logger.info("Authorizing with SensorPush API.")
        headers = create_headers()
        body = {"authorization": authentication}
        response = make_api_request(url, headers, body)
        return response.get("accesstoken")


def fetch_sensor_data(url: str, access_token: str, sensor_id: str, measures: List[str], start_time: str, limit: int,) -> Dict[str, Any]:
    """
    Fetch sensor data from the API.

    Args:
        url (str): API endpoint for sensor data.
        access_token (str): Access token for API authorization.
        sensor_id (str): ID of the sensor to fetch data for.
        measures (List[str]): List of measures to fetch (e.g., temperature, humidity).
        start_time (str): Start time for data retrieval.
        limit (int): Maximum number of records to fetch.

    Returns:
        Dict[str, Any]: Raw sensor data from the API, or an empty dictionary on failure.
    """
    with elasticapm.capture_span(name="fetch_sensor_data"):  # type: ignore
        logger.info(f"Fetching data for sensor_id: [{sensor_id}].")
        headers = create_headers(auth_token=access_token)
        body = {
            "sensors": [sensor_id],
            "limit": limit,
            "startTime": start_time,
            "measures": measures,
        }

        return make_api_request(url, headers, body)


# Database interaction functions
def get_sensor_timestamp(sensor_id: str) -> Optional[str]:
    """
    Retrieve the latest timestamp for a sensor from the database.

    Args:
        sensor_id (str): ID of the sensor.

    Returns:
        Optional[str]: Latest timestamp, or None if not found.
    """
    with elasticapm.capture_span(name="get_sensor_timestamp"):  # type: ignore
        logger.info(f"Fetching timestamp for sensor_id: [{sensor_id}].")
        with Session(engine) as session:
            result = session.exec(select(Sensor).where(Sensor.id == sensor_id)).first()
            return result.timestamp if result else None


def update_sensor_timestamp(sensor_id: str, timestamp: str) -> None:
    """
    Update the timestamp for a sensor in the database.

    Args:
        sensor_id (str): ID of the sensor.
        timestamp (str): New timestamp to save.
    """
    with elasticapm.capture_span(name="update_sensor_timestamp"):  # type: ignore
        logger.info( f"Updating timestamp in the database for sensor_id: [{sensor_id}] timestamp: [{timestamp}].")
        with Session(engine) as session:
            sensor = session.exec(
                select(Sensor).where(Sensor.id == sensor_id)
            ).one_or_none()
            if sensor:
                sensor.timestamp = timestamp
                session.add(sensor)
                session.commit()
            else:
                logger.info(f"Record for sensor_id: [{sensor_id}] not found in the database.")
                insert_sensor_record(sensor_id=sensor_id, timestamp=timestamp)


def insert_sensor_record(sensor_id: str, timestamp: str) -> None:
    """
    Insert a new sensor record into the database.

    Args:
        sensor (str): ID of the sensor.
        timestamp (str): Timestamp for the record.
    """
    with elasticapm.capture_span(name="insert_sensor_timestamp"):  # type: ignore
        logger.info(f"Inserting new record in the database for sensor_id: [{sensor_id}] timestamp: [{timestamp}].")
        with Session(engine) as session:
            new_record = Sensor(
                id=sensor_id,
                timestamp=timestamp,
            )
            session.add(new_record)
            session.commit()


# Formatting and Elasticsearch functions
def format_sensor_data(sensor_list: Dict[str, Any], sensor_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    with elasticapm.capture_span(name="format_sensor_data"):
        # Sensors can go offline, so not every API query will return data for
        # a given sensor. If no data is found, return an empty list.
        if not sensor_data or "sensors" not in sensor_data:
            logger.error("No sensor data found for formatting.")
            return []

        records = []
        current_datetime = datetime.datetime.now(datetime.timezone.utc)
        formatted_datetime = current_datetime.strftime('%Y-%m-%dT%H:%M:%S.000Z')

        for sensor_id, sensor_readings in sensor_data["sensors"].items():
            logger.info(f"Formatting data for sensor {sensor_id}.")
            for reading in sensor_readings:
                record = {}
                reading_hash = hashlib.sha256( json.dumps(reading, sort_keys=True).encode()).hexdigest()
                record = {
                    "hash": reading_hash,
                    "@timestamp": reading.get("observed"),
                    "message": reading,
                    "sensor.ingested": formatted_datetime,
                    "sensor.observed": reading.get("observed", None),
                    "sensor.name": sensor_list.get("name", None),
                    "sensor.id": sensor_id,
                    "sensor.description": sensor_list.get("description", None),
                    "sensor.gateways": reading.get("gateways", None),
                    "sensor.temperature": reading.get("temperature", None),
                    "sensor.humidity": reading.get("humidity", None),
                    "sensor.dewpoint": reading.get("dewpoint", None),
                    "sensor.barometric_pressure": reading.get(
                        "barometric_pressure", None
                    ),
                    "sensor.altitude": reading.get("altitude", None),
                }
                records.append(record)
        return records


def send_to_elasticsearch(
    es_client: Elasticsearch, records: List[Dict[str, Any]], index_name: str
) -> None:
    """
    Send sensor data to Elasticsearch for indexing.

    Args:
        es_client (Elasticsearch): Elasticsearch client instance.
        records (List[Dict[str, Any]]): Data records to index.
        index_name (str): Elasticsearch index name.
    """
    with elasticapm.capture_span(name="send_to_elasticsearch"):  # type: ignore
        logger.info( f"Sending [{len(records)}] records to Elasticsearch index [{index_name}].")
        success = 0

        try:
            for ok, action in streaming_bulk(
                client=es_client,
                actions=document_generator(records, index_name),
                raise_on_error=False,
            ):
                if not ok:
                    logger.error(f"Failed to index document: {action}")
                else:
                    success += 1

            logger.info(f"Successfully indexed [{success}] documents in Elasticsearch.")
        except (ConnectionError, TransportError, RequestError) as e:
            logger.error(f"Error during Elasticsearch indexing: {e}")


def document_generator(records: List[Dict[str, Any]], index_name: str) -> Generator[Dict[str, Any], None, None]:
    """
    Generate documents for bulk Elasticsearch indexing.

    Args:
        records (List[Dict[str, Any]]): Data records to index.
        index_name (str): Elasticsearch index name.

    Yields:
        Dict[str, Any]: Document for Elasticsearch indexing.
    """
    for record in records:
        yield {
            "_op_type": "create",
            "_index": index_name,
            "_id": record["hash"],
            "_source": record,
        }


# Main Execution Loop
def main():
    """
    Main script execution loop for processing SensorPush data.

    Steps:
        - Authenticate with SensorPush API.
        - Fetch sensor data.
        - Process and format data.
        - Index data into Elasticsearch.
    """

    create_db_and_tables()

    # Validate settings in settings.toml
    required_settings = [
        "INDEX_NAME",
        "AUTHENTICATE_URL",
        "AUTHORIZATION_URL",
        "DATA_URL",
        "DEFAULT_START_TIME",
        "APM_SERVICE_VERSION",
        "APM_ENVIRONMENT",
        "APM_SERVICE_NAME",
        "GATEWAY_URL",
        "SENSOR_URL",
        "LIMIT",
        "SLEEP_DURATION",
    ]
    missing_settings = [
        key
        for key in required_settings
        if key not in CFG["SETTINGS"] or not CFG["SETTINGS"][key]
    ]

    if missing_settings:
        logger.error("Missing configuration settings in app/config/settings.toml:")
        for setting in missing_settings:
            logger.error(f" - {setting}")
        sys.exit(1)

    # Validate secrets in .secrets.toml
    required_secrets = [
        "ES_USERNAME",
        "ES_PASSWORD",
        "ES_URL",
        "KB_URL",
        "APM_SECRET_TOKEN",
        "APM_SERVER_URL",
        "SENSORPUSH_EMAIL",
        "SENSORPUSH_PASSWORD",
    ]
    missing_secrets = [
        key
        for key in required_secrets
        if key not in CFG["SECRETS"] or not CFG["SECRETS"][key]
    ]

    if missing_secrets:
        logger.error("Missing configuration secrets in app/config/.secrets.toml:")
        for secret in missing_secrets:
            logger.error(f" - {secret}")
        sys.exit(1)

    # Initialize Elasticsearch client
    es_client = Elasticsearch(CFG["SECRETS"]["ES_URL"], basic_auth=(CFG["SECRETS"]["ES_USERNAME"], CFG["SECRETS"]["ES_PASSWORD"]),)

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
            "SERVER_URL": CFG["SECRETS"]["APM_SERVER_URL"],
            "SERVICE_NAME": CFG["SETTINGS"]["APM_SERVICE_NAME"],
            "SECRET_TOKEN": CFG["SECRETS"]["APM_SECRET_TOKEN"],
            "ENVIRONMENT": CFG["SETTINGS"]["APM_ENVIRONMENT"],
            "SERVICE_VERSION": CFG["SETTINGS"]["APM_SERVICE_VERSION"],
        }
    )

    elasticapm.instrument()  # type: ignore

    while True:
        apm_client.begin_transaction(transaction_type="script")
        authentication = authenticate_sensorpush(
            CFG["SETTINGS"]["AUTHENTICATE_URL"],
            CFG["SECRETS"]["SENSORPUSH_EMAIL"],
            CFG["SECRETS"]["SENSORPUSH_PASSWORD"],
        )

        authorization = authorize_sensorpush( CFG["SETTINGS"]["AUTHORIZATION_URL"], authentication)

        if authorization:
            for sensor in CFG["SENSORS"]:
                logger.info( f"Processing data for sensor_id: [{sensor['id']}] sensor_name: [{sensor['name']}].")
                timestamp = ( get_sensor_timestamp(sensor["id"]) or CFG["SETTINGS"]["DEFAULT_START_TIME"])
                logger.info( f"Last timestamp for sensor_id: [{sensor['id']}]: [{timestamp}].")

                raw_data = fetch_sensor_data(
                    url=CFG["SETTINGS"]["DATA_URL"],
                    access_token=authorization,
                    sensor_id=sensor["id"],
                    measures=["temperature", "humidity", "dewpoint", "barometric_pressure", "altitude"],
                    start_time=timestamp,
                    limit=CFG["SETTINGS"]["LIMIT"],
                )

                if raw_data:
                    formatted_data = format_sensor_data(sensor, raw_data)
                    if formatted_data:
                        update_sensor_timestamp( sensor_id=sensor["id"], timestamp=formatted_data[0]["sensor.observed"],)  # most recent timestamp is the first record
                        send_to_elasticsearch(es_client, formatted_data, CFG["SETTINGS"]["INDEX_NAME"])
                    else:
                        logger.error(f"No formated data found for sensor_id: [{sensor['id']}].")
                else:
                    logger.error(f"No raw data found for sensor_id: [{sensor['id']}].")

        else:
            logger.error("Authorization failed. Skipping data processing.")
            apm_client.end_transaction(__name__, result="failure")
        apm_client.end_transaction(__name__, result="success")

        logger.info(f"Sleeping for {CFG['SETTINGS']['SLEEP_DURATION']} seconds.")
        time.sleep(int(CFG["SETTINGS"]["SLEEP_DURATION"]))


# Configure logging at module level so it's accessible globally
configure_logging()

# Create the logger for the application
logger = logging.getLogger("python-sensorpush")
logger.info("Logging configured successfully!")

if __name__ == "__main__":
    main()
