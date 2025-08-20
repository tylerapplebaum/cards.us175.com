#demo-receive-event
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
    #timestamp = "T00:00:00Z"
    txnIdValue = str(uuid.uuid4())
    
    logger.info(event)
    logger.info(event['body'])
    
    #event['body']['TxnDate'] = event['body'].get('TxnDate',"01-01-1900") + timestamp
    #event['body']['TxnDate'] = event['body']['TxnDate' + timestamp]
    #event['body']['TxnId'] = txnIdValue
    bodyParsed = json.loads(event['body'])
    
    #itemDetailsValueStr = bodyParsed.get('ItemDetails', "")
    #itemDetailsValue = json.loads(itemDetailsValueStr)
    
    #itemset = itemDetailsValue.get('Set', "")
    #subset = itemDetailsValue.get('Subset',"")
    #cardnum = itemDetailsValue.get('CardNum', "")
    #players = itemDetailsValue.get('Players',"")
    
    itemset = bodyParsed.get('Set', "")
    subset = bodyParsed.get('Subset',"")
    cardnum = bodyParsed.get('CardNum', "")
    players = bodyParsed.get('Players',"")
    
    
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
                    'S': txnIdValue
                },
                'TxnType': {
                    'S': bodyParsed.get('TxnType', "")
                },
                'TxnSource': {
                    'S': bodyParsed.get('TxnSource', "")
                },
                'TxnDate': {
                    #'S': bodyParsed.get('TxnDate', "01-01-1900") + timestamp
                    'S': bodyParsed.get('TxnDate', "01-01-1900")
                },
                'eBayItemId': {
                    'S': bodyParsed.get('eBayItemId', "")
                },
                'PurchasePrice': {
                    'N': bodyParsed.get("PurchasePrice", "0")
                },
                'GradingFee': {
                    'N': bodyParsed.get("GradingFee", "0")
                },
                'SalePrice': {
                    'N': bodyParsed.get("SalePrice", "0")
                },
                'AccountRecv': {
                    'S': bodyParsed.get('AccountRecv', "")
                },
                'AccountSent': {
                    'S': bodyParsed.get('AccountSent', "")
                },
                'ItemType': {
                    'S': bodyParsed.get('ItemType', "")
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
    
    txnResponse = event['body']
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
