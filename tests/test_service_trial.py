from __future__ import annotations

import unittest
from unittest.mock import call, patch

from client.service_trial import run_trial


class ServiceTrialTests(unittest.TestCase):
    @patch("client.service_trial.post_json")
    def test_encrypts_adds_decrypts_and_verifies(self, post_json) -> None:
        post_json.side_effect = [
            {
                "session_id": "session-1",
                "evaluation_bundle": {
                    "context": "context",
                    "ciphertext_a": "left-ciphertext",
                    "ciphertext_b": "right-ciphertext",
                },
            },
            {"ciphertext": "sum-ciphertext"},
            {"values": [11.0, 22.0]},
        ]

        result = run_trial(
            encryptor_url="http://he-encryptor:8080/v1",
            add_url="http://he-add-api:8080/v1/add",
            left=[1.0, 2.0],
            right=[10.0, 20.0],
            tolerance=1e-4,
            timeout=30.0,
        )

        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["actual"], [11.0, 22.0])
        self.assertEqual(
            post_json.call_args_list,
            [
                call(
                    "http://he-encryptor:8080/v1/encrypt-pair",
                    {"left": [1.0, 2.0], "right": [10.0, 20.0]},
                    30.0,
                ),
                call(
                    "http://he-add-api:8080/v1/add",
                    {
                        "context": "context",
                        "ciphertext_a": "left-ciphertext",
                        "ciphertext_b": "right-ciphertext",
                    },
                    30.0,
                ),
                call(
                    "http://he-encryptor:8080/v1/sessions/session-1/decrypt",
                    {"ciphertext": "sum-ciphertext"},
                    30.0,
                ),
            ],
        )

    @patch("client.service_trial.post_json")
    def test_fails_when_decrypted_sum_is_wrong(self, post_json) -> None:
        post_json.side_effect = [
            {
                "session_id": "session-1",
                "evaluation_bundle": {
                    "context": "context",
                    "ciphertext_a": "left",
                    "ciphertext_b": "right",
                },
            },
            {"ciphertext": "sum"},
            {"values": [99.0]},
        ]

        with self.assertRaisesRegex(RuntimeError, "exceeds tolerance"):
            run_trial(
                encryptor_url="http://he-encryptor:8080/v1",
                add_url="http://he-add-api:8080/v1/add",
                left=[1.0],
                right=[2.0],
                tolerance=1e-4,
                timeout=30.0,
            )


if __name__ == "__main__":
    unittest.main()
