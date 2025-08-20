#Set values
export TABLE_NAME="us175-inventory-3"
export ERROR_LOG="update_errors.log"
export OLD_VALUE="Heritage High Number"
export NEW_VALUE="Topps Heritage High Number"
export FILE_NAME="scan_output.json"
export ATTR_NAME="Set"
export ATTR_ALIAS="#s"
export VALUE_ALIAS=":oldval"

# Gather the guid for all items with the Set property that has "Heritage" as a value.
aws dynamodb scan \
  --table-name "$TABLE_NAME" \
  --filter-expression "$ATTR_ALIAS = $VALUE_ALIAS" \
  --expression-attribute-names "{\"$ATTR_ALIAS\": \"$ATTR_NAME\"}" \
  --expression-attribute-values "{\"$VALUE_ALIAS\": {\"S\": \"$OLD_VALUE\"}}" \
  --projection-expression "guid" \
  --output json > "$FILE_NAME"

# Clear error log before starting
> "$ERROR_LOG"
# Use that output to update Set to "Topps Heritage" in parallel
cat $FILE_NAME | jq -r '.Items[].guid.S' | \
xargs -P 4 -n 1 -I {} bash -c '
  guid="{}"
  echo "Updating item with guid: $guid"

  aws dynamodb update-item \
    --table-name "$TABLE_NAME" \
    --key "{\"guid\": {\"S\": \"$guid\"}}" \
    --update-expression "SET #s = :newval" \
    --condition-expression "#s = :expectedval" \
    --expression-attribute-names "{\"#s\": \"Set\"}" \
    --expression-attribute-values "{
      \":newval\": {\"S\": \"$NEW_VALUE\"},
      \":expectedval\": {\"S\": \"$OLD_VALUE\"}
    }" \
    >/dev/null \
    || echo "❌ Failed to update guid: $guid" >> "$ERROR_LOG"
'
