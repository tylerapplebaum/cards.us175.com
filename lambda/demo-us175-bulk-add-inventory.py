#demo-us175-bulk-add-inventory
import os
import json
import uuid
import logging
import base64
import csv
import io
import boto3
import botocore
from botocore.exceptions import ClientError

# Set up clients and resources
ddbclient = boto3.client('dynamodb')

# Set up the logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Env variables from CFN
tablename = os.environ.get('TableName')

def lambda_handler(event, context):

    #logger.info(event)
    #logger.info(event['body'])

    bodyParsed = json.loads(event['body'])
    csvFile = bodyParsed.get('CSVFile')
    csvFileDecoded = base64.b64decode(csvFile).decode('utf-8')
    with io.StringIO(csvFileDecoded) as fp:
        reader = csv.DictReader(fp, delimiter=",", quotechar='"')
        csvData = [row for row in reader]
    logger.info(csvData)

    def ddb_client(tablename):
        ddbresponse = ddbclient.update_item(
            Key={
                'guid': {
                    'S': csvItem.get('guid')
                }
            },
            UpdateExpression='SET #itemset = :itemset, #itemyear = :itemyear, #itemsubset = :itemsubset, #itemplayer = :itemplayer, #itemqty = :itemqty, #itemcardnum = :itemcardnum, #itembrand = :itembrand, #itemauthenticator = :itemauthenticator, #itemgrade = :itemgrade',
            ExpressionAttributeNames={
                '#itemset': 'Set',
                '#itemyear': 'Year',
                '#itemsubset': 'Subset',
                '#itemplayer': 'PlayerName',
                '#itemqty': 'Qty',
                '#itemcardnum': 'CardNum',
                '#itembrand': 'Brand',
                '#itemauthenticator': 'Authenticator',
                '#itemgrade': 'Grade'
            },
            ExpressionAttributeValues={
                ':itemset': {
                    'S': csvItem.get('Set', "")
                },
                ':itemyear': {
                    'S': csvItem.get('Year', "")
                },
                ':itemsubset': {
                    'S': csvItem.get('Subset', "")
                },
                ':itemplayer': {
                    'S': csvItem.get('PlayerName', "")   
                },
                ':itemqty':{
                    'N': csvItem.get('Qty', "")
                },
                ':itemcardnum':{
                    'S': csvItem.get('CardNum', "")
                },
                ':itembrand':{
                    'S': csvItem.get('Brand', "")
                },
                ':itemauthenticator':{
                    'S': csvItem.get('Authenticator', "")
                },
                ':itemgrade':{
                    'N': csvItem.get('Grade', 0) if csvItem.get('Grade') else '0'
                }
            },
            ReturnValues='UPDATED_NEW',
            ReturnConsumedCapacity='TOTAL',
            TableName=tablename
        )
        return ddbresponse

    if any(dictionary.get('guid') for dictionary in csvData):
      for csvItem in csvData:
        if csvItem.get('guid'): # detect update case
            try:    
                ddb_response = ddb_client(tablename)
                logger.info(ddb_response)
            except botocore.exceptions.ClientError as error:
                # Put your error handling logic here
                raise error
    if not any(dictionary.get('guid') for dictionary in csvData):
        def batch_write(tablename):
            batch_items = {tablename: []}
            #guid = str(uuid.uuid4()) # assign a guid to each item
            for csvItem in csvData:
                batch_items[tablename].append({
                    'PutRequest': {
                        'Item': {
                            'guid': {'S': str(uuid.uuid4())},
                            'Set': {'S': csvItem.get('Set')},
                            'Year': {'S': csvItem.get('Year', "None")},
                            'Subset': {'S': csvItem.get('Subset', "None")},
                            'PlayerName': {'S': csvItem.get('PlayerName', "None")},
                            'Qty': {'N': csvItem.get('Qty', 0)},
                            'QtyMade': {'N': csvItem.get('QtyMade', 0)},
                            'CardNum': {'S': csvItem.get('CardNum', "None")},
                            'Authenticator': {'S': csvItem.get('Authenticator', "None")},
                            'Grade': {'N': csvItem.get('Grade', 0) if csvItem.get('Grade') else '0'},
                            'Brand': {'S': csvItem.get('Brand', "None")}
                        }
                    }
                })
                if len(batch_items[tablename]) == 25:
                    try:
                        response = ddbclient.batch_write_item(RequestItems=batch_items)
                        print(f"Processed 25 items. Unprocessed: {response['UnprocessedItems']}")
                        batch_items[tablename] = []
                    except ClientError as e:
                        print(f"Error processing batch: {e}")
                        return
        
            # Send any remaining items
            if batch_items[tablename]:
                try:
                    response = ddbclient.batch_write_item(RequestItems=batch_items)
                    print(f"Processed remaining items. Unprocessed: {response['UnprocessedItems']}")
                except ClientError as e:
                    print(f"Error processing final batch: {e}")
        
        try:    
            ddb_response = batch_write(tablename)
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
