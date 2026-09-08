from unittest import TestCase, mock

from toolbox import windows_windowing


class WindowsMessageTimerTests(TestCase):
    def test_native_message_timer_has_no_callback_and_preserves_full_identifier(self) -> None:
        timer_id = 0x123456789
        with mock.patch.object(windows_windowing._user32, "SetTimer", return_value=timer_id) as create, mock.patch.object(windows_windowing._user32, "KillTimer", return_value=1) as release:
            actual = windows_windowing.start_ui_message_timer()
            self.assertEqual(actual, timer_id)
            create.assert_called_once_with(None, 0, 250, None)
            self.assertTrue(windows_windowing.stop_ui_message_timer(actual))
            release.assert_called_once_with(None, timer_id)

    def test_creation_failure_does_not_kill_an_unrelated_timer(self) -> None:
        with mock.patch.object(windows_windowing._user32, "SetTimer", return_value=0), mock.patch.object(windows_windowing._user32, "KillTimer") as release:
            actual = windows_windowing.start_ui_message_timer()
            self.assertEqual(actual, 0)
            self.assertTrue(windows_windowing.stop_ui_message_timer(actual))
            release.assert_not_called()
