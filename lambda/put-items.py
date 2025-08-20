import os
import json
import uuid
import logging
import boto3
import botocore

# Set up clients and resources
ddbclient = boto3.client('dynamodb')

# Set up the logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Env variables from CFN
tablename = os.environ.get('TableName')

def lambda_handler(event, context):
    timestamp = "T00:00:00Z"
    txnIdValue = str(uuid.uuid4())
    
    event['queryStringParameters']['TxnDate'] = event['queryStringParameters'].get('TxnDate',"01-01-1900") + timestamp
    event['queryStringParameters']['TxnId'] = txnIdValue
    
    itemDetailsValueStr = event['queryStringParameters'].get('ItemDetails', "")
    itemDetailsValue = json.loads(itemDetailsValueStr)
    
    itemset = itemDetailsValue.get('Set', "")
    subset = itemDetailsValue.get('Subset',"")
    cardnum = itemDetailsValue.get('CardNum', "")
    players = itemDetailsValue.get('Players',"")
    
    if isinstance(players, list):
        playerList = []
        for player in players:
            playerstr = {"S": player}
            playerList.append(playerstr)
        listType = {"L": playerList}
    elif isinstance(players, str):
        listType = {"S": players}
    else:
        print("Players is neither string or list")

    itemDetailsStructure = {
        "Set":{"S":itemset},
        "Subset":{"S":subset},
        "CardNum":{"S":cardnum},
        "Players":listType
    }
    
    def ddb_client(tablename):
        ddbresponse = ddbclient.put_item(
            Item={
                'TxnId': {
                    'S': event['queryStringParameters'].get('TxnId', "0000-0000-0000")
                },
                'TxnType': {
                    'S': event['queryStringParameters'].get('TxnType', "")
                },
                'TxnSource': {
                    'S': event['queryStringParameters'].get('TxnSource', "")
                },
                'TxnDate': {
                    'S': event['queryStringParameters'].get('TxnDate', "01-01-1900")
                },
                'eBayItemId': {
                    'S': event['queryStringParameters'].get('eBayItemId', "")
                },
                'PurchasePrice': {
                    'N': event['queryStringParameters'].get("PurchasePrice", 0)
                },
                'GradingFee': {
                    'N': event['queryStringParameters'].get("GradingFee", 0)
                },
                'SalePrice': {
                    'N': event['queryStringParameters'].get("SalePrice", 0)
                },
                'AccountRecv': {
                    'S': event['queryStringParameters'].get('AccountRecv', "")
                },
                'AccountSent': {
                    'S': event['queryStringParameters'].get('AccountSent', "")
                },
                'ItemType': {
                    'S': event['queryStringParameters'].get('ItemType', "")
                },
                'ItemDetails': {
                    'M': itemDetailsStructure
                }
            },
            ReturnConsumedCapacity='TOTAL',
            TableName=tablename
        )
        return ddbresponse
    
    try:    
        ddb_response = ddb_client(tablename)
        logger.info(ddb_response)
    except botocore.exceptions.ClientError as error:
        # Put your error handling logic here
        raise error
    
    txnResponse = event['queryStringParameters']
    #txnResponse['txnIdValue'] = txnIdValue
    #txnResponse['txnTypeValue'] = txnTypeValue
    #txnResponse['txnSourceValue'] = txnSourceValue
    #txnResponse['txnDateValue'] = txnDateValue
    #txnResponse['eBayItemIdValue'] = eBayItemIdValue
    #txnResponse['purchasePriceValue'] = purchasePriceValue
    #txnResponse['gradingFeeValue'] = gradingFeeValue
    #txnResponse['salePriceValue'] = salePriceValue
    #txnResponse['accountRecvValue'] = accountRecvValue
    #txnResponse['accountSentValue'] = accountSentValue
    #txnResponse['itemTypeValue'] = itemTypeValue
    #txnResponse['itemDetailsValue'] = itemDetailsValue
    
    responseObject = {}
    responseObject['StatusCode'] = 200
    responseObject['headers'] = {}
    responseObject['headers']['Content-Type'] = 'application/json'
    responseObject['body'] = txnResponse
    
    return (
        responseObject
    )
