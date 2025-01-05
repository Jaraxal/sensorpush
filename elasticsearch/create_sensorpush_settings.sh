#!/bin/bash

# Load environment variables from file
export $(egrep -v '^#' ../app/env | xargs)

curl -X PUT --user $ELASTIC_SERVER_USERNAME:$ELASTIC_SERVER_PASSWORD "$ELASTIC_SERVER_URL/_component_template/sensorpush-mappings?pretty" -H 'Content-Type: application/json' -d @sensorpush_index_mappings.json

echo "Uploading component template: setttings"
curl -X PUT --user $ELASTIC_SERVER_USERNAME:$ELASTIC_SERVER_PASSWORD "$ELASTIC_SERVER_URL/_component_template/sensorpush-settings?pretty" -H 'Content-Type: application/json' -d @sensorpush_index_settings.json

echo "Uploading index template"
curl -X PUT --user $ELASTIC_SERVER_USERNAME:$ELASTIC_SERVER_PASSWORD "$ELASTIC_SERVER_URL/_index_template/sensorpush?pretty" -H 'Content-Type: application/json' -d @sensorpush_index_template.json

echo "Uploading ILM policy"
curl -X PUT --user $ELASTIC_SERVER_USERNAME:$ELASTIC_SERVER_PASSWORD "$ELASTIC_SERVER_URL/_ilm/policy/sensorpush?pretty" -H 'Content-Type: application/json' -d @sensorpush_lifecycle_policy.json

echo "Creating data stream"
curl -X PUT --user $ELASTIC_SERVER_USERNAME:$ELASTIC_SERVER_PASSWORD "$ELASTIC_SERVER_URL/_data_stream/sensorpush?pretty"
