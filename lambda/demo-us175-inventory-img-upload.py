import os
import json
import logging
import base64
import boto3
from botocore.exceptions import ClientError

s3 = boto3.client("s3")

logger = logging.getLogger()
logger.setLevel(logging.INFO)

bucketName = os.environ.get("bucketName")
imagePath = (os.environ.get("imagePath") or "").strip("/")  # allow blank


def _response(status, body_obj):
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body_obj),
    }


def _get_body(event):
    raw = event.get("body") or ""
    if event.get("isBase64Encoded"):
        raw = base64.b64decode(raw).decode("utf-8")
    return raw


def _key(name):
    return f"{imagePath}/{name}" if imagePath else name


def lambda_handler(event, context):
    if not bucketName:
        return _response(500, {"ok": False, "error": "Missing env var bucketName"})

    try:
        body = json.loads(_get_body(event) or "{}")
    except Exception as e:
        logger.exception("Invalid JSON")
        return _response(400, {"ok": False, "error": "Invalid JSON body", "detail": str(e)})

    guid = str(body.get("guid") or "").strip()
    files = body.get("files") or []

    if not guid:
        return _response(400, {"ok": False, "error": "Missing required field: guid"})
    if not isinstance(files, list):
        return _response(400, {"ok": False, "error": "files must be an array"})

    # Map incoming by side
    by_side = {}
    errors = []

    for i, f in enumerate(files):
        if not isinstance(f, dict):
            errors.append({"index": i, "error": "Each files[] item must be an object"})
            continue

        side = str(f.get("side") or "").strip().lower()
        if side not in ("front", "back"):
            errors.append({"index": i, "error": "files[].side must be 'front' or 'back'"})
            continue

        data_b64 = f.get("dataBase64") or ""
        if not data_b64:
            errors.append({"index": i, "side": side, "error": "Missing dataBase64"})
            continue

        content_type = str(f.get("contentType") or "image/webp").strip()
        by_side[side] = {"b64": data_b64, "contentType": content_type}

    if not by_side:
        return _response(400, {
            "ok": False,
            "error": "At least one valid front or back image is required",
            "receivedSides": sorted(list(by_side.keys())),
            "errors": errors
        })

    uploaded = []

    for side in sorted(by_side.keys()):
        filename = f"{guid}-{side}.webp"
        key = _key(filename)

        try:
            img_bytes = base64.b64decode(by_side[side]["b64"], validate=True)
        except Exception as e:
            errors.append({"side": side, "error": "Invalid base64", "detail": str(e)})
            continue

        if len(img_bytes) < 200:
            errors.append({"side": side, "error": "Image too small / likely invalid"})
            continue

        try:
            s3.put_object(
                Bucket=bucketName,
                Key=key,
                Body=img_bytes,
                ContentType=by_side[side]["contentType"] or "image/webp",
                Metadata={"guid": guid, "side": side},
            )
            uploaded.append({"side": side, "key": key, "bytes": len(img_bytes)})
        except ClientError as e:
            logger.exception("S3 put_object failed")
            errors.append({"side": side, "error": "S3 put_object failed", "detail": str(e)})

    if errors:
        return _response(400, {"ok": False, "uploaded": uploaded, "errors": errors})

    return _response(200, {"ok": True, "guid": guid, "uploaded": uploaded})
