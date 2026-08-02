import importlib.util
import os
import sys
import types
import unittest
from pathlib import Path


class FakeSecretsClient:
    pass


class FakeTable:
    pass


class FakeDdbResource:
    def Table(self, name):
        return FakeTable()


def load_lister_module():
    boto3_stub = types.ModuleType("boto3")
    boto3_stub.client = lambda *args, **kwargs: FakeSecretsClient()
    boto3_stub.resource = lambda *args, **kwargs: FakeDdbResource()

    botocore_stub = types.ModuleType("botocore")
    botocore_exceptions_stub = types.ModuleType("botocore.exceptions")
    botocore_exceptions_stub.ClientError = Exception

    sys.modules["boto3"] = boto3_stub
    sys.modules["botocore"] = botocore_stub
    sys.modules["botocore.exceptions"] = botocore_exceptions_stub

    env = {
        "DDB_TABLE": "inventory",
        "EBAY_SECRET_NAME": "ebay",
        "EBAY_SECRET_REGION": "us-east-1",
        "EBAY_MARKETPLACE_ID": "EBAY_US",
        "EBAY_CATEGORY_ID": "261328",
        "EBAY_FULFILLMENT_POLICY_ID_UNDER20": "under-20-policy",
        "EBAY_FULFILLMENT_POLICY_ID_OVER20": "over-20-policy",
        "EBAY_PAYMENT_POLICY_ID": "fixed-payment-policy",
        "EBAY_RETURN_POLICY_ID": "return-policy",
        "EBAY_PAYMENT_POLICY_ID_AUCTION": "auction-payment-policy",
        "EBAY_MERCHANT_LOCATION_KEY": "warehouse",
        "BUY_IT_NOW_LISTING_DURATION": "GTC",
        "AUCTION_LISTING_DURATION": "DAYS_7",
    }
    os.environ.update(env)

    module_path = Path(__file__).resolve().parents[1] / "lambda" / "us175-ebay-lister.py"
    spec = importlib.util.spec_from_file_location("us175_ebay_lister_test", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FulfillmentPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lister = load_lister_module()

    def make_item(self, market_value="5.00"):
        return {
            "guid": "card-1",
            "MktVal": market_value,
            "Set": "Test Set",
            "Subset": "Base",
            "PlayerName": "Test Player",
            "CardNum": "1",
        }

    def make_payload(self, starting_bid, expected_sale_over_20=False):
        payload = {
            "guid": "card-1",
            "title": "Test Player Card",
            "listingType": "AUCTION",
            "allowOffers": False,
            "team": "Test Team",
            "autographed": "No",
            "startingBid": starting_bid,
            "expectedSaleOver20": expected_sale_over_20,
        }
        self.lister.validate_request_payload(payload)
        return payload

    def test_auction_starting_bid_under_20_uses_under_20_policy(self):
        offer = self.lister.build_offer_payload(
            item=self.make_item(),
            payload=self.make_payload("19.99"),
            access_token="token",
        )

        self.assertEqual(
            offer["listingPolicies"]["fulfillmentPolicyId"],
            "under-20-policy",
        )

    def test_auction_starting_bid_over_20_uses_over_20_policy(self):
        offer = self.lister.build_offer_payload(
            item=self.make_item(),
            payload=self.make_payload("20.01"),
            access_token="token",
        )

        self.assertEqual(
            offer["listingPolicies"]["fulfillmentPolicyId"],
            "over-20-policy",
        )

    def test_auction_expected_sale_over_20_override_uses_over_20_policy(self):
        offer = self.lister.build_offer_payload(
            item=self.make_item(),
            payload=self.make_payload("9.99", expected_sale_over_20=True),
            access_token="token",
        )

        self.assertEqual(
            offer["listingPolicies"]["fulfillmentPolicyId"],
            "over-20-policy",
        )

    def test_auction_market_value_over_20_uses_over_20_policy(self):
        offer = self.lister.build_offer_payload(
            item=self.make_item(market_value="25.00"),
            payload=self.make_payload("9.99"),
            access_token="token",
        )

        self.assertEqual(
            offer["listingPolicies"]["fulfillmentPolicyId"],
            "over-20-policy",
        )

    def test_auction_expected_sale_over_20_string_false_uses_under_20_policy(self):
        offer = self.lister.build_offer_payload(
            item=self.make_item(),
            payload=self.make_payload("9.99", expected_sale_over_20="false"),
            access_token="token",
        )

        self.assertEqual(
            offer["listingPolicies"]["fulfillmentPolicyId"],
            "under-20-policy",
        )


if __name__ == "__main__":
    unittest.main()
