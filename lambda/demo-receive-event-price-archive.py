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
    archiveIdValue = str(uuid.uuid4())
    
    #logger.info(event)
    #logger.info(event['body'])
    
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
    
    #year = bodyParsed.get('Year', "")
    #itemset = bodyParsed.get('Set', "")
    #subset = bodyParsed.get('Subset',"")
    #cardnum = bodyParsed.get('CardNum', "")
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
    #itemDetailsStructure = {
    #    "Set":{"S":itemset},
    #    "Subset":{"S":subset},
    #    "CardNum":{"S":cardnum},
    #    "Players":listType
    #}
    
    # need to set up if/else so this doesn't run in the event that no screenshot exists
    bucket = s3.Bucket('dev.txn.us175.com')
    path_tmp = '/tmp/output'
    mimetype = bodyParsed.get('Mimetype',"")
    ext = mimetype.replace('image/','')
    key = 'PriceArchive/pricearchiveimg/' + archiveIdValue + '.' + ext
    data = bodyParsed.get('Screenshot', "")
    img = base64.b64decode(data)
    with open(path_tmp, 'wb') as data:
        data.write(img)
        bucket.upload_file(path_tmp, key, ExtraArgs={'ContentType': mimetype})
    logger.info(key)
    fullPath = cloudFrontBasePath + '/' + archiveIdValue + '.' + ext
    logger.info(fullPath)
    
    def ddb_client(tablename):
        ddbresponse = ddbclient.put_item(
            Item={
                'ArchiveId': {
                    'S': archiveIdValue
                },
                'Year': {
                    'S': bodyParsed.get('Year', "")
                },
                'Set': {
                    'S': bodyParsed.get('Set', "")
                },
                'Subset': {
                    'S': bodyParsed.get('Subset', "")
                },
                'Player': listType,
                    #'S': bodyParsed.get('Players', "")
                'Grade': {
                    'S': bodyParsed.get('Grade', "")
                },     
                'Date': {
                    #'S': bodyParsed.get('TxnDate', "01-01-1900") + timestamp
                    'S': bodyParsed.get('TxnDate', "01-01-1900")
                },
                'ItemType': {
                    'S': bodyParsed.get('ItemType', "")
                },
                'Price': {
                    'N': bodyParsed.get("Price", "0")
                },
                'Source': {
                    'S': bodyParsed.get("Source", "")
                },
                'Screenshot': {
                    'S': fullPath
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
