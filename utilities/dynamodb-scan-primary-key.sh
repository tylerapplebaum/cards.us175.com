#!/bin/bash
# Retrieve all primary keys from a table and save one per line.

# === Configuration ===
export TABLE_NAME="us175-price-archive"
export FILE_NAME="archive_ids.txt"
export PRIMARY_KEY="ArchiveId"

echo "Scanning table $TABLE_NAME for items ..."
aws dynamodb scan \
  --table-name "$TABLE_NAME" \
  --projection-expression "$PRIMARY_KEY" \
  --query "Items[].$PRIMARY_KEY.S" \
  --output text | tr '\t' '\n' > "$FILE_NAME"

if [ ${PIPESTATUS[0]} -ne 0 ]; then
  echo "❌ Scan failed. Exiting."
  exit 1
fi
echo "✅ Scan complete. Results saved to $FILE_NAME."
