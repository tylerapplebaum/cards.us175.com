# cards.us175.com

## Authentication

## Backend

## Frontend

## To do (Inventory)
1) Fix sign out functionality. Use a custom Cognito domain (auth.us175.com). Use a Lambda function on logout to clear cookies.
2) Move sets.json, subsets.json, boxes.json to /Inventory/partials/ and update reference in lookups.js.
3) Adapt the Lambda function in PriceArchive to generate players.json for the Inventory site. Will require cleanup of many player names, and maybe implementing a 'Notes' field to capture SP/SSP details that are currently stored along with the PlayerName data.
4) Re-run the PurchaseDate utility to capture dates in other formats and convert them to ISO8601.
5) Finish writing readme; add architecture and data flow diagrams.

## To do (PriceArchive)
1) Merge all of the changes from the Inventory site.