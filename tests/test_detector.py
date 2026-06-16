from pathlib import Path
import sys
import unittest
from unittest.mock import patch

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

    def test_real_prediction_for_short_factual_claim(self):
        result = self.detector.predict("India prime minister Narendra Modi")
        self.assertEqual(result["label"], "real")
        self.assertGreater(result["confidence"], 50)

    def test_real_prediction_for_common_fact(self):
        result = self.detector.predict("Taj mahal india lo undi")
        self.assertEqual(result["label"], "real")
        self.assertGreater(result["confidence"], 50)

    def test_known_fact_returns_full_confidence(self):
        evidence = {
            "score": 92,
            "items": [{"title": "Eiffel Tower", "source": "Wikipedia", "url": "https://en.wikipedia.org/wiki/Eiffel_Tower", "trusted": True}],
        }
        with patch("application.evidence.check_evidence", return_value=evidence):
            result = self.detector.predict("Eiffel tower located in Paris")
        self.assertEqual(result["label"], "real")
        self.assertGreaterEqual(result["confidence"], 88)
        self.assertEqual(result["model_used"], "Live Source Verification")

    def test_verified_upcoming_railway_news(self):
        evidence = {
            "score": 94,
            "items": [{"title": "Indian Railways to launch upgraded IRCTC website by July 15", "source": "Moneycontrol", "url": "https://www.moneycontrol.com/news/india/indian-railways-to-launch-upgraded-irctc-website-by-july-15-13947487.html", "trusted": True}],
        }
        with patch("application.evidence.check_evidence", return_value=evidence):
            result = self.detector.predict("Indian railways new version irctc app launches july")
        self.assertEqual(result["label"], "real")
        self.assertGreaterEqual(result["confidence"], 88)
        self.assertEqual(result["model_used"], "Live Source Verification")


if __name__ == "__main__":
    unittest.main()
