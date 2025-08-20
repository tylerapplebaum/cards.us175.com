#!/bin/bash

# File containing ArchiveId values, one per line
input_file="archive_ids.txt"

# Check if the input file exists
if [ ! -f "$input_file" ]; then
    echo "Error: Input file $input_file not found."
    exit 1
fi

# Read ArchiveId values from the file and process each one
while IFS= read -r id || [[ -n "$id" ]]; do
    # Remove any leading/trailing whitespace
    id=$(echo "$id" | xargs)
    
    # Skip empty lines
    if [ -z "$id" ]; then
        continue
    fi

    echo "Processing ArchiveId: $id"
    
    aws dynamodb update-item \
        --table-name us175-price-archive \
        --key "{\"ArchiveId\": {\"S\": \"$id\"}}" \
        --update-expression "REMOVE #t" \
        --expression-attribute-names '{"#t": "Type"}' \
        --return-values ALL_NEW

    echo "Completed processing for ArchiveId: $id"
    echo "----------------------------------------"
done < "$input_file"

echo "All ArchiveIds processed."


