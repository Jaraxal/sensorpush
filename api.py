import logging
from typing import Any

import requests

logger = logging.getLogger()


def create_headers(auth_token: str | None = None) -> dict[str, str]:
    headers = {"content-type": "application/json", "accept": "application/json"}
    if auth_token:
        headers["Authorization"] = auth_token
    return headers


def make_api_request(url: str, headers: dict[str, str], body: dict[str, Any]) -> dict[str, Any]:
    try:
        response = requests.post(url=url, json=body, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Request to {url} failed: {e}")
        return {}


def authenticate_sensorpush(url: str, email: str, password: str) -> str | None:
    logger.info("Authenticating with SensorPush API.")
    headers = create_headers()
    body = {"email": email, "password": password}
    response = make_api_request(url, headers, body)
    return response.get("authorization")


def authorize_sensorpush(url: str, authentication: str | None) -> str | None:
    logger.info("Authorizing with SensorPush API.")

    if not authentication:
        logger.error("Invalid authentication!")
        return None

    headers = create_headers()
    body = {"authorization": authentication}
    response = make_api_request(url, headers, body)
    return response.get("accesstoken")


def fetch_sensor_data( url: str, access_token: str, sensor_id: str, measures: list[str], start_time: str, limit: int,) -> dict[str, Any]:
    logger.info(f"Fetching data for sensor_id: [{sensor_id}].")
    headers = create_headers(auth_token=access_token)
    body = {
        "sensors": [sensor_id],
        "limit": limit,
        "startTime": start_time,
        "measures": measures,
    }

    return make_api_request(url, headers, body)
