#!/bin/bash

# File containing guid values, one per line
input_file="guids.txt"
table_name="us175-inventory-3"

# Check if the input file exists
if [ ! -f "$input_file" ]; then
    echo "Error: Input file $input_file not found."
    exit 1
fi

while IFS= read -r id || [[ -n "$id" ]]; do
    id=$(echo "$id" | xargs)
    [[ -z "$id" ]] && continue

    echo "Processing guid: $id"

    # Fetch the current PlayerName string
    playername=$(aws dynamodb get-item \
        --table-name "$table_name" \
        --key "{\"guid\": {\"S\": \"$id\"}}" \
        --projection-expression "PlayerName" \
        --query "Item.PlayerName.S" \
        --output text 2>/dev/null)

    # Skip if no PlayerName
    if [ "$playername" == "None" ] || [ -z "$playername" ]; then
        echo "⚠️ No PlayerName found for guid: $id"
        echo "----------------------------------------"
        continue
    fi

    echo "  Current PlayerName: '$playername'"

    # Split by comma into array
    IFS=',' read -ra names <<< "$playername"

    # Build JSON string set for DynamoDB
    ss_json="{\"SS\": ["
    first=true
    for name in "${names[@]}"; do
        trimmed=$(echo "$name" | xargs)
        if [ -n "$trimmed" ]; then
            if [ "$first" = true ]; then
                first=false
            else
                ss_json+=", "
            fi
            ss_json+="\"$trimmed\""
        fi
    done
    ss_json+="]}"

    echo "  Converting to StringSet: $ss_json"

    # Backup the original PlayerName string
    aws dynamodb update-item \
        --table-name "$table_name" \
        --key "{\"guid\": {\"S\": \"$id\"}}" \
        --update-expression "SET PlayerName_raw = :backup" \
        --expression-attribute-values "{\":backup\": {\"S\": \"$playername\"}}" \
        --return-values NONE > /dev/null

    # Replace PlayerName with StringSet
    aws dynamodb update-item \
        --table-name "$table_name" \
        --key "{\"guid\": {\"S\": \"$id\"}}" \
        --update-expression "SET PlayerName = :playername" \
        --expression-attribute-values "{\":playername\": $ss_json}" \
        --return-values UPDATED_NEW > /dev/null

    echo "✅ Converted and backed up PlayerName for guid: $id"
    echo "----------------------------------------"

done < "$input_file"

echo "🎉 All guids processed safely."

