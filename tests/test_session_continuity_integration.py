import unittest
from pathlib import Path


PET_SOURCE = (Path(__file__).resolve().parents[1] / "pet.py").read_text(encoding="utf-8")


class SessionContinuityIntegrationTests(unittest.TestCase):
    def test_detection_loop_keeps_a_pending_away_session_for_resumption(self):
        self.assertIn("session_away_start", PET_SOURCE)
        self.assertIn("session_gap_expired", PET_SOURCE)
        self.assertIn("SESSION_RESUME_SEC", PET_SOURCE)

    def test_lock_still_clears_the_pending_session_immediately(self):
        self.assertIn("session_away_start=None", PET_SOURCE)
        self.assertIn('STATE["sit_session_start"]=None', PET_SOURCE)

    def test_camera_read_failure_updates_away_state_instead_of_freezing_overdue(self):
        failure_branch = PET_SOURCE.split("if not ok or fr is None:", 1)[1].split(
            "gray=cv2.cvtColor",
            1,
        )[0]
        self.assertIn('mode="away"', failure_branch)
        self.assertIn("session_gap_expired", failure_branch)
        self.assertIn('sit=kept_sit', failure_branch)
        self.assertIn('frame=None', failure_branch)


if __name__ == "__main__":
    unittest.main()
