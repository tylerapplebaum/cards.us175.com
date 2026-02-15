import json
import time
import os
import urllib.request
import urllib.parse
from jose import jwk, jwt
from jose.utils import base64url_decode
import boto3
import re
import logging
from botocore.exceptions import ClientError

# Set up the logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

REGION = "us-east-2"
PUBLIC_PATH_PREFIXES = (
    "/Inventory/wantlist",
)
PUBLIC_ASSET_PREFIXES = (
    "/vendor/",
    "/css/",
    "/fonts/",
    "/js/",
    "/img/",
    "/Inventory/css/",
    "/Inventory/public/",
)


def is_public_path(uri):
    """
    Return True for paths that should bypass auth checks.
    """
    return any(uri == p or uri.startswith(f"{p}/") for p in PUBLIC_PATH_PREFIXES)


def is_public_asset(uri):
    """
    Return True for static assets needed by the public wantlist page.
    """
    return any(uri.startswith(prefix) for prefix in PUBLIC_ASSET_PREFIXES)

def lambda_handler(event, context):
    request = event["Records"][0]["cf"]["request"]
    headers = request["headers"]
    domainName = headers["host"][0]["value"]
    requestedUri = request["uri"]
    queryString = request.get("querystring", "")

    logger.info(f"requestedUri: {requestedUri}?{queryString}")

    # Allow selected public pages/files through without Cognito auth.
    if is_public_path(requestedUri) or is_public_asset(requestedUri):
        logger.info("Public path requested - bypassing auth")
        return request
    
    # --- NEW LOGIC: redirect root-level .png files to /Inventory/public/ ---
    if re.match(r"^/[^/]+\.(png|ico)$", requestedUri, re.IGNORECASE):  # e.g. "/apple-touch-icon.png" or "/favicon.ico"
        filename = requestedUri.lstrip("/")       # strip leading slash
        return {
            "status": "302",
            "statusDescription": "Found",
            "headers": {
                "location": [
                    {
                        "key": "location",
                        "value": f"/Inventory/public/{filename}"
                    }
                ]
            }
        }
    
    idToken = ""

    # Check cookies for idToken
    for cookie in headers.get("cookie", []):
        cookiesList = cookie["value"].split(";")
        for subCookie in cookiesList:
            if "idToken" in subCookie:
                idToken = subCookie.split("=")[1].strip()
                break
        if idToken:
            break

    # If no token, redirect to Cognito login
    if not idToken:
        logger.info("ID Token not found - redirecting to Cognito login")
        return create_redirect_to_login_response(
            request, requestedUri, queryString
        )

    # Validate JWT header
    try:
        jwtHeaders = jwt.get_unverified_headers(idToken)
        kid = jwtHeaders["kid"]
    except Exception as e:
        logger.error(f"Failed to get JWT headers: {e}")
        return create_redirect_to_login_response(
            request, requestedUri, queryString
        )

    key_index = -1
    for i in range(len(KEYS)):
        if kid == KEYS[i]["kid"]:
            key_index = i
            break
    
    if key_index == -1:
        logger.error("Public key not found in jwks.json")
        return create_redirect_to_login_response(
            request, requestedUri, queryString
        )

    try:
        publicKey = jwk.construct(KEYS[key_index])

        message, encoded_signature = str(idToken).rsplit(".", 1)
        decoded_signature = base64url_decode(encoded_signature.encode("utf-8"))
        
        if not publicKey.verify(message.encode("utf8"), decoded_signature):
            logger.error("Signature verification failed")
            return create_redirect_to_login_response(
                request, requestedUri, queryString
            )

        claims = jwt.get_unverified_claims(idToken)
        
        # Check if token is expired
        if time.time() > claims["exp"]:
            logger.info("Token expired - redirecting to refresh")
            # FIXED: Pass the current URI and query string to the refresh function
            return create_redirect_to_refresh_response(requestedUri, queryString)

        if claims["aud"] != CLIENT_ID:
            logger.error("Token was not issued for this audience")
            return create_redirect_to_login_response(
                request, requestedUri, queryString
            )
            
    except Exception as e:
        logger.error(f"Token validation failed: {e}")
        return create_redirect_to_login_response(
            request, requestedUri, queryString
        )

    # Token is valid, proceed with the request
    return request


def create_redirect_to_login_response(request, requestedUri=None, queryString=None):
    """
    Create a redirect response to the Cognito login page
    """
    # Preserve original path + query
    state = requestedUri or "/"
    if queryString:
        state += f"?{queryString}"
    state = urllib.parse.quote(state, safe="")

    # Cognito login URL (SIGN_IN_URL must be just the /login endpoint, no query params)
    login_url = (
        f"{SIGN_IN_URL}"
        f"?client_id={CLIENT_ID}"
        f"&response_type=code"
        f"&scope=email+openid+phone+profile"
        f"&redirect_uri=https://{request['headers']['host'][0]['value']}/signin"
        f"&state={state}"
    )
    logger.info(f"login_url: {login_url}")
    
    response = {
        "status": "307",
        "statusDescription": "Temporary Redirect",
        "headers": {
            "location": [
                {
                    "key": "location",
                    "value": login_url,
                },
            ],
        },
    }
    return response


def create_redirect_to_refresh_response(requestedUri=None, queryString=None):
    """
    Create a redirect response to the refresh endpoint
    FIXED: Now accepts and passes the current URI and query string as state
    """
    # Preserve the original path + query in the state parameter
    state = requestedUri or "/"
    if queryString:
        state += f"?{queryString}"
    
    # URL encode the state parameter
    state_encoded = urllib.parse.quote(state, safe="")
    
    # Build the refresh URL with the state parameter
    refresh_url = f"{REFRESH_URL}?state={state_encoded}"
    
    logger.info(f"Redirecting to refresh with state: {state}")
    
    response = {
        "status": "307",
        "statusDescription": "Temporary Redirect",
        "headers": {
            "location": [
                {
                    "key": "location",
                    "value": refresh_url,
                },
            ],
        },
    }
    return response


def get_secret():
    """
    Retrieve secret from AWS Secrets Manager
    """
    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(service_name="secretsmanager", region_name=REGION)

    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=os.environ["USER_POOL_SECRET"]
        )
    except ClientError as e:
        logger.error(f"Failed to retrieve secret: {e}")
        raise e

    secret = get_secret_value_response["SecretString"]
    return secret


# LOAD SSM PARAMETERS
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


# CONFIGS
SECRET_NAME = os.environ["USER_POOL_SECRET"]
USER_POOL_ID = os.environ["USER_POOL_ID"]
SIGN_IN_URL = os.environ["USER_POOL_HOSTED_UI"]  # should be like https://xxxx.auth.us-east-2.amazoncognito.com/login
REFRESH_URL = f"{os.environ['CONTENT_ROOT']}/refresh"

# Load Secrets and jwks outside of the handler
secret = json.loads(get_secret())
CLIENT_ID = secret["clientId"]
CLIENT_SECRET = secret["clientSecret"]

keys_url = (
    f"https://cognito-idp.{REGION}.amazonaws.com/{USER_POOL_ID}/.well-known/jwks.json"
)

with urllib.request.urlopen(keys_url) as f:
    response = f.read()
KEYS = json.loads(response.decode("utf-8"))["keys"]
