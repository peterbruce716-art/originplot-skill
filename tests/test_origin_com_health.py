import unittest

from scripts.origin_com_health import classify_origin_com_failure


class OriginComHealthTests(unittest.TestCase):
    def test_onag_crash_and_dcom_timeout_are_a_blocking_initialization_failure(self):
        events = [
            {
                "log": "Application",
                "id": 1000,
                "message": "Origin64.exe faulting module ONAG.dll, exception code 0xc0000005",
            },
            {
                "log": "System",
                "id": 10010,
                "message": "server {2F234A01-A4EB-4EAB-A130-A13C97953F0B} did not register with DCOM",
            },
        ]
        result = classify_origin_com_failure(events)
        self.assertEqual("E301_ORIGIN_COM_SERVER_INITIALIZATION_BLOCKED", result["error_code"])
        self.assertTrue(result["blocking"])
        self.assertTrue(result["onag_crash_detected"])
        self.assertTrue(result["dcom_timeout_detected"])


if __name__ == "__main__":
    unittest.main()
