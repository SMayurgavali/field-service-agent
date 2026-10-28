import unittest
from unittest.mock import Mock, call

from retry_utils import run_with_retries


class TestRetryUtils(unittest.TestCase):

    def test_success_without_retry(self):
        operation = Mock(return_value="success")
        sleep = Mock()

        result = run_with_retries(
            operation,
            sleep_fn=sleep,
        )

        self.assertEqual(result, "success")
        operation.assert_called_once()
        sleep.assert_not_called()

    def test_retries_after_503(self):
        operation = Mock(
            side_effect=[
                RuntimeError("503 UNAVAILABLE"),
                "success",
            ]
        )
        sleep = Mock()
        on_retry = Mock()

        result = run_with_retries(
            operation,
            sleep_fn=sleep,
            on_retry=on_retry,
        )

        self.assertEqual(result, "success")
        self.assertEqual(operation.call_count, 2)
        sleep.assert_called_once_with(2)
        on_retry.assert_called_once()

    def test_does_not_retry_401(self):
        operation = Mock(
            side_effect=RuntimeError("401 Invalid API key")
        )
        sleep = Mock()

        with self.assertRaisesRegex(RuntimeError, "401"):
            run_with_retries(
                operation,
                sleep_fn=sleep,
            )

        operation.assert_called_once()
        sleep.assert_not_called()

    def test_fails_after_max_attempts(self):
        operation = Mock(
            side_effect=RuntimeError("503 UNAVAILABLE")
        )
        sleep = Mock()

        with self.assertRaisesRegex(RuntimeError, "503"):
            run_with_retries(
                operation,
                max_attempts=3,
                sleep_fn=sleep,
            )

        self.assertEqual(operation.call_count, 3)
        self.assertEqual(
            sleep.call_args_list,
            [call(2), call(4)],
        )


if __name__ == "__main__":
    unittest.main()