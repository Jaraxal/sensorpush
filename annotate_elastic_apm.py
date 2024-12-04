import argparse
import json
import sys
from datetime import datetime, timezone

import requests
from app.config import config as CFG


def main():
    # Validate the configuration
    missing_config = False

    for secrets in ("ES_USERNAME", "ES_PASSWORD"):
        if secrets not in CFG["SECRETS"].keys() and not CFG["SECRETS"][secrets]:
            print(f"{secrets} is not set in app/config/.secrets.toml!")
            missing_config = True

    for settings in (
        "KB_URL",
        "APM_SERVICE_NAME",
        "APM_SERVICE_VERSION",
        "APM_ENVIRONMENT",
    ):
        if settings not in CFG["SETTINGS"].keys() and not CFG["SETTINGS"][settings]:
            print(f"{settings} is not set in app/config/settings.toml!")
            missing_config = True

    if missing_config:
        sys.exit(1)

    # Prepare request
    url = f"{CFG['SETTINGS']['KB_URL']}/api/apm/services/{CFG['SETTINGS']['APM_SERVICE_NAME']}/annotation"

    header = {
        "Content-Type": "application/json",
        "kbn-xsrf": "true",
    }

    if args.message:
        message = f"{CFG['SETTINGS']['APM_SERVICE_VERSION']} - {args.message}"
    else:
        message = f"{CFG['SETTINGS']['APM_SERVICE_VERSION']}"

    data = {
        "@timestamp": formatted_date,
        "service": {
            "version": CFG["SETTINGS"]["APM_SERVICE_VERSION"],
            "environment": CFG["SETTINGS"]["APM_ENVIRONMENT"],
        },
        "message": f"{message}",
    }

    # Annonate the APM service
    response = requests.post(
        url,
        headers=header,
        data=json.dumps(data),
        auth=(CFG["SECRETS"]["ES_USERNAME"], CFG["SECRETS"]["ES_PASSWORD"]),
    )

    print(response.json())


if __name__ == "__main__":
    # Initialize parser
    parser = argparse.ArgumentParser()

    # Adding optional argument
    parser.add_argument(
        "-m", "--message", help="Short message to be displayed for APM annotation"
    )

    # Read arguments from command line
    args = parser.parse_args()

    # Get the current date and time in UTC
    now = datetime.now(timezone.utc)

    # Format the date and time as desired
    formatted_date = now.strftime("%Y-%m-%dT%H:%M:%SZ")

    main()
