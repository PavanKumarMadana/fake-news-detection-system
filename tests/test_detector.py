from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from application.detector import FakeNewsDetector


DATASET = Path(__file__).resolve().parents[1] / "data" / "training_data.json"


class DetectorTest(unittest.TestCase):
    def setUp(self):
        self.detector = FakeNewsDetector(DATASET).train()

    def test_fake_prediction_for_sensational_claim(self):
        result = self.detector.predict(
            "Shocking secret miracle cure exposed in viral message!!!"
        )
        self.assertEqual(result["label"], "fake")
        self.assertGreater(result["confidence"], 50)

    def test_real_prediction_for_official_report(self):
        result = self.detector.predict(
            "According to official ministry data, rainfall report was published today."
        )
        self.assertEqual(result["label"], "real")
        self.assertGreater(result["confidence"], 50)


if __name__ == "__main__":
    unittest.main()
