import unittest

from session_state import is_present, is_session_locked


class FakeUser32:
    def __init__(self, handle):
        self.handle = handle
        self.closed = []

    def OpenInputDesktop(self, flags, inherit, access):
        return self.handle

    def CloseDesktop(self, handle):
        self.closed.append(handle)


class SessionStateTests(unittest.TestCase):
    def test_open_input_desktop_means_unlocked(self):
        user32 = FakeUser32(handle=123)
        self.assertFalse(is_session_locked(user32=user32, platform_name="nt"))
        self.assertEqual(user32.closed, [123])

    def test_failed_input_desktop_means_locked(self):
        user32 = FakeUser32(handle=0)
        self.assertTrue(is_session_locked(user32=user32, platform_name="nt"))
        self.assertEqual(user32.closed, [])

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
