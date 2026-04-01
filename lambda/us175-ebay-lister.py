import os
import json
import base64
import logging
import decimal
import re
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from urllib import request, parse, error

import boto3
from botocore.exceptions import ClientError


logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWS clients/resources
secrets_client = boto3.client("secretsmanager", region_name=os.environ["EBAY_SECRET_REGION"])
ddb = boto3.resource("dynamodb")
table = ddb.Table(os.environ["DDB_TABLE"])

# Environment
DDB_TABLE = os.environ["DDB_TABLE"]
EBAY_SECRET_NAME = os.environ["EBAY_SECRET_NAME"]
EBAY_SECRET_REGION = os.environ["EBAY_SECRET_REGION"]
EBAY_MARKETPLACE_ID = os.environ["EBAY_MARKETPLACE_ID"]
EBAY_CATEGORY_ID = os.environ["EBAY_CATEGORY_ID"]
EBAY_CONTENT_LANGUAGE = os.environ.get("EBAY_CONTENT_LANGUAGE", "en-US")
EBAY_FULFILLMENT_POLICY_ID_UNDER20 = os.environ["EBAY_FULFILLMENT_POLICY_ID_UNDER20"]
EBAY_FULFILLMENT_POLICY_ID_OVER20 = os.environ["EBAY_FULFILLMENT_POLICY_ID_OVER20"]
EBAY_PAYMENT_POLICY_ID = os.environ["EBAY_PAYMENT_POLICY_ID"]
EBAY_RETURN_POLICY_ID = os.environ["EBAY_RETURN_POLICY_ID"]
EBAY_MERCHANT_LOCATION_KEY = os.environ["EBAY_MERCHANT_LOCATION_KEY"]
BUY_IT_NOW_LISTING_DURATION = os.environ["BUY_IT_NOW_LISTING_DURATION"]
AUCTION_LISTING_DURATION = os.environ["AUCTION_LISTING_DURATION"]

# eBay constants
EBAY_API_BASE = "https://api.ebay.com"
EBAY_IDENTITY_BASE = "https://api.ebay.com"
EBAY_US_CATEGORY_TREE_ID = "0"
USD = "USD"

class BadRequest(Exception):
    pass


class EbayApiError(Exception):
    def __init__(self, message: str, status: int | None = None, payload: dict | None = None):
        super().__init__(message)
        self.status = status
        self.payload = payload or {}


class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            if o % 1 == 0:
                return int(o)
            return float(o)
        return super().default(o)


def response(status_code: int, body: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json"
        },
        "body": json.dumps(body, cls=DecimalEncoder)
    }


def lambda_handler(event, context):
    logger.info("Incoming event: %s", json.dumps(event, cls=DecimalEncoder))

    try:
        payload = parse_event_payload(event)
        validate_request_payload(payload)

        item = get_inventory_item(payload["guid"])
        secret = get_ebay_secret()
        access_token = get_user_access_token(secret)        
        title = build_title(item)
        aspects = build_item_specifics(item=item, payload=payload)
        condition_payload = build_condition_payload(item)

        sku = payload["guid"]
        inventory_payload = build_inventory_payload(
            item=item,
            title=title,
            aspects=aspects,
            condition_payload=condition_payload,
        )        
        logger.info("Inventory payload: %s", json.dumps(inventory_payload))

        inventory_result = create_or_replace_inventory_item(
            access_token=access_token,
            sku=sku,
            payload=inventory_payload,
        )
        
        logger.info("eBay createOrReplaceInventoryItem result: %s", json.dumps(inventory_result))        
        
        offer_payload = build_offer_payload(
            item=item,
            payload=payload,
            access_token=access_token,
        )
        logger.info("Offer payload: %s", json.dumps(offer_payload))

        offer_result = create_offer(access_token=access_token, payload=offer_payload)
        logger.info("eBay createOffer result: %s", json.dumps(offer_result))

        offer_id = offer_result["offerId"]
        publish_result = publish_offer(access_token=access_token, offer_id=offer_id)
        logger.info("eBay publishOffer result: %s", json.dumps(publish_result))

        listing_id = publish_result.get("listingId")
        if listing_id:
            update_inventory_record_after_listing(
                guid=payload["guid"],
                ebay_item_id=listing_id,
            )

        return response(
            200,
            {
                "message": "eBay listing created successfully",
                "guid": payload["guid"],
                "sku": sku,                "offerId": offer_id,
                "listingId": listing_id,
                "inventoryResult": inventory_result,
                "offerResult": offer_result,
                "publishResult": publish_result,
            },
        )

    except BadRequest as e:
        logger.warning("Bad request: %s", str(e))
        return response(400, {"message": str(e)})
    except EbayApiError as e:
        logger.exception("eBay API error")
        return response(
            502,
            {
                "message": str(e),
                "status": e.status,
                "ebay": e.payload,
            },
        )
    except ClientError as e:
        logger.exception("AWS client error")
        return response(500, {"message": "AWS client error", "detail": str(e)})
    except Exception as e:
        logger.exception("Unhandled exception")
        return response(500, {"message": "Unhandled exception", "detail": str(e)})


