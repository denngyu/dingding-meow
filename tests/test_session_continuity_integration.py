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

    def test_camera_read_failure_moves_from_away_to_manual_restart_without_freezing(self):
        failure_branch = PET_SOURCE.split("if not ok or fr is None:", 1)[1].split(
            "gray=cv2.cvtColor",
            1,
        )[0]
        self.assertIn('mode="camera_off" if needs_restart else "away"', failure_branch)
        self.assertIn("camera_needs_manual_restart", failure_branch)
        self.assertIn("session_gap_expired", failure_branch)
        self.assertIn('sit=kept_sit', failure_branch)
        self.assertIn('frame=None', failure_branch)

    def test_sleep_releases_camera_and_wake_uses_recovery_manager(self):
        self.assertIn("camera=CameraCapture(cv2,CAM_INDEX)", PET_SOURCE)
        self.assertIn("camera.set_locked(locked,now)", PET_SOURCE)
        self.assertIn("ok,fr=camera.read(now)", PET_SOURCE)
        self.assertNotIn("cap=cv2.VideoCapture(CAM_INDEX,cv2.CAP_DSHOW)", PET_SOURCE)

    def test_drinking_requires_three_consecutive_hits(self):
        self.assertIn("CUP_HITS_NEEDED=3", PET_SOURCE)

    def test_detected_faces_refresh_last_seen(self):
        self.assertIn("fb=[] if blocked else face_boxes", PET_SOURCE)
        self.assertIn("if fb: last_seen=now", PET_SOURCE)

    def test_detection_supervisor_prevents_stale_overdue_ui(self):
        self.assertIn("def detection_supervisor():", PET_SOURCE)
        self.assertIn("target=detection_supervisor", PET_SOURCE)
        self.assertIn('mode="away"', PET_SOURCE)


if __name__ == "__main__":
    unittest.main()
