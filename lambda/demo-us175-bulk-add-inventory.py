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

    bodyParsed = json.loads(event['body'])
    csvFile = bodyParsed.get('CSVFile')
    logger.info(csvFile)

    csvFileDecoded = base64.b64decode(csvFile).decode('utf-8')
    with io.StringIO(csvFileDecoded) as fp:
        reader = csv.DictReader(fp, delimiter=",", quotechar='"')
        csvData = [row for row in reader]
    logger.info(csvData)

    def safe_num(value, default=0):
        try:
            return str(float(value))
        except (TypeError, ValueError):
            return str(default)

    # ---------- Update existing items ----------
    def ddb_client(tablename):
        player_name = csvItem.get('PlayerName', "")
        # Detect multiple players and create a string set
        if ',' in player_name:
            player_names_set = list({p.strip() for p in player_name.split(',') if p.strip()})
            number_players = len(player_names_set)
        else:
            player_names_set = None

        update_expr = (
            'SET #itemset = :itemset, #itemyear = :itemyear, #itemsubset = :itemsubset, '
            '#itemplayer = :itemplayer, #itemqty = :itemqty, #itemcardnum = :itemcardnum, '
            '#itemauthenticator = :itemauthenticator, #itemgrade = :itemgrade, #itemboxnum = :itemboxnum, '
            '#itemcertnum = :itemcertnum, #itemebayitemid = :itemebayitemid, #itemgradingfee = :itemgradingfee, '
            '#itempurchaseprice = :itempurchaseprice, #itemqtymade = :itemqtymade, #itemsaleprice = :itemsaleprice, '
            '#itemserialnumber = :itemserialnumer, #itemtxndate = :itemtxndate, #itemtxnid = :itemtxnid, '
            '#itemtxnsource = :itemtxnsource, #itemtxntype = :itemtxntype, #itemmktval = :itemmktval'
        )

        expr_attr_names = {
            '#itemset': 'Set',
            '#itemyear': 'Year',
            '#itemsubset': 'Subset',
            '#itemplayer': 'PlayerName',
            '#itemqty': 'Qty',
            '#itemcardnum': 'CardNum',
            '#itemauthenticator': 'Authenticator',
            '#itemgrade': 'Grade',
            '#itemboxnum': 'BoxNum',
            '#itemcertnum': 'CertNumber',
            '#itemebayitemid': 'ebayItemID',
            '#itemgradingfee': 'GradingFee',
            '#itempurchaseprice': 'PurchasePrice',
            '#itemqtymade': 'QtyMade',
            '#itemsaleprice': 'SalePrice',
            '#itemserialnumber': 'SerialNumber',
            '#itemtxndate': 'TxnDate',
            '#itemtxnid': 'TxnId',
            '#itemtxnsource': 'TxnSource',
            '#itemtxntype': 'TxnType',
            '#itemmktval': 'MktVal'
        }

        expr_attr_values = {
            ':itemset': {'S': csvItem.get('Set', "")},
            ':itemyear': {'S': csvItem.get('Year', "")},
            ':itemsubset': {'S': csvItem.get('Subset', "")},
            ':itemplayer': {'S': player_name},
            ':itemqty': {'N': safe_num(csvItem.get('Qty', ""))},
            ':itemcardnum': {'S': csvItem.get('CardNum', "")},
            ':itemauthenticator': {'S': csvItem.get('Authenticator', "")},
            ':itemgrade': {'N': safe_num(csvItem.get('Grade', ""))},
            ':itemboxnum': {'S': csvItem.get('BoxNum', "")},
            ':itemcertnum': {'S': csvItem.get('CertNumber', "")},
            ':itemebayitemid': {'S': csvItem.get('ebayItemId', "")},
            ':itemgradingfee': {'N': safe_num(csvItem.get('GradingFee', ""))},
            ':itempurchaseprice': {'N': safe_num(csvItem.get('PurchasePrice', ""))},
            ':itemqtymade': {'N': safe_num(csvItem.get('QtyMade', ""))},
            ':itemsaleprice': {'N': safe_num(csvItem.get('SalePrice', ""))},
            ':itemserialnumber': {'S': csvItem.get('SerialNumber', "")},
            ':itemtxndate': {'S': csvItem.get('TxnDate', "")},
            ':itemtxnid': {'S': csvItem.get('TxnId', "")},
            ':itemtxnsource': {'S': csvItem.get('TxnSource', "")},
            ':itemtxntype': {'S': csvItem.get('TxnType', "")},
            ':itemmktval': {'N': safe_num(csvItem.get('MktVal', ""))}
        }

        # Add PlayerNames and NumPlayers attributes if multiple names exist
        if player_names_set:
            update_expr += ', #itemplayerset = :itemplayerset'
            expr_attr_names['#itemplayerset'] = 'PlayerNames'
            expr_attr_values[':itemplayerset'] = {'SS': player_names_set}
            update_expr += ', #itemnumplayers = :itemnumplayers'
            expr_attr_names['#itemnumplayers'] = 'NumPlayers'
            expr_attr_values[':itemnumplayers'] = {'N': safe_num(number_players)}

        ddbresponse = ddbclient.update_item(
            Key={'guid': {'S': csvItem.get('guid')}},
            UpdateExpression=update_expr,
            ExpressionAttributeNames=expr_attr_names,
            ExpressionAttributeValues=expr_attr_values,
            ReturnValues='UPDATED_NEW',
            ReturnConsumedCapacity='TOTAL',
            TableName=tablename
        )
        return ddbresponse

    # ---------- Batch write for new items ----------
    def batch_write(tablename):
        batch_items = {tablename: []}
        for csvItem in csvData:
            player_name = csvItem.get('PlayerName', "None")
            item = {
                'guid': {'S': str(uuid.uuid4())},
                'Set': {'S': csvItem.get('Set')},
                'Year': {'S': csvItem.get('Year', "None")},
                'Subset': {'S': csvItem.get('Subset', "None")},
                'PlayerName': {'S': player_name},
                'Qty': {'N': safe_num(csvItem.get('Qty', 0))},
                'QtyMade': {'N': safe_num(csvItem.get('QtyMade', 0))},
                'CardNum': {'S': csvItem.get('CardNum', "None")},
                'Authenticator': {'S': csvItem.get('Authenticator', "None")},
                'Grade': {'N': safe_num(csvItem.get('Grade', 0))},
                'BoxNum': {'S': csvItem.get('BoxNum', "Z1")},
                'CertNumber': {'S': csvItem.get('CertNumber', "None")},
                'ebayItemId': {'S': csvItem.get('ebayItemId', "None")},
                'GradingFee': {'N': safe_num(csvItem.get('GradingFee', 0))},
                'PurchasePrice': {'N': safe_num(csvItem.get('PurchasePrice', 0))},
                'SalePrice': {'N': safe_num(csvItem.get('SalePrice', 0))},
                'SerialNumber': {'S': csvItem.get('SerialNumber', "None")},
                'TxnDate': {'S': csvItem.get('TxnDate', "None")},
                'TxnId': {'S': csvItem.get('TxnId', "None")},
                'TxnSource': {'S': csvItem.get('TxnSource', "None")},
                'TxnType': {'S': csvItem.get('TxnType', "None")},
                'MktVal': {'N': safe_num(csvItem.get('MktVal', 0))}
            }

            # Add PlayerNames set if applicable
            if ',' in player_name:
                player_names_set = list({p.strip() for p in player_name.split(',') if p.strip()})
                item['PlayerNames'] = {'SS': player_names_set}

            batch_items[tablename].append({'PutRequest': {'Item': item}})

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

    # ---------- Main execution flow ----------
    if any(dictionary.get('guid') for dictionary in csvData):
        for csvItem in csvData:
            if csvItem.get('guid'):
                try:
                    ddb_response = ddb_client(tablename)
                    logger.info(ddb_response)
                except botocore.exceptions.ClientError as error:
                    raise error
    else:
        try:
            ddb_response = batch_write(tablename)
            logger.info(ddb_response)
        except botocore.exceptions.ClientError as error:
            raise error

    responseObject = {
        'StatusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': str(ddb_response)
    }

    return responseObject
