#demo-receive-event-inventory
import os
import json
import uuid
import logging
import boto3
import botocore
import base64

# Set up clients and resources
ddbclient = boto3.client('dynamodb')

# Set up the logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Env variables from CFN
tablename = os.environ.get('TableName')

def lambda_handler(event, context):
    guid = str(uuid.uuid4())
    #logger.info(event)
    logger.info(event['body'])
    bodyParsed = json.loads(event['body'])

    players = bodyParsed.get('PlayerName',"")
    
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

    def safe_number(value):
        try:
            return str(float(value)) if value else '0'
        except ValueError:
            return '0'

    def safe_string(value):
        return value if isinstance(value, str) else ""
    
    def ddb_client(tablename):
        ddbresponse = ddbclient.put_item(
            Item={
                'guid': {'S': guid},
                'Year': {'S': bodyParsed.get('Year', "")},
                'Set': {'S': bodyParsed.get('Set', "")},
                'Subset': {'S': bodyParsed.get('Subset', "")},
                'PlayerName': listType,
                'Authenticator': {'S': bodyParsed.get('Authenticator', "")},
                'Grade': {'N': safe_number(bodyParsed.get('Grade'))},
                'CertNumber': {'S': bodyParsed.get('CertNumber', "")},
                'SerialNumber': {'S': bodyParsed.get('SerialNumber', "")},
                'TxnDate': {'S': bodyParsed.get('TxnDate', "")},
                'TxnId': {'S': bodyParsed.get('TxnId', "")},
                'TxnSource': {'S': bodyParsed.get("TxnSource", "")},
                'CardNum': {'S': bodyParsed.get("CardNum", "")},
                'eBayItemId': {'S': bodyParsed.get("eBayItemId", "")},
                'PurchasePrice': {'N': safe_number(bodyParsed.get("PurchasePrice"))},
                'MktVal': {'N': safe_number(bodyParsed.get("MktVal"))},
                'BoxNum': {'S': bodyParsed.get("BoxNum", "")},
                'Qty': {'N': safe_number(bodyParsed.get("Qty"))},
                'TxnType': {'S': bodyParsed.get("TxnType", "")},
                'GradingFee': {'N': safe_number(bodyParsed.get("GradingFee"))},
                'SalePrice': {'N': safe_number(bodyParsed.get("SalePrice"))},
                'SaleDate': {'S': safe_string(bodyParsed.get("SaleDate"))},
                'SaleMarketplace': {'S': safe_string(bodyParsed.get("SaleMarketplace"))},
                'SoldeBayItemId': {'S': safe_string(bodyParsed.get("SoldeBayItemId"))},
                'SoldTxnId': {'S': safe_string(bodyParsed.get("SoldTxnId"))}
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
    
    #txnResponse = event['body']
    responseObject = {}
    responseObject['StatusCode'] = 200
    responseObject['headers'] = {}
    responseObject['headers']['Content-Type'] = 'application/json'
    responseObject['body'] = ddb_response
    
    return (
        responseObject
    )
