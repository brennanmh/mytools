import unittest
from unittest.mock import patch, MagicMock
from update_nthroot_cf import get_wan_ip, get_record_id, update_dns_record, get_zone_id, has_record_changed, get_credentials

class TestUpdateNthrootCF(unittest.TestCase):

    @patch('requests.get')
    def test_get_wan_ip(self, mock_get):
        # Mock the response from ifconfig.me
        mock_get.return_value = MagicMock(status_code=200, text='123.123.123.123')
        ip = get_wan_ip()
        self.assertEqual(ip, '123.123.123.123')
        mock_get.assert_called_once_with('https://ifconfig.me/ip')

    @patch('requests.get')
    def test_get_record_id(self, mock_get):
        # Mock the response from Cloudflare API to get the record ID
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "result": [
                {"id": "record_id_123", "name": "nthroot.org", "type": "A"}
            ]
        }
        mock_get.return_value = mock_response
        record_id = get_record_id('zone_id', 'email', '049f21201ec7867101b63a4b653de9204bf2f')
        self.assertEqual(record_id, 'record_id_123')
        mock_get.assert_called_once_with(
            'https://api.cloudflare.com/client/v4/zones/zone_id/dns_records',
            headers={
                "Content-Type": "application/json",
                "X-Auth-Email": 'email',
                "X-Auth-Key": '049f21201ec7867101b63a4b653de9204bf2f'
            }
        )

    @patch('requests.get')
    def test_get_zone_id(self, mock_get):
        # Mock the response from Cloudflare API to get the zone ID
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "result": [
                {"id": "zone_id_123", "name": "nthroot.org"}
            ]
        }
        mock_get.return_value = mock_response
        zone_id = get_zone_id('email', '049f21201ec7867101b63a4b653de9204bf2f')
        self.assertEqual(zone_id, 'zone_id_123')
        mock_get.assert_called_once_with(
            'https://api.cloudflare.com/client/v4/zones',
            headers={
                "Content-Type": "application/json",
                "X-Auth-Email": 'email',
                "X-Auth-Key": '049f21201ec7867101b63a4b653de9204bf2f'
            }
        )

    @patch('requests.put')
    def test_update_dns_record(self, mock_put):
        # Mock the response from Cloudflare API to update the DNS record
        mock_response = MagicMock()
        mock_response.json.return_value = {"success": True}
        mock_put.return_value = mock_response
        result = update_dns_record('zone_id', 'record_id', '123.123.123.123', 'email', '049f21201ec7867101b63a4b653de9204bf2f')
        self.assertTrue(result['success'])
        mock_put.assert_called_once_with(
            'https://api.cloudflare.com/client/v4/zones/zone_id/dns_records/record_id',
            json={
                "type": "A",
                "name": "nthroot.org",
                "content": '123.123.123.123',
                "ttl": 120,
                "proxied": False
            },
            headers={
                "Content-Type": "application/json",
                "X-Auth-Email": 'email',
                "X-Auth-Key": '049f21201ec7867101b63a4b653de9204bf2f'
            }
        )

    @patch('requests.get')
    def test_has_record_changed(self, mock_get):
        # Mock the response from Cloudflare API to check if the record has changed
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "result": {
                "content": "123.123.123.123"
            }
        }
        mock_get.return_value = mock_response
        changed = has_record_changed('zone_id', 'record_id', '124.124.124.124', 'email', '049f21201ec7867101b63a4b653de9204bf2f')
        self.assertTrue(changed)
        mock_get.assert_called_once_with(
            'https://api.cloudflare.com/client/v4/zones/zone_id/dns_records/record_id',
            headers={
                "Content-Type": "application/json",
                "X-Auth-Email": 'email',
                "X-Auth-Key": '049f21201ec7867101b63a4b653de9204bf2f'
            }
        )

    @patch('configparser.ConfigParser.read')
    @patch('configparser.ConfigParser.get')
    def test_get_credentials(self, mock_get, mock_read):
        # Mock the response from the config file
        mock_get.side_effect = ['brennanmh@gmail.com', '049f21201ec7867101b63a4b653de9204bf2f']
        email, api_key = get_credentials()
        self.assertEqual(email, 'brennanmh@gmail.com')
        self.assertEqual(api_key, '049f21201ec7867101b63a4b653de9204bf2f')
        mock_read.assert_called_once()
        mock_get.assert_any_call('cloudflare', 'email')
        mock_get.assert_any_call('cloudflare', 'api_key')

if __name__ == '__main__':
    unittest.main()
