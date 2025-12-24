#!/bin/bash

TABLE_NAME="us175-inventory-3"

echo "Scanning table for MM/DD/YYYY TxnDate values..."

aws dynamodb scan \
  --table-name "$TABLE_NAME" \
  --projection-expression "guid, TxnDate" \
  --filter-expression "attribute_exists(TxnDate)" \
  --output json |
jq -r '
  .Items[]
  | select(.TxnDate.S | test("^[0-9]{2}/[0-9]{2}/[0-9]{4}$"))
  | [.guid.S, .TxnDate.S]
  | @tsv
' |
while IFS=$'\t' read -r guid old_date; do
  # Convert MM/DD/YYYY -> YYYY-MM-DD
  new_date=$(date -d "$old_date" +"%Y-%m-%d" 2>/dev/null)

  if [[ -z "$new_date" ]]; then
    echo "Skipping invalid date: $old_date (GUID: $guid)"
    continue
  fi

  echo "Updating GUID $guid: $old_date -> $new_date"

  aws dynamodb update-item \
    --table-name "$TABLE_NAME" \
    --key "{\"guid\": {\"S\": \"$guid\"}}" \
    --update-expression "SET TxnDate = :newDate" \
    --expression-attribute-values "{
      \":newDate\": {\"S\": \"$new_date\"}
    }" \
    >/dev/null
done

echo "Done."

