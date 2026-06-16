import unittest
from unittest.mock import Mock, patch

from application.evidence import extract_claim_from_url


class EvidenceTest(unittest.TestCase):
    def test_extracts_youtube_oembed_title(self):
        response = Mock()
        response.json.return_value = {
            "title": "Official railways update explained",
            "author_name": "News Channel",
        }
        response.raise_for_status.return_value = None

        with patch("application.evidence.requests.get", return_value=response):
            result = extract_claim_from_url("https://www.youtube.com/watch?v=abc123")

        self.assertIn("Official railways update explained", result["text"])
        self.assertEqual(result["source"], "News Channel")

    def test_extracts_article_metadata(self):
        html = b"""
        <html><head>
            <meta property="og:title" content="IRCTC website to launch by July 15">
            <meta name="description" content="Railway minister announced an upgraded booking portal.">
        </head><body></body></html>
        """
        response = Mock()
        response.raw.read.return_value = html
        response.encoding = "utf-8"
        response.raise_for_status.return_value = None

        with patch("application.evidence.requests.get", return_value=response):
            result = extract_claim_from_url("https://example.com/news/irctc")

        self.assertIn("IRCTC website to launch by July 15", result["text"])
        self.assertIn("upgraded booking portal", result["text"])


if __name__ == "__main__":
    unittest.main()
