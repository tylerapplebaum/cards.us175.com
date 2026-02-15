import re

def lambda_handler(event, context):
    request = event["Records"][0]["cf"]["request"]
    uri = request["uri"]
    # Support extensionless request for the public wantlist page.
    if uri == "/Inventory/wantlist":
        uri = "/Inventory/wantlist/index.html"
    uri = re.sub(r"/$", "/index.html", uri)
    request["uri"] = uri
    return request
