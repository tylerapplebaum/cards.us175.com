#!/bin/bash

# === Configuration ===
export TABLE_NAME="us175-inventory-3"
export ERROR_LOG="update_errors.log"
export OLD_VALUE="Heritage High Number"
export NEW_VALUE="Topps Heritage High Number"
export FILE_NAME="scan_output.json"
export ATTR_NAME="Set"
export ATTR_ALIAS="#s"
export VALUE_ALIAS=":oldval"

# === Step 1: Scan for matching items ===
echo "Scanning table $TABLE_NAME for items where $ATTR_NAME = \"$OLD_VALUE\"..."
aws dynamodb scan \
  --table-name "$TABLE_NAME" \
  --filter-expression "$ATTR_ALIAS = $VALUE_ALIAS" \
  --expression-attribute-names "{\"$ATTR_ALIAS\": \"$ATTR_NAME\"}" \
  --expression-attribute-values "{\"$VALUE_ALIAS\": {\"S\": \"$OLD_VALUE\"}}" \
  --projection-expression "guid" \
  --output json > "$FILE_NAME"

if [ $? -ne 0 ]; then
  echo "❌ Scan failed. Exiting."
  exit 1
fi
echo "✅ Scan complete. Results saved to $FILE_NAME."

# === Step 2: Update items in parallel ===
echo "Starting parallel updates..."

# Clear previous error log
> "$ERROR_LOG"

cat "$FILE_NAME" | jq -r '.Items[].guid.S' | \
xargs -P 4 -n 1 -I {} bash -c '
  guid="$1"
  echo "🔄 Updating item with guid: $guid"

  aws dynamodb update-item \
    --table-name "$2" \
    --key "{\"guid\": {\"S\": \"$guid\"}}" \
    --update-expression "SET #s = :newval" \
    --condition-expression "#s = :expectedval" \
    --expression-attribute-names "{\"#s\": \"Set\"}" \
    --expression-attribute-values "{
      \":newval\": {\"S\": \"$3\"},
      \":expectedval\": {\"S\": \"$4\"}
    }" \
    >/dev/null \
    || echo "❌ Failed to update guid: $guid" >> "$5"
' _ {} "$TABLE_NAME" "$NEW_VALUE" "$OLD_VALUE" "$ERROR_LOG"

echo "✅ Update process complete."
echo "Check $ERROR_LOG for any failed updates."

