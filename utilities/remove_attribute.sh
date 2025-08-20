#!/bin/bash

# === Configuration ===
export TABLE_NAME="us175-inventory-3"
export OUTPUT_FILE="scan_for_removal.json"
export ERROR_LOG="remove_attribute_errors.log"
export ATTR_TO_REMOVE="Brand"
export PARTITION_KEY="guid"

# === Step 1: Scan table to get all partition key values ===
echo "📦 Scanning table $TABLE_NAME for all items..."
aws dynamodb scan \
  --table-name "$TABLE_NAME" \
  --projection-expression "$PARTITION_KEY" \
  --output json > "$OUTPUT_FILE"

if [ $? -ne 0 ]; then
  echo "❌ Scan failed. Exiting."
  exit 1
fi

echo "✅ Scan complete. Results saved to $OUTPUT_FILE."
echo "jq '.Count' $OUTPUT_FILE"
# === Step 2: Remove the specified attribute from each item ===
echo "🧹 Removing attribute '$ATTR_TO_REMOVE' from each item..."
> "$ERROR_LOG"

cat "$OUTPUT_FILE" | jq -r ".Items[].$PARTITION_KEY.S" | \
xargs -P 4 -n 1 -I {} bash -c '
  key="$1"
  echo "🔧 Removing $3 from item with $2: $key"

  aws dynamodb update-item \
    --table-name "$4" \
    --key "{\"$2\": {\"S\": \"$key\"}}" \
    --update-expression "REMOVE $3" \
    >/dev/null \
    || echo "❌ Failed to remove $3 from $2=$key" >> "$5"
' _ {} "$PARTITION_KEY" "$ATTR_TO_REMOVE" "$TABLE_NAME" "$ERROR_LOG"

echo "✅ Attribute removal complete. Check $ERROR_LOG for any errors."

