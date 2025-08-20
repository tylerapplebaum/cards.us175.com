#demo-get-transactions
import os
import json
import logging
import boto3
import botocore

# Set up clients and resources
ddbclient = boto3.client('dynamodb')

# Set up the logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Env variables from CFN
tablename = os.environ.get('TableName')

# To do: 
# Implement Query
# Must paginate after 1MB (roughly 3800 items in DDB)

def lambda_handler(event, context):
    def ddb_client(tablename):
        ddbresponse = ddbclient.scan(
            ReturnConsumedCapacity='TOTAL',
            TableName=tablename,
            Select='ALL_ATTRIBUTES'
        )
        return ddbresponse
    
    try:    
        ddb_response = ddb_client(tablename)
    except botocore.exceptions.ClientError as error:
        # Put your error handling logic here
        raise error
    def parseddbresponse(ddb_response):
        itemsList = []
        itemDict = {}
        for item in ddb_response['Items']:
            ItemTypeDict = {'ItemType':item['ItemType']['S']}
            itemDict |= ItemTypeDict
            SalePriceDict = {'SalePrice':item['SalePrice']['N']}
            itemDict |= SalePriceDict
            PurchasePriceDict = {'PurchasePrice':item['PurchasePrice']['N']}
            itemDict |= PurchasePriceDict
            TxnIdDict = {'TxnId':item['TxnId']['S']}
            itemDict |= TxnIdDict
            AccountRecvDict = {'AccountRecv':item['AccountRecv']['S']}
            itemDict |= AccountRecvDict
            TxnSourceDict = {'TxnSource':item['TxnSource']['S']}
            itemDict |= TxnSourceDict
            TxnTypeDict = {'TxnType':item['TxnType']['S']}
            itemDict |= TxnTypeDict
            eBayItemIdDict = {'eBayItemId':item['eBayItemId']['S']}
            itemDict |= eBayItemIdDict
            CardNumDict = {'CardNum':item['ItemDetails']['M']['CardNum']['S']}
            itemDict |= CardNumDict
            SetDict = {'Set':item['ItemDetails']['M']['Set']['S']}
            itemDict |= SetDict
            SubsetDict = {'Subset':item['ItemDetails']['M']['Subset']['S']}
            itemDict |= SubsetDict
            if 'L' in item['ItemDetails']['M']['Players']:
                Players = item['ItemDetails']['M']['Players']['L']
                PlayersList = []
                for P in Players:
                    PlayersList.append(P['S'])
                PlayersDict = {'Players':PlayersList}
            elif 'S' in item['ItemDetails']['M']['Players']:
                PlayersDict = {'Players':item['ItemDetails']['M']['Players']['S']}
            else:
                PlayersDict = {'Players':null}
            itemDict |= PlayersDict
            TxnDateDict = {'TxnDate':item['TxnDate']['S']}
            itemDict |= TxnDateDict
            GradingFeeDict = {'GradingFee':item['GradingFee']['N']}
            itemDict |= GradingFeeDict
            AccountSentDict = {'AccountSent':item['AccountSent']['S']}
            itemDict |= AccountSentDict
            
            itemsList.append(itemDict.copy())
            #logger.info(itemsList)
            # https://stackoverflow.com/a/73050
            itemsListSorted = sorted(itemsList, key=lambda d: d['TxnDate'])
            itemsListSorted.reverse() # sort by most recent TxnDate
        return itemsListSorted
    itemsJson = parseddbresponse(ddb_response)
    #logger.info(itemsJson)
    responseObject = {}
    responseObject['StatusCode'] = 200
    responseObject['headers'] = {}
    responseObject['headers']['Content-Type'] = 'application/json'
    responseObject['body'] = itemsJson
    #logger.info(responseObject)
    
    return (
        responseObject
    )
