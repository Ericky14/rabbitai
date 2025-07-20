#!/bin/bash

GRAFANA_URL="http://localhost:3001"
GRAFANA_USER="admin"
GRAFANA_PASS="admin123"

echo "Importing dashboards to Grafana..."

# Wait for Grafana to be ready
echo "Waiting for Grafana to be ready..."
until curl -s -f -u $GRAFANA_USER:$GRAFANA_PASS $GRAFANA_URL/api/health > /dev/null; do
    echo "Waiting for Grafana..."
    sleep 2
done

echo "Grafana is ready!"

# Import each dashboard
for dashboard_file in monitoring/grafana/dashboards/*.json; do
    if [ -f "$dashboard_file" ]; then
        echo "Importing $(basename $dashboard_file)..."
        
        # Wrap the dashboard JSON in the required format
        dashboard_json=$(cat "$dashboard_file")
        import_payload=$(echo '{}' | jq --argjson dashboard "$dashboard_json" '.dashboard = $dashboard | .overwrite = true')
        
        response=$(curl -s -X POST \
            -H "Content-Type: application/json" \
            -u $GRAFANA_USER:$GRAFANA_PASS \
            -d "$import_payload" \
            $GRAFANA_URL/api/dashboards/db)
        
        echo "Response: $response"
    fi
done

echo "Dashboard import complete!"
echo "Available dashboards:"
curl -s -u $GRAFANA_USER:$GRAFANA_PASS $GRAFANA_URL/api/search | jq '.[] | {title: .title, uid: .uid}'