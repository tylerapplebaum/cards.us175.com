#!/bin/bash

# DynamoDB configuration
TABLE_NAME="us175-inventory-3"
REGION="us-east-2"
INPUT_FILE="multiplayer-guids.txt"

# Check input file
if [ ! -f "$INPUT_FILE" ]; then
    echo "Error: Input file $INPUT_FILE not found."
    exit 1
fi

# Process each guid
while IFS= read -r guid; do
    # skip empty lines
    if [ -z "$guid" ]; then
        continue
    fi

    echo "Processing item: $guid"

    # 1️⃣ Get the existing PlayerName value
    PLAYER_NAME=$(aws dynamodb get-item \
        --region "$REGION" \
        --table-name "$TABLE_NAME" \
        --key "{\"guid\": {\"S\": \"$guid\"}}" \
        --projection-expression "PlayerName" \
        --query "Item.PlayerName.S" \
        --output text 2>/dev/null)

    if [ -z "$PLAYER_NAME" ] || [ "$PLAYER_NAME" == "None" ]; then
        echo "  ⚠️  No PlayerName found for $guid — skipping."
        continue
    fi

    # 2️⃣ Split by commas into a bash array
    IFS=',' read -ra NAMES_ARRAY <<< "$PLAYER_NAME"

    # Trim whitespace around names
    for i in "${!NAMES_ARRAY[@]}"; do
        NAMES_ARRAY[$i]=$(echo "${NAMES_ARRAY[$i]}" | xargs)
    done

    # 3️⃣ Convert array to JSON string set for AWS CLI
    PLAYER_NAMES_JSON=$(printf '"%s",' "${NAMES_ARRAY[@]}")
    PLAYER_NAMES_JSON="[${PLAYER_NAMES_JSON%,}]"

    # 4️⃣ Compute NumPlayers
    NUM_PLAYERS=${#NAMES_ARRAY[@]}

    echo "  PlayerNames: ${NAMES_ARRAY[*]}"
    echo "  NumPlayers:  $NUM_PLAYERS"

    # 5️⃣ Update the item in DynamoDB
    aws dynamodb update-item \
        --region "$REGION" \
        --table-name "$TABLE_NAME" \
        --key "{\"guid\": {\"S\": \"$guid\"}}" \
        --update-expression "SET PlayerNames = :p, NumPlayers = :n" \
        --expression-attribute-values "{
            \":p\": {\"SS\": $PLAYER_NAMES_JSON},
            \":n\": {\"N\": \"$NUM_PLAYERS\"}
        }" \
        --return-values "UPDATED_NEW" >/dev/null

    echo "  ✅ Updated $guid"

done < "$INPUT_FILE"

