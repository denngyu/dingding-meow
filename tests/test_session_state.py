import unittest
from unittest.mock import patch

from session_state import (
    SESSION_RESUME_SEC,
    is_present,
    is_session_locked,
    session_end_time,
    session_gap_expired,
)


class FakeUser32:
    def __init__(self, handle, switchable=True):
        self.handle = handle
        self.switchable = switchable
        self.closed = []
        self.switched = []

    def OpenInputDesktop(self, flags, inherit, access):
        return self.handle

    def SwitchDesktop(self, handle):
        self.switched.append(handle)
        return self.switchable

    def CloseDesktop(self, handle):
        self.closed.append(handle)


class SessionStateTests(unittest.TestCase):
    def test_short_face_loss_keeps_the_same_sitting_session(self):
        self.assertEqual(SESSION_RESUME_SEC, 30)
        self.assertFalse(session_gap_expired(100.0, 130.0))
        self.assertTrue(session_gap_expired(100.0, 130.01))

    def test_lock_ends_session_immediately(self):
        self.assertTrue(session_gap_expired(100.0, 101.0, locked=True))

    def test_lock_ends_a_pending_session_even_after_mode_changed_to_away(self):
        self.assertEqual(
            session_end_time(
                sit_start=100.0,
                away_since=120.0,
                now=121.0,
                locked=True,
            ),
            121.0,
        )

    def test_short_unlocked_gap_keeps_the_pending_session(self):
        self.assertIsNone(
            session_end_time(
                sit_start=100.0,
                away_since=120.0,
                now=121.0,
                locked=False,
            )
        )

    def test_wts_lock_state_takes_priority_over_desktop_switch_fallback(self):
        with patch("session_state.query_wts_session_lock_state", return_value=True):
            self.assertTrue(
                is_session_locked(
                    user32=FakeUser32(handle=123, switchable=True),
                    platform_name="nt",
                    prefer_wts=True,
                )
            )

    def test_desktop_switch_fallback_is_used_when_wts_query_is_unknown(self):
        user32 = FakeUser32(handle=123, switchable=False)
        with patch("session_state.query_wts_session_lock_state", return_value=None):
            self.assertTrue(
                is_session_locked(
                    user32=user32,
                    platform_name="nt",
                    prefer_wts=True,
                )
            )
        self.assertEqual(user32.switched, [123])
        self.assertEqual(user32.closed, [123])

    def test_open_input_desktop_means_unlocked(self):
        user32 = FakeUser32(handle=123, switchable=True)
        self.assertFalse(is_session_locked(user32=user32, platform_name="nt"))
        self.assertEqual(user32.switched, [123])
        self.assertEqual(user32.closed, [123])

    def test_failed_input_desktop_means_locked(self):
        user32 = FakeUser32(handle=0)
        self.assertTrue(is_session_locked(user32=user32, platform_name="nt"))
        self.assertEqual(user32.switched, [])
        self.assertEqual(user32.closed, [])

    def test_secure_desktop_handle_that_cannot_switch_means_locked(self):
        user32 = FakeUser32(handle=123, switchable=False)
        self.assertTrue(is_session_locked(user32=user32, platform_name="nt"))
        self.assertEqual(user32.switched, [123])
        self.assertEqual(user32.closed, [123])

    def test_non_windows_is_not_reported_as_locked(self):
        self.assertFalse(is_session_locked(user32=FakeUser32(0), platform_name="posix"))

    def test_lock_overrides_a_recent_face_without_grace_period(self):
        self.assertFalse(
            is_present(
                blocked=False,
                locked=True,
                last_seen=99.0,
                now=100.0,
                grace_seconds=25,
            )
        )
        self.assertTrue(
            is_present(
                blocked=False,
                locked=False,
                last_seen=99.0,
                now=100.0,
                grace_seconds=25,
            )
        )


if __name__ == "__main__":
    unittest.main()
