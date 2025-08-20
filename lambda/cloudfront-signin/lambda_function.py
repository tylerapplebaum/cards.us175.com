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
    code = qs.get("code", [None])[0]
    state = qs.get("state", [None])[0]

    if not code:
        logger.error(f"Missing authorization code in /signin request. querystring={raw_qs}")
        return _error_response("Missing authorization code.")

    # Determine final redirect URL (original path carried in `state`)
    if state:
        try:
            state_decoded = urllib.parse.unquote(state)
        except Exception:
            state_decoded = state  # fallback; worst case we pass the encoded value
        # Prevent open-redirects: only allow paths
        if state_decoded.startswith("http://") or state_decoded.startswith("https://"):
            logger.warning(f"Blocking absolute URL in state: {state_decoded}")
            redirect_url = CONTENT_ROOT
        else:
            redirect_url = f"{CONTENT_ROOT}{state_decoded}"
    else:
        redirect_url = CONTENT_ROOT

    # Prepare Basic auth for token exchange
    basic = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode("ascii")).decode("ascii")

    try:
        tokens = call_cognito_token(
            client_id=CLIENT_ID,
            code=code,
            redirect_uri=f"https://{domain_name}/signin",
            basic_auth=basic,
        )
    except Exception as e:
        logger.exception("Token exchange with Cognito failed")
        return _error_response("Token exchange failed.")

    # Validate token payload shape
    if not isinstance(tokens, dict) or "id_token" not in tokens or "access_token" not in tokens or "refresh_token" not in tokens:
        logger.error(f"Unexpected token response: {tokens}")
        return _error_response("Invalid token response.")

    # Build cookies
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
        {
            "key": "Set-Cookie",
            "value": f"refreshToken={tokens['refresh_token']}; {cookie_attrs}",
        },
    ]

# Redirect the user back to the original URL
    response = {
        "status": "307",
        "statusDescription": "Temporary Redirect",
        "headers": {
            "location": [{"key": "location", "value": redirect_url}],
            "set-cookie": set_cookie_headers,
        },
    }
    return response


def call_cognito_token(client_id: str, code: str, redirect_uri: str, basic_auth: str) -> dict:
    """
    Exchange the authorization code for tokens at Cognito's /oauth2/token endpoint.
    NOTE: USER_POOL_ENDPOINT must be the token endpoint, e.g.:
          https://<your-domain>.auth.<region>.amazoncognito.com/oauth2/token
    """
    payload = {
        "grant_type": "authorization_code",
        "client_id": client_id,
        "code": code,
        "redirect_uri": redirect_uri,
    }
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Basic {basic_auth}",
    }

    # IMPORTANT: send form body via data=payload (NOT params=payload)
    resp = requests.post(USER_POOL_ENDPOINT, data=payload, headers=headers, timeout=10)
    try:
        resp.raise_for_status()
    except Exception:
        # Log body for diagnostics but don't leak to client
        logger.error(f"Cognito token endpoint error: status={resp.status_code}, body={resp.text}")
        raise
    return resp.json()


def _error_response(message: str):
    # Minimal 400 to avoid loops; customize as needed (e.g., redirect to login)
    return {
        "status": "400",
        "statusDescription": "Bad Request",
        "body": message,
    }


def get_secret():
    # Lambda@Edge doesn't support static env vars at build-time; pull from Secrets Manager
    secret_name = SECRET_NAME
    session = boto3.session.Session()
    client = session.client(service_name="secretsmanager", region_name=REGION)
    try:
        get_secret_value_response = client.get_secret_value(SecretId=secret_name)
    except ClientError as e:
        raise e
    return get_secret_value_response["SecretString"]


# ------- Load config from SSM --------
ssm_client = boto3.client("ssm", region_name=REGION)

param = ssm_client.get_parameter(Name="/prod/serverlessAuth/userPoolSecretName")
os.environ["USER_POOL_SECRET"] = param["Parameter"]["Value"]

param = ssm_client.get_parameter(Name="/prod/serverlessAuth/userPoolId")
os.environ["USER_POOL_ID"] = param["Parameter"]["Value"]

param = ssm_client.get_parameter(Name="/prod/serverlessAuth/userPoolEndpoint")
os.environ["USER_POOL_ENDPOINT"] = param["Parameter"]["Value"]  # should be .../oauth2/token

param = ssm_client.get_parameter(Name="/prod/serverlessAuth/userPoolHostedUi")
os.environ["USER_POOL_HOSTED_UI"] = param["Parameter"]["Value"]

param = ssm_client.get_parameter(Name="/prod/serverlessAuth/contentRoot")
os.environ["CONTENT_ROOT"] = param["Parameter"]["Value"]

# ------- Configs --------
SECRET_NAME = os.environ["USER_POOL_SECRET"]
USER_POOL_ID = os.environ["USER_POOL_ID"]
USER_POOL_ENDPOINT = os.environ["USER_POOL_ENDPOINT"]  # e.g. https://<domain>/oauth2/token
SIGN_IN_URL = os.environ["USER_POOL_HOSTED_UI"]
CONTENT_ROOT = os.environ["CONTENT_ROOT"]
REFRESH_URL = f"{CONTENT_ROOT}/refresh"

# Load secrets outside handler
secret = json.loads(get_secret())
CLIENT_ID = secret["clientId"]
CLIENT_SECRET = secret["clientSecret"]

# (Optional) If you still need JWKS for anything else later
keys_url = f"https://cognito-idp.{REGION}.amazonaws.com/{USER_POOL_ID}/.well-known/jwks.json"
with urllib.request.urlopen(keys_url) as f:
    response = f.read()
KEYS = json.loads(response.decode("utf-8"))["keys"]
