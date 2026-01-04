# cards.us175.com

## Authentication

## Backend

## Frontend

## To do (Inventory)
- Fix sign out functionality. Use a custom Cognito domain (auth.us175.com). Use a Lambda function on logout to clear cookies.
- Adapt the Lambda function in PriceArchive to generate players.json for the Inventory site. Will require cleanup of many player names, and maybe implementing a 'Notes' field to capture SP/SSP details that are currently stored along with the PlayerName data.
- Re-run the PurchaseDate utility to capture dates in other formats and convert them to ISO8601.
- Finish writing readme; add architecture and data flow diagrams.

## To do (PriceArchive)
- Merge all of the changes from the Inventory site.