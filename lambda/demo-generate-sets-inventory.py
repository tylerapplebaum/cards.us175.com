import boto3
import os
import json
import logging

# Set up clients and resources
ddbclient = boto3.client('dynamodb')
s3 = boto3.resource('s3')
outputObjectName1 = "sets.json"
outputObjectName2 = "subsets.json"

# Set up the logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Env variables from CFN
tablename = os.environ.get('TableName')
index1name = os.environ.get('Index1Name')

def lambda_handler(event, context):

    def ddb_client(tablename):
        ddbresponse = ddbclient.scan(
            ReturnConsumedCapacity='TOTAL',
            TableName=tablename,
            IndexName=index1name,
            ProjectionExpression='#S, #SUB',
            ExpressionAttributeNames={"#S":"Set", "#SUB":"Subset"}
        )
        return ddbresponse
        
    try:    
        ddb_response = ddb_client(tablename)
    except botocore.exceptions.ClientError as error:
        # Put your error handling logic here
        raise error
    
    # Sets and Subsets
    SetList = []
    SubsetList = []
    for Item in ddb_response['Items']:
        SetList.append(Item['Set']['S'])
        if 'Subset' in Item:
            SubsetList.append(Item['Subset']['S'])
    	
    SetListSorted = sorted(list(set(SetList)))
    SetDict = {'Sets': SetListSorted}
    JsonSetDict = json.dumps(SetDict)
    
    SubsetListSorted = sorted(list(set(SubsetList)))
    SubsetDict = {'Subsets': SubsetListSorted}
    JsonSubsetDict = json.dumps(SubsetDict)
    
    bucket = 'dev.txn.us175.com'
    key1 = 'Inventory/' + outputObjectName1
    key2 = 'Inventory/' + outputObjectName2
    s3.Object(bucket, key1).put(Body=JsonSetDict)
    s3.Object(bucket, key2).put(Body=JsonSubsetDict)
    return {
        'statusCode': 200,
        'body': json.dumps(JsonSetDict)
    }