def parse_event_payload(event: dict) -> dict:
    body = event.get("body")
    if body is None:
        raise BadRequest("Request body is required")

    if event.get("isBase64Encoded"):
        body = base64.b64decode(body).decode("utf-8")

    try:
        payload = json.loads(body)
    except json.JSONDecodeError as e:
        raise BadRequest(f"Request body must be valid JSON: {e}")

    if not isinstance(payload, dict):
        raise BadRequest("Request body must be a JSON object")

    return payload

def get_fulfillment_policy_id_for_item(item: dict, payload: dict) -> str:
    listing_type = payload["listingType"]

    if listing_type == "BUY_IT_NOW":
        listing_price = to_decimal(item.get("MktVal") or 0)
    else:
        listing_price = to_decimal(payload["startingBid"])

    if listing_price < decimal.Decimal("20.00"):
        return EBAY_FULFILLMENT_POLICY_ID_UNDER20

    return EBAY_FULFILLMENT_POLICY_ID_OVER20

def validate_request_payload(payload: dict) -> None:
    required = ["guid", "listingType", "allowOffers", "team", "autographed"]
    missing = [k for k in required if k not in payload]
    if missing:
        raise BadRequest(f"Missing required field(s): {', '.join(missing)}")

    listing_type = str(payload["listingType"]).strip().upper()
    if listing_type not in {"AUCTION", "BUY_IT_NOW"}:
        raise BadRequest("listingType must be AUCTION or BUY_IT_NOW")
    payload["listingType"] = listing_type

    payload["allowOffers"] = bool(payload["allowOffers"])
    payload["guid"] = str(payload["guid"]).strip()
    payload["team"] = str(payload["team"]).strip()
    payload["autographed"] = normalize_yes_no(payload["autographed"], field_name="autographed")

    if not payload["guid"]:
        raise BadRequest("guid must not be empty")
    if not payload["team"]:
        raise BadRequest("team must not be empty")

    if listing_type == "AUCTION":
        if "startingBid" not in payload:
            raise BadRequest("startingBid is required when listingType is AUCTION")
        try:
            starting_bid = int(payload["startingBid"])
        except (TypeError, ValueError):
            raise BadRequest("startingBid must be an integer")
        if starting_bid <= 0:
            raise BadRequest("startingBid must be greater than 0")
        payload["startingBid"] = starting_bid


def normalize_yes_no(value, field_name: str) -> str:
    if value is None:
        raise BadRequest(f"{field_name} is required")
    normalized = str(value).strip().upper()
    if normalized in {"YES", "Y", "TRUE", "1"}:
        return "Yes"
    if normalized in {"NO", "N", "FALSE", "0"}:
        return "No"
    raise BadRequest(f"{field_name} must be Yes or No")


def get_inventory_item(guid: str) -> dict:
    result = table.get_item(Key={"guid": guid})
    item = result.get("Item")
    if not item:
        raise BadRequest(f"Item not found for guid '{guid}'")
    return item


