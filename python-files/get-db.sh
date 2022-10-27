#!/bin/bash


declare -A endpoints

#  ep["name"]="sort_key"
endpoints["tle"]=".sat_id"
endpoints["modes"]=".id"
endpoints["satellites"]=".sat_id"
endpoints["transmitters"]=".uuid"

for endpoint in ${!endpoints[@]}; do
    echo "$endpoint - ${endpoints[$endpoint]}"
    wget -O - "https://db.satnogs.org/api/$endpoint/?format=json" \
        | jq "sort_by(${endpoints[$endpoint]})" > "db-$endpoint.json"
done

