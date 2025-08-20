#demo-delete-event-price-archive
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
    #logger.info(event)
    bodyParsed = json.loads(event['body'])
    logger.info(bodyParsed)
    #cardnum = bodyParsed.get('CardNum', "")
    archiveIdValue = bodyParsed.get('ArchiveId',"")
    logger.info(archiveIdValue)
    
    # need to set up if/else so this doesn't run in the event that no screenshot exists
    #bucket = s3.Bucket('dev.txn.us175.com')
    #path_tmp = '/tmp/output'
    #mimetype = bodyParsed.get('Mimetype',"")
    #ext = mimetype.replace('image/','')
    #key = 'PriceArchive/pricearchiveimg/' + archiveIdValue + '.' + ext
    #data = bodyParsed.get('Screenshot', "")
    #img = base64.b64decode(data)
    #with open(path_tmp, 'wb') as data:
    #    data.write(img)
    #    bucket.upload_file(path_tmp, key, ExtraArgs={'ContentType': mimetype})
    #logger.info(key)
    #fullPath = cloudFrontBasePath + '/' + archiveIdValue + '.' + ext
    #logger.info(fullPath)
    
    def ddb_client(tablename):
        ddbresponse = ddbclient.delete_item(
            Key={
                'ArchiveId': {
                    'S': archiveIdValue
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
    
    #txnResponse = event['body']
    responseObject = {}
    responseObject['StatusCode'] = 200
    responseObject['headers'] = {}
    responseObject['headers']['Content-Type'] = 'application/json'
    responseObject['body'] = ddb_response
    
    return (
        responseObject
    )
