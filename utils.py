import datetime
import hashlib
import json
import logging
from typing import Any

logger = logging.getLogger()


def format_sensor_data(sensor_list: dict[str, Any], sensor_data: dict[str, Any]) -> list[dict[str, Any]]:
    # Sensors can go offline, so not every API query will return data for
    # a given sensor. If no data is found, return an empty list.
    if not sensor_data or "sensors" not in sensor_data:
        logger.error("No sensor data found for formatting.")
        return []

    records = []
    current_datetime = datetime.datetime.now(datetime.UTC)
    formatted_datetime = current_datetime.strftime("%Y-%m-%dT%H:%M:%S.000Z")

    for sensor_id, sensor_readings in sensor_data["sensors"].items():
        logger.info(f"Formatting data for sensor {sensor_id}.")
        for reading in sensor_readings:
            record = {}
            reading_hash = hashlib.sha256(json.dumps(reading, sort_keys=True).encode()).hexdigest()
            record = {
                "hash": reading_hash,
                "@timestamp": reading.get("observed"),
                "message": reading,
                "sensor.ingested": formatted_datetime,
                "sensor.observed": reading.get("observed", None),
                "sensor.name": sensor_list.get("name"),
                "sensor.id": sensor_id,
                "sensor.description": sensor_list.get("description"),
                "sensor.gateways": reading.get("gateways", None),
                "sensor.temperature": reading.get("temperature", None),
                "sensor.humidity": reading.get("humidity", None),
                "sensor.dewpoint": reading.get("dewpoint", None),
                "sensor.barometric_pressure": reading.get("barometric_pressure", None),
                "sensor.altitude": reading.get("altitude", None),
            }
            records.append(record)
    return records
