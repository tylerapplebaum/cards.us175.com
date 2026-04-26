# deleting an offer with invalid parameters, ex:
# https://api.ebay.com/sell/inventory/v1/offer/1234567890
# use this script to fetch the token, then paste it here for API testing usage
# https://developer.ebay.com/my/api_test_tool?index=0&api=inventory&call=offer-offerId__DELETE&variation=json&env=production
import os
import json
import base64
import logging
import decimal
import re
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from urllib import request, parse, error
def get_user_access_token():
    client_id = "paste-here"
    client_secret = "paste-here"
    refresh_token = "paste-here"
    creds = f"{client_id}:{client_secret}".encode("utf-8")
    basic = base64.b64encode(creds).decode("ascii")
    data = parse.urlencode(
        {
		    "grant_type": "refresh_token",
		    "refresh_token": refresh_token,
        }
    ).encode("utf-8")
    req = request.Request(
    url=f"https://api.ebay.com/identity/v1/oauth2/token",
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
            f"eBay token refresh failed: POST https://api.ebay.com/identity/v1/oauth2/token",
            status=e.code,
            payload=parsed,
        )
    token = body.get("access_token")
    if not token:
        raise RuntimeError("eBay token response did not include access_token")
    return token
    
get_user_access_token()
