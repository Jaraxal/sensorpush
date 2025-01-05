#!/bin/sh

# Path to the environment file
ENV_FILE="../config/.env"

# Check if the file exists
if [ ! -f "$ENV_FILE" ]; then
    echo "Error: File '$ENV_FILE' does not exist."
    exit 1
fi

# Load environment variables from the file
export $(grep -v '^#' "$ENV_FILE" | xargs)

echo "Environment variables loaded successfully."

curl -X PUT --user $ELASTIC_SERVER_USERNAME:$ELASTIC_SERVER_PASSWORD "$ELASTIC_SERVER_URL/_component_template/sensorpush-mappings?pretty" -H 'Content-Type: application/json' -d @sensorpush_index_mappings.json

echo "Uploading component template: setttings"
curl -X PUT --user $ELASTIC_SERVER_USERNAME:$ELASTIC_SERVER_PASSWORD "$ELASTIC_SERVER_URL/_component_template/sensorpush-settings?pretty" -H 'Content-Type: application/json' -d @sensorpush_index_settings.json

echo "Uploading index template"
curl -X PUT --user $ELASTIC_SERVER_USERNAME:$ELASTIC_SERVER_PASSWORD "$ELASTIC_SERVER_URL/_index_template/sensorpush?pretty" -H 'Content-Type: application/json' -d @sensorpush_index_template.json

echo "Uploading ILM policy"
curl -X PUT --user $ELASTIC_SERVER_USERNAME:$ELASTIC_SERVER_PASSWORD "$ELASTIC_SERVER_URL/_ilm/policy/sensorpush?pretty" -H 'Content-Type: application/json' -d @sensorpush_lifecycle_policy.json

echo "Creating data stream"
curl -X PUT --user $ELASTIC_SERVER_USERNAME:$ELASTIC_SERVER_PASSWORD "$ELASTIC_SERVER_URL/_data_stream/sensorpush?pretty"
