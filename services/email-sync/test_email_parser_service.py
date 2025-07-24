import pytest
from email_parser_service import process_email, UPS_REGEX, FEDEX_REGEX, USPS_REGEX, SURVEY_URL_REGEX

class DummyMessage:
    def __init__(self, data):
        self.data = data
        self.acked = False
        self.nacked = False
    def ack(self):
        self.acked = True
    def nack(self):
        self.nacked = True

def make_email(body, from_addr="noreply@example.com"):
    import json
    return DummyMessage(data=json.dumps({"body": body, "from": from_addr}).encode("utf-8"))

def test_ups_extraction():
    # UPS tracking numbers are 18 characters: 1Z + 16 alphanumeric
    tracking = "1Z12345E1512345676"
    msg = make_email(f"Your UPS tracking: {tracking}")
    process_email(msg)
    assert msg.acked
    assert not msg.nacked
    assert UPS_REGEX.findall(f"Your UPS tracking: {tracking}") == [tracking]

def test_fedex_extraction():
    msg = make_email("FedEx: 1234 5678 9012 and 123456789012")
    process_email(msg)
    assert msg.acked
    assert not msg.nacked
    assert FEDEX_REGEX.findall("FedEx: 1234 5678 9012 and 123456789012") == ["1234 5678 9012", "123456789012"]

def test_usps_extraction():
    msg = make_email("USPS: 9400111899223856928499")
    process_email(msg)
    assert msg.acked
    assert not msg.nacked
    assert USPS_REGEX.findall("USPS: 9400111899223856928499") == ["9400111899223856928499"]

def test_survey_url_extraction():
    msg = make_email("Take our survey: https://survey.ourapp.com/response/abc123")
    process_email(msg)
    assert msg.acked
    assert not msg.nacked
    assert SURVEY_URL_REGEX.findall("Take our survey: https://survey.ourapp.com/response/abc123") == ["https://survey.ourapp.com/response/abc123"]

def test_invalid_json():
    msg = DummyMessage(data=b"not a json")
    process_email(msg)
    assert not msg.acked
    assert msg.nacked 

def test_amazon_status_shipped():
    msg = make_email("Your Amazon order has shipped!", from_addr="order-update@amazon.com")
    process_email(msg)
    assert msg.acked
    assert not msg.nacked

def test_amazon_status_expected_delivery():
    msg = make_email("Amazon: expected delivery tomorrow", from_addr="order-update@amazon.com")
    process_email(msg)
    assert msg.acked
    assert not msg.nacked

def test_amazon_status_delayed():
    msg = make_email("Amazon: delayed delivery date", from_addr="order-update@amazon.com")
    process_email(msg)
    assert msg.acked
    assert not msg.nacked

def test_amazon_status_delivered():
    msg = make_email("Amazon: delivered", from_addr="order-update@amazon.com")
    process_email(msg)
    assert msg.acked
    assert not msg.nacked

def test_amazon_unsupported_format():
    msg = make_email("Amazon: your order is being processed", from_addr="order-update@amazon.com")
    process_email(msg)
    assert msg.acked
    assert not msg.nacked

def test_amazon_order_link():
    link = "https://www.amazon.com/gp/your-account/order-details?orderID=123ABC456"
    msg = make_email(f"Amazon: shipped. View order: {link}", from_addr="order-update@amazon.com")
    process_email(msg)
    assert msg.acked
    assert not msg.nacked 