def get_ebay_secret() -> dict:
    result = secrets_client.get_secret_value(SecretId=EBAY_SECRET_NAME)
    secret_string = result.get("SecretString")
    if not secret_string:
        raise RuntimeError(f"Secret {EBAY_SECRET_NAME} has no SecretString")
    secret = json.loads(secret_string)

    for field in ["client_id", "client_secret", "refresh_token", "environment"]:
        if field not in secret or not str(secret[field]).strip():
            raise RuntimeError(f"Secret is missing required field '{field}'")

    env = str(secret["environment"]).strip().lower()
    if env != "production":
        raise RuntimeError("This Lambda is configured for eBay production only")

    return secret


def get_user_access_token(secret: dict) -> str:
    client_id = secret["client_id"]
    client_secret = secret["client_secret"]
    refresh_token = secret["refresh_token"]

    creds = f"{client_id}:{client_secret}".encode("utf-8")
    basic = base64.b64encode(creds).decode("ascii")

    data = parse.urlencode(
        {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        }
    ).encode("utf-8")

    req = request.Request(
        url=f"{EBAY_IDENTITY_BASE}/identity/v1/oauth2/token",
        data=data,
        method="POST",
        headers={
            "Authorization": f"Basic {basic}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )

    try:
        with request.urlopen(req, timeout=10) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except error.HTTPError as e:
        raw = e.read().decode("utf-8")
        logger.error("eBay token refresh failed. status=%s body=%s", e.code, raw)
        try:
            parsed = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            parsed = {"raw": raw}
        raise EbayApiError(
            f"eBay token refresh failed: POST {EBAY_IDENTITY_BASE}/identity/v1/oauth2/token",
            status=e.code,
            payload=parsed,
        )

    token = body.get("access_token")
    if not token:
        raise RuntimeError("eBay token response did not include access_token")
    return token


def build_title(item: dict) -> str:
    grade = clean_str(item.get("Grade"))
    if grade in {"0", "0.0"}:
        grade = ""

    parts = [
        clean_str(item.get("Year")),
        clean_str(item.get("Set")),
        clean_str(item.get("Subset")),
        clean_str(item.get("PlayerName")),
        clean_str(item.get("Authenticator")),
        grade,
        clean_str(item.get("SerialNumber")),
    ]
    title = " ".join(p for p in parts if p)
    title = re.sub(r"\s+", " ", title).strip()
    if not title:
        raise BadRequest("Unable to build title from inventory data")
    # eBay title max length is 80 chars for standard listings.
    return title[:80].rstrip()


def build_item_specifics(item: dict, payload: dict) -> dict[str, list[str]]:
    has_authenticator = bool(clean_str(item.get("Authenticator")))
    print_run = normalize_print_run(item.get("SerialNumber"))

    aspects: dict[str, list[str]] = {
        "Sport": ["Baseball"],
        "League": ["Major League Baseball (MLB)"],
        "Type": ["Sports Trading Card"],
        "Card Size": ["Standard"],
        "Country of Origin": ["United States"],
        "Original/Licensed Reprint": ["Original"],
        "Player/Athlete": [safe_value(item.get("PlayerName"))],
        "Season": [safe_value(item.get("Year"))],
        "Parallel/Variety": [safe_value(item.get("Subset"))],
        "Set": [safe_value(item.get("Set"))],
        "Card Number": [safe_value(item.get("CardNum"))],
        "Year Manufactured": [safe_value(item.get("Year"))],
        "Team": [payload["team"]],
        "Autographed": [payload["autographed"]],
        "guid": [safe_value(item.get("guid"))],
    }

    if print_run:
        aspects["Print Run"] = [print_run]

    if has_authenticator:
        aspects["Professional Grader"] = [safe_value(item.get("Authenticator"))]
        aspects["Grade"] = [safe_value(item.get("Grade"))]
        cert_num = clean_str(item.get("CertNumber"))
        if cert_num:
            aspects["Certification Number"] = [cert_num]

    return {k: v for k, v in aspects.items() if v and v[0]}


# Trading card condition descriptor name IDs
EBAY_CD_GRADED_GRADER = "27501"
EBAY_CD_GRADED_GRADE = "27502"
EBAY_CD_GRADED_CERT = "27503"
EBAY_CD_UNGRADED_CARD_CONDITION = "40001"

# Ungraded condition value IDs
EBAY_UNGRADED_CONDITION_NEAR_MINT_OR_BETTER = "400010"

# Supported grader value IDs
EBAY_GRADER_VALUE_IDS = {
    "PSA": "275010",
    "BCCG": "275011",
    "BVG": "275012",
    "BGS": "275013",
    "CSG": "275014",
    "CGC": "275015",
    "SGC": "275016",
}

# Supported grade value IDs
EBAY_GRADE_VALUE_IDS = {
    "10": "275020",
    "9.5": "275021",
    "9": "275022",
    "8.5": "275023",
    "8": "275024",
    "7.5": "275025",
    "7": "275026",
    "6.5": "275027",
    "6": "275028",
    "5.5": "275029",
    "5": "2750210",
    "4.5": "2750211",
    "4": "2750212",
    "3.5": "2750213",
    "3": "2750214",
    "2.5": "2750215",
    "2": "2750216",
    "1.5": "2750217",
    "1": "2750218",
    "AUTHENTIC": "2750219",
    "AUTHENTIC ALTERED": "2750220",
    "AUTHENTIC - TRIMMED": "2750221",
    "AUTHENTIC - COLOURED": "2750222",
}

def build_condition_payload(item: dict) -> dict:
    authenticator = clean_str(item.get("Authenticator")).upper()
    grade_raw = clean_str(item.get("Grade"))
    cert_number = clean_str(item.get("CertNumber"))

    has_authenticator = bool(authenticator)

    if has_authenticator:
        grader_value_id = EBAY_GRADER_VALUE_IDS.get(authenticator)
        if not grader_value_id:
            raise BadRequest(
                f"Unsupported Authenticator '{authenticator}'. "
                f"Allowed values: {sorted(EBAY_GRADER_VALUE_IDS.keys())}"
            )

        grade_key = normalize_grade_for_ebay(grade_raw)
        grade_value_id = EBAY_GRADE_VALUE_IDS.get(grade_key)
        if not grade_value_id:
            raise BadRequest(
                f"Unsupported Grade '{grade_raw}'. "
                f"Allowed values: {sorted(EBAY_GRADE_VALUE_IDS.keys())}"
            )

        descriptors = [
            {
                "name": EBAY_CD_GRADED_GRADER,
                "values": [grader_value_id],
            },
            {
                "name": EBAY_CD_GRADED_GRADE,
                "values": [grade_value_id],
            },
        ]

        if cert_number:
            descriptors.append(
                {
                    "name": EBAY_CD_GRADED_CERT,
                    "additionalInfo": cert_number[:30],
                }
            )

        return {
            "condition": "LIKE_NEW",
            "conditionDescriptors": descriptors,
        }

    return {
        "condition": "USED_VERY_GOOD",
        "conditionDescriptors": [
            {
                "name": EBAY_CD_UNGRADED_CARD_CONDITION,
                "values": [EBAY_UNGRADED_CONDITION_NEAR_MINT_OR_BETTER],
            }
        ],
    }


def normalize_grade_for_ebay(value: str) -> str:
    text = clean_str(value).upper()

    replacements = {
        "AUTH": "AUTHENTIC",
        "AUTHENTIC ALTERED": "AUTHENTIC ALTERED",
        "AUTHENTIC-ALTERED": "AUTHENTIC ALTERED",
        "AUTHENTIC - ALTERED": "AUTHENTIC ALTERED",
        "AUTHENTIC TRIMMED": "AUTHENTIC - TRIMMED",
        "AUTHENTIC-TRIMMED": "AUTHENTIC - TRIMMED",
        "AUTHENTIC COLOURED": "AUTHENTIC - COLOURED",
        "AUTHENTIC-COLOURED": "AUTHENTIC - COLOURED",
    }

    if text in replacements:
        return replacements[text]

    return text

def build_inventory_payload(item: dict, title: str, aspects: dict, condition_payload: dict) -> dict:
    guid = safe_value(item.get("guid"))
    product = {
        "title": title,
        "description": build_description(item),
        "aspects": aspects,
        "imageUrls": [
            f"https://test.us175.com/test-gallery/{guid}-front.webp",
            f"https://test.us175.com/test-gallery/{guid}-back.webp",
        ],
    }

    inventory_payload = {
        "availability": {
            "shipToLocationAvailability": {
                "quantity": 1
            }
        },
        "product": product,
        "packageWeightAndSize": build_package_weight_and_size(item),
        **condition_payload,
    }

    return inventory_payload


def build_description(item: dict) -> str:
    parts = [
        build_title(item),
        "",
        f"GUID: {safe_value(item.get('guid'))}",
        f"Set: {safe_value(item.get('Set'))}",
        f"Subset: {safe_value(item.get('Subset'))}",
        f"Player: {safe_value(item.get('PlayerName'))}",
        f"Card Number: {safe_value(item.get('CardNum'))}",
    ]

    if clean_str(item.get("SerialNumber")):
        parts.append(f"Serial Number: {clean_str(item.get('SerialNumber'))}")
    if clean_str(item.get("Authenticator")):
        parts.append(f"Grader: {clean_str(item.get('Authenticator'))}")
    if clean_str(item.get("Grade")):
        parts.append(f"Grade: {clean_str(item.get('Grade'))}")
    if clean_str(item.get("CertNumber")):
        parts.append(f"Certification Number: {clean_str(item.get('CertNumber'))}")

    return "\n".join(parts)


def build_offer_payload(item: dict, payload: dict, access_token: str) -> dict:
    listing_type = payload["listingType"]
    has_authenticator = bool(clean_str(item.get("Authenticator")))
    fulfillment_policy_id = get_fulfillment_policy_id_for_item(item, payload)

    if listing_type == "BUY_IT_NOW":
        price = format_currency_value(item.get("MktVal"))
        if decimal.Decimal(price) <= 0:
            raise BadRequest("MktVal must be greater than 0 for Buy It Now listings")
        listing_start_date = None
        format_value = "FIXED_PRICE"
        listing_duration = BUY_IT_NOW_LISTING_DURATION
    else:
        price = format_currency_value(payload["startingBid"])
        listing_start_date = compute_same_day_auction_start_utc()
        format_value = "AUCTION"
        listing_duration = AUCTION_LISTING_DURATION

    offer_payload = {
        "sku": safe_value(item.get("guid")),
        "marketplaceId": EBAY_MARKETPLACE_ID,
        "format": format_value,
        "availableQuantity": 1,
        "categoryId": EBAY_CATEGORY_ID,
        "merchantLocationKey": EBAY_MERCHANT_LOCATION_KEY,
        "listingDescription": build_description(item),
        "listingDuration": listing_duration,
        "pricingSummary": {
            "price": {
                "currency": USD,
                "value": price,
            }
        },
        "listingPolicies": {
            "fulfillmentPolicyId": fulfillment_policy_id,
            "paymentPolicyId": EBAY_PAYMENT_POLICY_ID,
            "returnPolicyId": EBAY_RETURN_POLICY_ID,
        },
        "tax": {"applyTax": True},
    }

    if listing_start_date:
        offer_payload["listingStartDate"] = listing_start_date

    if listing_type == "BUY_IT_NOW" and payload["allowOffers"]:
        offer_payload["listingPolicies"]["bestOfferTerms"] = {
            "bestOfferEnabled": True
        }


    # Validate that required condition metadata exists before trying to publish.
    # This avoids building the offer only to fail later for known missing data.
    _ = access_token
    _ = has_authenticator

    return offer_payload


def create_or_replace_inventory_item(access_token: str, sku: str, payload: dict) -> dict:
    encoded_sku = parse.quote(sku, safe="")
    status, data = ebay_request(
        method="PUT",
        url=f"{EBAY_API_BASE}/sell/inventory/v1/inventory_item/{encoded_sku}",
        access_token=access_token,
        body=payload,
        extra_headers={
            "Content-Language": EBAY_CONTENT_LANGUAGE,
        },
        allow_empty=True,
    )
    return {
        "status": status,
        "body": data,
    }


def create_offer(access_token: str, payload: dict) -> dict:
    status, data = ebay_request(
        method="POST",
        url=f"{EBAY_API_BASE}/sell/inventory/v1/offer",
        access_token=access_token,
        body=payload,
        extra_headers={
            "Content-Language": EBAY_CONTENT_LANGUAGE,
        },
    )
    if status not in (200, 201):
        raise EbayApiError("Unexpected createOffer response", status=status, payload=data)
    return data


def publish_offer(access_token: str, offer_id: str) -> dict:
    encoded_offer_id = parse.quote(offer_id, safe="")
    status, data = ebay_request(
        method="POST",
        url=f"{EBAY_API_BASE}/sell/inventory/v1/offer/{encoded_offer_id}/publish",
        access_token=access_token,
        body=None,
    )
    if status not in (200, 201):
        raise EbayApiError("Unexpected publishOffer response", status=status, payload=data)
    return data


def update_inventory_record_after_listing(guid: str, ebay_item_id: str) -> None:
    table.update_item(
        Key={"guid": guid},
        UpdateExpression="SET SoldeBayItemId = :ebay_item_id",
        ExpressionAttributeValues={
            ":ebay_item_id": ebay_item_id,
        },
    )


def ebay_request(method: str, url: str, access_token: str, body: dict | None, extra_headers: dict | None = None, allow_empty: bool = False):
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
    }
    if body is not None:
        headers["Content-Type"] = "application/json"
    if extra_headers:
        headers.update(extra_headers)

    data = None if body is None else json.dumps(body).encode("utf-8")
    req = request.Request(url=url, data=data, method=method, headers=headers)

    try:
        with request.urlopen(req, timeout=12) as resp:
            raw = resp.read().decode("utf-8")
            parsed = json.loads(raw) if raw else {}
            return resp.status, parsed
    except error.HTTPError as e:
        raw = e.read().decode("utf-8")
        parsed = json.loads(raw) if raw else {}
        logger.error("eBay HTTP error. status=%s body=%s", e.code, raw)
        raise EbayApiError(f"eBay API call failed: {method} {url}", status=e.code, payload=parsed)
    except error.URLError as e:
        logger.error("eBay URL error: %s", str(e))
        raise EbayApiError(f"eBay API network error: {e}")
    except json.JSONDecodeError as e:
        if allow_empty:
            return 204, {}
        raise EbayApiError(f"Non-JSON response from eBay: {e}")


def get_item_condition_policy(access_token: str, category_id: str) -> dict:
    filter_param = parse.quote(f"categoryIds:{{{category_id}}}", safe=":{}")
    url = (
        f"{EBAY_API_BASE}/sell/metadata/v1/marketplace/{EBAY_MARKETPLACE_ID}"
        f"/get_item_condition_policies?filter={filter_param}"
    )
    _, data = ebay_request(method="GET", url=url, access_token=access_token, body=None)
    policies = data.get("itemConditionPolicies", [])
    if not policies:
        raise RuntimeError(f"No item condition policy returned for category {category_id}")
    for policy in policies:
        if str(policy.get("categoryId")) == str(category_id):
            return policy
    return policies[0]


def build_condition_descriptor_map(policy: dict) -> dict:
    descriptor_map = {}
    for condition in policy.get("itemConditions", []):
        for descriptor in condition.get("conditionDescriptors", []) or []:
            descriptor_name = descriptor.get("conditionDescriptorName")
            if descriptor_name:
                descriptor_map[descriptor_name.lower()] = descriptor
    if not descriptor_map:
        raise RuntimeError("No condition descriptors were returned by eBay for this category")
    return descriptor_map


def make_closed_set_descriptor(descriptor_map: dict, descriptor_name: str, selected_display_value: str) -> dict:
    descriptor = descriptor_map.get(descriptor_name.lower())
    if not descriptor:
        raise RuntimeError(f"Condition descriptor '{descriptor_name}' not found")

    allowed_values = descriptor.get("conditionDescriptorValues", []) or []
    selected = find_matching_descriptor_value(allowed_values, selected_display_value)
    if not selected:
        choices = [v.get("value") for v in allowed_values]
        raise BadRequest(
            f"'{selected_display_value}' is not a valid eBay value for descriptor '{descriptor_name}'. "
            f"Allowed values: {choices}"
        )

    return {
        "name": str(descriptor["conditionDescriptorId"]),
        "values": [str(selected["conditionDescriptorValueId"])],
    }


def make_open_text_descriptor(descriptor_map: dict, descriptor_name: str, text_value: str) -> dict:
    descriptor = descriptor_map.get(descriptor_name.lower())
    if not descriptor:
        raise RuntimeError(f"Condition descriptor '{descriptor_name}' not found")

    return {
        "name": str(descriptor["conditionDescriptorId"]),
        "additionalInfo": text_value[:30],
    }


def find_matching_descriptor_value(allowed_values: list[dict], desired_text: str) -> dict | None:
    desired_norm = normalize_match(desired_text)
    for value in allowed_values:
        candidate = value.get("value")
        if normalize_match(candidate) == desired_norm:
            return value

    # Flexible fallback for common formatting differences.
    for value in allowed_values:
        candidate = value.get("value")
        if desired_norm in normalize_match(candidate) or normalize_match(candidate) in desired_norm:
            return value

    return None


def normalize_match(value) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value or "").lower())


