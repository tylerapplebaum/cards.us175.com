#demo-update-event-inventory
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

    #logger.info(event)
    #logger.info(event['body'])

    bodyParsed = json.loads(event['body'])

    def ddb_client(tablename):
        ddbresponse = ddbclient.update_item(
            Key={
                'guid': {
                    'S': bodyParsed.get('guid')
                }
            },
            UpdateExpression='SET #itemset = :itemset, \
            #itemyear = :itemyear, \
            #itemsubset = :itemsubset, \
            #itemplayer = :itemplayer, \
            #itemqty = :itemqty, \
            #itemcardnum = :itemcardnum, \
            #itemserialnumber = :itemserialnumber, \
            #itemauthenticator = :itemauthenticator, \
            #itemgrade = :itemgrade, \
            #itemcertnumber = :itemcertnumber, \
            #itemtxnid = :itemtxnid, \
            #itemebayitemid = :itemebayitemid, \
            #itempurchaseprice = :itempurchaseprice, \
            #itemsaleprice = :itemsaleprice, \
            #itemtxndate = :itemtxndate, \
            #itemtxnsource = :itemtxnsource, \
            #itemtxntype = :itemtxntype, \
            #itemgradingfee = :itemgradingfee',
            ExpressionAttributeNames={
                '#itemset': 'Set',
                '#itemyear': 'Year',
                '#itemsubset': 'Subset',
                '#itemplayer': 'PlayerName',
                '#itemqty': 'Qty',
                '#itemcardnum': 'CardNum',
                '#itemserialnumber': 'SerialNumber',
                '#itemauthenticator': 'Authenticator',
                '#itemgrade': 'Grade',
                '#itemcertnumber': 'CertNumber',
                '#itemtxnid': 'TxnId',
                '#itemebayitemid': 'eBayItemId',
                '#itempurchaseprice': 'PurchasePrice',
                '#itemsaleprice': 'SalePrice',
                '#itemtxndate': 'TxnDate',
                '#itemtxnsource': 'TxnSource',
                '#itemtxntype': 'TxnType',
                '#itemgradingfee': 'GradingFee'
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
                    'S': bodyParsed.get('PlayerName', "")   
                },
                ':itemqty':{
                    'N': bodyParsed.get('Qty', "")
                },
                ':itemcardnum':{
                    'S': bodyParsed.get('CardNum', "")
                },
                ':itemserialnumber':{
                    'S': bodyParsed.get('SerialNumber', "")
                },
                ':itemauthenticator':{
                    'S': bodyParsed.get('Authenticator', "")
                },
                ':itemgrade':{
                    'S': bodyParsed.get('Grade', "")
                },
                ':itemcertnumber':{
                    'S': bodyParsed.get('CertNumber', "")
                },
                ':itemtxnid':{
                    'S': bodyParsed.get('TxnId', "")
                },
                ':itemebayitemid':{
                    'S': bodyParsed.get('eBayItemId', "")
                },
                ':itempurchaseprice':{
                    'N': bodyParsed.get('PurchasePrice', 0)
                },
                ':itemsaleprice':{
                    'S': bodyParsed.get('SalePrice', "")
                },
                ':itemtxndate':{
                    'S': bodyParsed.get('TxnDate', "")
                },
                ':itemtxnsource':{
                    'S': bodyParsed.get('TxnSource', "")
                },
                ':itemtxntype':{
                    'S': bodyParsed.get('TxnType', "")
                },
                ':itemgradingfee':{
                    'S': bodyParsed.get('GradingFee', "")
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
