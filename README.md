# Python Sensorpush Application

Example Python application that uses the SensorPush API, Elastic Cloud with Elastic APM

## Configuration

Before running the app you must update the `config/settings.toml` and `aonfig/.secrets.toml` configuration files.

### config/settings.toml

The `settings.toml` configuration file should have the following configuration settings defined, as appropriate, for your
environment.

```toml
# Elastic configuration
INDEX_NAME = "sensorpush"
DELETE_INDEX = false

# APM Configuration
APM_SERVICE_VERSION = "2.0"
APM_ENVIRONMENT = "Production"
APM_SERVICE_NAME = "python-sensorpush"

# SensorPush Configuration
DEFAULT_START_TIME = "2024-12-01T00:00:00.000Z"
AUTHENTICATE_URL = "https://api.sensorpush.com/api/v1/oauth/authorize"
AUTHORIZATION_URL = "https://api.sensorpush.com/api/v1/oauth/accesstoken"
GATEWAY_URL = "https://api.sensorpush.com/api/v1/devices/gateways"
SENSOR_URL = "https://api.sensorpush.com/api/v1/devices/sensors"
DATA_URL = "https://api.sensorpush.com/api/v1/samples"
LIMIT = 500
SLEEP_DURATION = 60

# Sensor Configuration
[[SENSORS]]
id = "16786480.31759915751390790374"
name = "sensor1"
description = "Back Outdoor Sensor"
```

For each SensorPush sensor you have, you should add them to `config/settings.toml`.  For example, two sensors would look
like this in the configuration.

```toml
# Sensor Configuration
[[SENSORS]]
id = "16786480.31759915751390790374"
name = "sensor1"
description = "Back Outdoor Sensor"

[[SENSORS]]
id = "16785468.27282632252927060817"
name = "sensor2"
description = "Office Sensor"
```

### config/.secrets.toml

The `.secrets.toml` configuration file should have the following configuration settings defined, as appropriate, for your
environment.

```toml
# Elastic Server Configuration
ES_USERNAME = "YOUR ELASTICSEARCH USERNAME"
ES_PASSWORD = "YOUR ELASTICSEARCH PASSWORD"
ES_URL = "YOUR ELASTICSEARCH SERVER URL - https://localhost:9200"
KB_URL = "YOUR KIBANA SERVER URL - https://localhost:5601"

# APM Configuration
APM_SECRET_TOKEN = "YOUR ELASTIC APM SECRET TOKEN"
APM_SERVER_URL = "YOUR ELASTIC APM SERVER URL - https://localhost:8201"

# App Configuration
SENSORPUSH_EMAIL = "YOUR SENSORPUSH EMAIL"
SENSORPUSH_PASSWORD = "YOUR SENSORPUSH PASSWORD"
```
