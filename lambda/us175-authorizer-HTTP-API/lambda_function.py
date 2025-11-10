import json
import urllib.request
import time
import logging
import os
from jose import jwk, jwt
from jose.utils import base64url_decode

# Set up the logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Config
REGION = "us-east-2"
USER_POOL_ID = os.environ["USER_POOL_ID"]

# Load Cognito JWKS once (at cold start)
keys_url = f"https://cognito-idp.{REGION}.amazonaws.com/{USER_POOL_ID}/.well-known/jwks.json"
with urllib.request.urlopen(keys_url) as f:
    KEYS = json.loads(f.read().decode("utf-8"))["keys"]


def lambda_handler(event, context):
    headers = event.get("headers", {}) or {}
    cookie_header = headers.get("cookie", "") or headers.get("Cookie", "")
    access_token = _get_cookie(cookie_header, "accessToken")

    #logger.info(f"Incoming event: {json.dumps(event)}")
    #logger.info(f"Access token (truncated): {access_token[:20]}..." if access_token else "No access token")

    if not access_token:
        return {"isAuthorized": False}

    try:
        claims = _verify_token(access_token)
    except Exception as e:
        logger.error(f"JWT validation failed: {e}")
        return {"isAuthorized": False}

    return {
        "isAuthorized": True,
        "context": claims  # optional, gets passed to backend integration
    }


def _get_cookie(cookie_header: str, name: str):
    """Extract a cookie by name from the Cookie header."""
    for cookie in cookie_header.split(";"):
        cookie = cookie.strip()
        if cookie.startswith(name + "="):
            return cookie.split("=", 1)[1]
    return None


def _verify_token(token: str):
    """Verify JWT signature and expiration using Cognito JWKS."""
    headers = jwt.get_unverified_headers(token)
    kid = headers["kid"]

    key_index = next((i for i, k in enumerate(KEYS) if k["kid"] == kid), -1)
    if key_index == -1:
        raise Exception("Public key not found in JWKS")

    public_key = jwk.construct(KEYS[key_index])
    message, encoded_sig = str(token).rsplit(".", 1)
    decoded_sig = base64url_decode(encoded_sig.encode("utf-8"))

    if not public_key.verify(message.encode("utf-8"), decoded_sig):
        raise Exception("Signature verification failed")

    claims = jwt.get_unverified_claims(token)

    if time.time() > claims["exp"]:
        raise Exception("Token expired")

    return claims

