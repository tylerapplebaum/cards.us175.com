import boto3
import os
import json
import logging

# Set up clients and resources
ddbclient = boto3.client('dynamodb')
s3 = boto3.resource('s3')
cloudFrontBasePath = "https://dev.txn.us175.com/PriceArchive/pricearchiveimg"
outputObjectName = "sets2.json"

# Set up the logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Env variables from CFN
tablename = os.environ.get('TableName')
index1name = os.environ.get('Index1Name')
index2name = os.environ.get('Index2Name')

def lambda_handler(event, context):

    def ddb_client(tablename):
        ddbresponse = ddbclient.scan(
            ReturnConsumedCapacity='TOTAL',
            TableName=tablename,
            IndexName=index2name,
            ProjectionExpression='#S',
            ExpressionAttributeNames={"#S":"Set"}
        )
        return ddbresponse
        
    try:    
        ddb_response = ddb_client(tablename)
    except botocore.exceptions.ClientError as error:
        # Put your error handling logic here
        raise error
        
    SetList = []
    for Set in ddb_response['Items']:
    	SetList.append(Set['Set']['S'])
    	
    SetListSorted = sorted(list(set(SetList)))
    SetDict = {'Sets': SetListSorted}
    JsonSetDict = json.dumps(SetDict)
    
    bucket = 'dev.txn.us175.com'
    key = 'PriceArchive/' + outputObjectName
    s3.Object(bucket, key).put(Body=JsonSetDict)
    return {
        'statusCode': 200,
        'body': json.dumps(JsonSetDict)
    }
