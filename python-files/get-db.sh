#!/bin/bash

for endpoint in "modes" "satellites" "transmitters"; do
    wget -O - "https://db.satnogs.org/api/$endpoint/?format=json" \
        | jq '.' > "db-$endpoint.json"
done

