#!/usr/bin/env python3
"""
One-time helper for obtaining an eBay SANDBOX refresh token and optionally
storing it in AWS Secrets Manager.

Usage examples:

1) Print the sandbox consent URL:
   python ebay_sandbox_refresh_helper.py \
     --client-id YOUR_CLIENT_ID \
     --runame YOUR_RUNAME \
     --print-consent-url

2) Exchange the authorization code returned by eBay:
   python ebay_sandbox_refresh_helper.py \
     --client-id YOUR_CLIENT_ID \
     --client-secret YOUR_CLIENT_SECRET \
     --runame YOUR_RUNAME \
     --auth-code YOUR_AUTH_CODE

3) Exchange the code and store/update the refresh token in Secrets Manager:
   python ebay_sandbox_refresh_helper.py \
     --client-id YOUR_CLIENT_ID \
     --client-secret YOUR_CLIENT_SECRET \
     --runame YOUR_RUNAME \
     --auth-code YOUR_AUTH_CODE \
     --secret-name YOUR_SECRET_NAME \
     --secret-region us-east-1 \
     --write-secret
     
Actual values:
python3 ebay_sandbox_refresh_helper.py \
  --client-id Lambda-SBX-abcde123-45678fab01 \
  --runame RuName-Lambda-abcdef \
  --print-consent-url
  
* take the URL after signing in and URL decode it and feed it back to the script.

python3 ebay_sandbox_refresh_helper.py \
  --client-id Lambda-SBX-abcde123-45678fab01 \
  --client-secret SBX-abcdef123-4567-8901-bcde \
  --runame RuName-Lambda-abcdef \
  --auth-code v^1.1#123#abc==  
  
* valid scopes for Lambda
https://api.ebay.com/oauth/api_scope
https://api.ebay.com/oauth/api_scope/buy.order.readonly
https://api.ebay.com/oauth/api_scope/buy.guest.order
https://api.ebay.com/oauth/api_scope/sell.marketing.readonly
https://api.ebay.com/oauth/api_scope/sell.marketing
https://api.ebay.com/oauth/api_scope/sell.inventory.readonly
https://api.ebay.com/oauth/api_scope/sell.inventory
https://api.ebay.com/oauth/api_scope/sell.account.readonly
https://api.ebay.com/oauth/api_scope/sell.account
https://api.ebay.com/oauth/api_scope/sell.fulfillment.readonly
https://api.ebay.com/oauth/api_scope/sell.fulfillment
https://api.ebay.com/oauth/api_scope/sell.analytics.readonly
https://api.ebay.com/oauth/api_scope/sell.marketplace.insights.readonly
https://api.ebay.com/oauth/api_scope/commerce.catalog.readonly
https://api.ebay.com/oauth/api_scope/buy.shopping.cart
https://api.ebay.com/oauth/api_scope/buy.offer.auction
https://api.ebay.com/oauth/api_scope/commerce.identity.readonly
https://api.ebay.com/oauth/api_scope/commerce.identity.email.readonly
https://api.ebay.com/oauth/api_scope/commerce.identity.phone.readonly
https://api.ebay.com/oauth/api_scope/commerce.identity.address.readonly
https://api.ebay.com/oauth/api_scope/commerce.identity.name.readonly
https://api.ebay.com/oauth/api_scope/commerce.identity.status.readonly
https://api.ebay.com/oauth/api_scope/sell.finances
https://api.ebay.com/oauth/api_scope/sell.payment.dispute
https://api.ebay.com/oauth/api_scope/sell.item.draft
https://api.ebay.com/oauth/api_scope/sell.item
https://api.ebay.com/oauth/api_scope/sell.reputation
https://api.ebay.com/oauth/api_scope/sell.reputation.readonly
https://api.ebay.com/oauth/api_scope/commerce.notification.subscription
https://api.ebay.com/oauth/api_scope/commerce.notification.subscription.readonly
https://api.ebay.com/oauth/api_scope/sell.stores
https://api.ebay.com/oauth/api_scope/sell.stores.readonly
https://api.ebay.com/oauth/api_scope/commerce.vero
https://api.ebay.com/oauth/api_scope/sell.inventory.mapping
https://api.ebay.com/oauth/api_scope/commerce.message
https://api.ebay.com/oauth/api_scope/commerce.feedback
https://api.ebay.com/oauth/api_scope/commerce.shipping
https://api.ebay.com/oauth/api_scope
https://api.ebay.com/oauth/api_scope/buy.guest.order
https://api.ebay.com/oauth/api_scope/buy.item.feed
https://api.ebay.com/oauth/api_scope/buy.marketing
https://api.ebay.com/oauth/api_scope/buy.product.feed
https://api.ebay.com/oauth/api_scope/buy.marketplace.insights
https://api.ebay.com/oauth/api_scope/buy.proxy.guest.order
https://api.ebay.com/oauth/api_scope/buy.item.bulk
https://api.ebay.com/oauth/api_scope/buy.deal
https://api.ebay.com/oauth/api_scope/commerce.feedback.readonly
"""

import argparse
import base64
import json
import sys
from urllib import parse, request, error

import boto3

EBAY_ENVIRONMENT = "sandbox"
EBAY_AUTH_BASE = "https://auth.sandbox.ebay.com"
EBAY_IDENTITY_BASE = "https://api.sandbox.ebay.com"

