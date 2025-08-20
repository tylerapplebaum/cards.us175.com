#demo-get-price-archive
import boto3
from boto3.dynamodb.conditions import Key
import os
import json
import logging
import botocore
import sys

# Set up the logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Env variables from CFN
dynamodb = boto3.resource('dynamodb', region_name='us-east-2')
table = dynamodb.Table(os.environ.get('TableName'))

# Must paginate after 1MB (roughly 3800 items in DDB)

def lambda_handler(event, context):
    logger.info(event['body'])
    bodyParsed = json.loads(event['body'])
    def ddbquery():
        itemset = bodyParsed.get('Set', "")
        player = bodyParsed.get('Player',"")
        date = bodyParsed.get('Date', "")
        if itemset != '': #set case
            Index = "Set-Date-index"
            KeyName = 'Set'
            KeyVal = itemset
            SortKeyName = Date
            SortKeyVal = date
        elif player != '': #player case
            Index = "Player-Set-index"
            KeyName = 'Player'
            KeyVal = player
        else:
            sys.exit("No index selected")
        logger.info(Index)
        resp = table.query(
            IndexName=Index, #Set or Player index
            ScanIndexForward=False,
            #KeyConditionExpression=Key('Set').eq('Skybox E-X 2001')
            #KeyConditionExpression=Key('Player').eq('Derek Jeter')
            KeyConditionExpression=Key(KeyName).eq(KeyVal)
            #KeyConditionExpression=Key(KeyName).eq(KeyVal) & Key(SortKeyName).gt(SortKeyVal)
            #FilterExpression=Attr(AttrName1).eq(AttrVal1)
            #KeyConditionExpression=Key('Set').contains(itemset)
            #KeyConditionExpression=Key('Set').begins_with(itemset)
        )
        #print("The query returned the following items:")
        #for item in resp['Items']:
        #    print(item)
        return resp['Items']
    try:    
        items = ddbquery()
        #itemsNoNull = list(filter(None, ({key: val for key, val in sub.items() if val} for sub in items)))
    except botocore.exceptions.ClientError as error:
        # Put your error handling logic here
        raise error
        #def ddbquery_parse(ddbquery):
        #    for item in resp['Items']:
            # https://stackoverflow.com/a/73050
        #    itemsListSorted = sorted(itemsList, key=lambda d: d['Date'])
        #    itemsListSorted.reverse() # sort by most recent Date
        #return itemsListSorted
    #itemsJson = ddbquery_parse(ddbquery)
    #logger.info(itemsJson)
    responseObject = {}
    responseObject['StatusCode'] = 200
    responseObject['headers'] = {}
    responseObject['headers']['Content-Type'] = 'application/json'
    responseObject['body'] = items
    #logger.info(responseObject)
    
    return (
        responseObject
    )
