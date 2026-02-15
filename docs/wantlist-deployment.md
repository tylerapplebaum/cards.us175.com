# Wantlist Deployment Notes

## 1) Public CloudFront behavior
- Add a behavior with path pattern `Inventory/wantlist*`.
- Do not attach the Cognito auth Lambda@Edge to this behavior.
- Keep the same S3/static origin used for `Inventory`.
- Ensure the index-rewrite Lambda (`cloudfront-handlemissingindex`) is attached so `/Inventory/wantlist/` maps to `/Inventory/wantlist/index.html`.

## 2) Public files
- Publish these objects:
  - `Inventory/wantlist/index.html`
  - `Inventory/wantlist/js/wantlist.js`
  - `Inventory/wantlist/wantlist.json`

## 3) Generator Lambda
- Deploy `lambda/demo-generate-wantlist.py` as a Lambda function.
- Environment variables:
  - `TableName=us175-inventory-3`
  - `OutputBucket=<your static site bucket>`
  - `OutputKey=Inventory/wantlist/wantlist.json`
  - `RegionName=us-east-2`
- IAM permissions:
  - `dynamodb:Scan` on table `us175-inventory-3`
  - `s3:PutObject` for `${OutputBucket}/${OutputKey}`
- Trigger with EventBridge schedule (example: every 15 minutes).

## 4) Optional auth-lambda-only approach
- `lambda/cloudfront-auth/lambda_function.py` now includes a public-path bypass for:
  - `/Inventory/wantlist`
  - `/Inventory/wantlist/*`
- If you keep auth Lambda on broader behaviors, this bypass still allows unauthenticated access.
