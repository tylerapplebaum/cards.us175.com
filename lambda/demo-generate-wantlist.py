import json
import logging
import os
import re
from datetime import datetime, timezone
from decimal import Decimal

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

REGION = os.environ.get("RegionName", "us-east-2")
TABLE_NAME = os.environ.get("TableName", "us175-inventory-3")
OUTPUT_BUCKET = os.environ.get("OutputBucket", "dev.txn.us175.com")
OUTPUT_KEY = os.environ.get("OutputKey", "Inventory/wantlist/wantlist.json")

dynamodb = boto3.resource("dynamodb", region_name=REGION)
table = dynamodb.Table(TABLE_NAME)
s3_client = boto3.client("s3", region_name=REGION)


def normalize_for_json(value):
    if isinstance(value, dict):
        return {k: normalize_for_json(v) for k, v in value.items()}
    if isinstance(value, list):
        return [normalize_for_json(v) for v in value]
    if isinstance(value, set):
        return [normalize_for_json(v) for v in value]
    if isinstance(value, Decimal):
        return int(value) if value == value.to_integral_value() else float(value)
    return value


def natural_key(value):
    text = "" if value is None else str(value)
    return [int(chunk) if chunk.isdigit() else chunk.lower() for chunk in re.split(r"(\d+)", text)]


def qty_is_zero(value):
    if value is None:
        return False
    if isinstance(value, Decimal):
        return value == 0
    if isinstance(value, (int, float)):
        return float(value) == 0.0
    text = str(value).strip()
    if not text:
        return False
    try:
        return Decimal(text) == 0
    except Exception:
        return False


def scan_all_inventory_items():
    items = []
    last_evaluated_key = None

    projection = (
        "guid, #Y, #S, Subset, CardNum, PlayerName, Qty, "
        "SerialNumber, Authenticator, Grade, CertNumber, BoxNum, "
        "PurchasePrice, GradingFee, MktVal, TxnSource"
    )

    while True:
        scan_kwargs = {
            "ProjectionExpression": projection,
            "ExpressionAttributeNames": {"#Y": "Year", "#S": "Set"},
        }
        if last_evaluated_key:
            scan_kwargs["ExclusiveStartKey"] = last_evaluated_key

        response = table.scan(**scan_kwargs)
        items.extend(response.get("Items", []))
        last_evaluated_key = response.get("LastEvaluatedKey")
        if not last_evaluated_key:
            break

    return items


def sort_wantlist(items):
    def _year(value):
        try:
            return int(str(value))
        except Exception:
            return 0

    return sorted(
        items,
        key=lambda item: (
            -_year(item.get("Year")),
            natural_key(item.get("Set")),
            natural_key(item.get("Subset")),
            natural_key(item.get("CardNum")),
            natural_key(item.get("PlayerName")),
        ),
    )


def lambda_handler(event, context):
    logger.info("Generating wantlist from table: %s", TABLE_NAME)
    write_to_s3 = True if event is None else event.get("writeToS3", True)

    items = scan_all_inventory_items()
    wantlist_items = [item for item in items if qty_is_zero(item.get("Qty"))]
    wantlist_items = sort_wantlist(wantlist_items)
    wantlist_items = normalize_for_json(wantlist_items)

    payload = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "count": len(wantlist_items),
        "items": wantlist_items,
    }

    if write_to_s3:
        s3_client.put_object(
            Bucket=OUTPUT_BUCKET,
            Key=OUTPUT_KEY,
            Body=json.dumps(payload).encode("utf-8"),
            ContentType="application/json",
            CacheControl="max-age=300",
        )
        logger.info("Wrote wantlist to s3://%s/%s", OUTPUT_BUCKET, OUTPUT_KEY)

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(
            {
                "message": "Wantlist generated",
                "outputBucket": OUTPUT_BUCKET,
                "outputKey": OUTPUT_KEY,
                "count": payload["count"],
            }
        ),
    }
