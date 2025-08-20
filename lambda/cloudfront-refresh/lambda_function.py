import json
import base64
import requests
import urllib.request
import urllib.parse
import boto3
import os
import logging
from botocore.exceptions import ClientError

# Set up the logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

REGION = "us-east-2"

def lambda_handler(event, context):
    request = event["Records"][0]["cf"]["request"]
    headers = request["headers"]
    domain_name = headers["host"][0]["value"]

    # Parse querystring safely
    raw_qs = request.get("querystring", "")
    qs = urllib.parse.parse_qs(raw_qs)
    state = qs.get("state", [None])[0]

    # Determine final redirect URL (original path carried in `state`)
    if state:
        try:
            state_decoded = urllib.parse.unquote(state)
        except Exception:
            state_decoded = state  # fallback
        # Prevent open-redirects
        if state_decoded.startswith("http://") or state_decoded.startswith("https://"):
            logger.warning(f"Blocking absolute URL in state: {state_decoded}")
            redirect_url = CONTENT_ROOT
        else:
            redirect_url = f"{CONTENT_ROOT}{state_decoded}"
    else:
        redirect_url = CONTENT_ROOT

    # Extract refresh token from cookies
    refresh_token = None
    for cookie in headers.get("cookie", []):
        cookies_list = cookie["value"].split(";")
        for sub_cookie in cookies_list:
            name, _, val = sub_cookie.strip().partition("=")
            if name == "refreshToken":
                refresh_token = val
                break
        if refresh_token:
            break

    if not refresh_token:
        logger.error("No refreshToken cookie found")
        return _error_response("Missing refresh token.")

    # Prepare Basic auth
    basic = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode("ascii")).decode("ascii")

    try:
        tokens = call_cognito_refresh(
            client_id=CLIENT_ID,
            refresh_token=refresh_token,
            basic_auth=basic,
        )
    except Exception as e:
        logger.exception("Token refresh with Cognito failed")
        return _error_response("Token refresh failed.")

    # Validate token payload shape
    if not isinstance(tokens, dict) or "id_token" not in tokens or "access_token" not in tokens:
        logger.error(f"Unexpected refresh response: {tokens}")
        return _error_response("Invalid refresh response.")

    # Build cookies (same attrs as sign-in)
    cookie_attrs = "Path=/; Domain=.us175.com; Secure; HttpOnly; SameSite=None"
    set_cookie_headers = [
        {
            "key": "Set-Cookie",
            "value": f"idToken={tokens['id_token']}; {cookie_attrs}",
        },
        {
            "key": "Set-Cookie",
            "value": f"accessToken={tokens['access_token']}; {cookie_attrs}",
        },
        # refreshToken stays as-is; don’t overwrite unless Cognito issues new one
    ]

    # Redirect back
    response = {
        "status": "307",
        "statusDescription": "Temporary Redirect",
        "headers": {
            "location": [{"key": "location", "value": redirect_url}],
            "set-cookie": set_cookie_headers,
        },
    }
    return response


def call_cognito_refresh(client_id: str, refresh_token: str, basic_auth: str) -> dict:
    payload = {
        "grant_type": "refresh_token",
        "client_id": client_id,
        "refresh_token": refresh_token,
    }
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Basic {basic_auth}",
    }
    resp = requests.post(USER_POOL_ENDPOINT, data=payload, headers=headers, timeout=10)
    try:
        resp.raise_for_status()
    except Exception:
        logger.error(f"Cognito refresh error: status={resp.status_code}, body={resp.text}")
        raise
    return resp.json()


def _error_response(message: str):
    return {
        "status": "400",
        "statusDescription": "Bad Request",
        "body": message,
    }


def get_secret():
    secret_name = SECRET_NAME
    session = boto3.session.Session()
    client = session.client(service_name="secretsmanager", region_name=REGION)
    try:
        get_secret_value_response = client.get_secret_value(SecretId=secret_name)
    except ClientError as e:
        raise e
    return get_secret_value_response["SecretString"]


# ------- Load SSM Parameters --------
ssm_client = boto3.client("ssm", region_name=REGION)

param = ssm_client.get_parameter(Name="/prod/serverlessAuth/userPoolSecretName")
os.environ["USER_POOL_SECRET"] = param["Parameter"]["Value"]

param = ssm_client.get_parameter(Name="/prod/serverlessAuth/userPoolId")
os.environ["USER_POOL_ID"] = param["Parameter"]["Value"]

param = ssm_client.get_parameter(Name="/prod/serverlessAuth/userPoolEndpoint")
os.environ["USER_POOL_ENDPOINT"] = param["Parameter"]["Value"]

param = ssm_client.get_parameter(Name="/prod/serverlessAuth/userPoolHostedUi")
os.environ["USER_POOL_HOSTED_UI"] = param["Parameter"]["Value"]

param = ssm_client.get_parameter(Name="/prod/serverlessAuth/contentRoot")
os.environ["CONTENT_ROOT"] = param["Parameter"]["Value"]

# ------- Configs --------
SECRET_NAME = os.environ["USER_POOL_SECRET"]
USER_POOL_ID = os.environ["USER_POOL_ID"]
USER_POOL_ENDPOINT = os.environ["USER_POOL_ENDPOINT"]
SIGN_IN_URL = os.environ["USER_POOL_HOSTED_UI"]
CONTENT_ROOT = os.environ["CONTENT_ROOT"]
REFRESH_URL = f"{CONTENT_ROOT}/refresh"

# Load secrets outside handler
secret = json.loads(get_secret())
CLIENT_ID = secret["clientId"]
CLIENT_SECRET = secret["clientSecret"]

# (Optional) JWKS load
keys_url = f"https://cognito-idp.{REGION}.amazonaws.com/{USER_POOL_ID}/.well-known/jwks.json"
with urllib.request.urlopen(keys_url) as f:
    response = f.read()
KEYS = json.loads(response.decode("utf-8"))["keys"]