def compute_same_day_auction_start_utc(now_utc: datetime | None = None) -> str:
    if now_utc is None:
        now_utc = datetime.now(timezone.utc)

    pt = ZoneInfo("America/Los_Angeles")
    now_pt = now_utc.astimezone(pt)
    scheduled_pt = now_pt.replace(hour=18, minute=59, second=0, microsecond=0)

    # Requirement says same day at 6:59 PM PT.
    # If that time has already passed when the Lambda is called, publish immediately instead of scheduling in the past.
    if now_pt >= scheduled_pt:
        return now_utc.strftime("%Y-%m-%dT%H:%M:%SZ")

    return scheduled_pt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_package_weight_and_size(item: dict) -> dict:
    has_authenticator = bool(clean_str(item.get("Authenticator")))
    market_value = to_decimal(item.get("MktVal") or 0)
    uses_ese = market_value < decimal.Decimal("20")

    if has_authenticator:
        return {
            "dimensions": {
                "height": 1,
                "length": 8,
                "unit": "INCH",
                "width": 5,
            },
            "weight": {
                "unit": "OUNCE",
                "value": 4,
            },
        }

    if uses_ese:
        return {
            "dimensions": {
                "height": 1,
                "length": 8,
                "unit": "INCH",
                "width": 4,
            },
            "weight": {
                "unit": "OUNCE",
                "value": 2,
            },
        }

    return {
        "dimensions": {
            "height": 1,
            "length": 8,
            "unit": "INCH",
            "width": 5,
        },
        "weight": {
            "unit": "OUNCE",
            "value": 3,
        },
    }


def normalize_print_run(serial_number) -> str:
    value = clean_str(serial_number)
    if not value:
        return ""
    if "/" not in value:
        return value
    return value.split("/")[-1].strip()


def clean_str(value) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if text.lower() in {"none", "null", "undefined"}:
        return ""
    return text


def safe_value(value) -> str:
    text = clean_str(value)
    return text


def to_decimal(value) -> decimal.Decimal:
    if isinstance(value, decimal.Decimal):
        return value
    try:
        return decimal.Decimal(str(value))
    except decimal.InvalidOperation:
        raise BadRequest(f"Invalid decimal value: {value}")


def format_currency_value(value) -> str:
    amount = to_decimal(value).quantize(decimal.Decimal("0.01"))
    return format(amount, "f")
