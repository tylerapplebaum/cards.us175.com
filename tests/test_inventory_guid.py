import importlib.util
import json
import sys
import unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch


class InventoryGuidTests(unittest.TestCase):
    def setUp(self):
        self.table = MagicMock()
        boto3 = MagicMock()
        boto3.resource.return_value.Table.return_value = self.table
        conditions = MagicMock()
        natsort = MagicMock()
        natsort.natsorted.side_effect = sorted
        modules = {
            'boto3': boto3,
            'boto3.dynamodb': MagicMock(),
            'boto3.dynamodb.conditions': conditions,
            'botocore': MagicMock(),
            'natsort': natsort,
        }
        path = Path(__file__).resolve().parents[1] / 'lambda/demo-get-inventory.py'
        spec = importlib.util.spec_from_file_location('inventory_under_test', path)
        self.module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, modules):
            spec.loader.exec_module(self.module)

    def request(self, **body):
        return self.module.lambda_handler({'body': json.dumps(body)}, None)

    def test_guid_direct_read_preserves_item_and_serializes_values(self):
        self.table.get_item.return_value = {'Item': {
            'guid': 'card-1', 'BoxNum': 'X', 'Qty': Decimal('1'),
            'MktVal': Decimal('2.50'), 'PlayerNames': {'Player'},
        }}
        result = self.request(SearchType='GUID', guid=' card-1 ', Qty='irrelevant')
        self.assertEqual(result['StatusCode'], 200)
        self.assertEqual(result['body'], [{
            'guid': 'card-1', 'BoxNum': 'X', 'Qty': 1,
            'MktVal': 2.5, 'PlayerNames': ['Player'],
        }])
        self.table.get_item.assert_called_once_with(Key={'guid': 'card-1'})
        self.table.query.assert_not_called()
        self.table.scan.assert_not_called()
        json.dumps(result)

    def test_missing_item_is_empty_result(self):
        self.table.get_item.return_value = {}
        self.assertEqual(self.request(SearchType='guid', guid='missing')['body'], [])

    def test_invalid_guid_does_not_call_dynamodb(self):
        for guid in [None, '', '  ', 123, [], {}]:
            with self.subTest(guid=guid):
                self.assertEqual(self.request(SearchType='guid', guid=guid)['StatusCode'], 400)
        self.assertEqual(self.request(SearchType='guid')['StatusCode'], 400)
        self.table.get_item.assert_not_called()
        self.table.query.assert_not_called()

    def test_existing_set_and_box_filters_remain(self):
        self.table.query.return_value = {'Items': [
            {'guid': 'hidden', 'BoxNum': 'X', 'CardNum': '2'},
            {'guid': 'visible', 'BoxNum': 'A', 'CardNum': '1'},
        ]}
        self.assertEqual(len(self.request(SearchType='set', Set='Test')['body']), 1)
        self.assertEqual(len(self.request(SearchType='box', BoxNum='X')['body']), 2)
        self.table.get_item.assert_not_called()


if __name__ == '__main__':
    unittest.main()
