import unittest

from session_state import SESSION_RESUME_SEC, is_present, is_session_locked, session_gap_expired


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
