import boto3
from boto3.dynamodb.conditions import Key, Attr
import os
import json
import logging
import botocore
from natsort import natsorted
from decimal import Decimal

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource('dynamodb', region_name='us-east-2')
table = dynamodb.Table(os.environ.get('TableName'))

INDEX_SET_YEAR = os.environ.get('IndexName_SetYear', 'Set-Year-index')
INDEX_BOX_PLAYER = os.environ.get('IndexName_BoxPlayer', 'BoxNum-PlayerName-index')
INDEX_PLAYER_SET = os.environ.get('IndexName_PlayerSet', 'PlayerName-Set-index')
INDEX_MULTIPLAYER = os.environ.get('IndexName_Multiplayer', 'Multiplayer-index')
EXCLUDED_SET_PLAYER_BOXES = {'X', 'Z1'}

def convert_sets(obj):
    """
    Recursively convert:
      - set -> list
      - Decimal -> int (if whole) or float (if fractional)
    This prepares DynamoDB results for json.dumps().
    """
    # dict -> convert each value
    if isinstance(obj, dict):
        return {k: convert_sets(v) for k, v in obj.items()}

    # list/tuple -> convert each element (returns list)
    if isinstance(obj, (list, tuple)):
        return [convert_sets(i) for i in obj]

    # set -> convert to list (preserve items converted)
    if isinstance(obj, set):
        return [convert_sets(i) for i in obj]

    # Decimal -> int or float
    if isinstance(obj, Decimal):
        # Decimal.is_integer-like check:
        if obj == obj.to_integral_value():
            return int(obj)
        else:
            return float(obj)

    # everything else -> return as-is
    return obj

def lambda_handler(event, context):
    logger.info(event['body'])
    bodyParsed = json.loads(event['body'])

    # Determine which index to use
    search_type = bodyParsed.get('SearchType', 'set').lower()  # default: set

    if search_type == 'box':
        index = INDEX_BOX_PLAYER
        KeyName = 'BoxNum'
        SortKeyName = 'PlayerName'
        KeyVal = bodyParsed.get('BoxNum', "")
        SortKeyVal = bodyParsed.get('PlayerName', "")
        if any(prefix in KeyVal for prefix in ('G', 'T', 'X')):
            LambdaSort = 'PlayerName'
        else:
            LambdaSort = 'CardNum'
    elif search_type == 'player': # find cards where player is featured
        index = INDEX_PLAYER_SET
        KeyName = 'PlayerName'
        SortKeyName = 'Set'
        KeyVal = bodyParsed.get('PlayerName', "")
        SortKeyVal = bodyParsed.get('Set', "")
        LambdaSort = 'Year'
    else:
        index = INDEX_SET_YEAR
        KeyName = 'Set'
        SortKeyName = 'Year'
        KeyVal = bodyParsed.get('Set', "")
        SortKeyVal = bodyParsed.get('Year', "")
        LambdaSort = 'CardNum'

    AttrName1 = 'Subset'
    AttrVal1 = bodyParsed.get('Subset', "")
    AttrName2 = 'Qty'
    AttrVal2 = int(bodyParsed.get('Qty', "0"))

    logger.info(f"Using Index: {index}")

    def exclude_set_player_boxes(items):
        return [
            item for item in items
            if item.get('BoxNum') not in EXCLUDED_SET_PLAYER_BOXES
        ]

    def ddbquery():
        lastEvaluatedKey = None
        key_condition_expression = Key(KeyName).eq(KeyVal)
        if SortKeyVal != "":
            key_condition_expression &= Key(SortKeyName).eq(SortKeyVal)

        filter_expression = None
        if AttrVal1:
            filter_expression = Attr(AttrName1).eq(AttrVal1)
        if AttrVal2 != 0:
            filter_expression = (
                Attr(AttrName2).eq(AttrVal2)
                if not filter_expression
                else filter_expression & Attr(AttrName2).eq(AttrVal2)
            )

        items = []
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

        itemsListSorted = natsorted(items, key=lambda d: d.get(LambdaSort, ''))
        return itemsListSorted

    def scan_multiplayer(player_name):
        """Scan the Multiplayer-index for cards containing the given player."""
        items = []
        lastEvaluatedKey = None
        while True:
            scan_params = {
                'IndexName': INDEX_MULTIPLAYER,
                'FilterExpression': Attr('PlayerNames').contains(player_name),
            }
            if lastEvaluatedKey:
                scan_params['ExclusiveStartKey'] = lastEvaluatedKey

            resp = table.scan(**scan_params)
            items.extend(resp.get('Items', []))

            if 'LastEvaluatedKey' in resp:
                lastEvaluatedKey = resp['LastEvaluatedKey']
            else:
                break

        return items

    try:
        if search_type == 'player':
            # Query single-player cards using the PlayerName-Set-index
            ddbitems = ddbquery()

            # Scan for multi-player cards using the new index
            player_name = bodyParsed.get('PlayerName', "")
            multiplayer_items = scan_multiplayer(player_name)

            # Merge and sort both sets of results
            ddbitems.extend(multiplayer_items)
            ddbitems = natsorted(ddbitems, key=lambda d: d.get(LambdaSort, ''))
        else:
            ddbitems = ddbquery()

        if search_type in ('set', 'player'):
            ddbitems = exclude_set_player_boxes(ddbitems)

        ddbitems = convert_sets(ddbitems)
    except botocore.exceptions.ClientError as error:
        raise error

    responseObject = {
        'StatusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': ddbitems
    }
    
    return responseObject