SCOPES = [
    "https://api.ebay.com/oauth/api_scope",
    "https://api.ebay.com/oauth/api_scope/sell.inventory",
    "https://api.ebay.com/oauth/api_scope/sell.account",
    "https://api.ebay.com/oauth/api_scope/sell.fulfillment",
    "https://api.ebay.com/oauth/api_scope/sell.analytics.readonly",
    "https://api.ebay.com/oauth/api_scope/commerce.identity.readonly",
]


def build_consent_url(client_id: str, runame: str, scopes: list[str], state: str | None) -> str:
    params = {
        "client_id": client_id,
        "redirect_uri": runame,
        "response_type": "code",
        "scope": " ".join(scopes),
    }
    if state:
        params["state"] = state
    return f"{EBAY_AUTH_BASE}/oauth2/authorize?{parse.urlencode(params)}"


def exchange_code_for_tokens(client_id: str, client_secret: str, runame: str, auth_code: str) -> dict:
    creds = f"{client_id}:{client_secret}".encode("utf-8")
    basic = base64.b64encode(creds).decode("ascii")

    body = parse.urlencode(
        {
            "grant_type": "authorization_code",
            "code": auth_code,
            "redirect_uri": runame,
        }
    ).encode("utf-8")

    req = request.Request(
        url=f"{EBAY_IDENTITY_BASE}/identity/v1/oauth2/token",
        data=body,
        method="POST",
        headers={
            "Authorization": f"Basic {basic}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )

    try:
        with request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except error.HTTPError as e:
        raw = e.read().decode("utf-8")
        raise SystemExit(f"eBay token request failed with HTTP {e.code}: {raw}") from e
    except error.URLError as e:
        raise SystemExit(f"Unable to reach eBay sandbox token endpoint: {e}") from e


def update_secret(
    secret_name: str,
    secret_region: str,
    client_id: str,
    client_secret: str,
    refresh_token: str,
    existing_secret_json: str | None = None,
) -> None:
    sm = boto3.client("secretsmanager", region_name=secret_region)

    secret_doc = {}
    if existing_secret_json:
        secret_doc = json.loads(existing_secret_json)
    else:
        try:
            current = sm.get_secret_value(SecretId=secret_name)
            if current.get("SecretString"):
                secret_doc = json.loads(current["SecretString"])
        except sm.exceptions.ResourceNotFoundException:
            secret_doc = {}

    secret_doc["client_id"] = client_id
    secret_doc["client_secret"] = client_secret
    secret_doc["refresh_token"] = refresh_token
    secret_doc["environment"] = EBAY_ENVIRONMENT

    payload = json.dumps(secret_doc)

    try:
        sm.put_secret_value(SecretId=secret_name, SecretString=payload)
        print(f"Updated existing secret: {secret_name}")
    except sm.exceptions.ResourceNotFoundException:
        sm.create_secret(Name=secret_name, SecretString=payload)
        print(f"Created new secret: {secret_name}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--client-id", required=True)
    parser.add_argument("--client-secret")
    parser.add_argument("--runame", required=True, help="Your eBay Sandbox RuName")
    parser.add_argument("--auth-code", help="Authorization code returned by eBay after consent")
    parser.add_argument("--state", help="Optional state value for the consent URL")
    parser.add_argument("--print-consent-url", action="store_true")
    parser.add_argument("--secret-name")
    parser.add_argument("--secret-region")
    parser.add_argument("--write-secret", action="store_true")
    parser.add_argument(
        "--existing-secret-json",
        help="Optional JSON blob to merge when creating/updating the secret",
    )
    args = parser.parse_args()

    if args.print_consent_url or not args.auth_code:
        consent_url = build_consent_url(
            client_id=args.client_id,
            runame=args.runame,
            scopes=SCOPES,
            state=args.state,
        )
        print("Open this URL in a browser and sign in with your SANDBOX eBay test user:\n")
        print(consent_url)
        print("\nAfter eBay redirects back to your accept URL, copy the `code` value and run this script again with --auth-code.")
        if not args.auth_code:
            return

    if not args.client_secret:
        raise SystemExit("--client-secret is required when using --auth-code")

    token_response = exchange_code_for_tokens(
        client_id=args.client_id,
        client_secret=args.client_secret,
        runame=args.runame,
        auth_code=args.auth_code,
    )

    refresh_token = token_response.get("refresh_token")
    access_token = token_response.get("access_token")

    if not refresh_token:
        raise SystemExit(f"eBay did not return a refresh_token: {json.dumps(token_response, indent=2)}")

    print("\nSuccess. eBay returned tokens.\n")
    print(json.dumps(
        {
            "environment": EBAY_ENVIRONMENT,
            "token_type": token_response.get("token_type"),
            "expires_in": token_response.get("expires_in"),
            "refresh_token_expires_in": token_response.get("refresh_token_expires_in"),
            "has_access_token": bool(access_token),
            "has_refresh_token": bool(refresh_token),
            "refresh_token_preview": refresh_token,
        },
        indent=2,
    ))

    if args.write_secret:
        if not args.secret_name or not args.secret_region:
            raise SystemExit("--secret-name and --secret-region are required with --write-secret")
        update_secret(
            secret_name=args.secret_name,
            secret_region=args.secret_region,
            client_id=args.client_id,
            client_secret=args.client_secret,
            refresh_token=refresh_token,
            existing_secret_json=args.existing_secret_json,
        )
    else:
        print("\nStore this refresh_token in AWS Secrets Manager under the sandbox secret used by your Lambda.")


if __name__ == "__main__":
    main()
