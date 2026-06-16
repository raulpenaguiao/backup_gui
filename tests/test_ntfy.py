import unittest
from unittest import mock

from tools_library.ntfy import send_ntfy


class TestSendNtfy(unittest.TestCase):
    def test_no_channel_fails_without_network_call(self):
        with mock.patch("tools_library.ntfy.urllib.request.urlopen") as m:
            ok, err = send_ntfy("", "hello")
        m.assert_not_called()
        self.assertFalse(ok)
        self.assertIsNotNone(err)

    def test_success(self):
        resp = mock.MagicMock()
        resp.__enter__.return_value = resp
        resp.status = 200
        with mock.patch("tools_library.ntfy.urllib.request.urlopen", return_value=resp):
            ok, err = send_ntfy("mychannel", "hello")
        self.assertTrue(ok)
        self.assertIsNone(err)

    def test_non_2xx_status_is_failure(self):
        resp = mock.MagicMock()
        resp.__enter__.return_value = resp
        resp.status = 500
        with mock.patch("tools_library.ntfy.urllib.request.urlopen", return_value=resp):
            ok, err = send_ntfy("mychannel", "hello")
        self.assertFalse(ok)
        self.assertIn("500", err)

    def test_network_exception_is_caught_not_raised(self):
        with mock.patch("tools_library.ntfy.urllib.request.urlopen",
                        side_effect=OSError("network down")):
            ok, err = send_ntfy("mychannel", "hello")
        self.assertFalse(ok)
        self.assertIn("network down", err)


if __name__ == "__main__":
    unittest.main()
