import urllib.parse

# Hardcoded for Lambda@Edge
#USER_POOL_DOMAIN = "test-us175.auth.us-east-2.amazoncognito.com"
USER_POOL_DOMAIN = "auth.us175.com"
CLIENT_ID = "38s6ieqmen5mf0oi0glnbhigj6"
LOGOUT_REDIRECT = "https://inv.us175.com/landing/"

def lambda_handler(event, context):
    # Build Cognito logout URL
    logout_uri = (
        f"https://{USER_POOL_DOMAIN}/logout"
        f"?client_id={CLIENT_ID}"
        f"&logout_uri={urllib.parse.quote(LOGOUT_REDIRECT, safe='')}"
    )

    # Must match original cookie attributes exactly
    cookie_attrs = "Path=/; Domain=.us175.com; Secure; HttpOnly; SameSite=None; Max-Age=0"

    expired_cookies = [
        f"idToken=; {cookie_attrs}",
        f"accessToken=; {cookie_attrs}",
        f"refreshToken=; {cookie_attrs}",
    ]

    response = {
        "status": "307",
        "statusDescription": "Temporary Redirect",
        "headers": {
            "location": [{"key": "Location", "value": logout_uri}],
            "set-cookie": [{"key": "Set-Cookie", "value": c} for c in expired_cookies],
        },
    }

    return response
