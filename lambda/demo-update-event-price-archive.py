#demo-receive-event-price-archive
import os
import json
import uuid
import logging
import boto3
import botocore
import base64

# Set up clients and resources
ddbclient = boto3.client('dynamodb')
s3 = boto3.resource('s3')
cloudFrontBasePath = "https://dev.txn.us175.com/PriceArchive/pricearchiveimg"

# Set up the logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Env variables from CFN
tablename = os.environ.get('TableName')

def lambda_handler(event, context):
    #timestamp = "T00:00:00Z"
    #logger.info(event)
    #logger.info(event['body'])

    bodyParsed = json.loads(event['body'])
    '''
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
    #print(listType)
    '''
    def ddb_client(tablename):
        ddbresponse = ddbclient.update_item(
            Key={
                'ArchiveId': {
                    'S': bodyParsed.get('ArchiveId')
                }
            },
            UpdateExpression='SET #itemset = :itemset, #itemyear = :itemyear, #itemsubset = :itemsubset, #itemplayer = :itemplayer, #itemgrade = :itemgrade, #itemdate = :itemdate, #itemprice = :itemprice, #itemsource = :itemsource, #itemtype = :itemtype',
            ExpressionAttributeNames={
                '#itemset': 'Set',
                '#itemyear': 'Year',
                '#itemsubset': 'Subset',
                '#itemplayer': 'Player',
                '#itemgrade': 'Grade',
                '#itemdate': 'Date',
                '#itemprice': 'Price',
                '#itemsource': 'Source',
                '#itemtype': 'Type'
            },
            ExpressionAttributeValues={
                ':itemset': {
                    'S': bodyParsed.get('Set', "")
                },
                ':itemyear': {
                    'S': bodyParsed.get('Year', "")
                },
                ':itemsubset': {
                    'S': bodyParsed.get('Subset', "")
                },
                ':itemplayer': {
                    'S': bodyParsed.get('Players', "")   
                },
                ':itemgrade':{
                    'S': bodyParsed.get('Grade', "")
                },
                ':itemdate': {
                    'S': bodyParsed.get('TxnDate', "01-01-1900")
                },
                ':itemprice': {
                    'N': bodyParsed.get("Price", "0")
                },
                ':itemsource': {
                    'S': bodyParsed.get("Source", "")
                },
                ':itemtype': {
                    'S': bodyParsed.get('ItemType', "")
                }
            },
            ReturnValues='UPDATED_NEW',
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
