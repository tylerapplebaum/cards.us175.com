#demo-get-price-archive
import boto3
from boto3.dynamodb.conditions import Key, Attr
import os
import json
import logging
import botocore
import sys
from natsort import natsorted

# Set up the logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Env variables from CFN
dynamodb = boto3.resource('dynamodb', region_name='us-east-2')
table = dynamodb.Table(os.environ.get('TableName'))
index = os.environ.get('IndexName')

# Must paginate after 1MB of scanned/queried data (roughly 3800 items in DDB).
# Pagination done: https://www.beabetterdev.com/2021/10/20/dynamodb-scan-query-not-returning-data/

def lambda_handler(event, context):
    logger.info(event['body'])
    bodyParsed = json.loads(event['body'])
    
    def ddbquery():
        lastEvaluatedKey = None
        SortKeyName = 'Year'
        SortKeyVal = bodyParsed.get('Year', "")
        KeyName = 'Set'
        KeyVal = bodyParsed.get('Set', "")
        AttrName1 = 'Subset'
        AttrVal1 = bodyParsed.get('Subset', "")
        AttrName2 = 'Qty'
        AttrVal2 = int(bodyParsed.get('Qty', "0"))
        
        key_condition_expression = Key(KeyName).eq(KeyVal) 
        if SortKeyVal != "" and SortKeyVal is not None:
            key_condition_expression &= Key(SortKeyName).eq(SortKeyVal)
        
        filter_expression = None
        if AttrVal1 != "": #Condition: Subset specified
            filter_expression = Attr(AttrName1).eq(AttrVal1)
        if AttrVal2 != 0: #Condition: Qty specified
            if filter_expression:
                filter_expression &= Attr(AttrName2).eq(AttrVal2)
            else:
                filter_expression = Attr(AttrName2).eq(AttrVal2)
        
        logger.info(f"Index: {index}")
        logger.info(f"SortKeyVal: {SortKeyVal}")
        logger.info(f"KeyVal: {KeyVal}")
        logger.info(f"AttrVal1: {AttrVal1}")
        logger.info(f"AttrVal2: {AttrVal2}")
        
        items = [] # Result Array
        while True:
            query_params = {
                'IndexName': index,
                'ScanIndexForward': False,
                'KeyConditionExpression': key_condition_expression
            }
            if filter_expression:
                query_params['FilterExpression'] = filter_expression
            if lastEvaluatedKey:
                query_params['ExclusiveStartKey'] = lastEvaluatedKey
            
            resp = table.query(**query_params)
            
            items.extend(resp['Items'])
            if 'LastEvaluatedKey' in resp:
                lastEvaluatedKey = resp['LastEvaluatedKey']
            else:
                break
        
        itemsListSorted = natsorted(items, key=lambda d: d['CardNum'])
        return itemsListSorted

    try:    
        ddbitems = ddbquery()
    except botocore.exceptions.ClientError as error:
        # Put your error handling logic here
        raise error

    responseObject = {
        'StatusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': ddbitems
    }
    
    return responseObject