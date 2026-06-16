import json
import math
import re
import time
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse


TOKEN_RE = re.compile(r"[a-zA-Z][a-zA-Z']+")

STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "has",
    "have", "in", "is", "it", "its", "of", "on", "or", "that", "the", "this",
    "to", "was", "were", "will", "with", "you", "your",
}

SENSATIONAL_WORDS = {
    "shocking", "miracle", "secret", "exposed", "urgent", "unbelievable",
    "guaranteed", "banned", "viral", "hoax", "conspiracy", "hidden",
}

SOURCE_HINTS = {
    "report", "according", "official", "study", "researchers", "ministry",
    "agency", "court", "data", "evidence", "published", "statement",
}

TRUSTED_DOMAINS = {
    "pib.gov.in", "who.int", "un.org", "reuters.com", "apnews.com", "bbc.com",
    "thehindu.com", "indiatoday.in", "ndtv.com", "nature.com", "science.org",
}

LOW_TRUST_HINTS = {
    "blogspot", "wordpress", "free", "viral", "truth", "exposed", "rumor",
    "forwarded", "unknown",
}

POSITIVE_WORDS = {"confirmed", "official", "evidence", "research", "published", "approved"}
NEGATIVE_WORDS = {"shocking", "danger", "secret", "exposed", "urgent", "banned", "conspiracy"}


def tokenize(text):
    return [
        token.lower()
        for token in TOKEN_RE.findall(text)
        if token.lower() not in STOP_WORDS
    ]


class FakeNewsDetector:
    """Small Multinomial Naive Bayes classifier for demonstration projects."""

    def __init__(self, dataset_path):
        self.dataset_path = Path(dataset_path)
        self.class_word_counts = defaultdict(Counter)
        self.class_doc_counts = Counter()
        self.class_total_words = Counter()
        self.vocabulary = set()
        self.labels = ("fake", "real")
        self.is_trained = False

    def train(self):
        records = json.loads(self.dataset_path.read_text(encoding="utf-8"))
        for record in records:
            label = record["label"].lower()
            tokens = tokenize(record["text"])
            self.class_doc_counts[label] += 1
            self.class_word_counts[label].update(tokens)
            self.class_total_words[label] += len(tokens)
            self.vocabulary.update(tokens)
        self.is_trained = True
        return self

    def predict(self, text, source_url=""):
        started = time.perf_counter()
        if not self.is_trained:
            self.train()

        tokens = tokenize(text)
        if not tokens:
            return {
                "label": "unknown",
                "confidence": 0,
                "fake_probability": 0,
                "real_probability": 0,
                "source_score": self.source_credibility(source_url)["score"],
                "source_summary": self.source_credibility(source_url)["summary"],
                "risk_level": "Unknown",
                "processing_time_ms": 0,
                "model_used": "Multinomial Naive Bayes",
                "prediction_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "keyword_analysis": [],
                "sentiment": "Neutral",
                "fact_check_suggestions": self.fact_check_suggestions(),
                "similar_news": [],
                "signals": ["Please enter a longer news headline or article body."],
            }

        scores = {}
        total_docs = sum(self.class_doc_counts.values())
        vocabulary_size = max(len(self.vocabulary), 1)

        for label in self.labels:
            prior = (self.class_doc_counts[label] + 1) / (total_docs + len(self.labels))
            score = math.log(prior)
            denominator = self.class_total_words[label] + vocabulary_size
            for token in tokens:
                numerator = self.class_word_counts[label][token] + 1
                score += math.log(numerator / denominator)
            scores[label] = score

        probabilities = self._softmax(scores)
        fake_probability = probabilities["fake"]
        real_probability = probabilities["real"]
        label = "fake" if fake_probability >= real_probability else "real"
        confidence = round(max(fake_probability, real_probability) * 100)

        source = self.source_credibility(source_url)
        signals = self._signals(text, tokens, label)
        if source_url:
            signals.append(source["summary"])
        risk_level = self.risk_level(label, confidence, source["score"])
        similar_news = self.similar_news(tokens, label)

        return {
            "label": label,
            "confidence": confidence,
            "fake_probability": round(fake_probability * 100, 2),
            "real_probability": round(real_probability * 100, 2),
            "source_score": source["score"],
            "source_summary": source["summary"],
            "risk_level": risk_level,
            "processing_time_ms": round((time.perf_counter() - started) * 1000, 2),
            "model_used": "Multinomial Naive Bayes",
            "prediction_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "keyword_analysis": self.keyword_analysis(tokens),
            "sentiment": self.sentiment(tokens),
            "fact_check_suggestions": self.fact_check_suggestions(),
            "similar_news": similar_news,
            "signals": signals,
        }

    def risk_level(self, label, confidence, source_score):
        if label == "fake" and confidence >= 80:
            return "High"
        if label == "fake" or source_score < 40:
            return "Medium"
        return "Low"

    def keyword_analysis(self, tokens):
        counts = Counter(tokens)
        return [word for word, _ in counts.most_common(8)]

    def sentiment(self, tokens):
        token_set = set(tokens)
        positive = len(token_set & POSITIVE_WORDS)
        negative = len(token_set & NEGATIVE_WORDS)
        if negative > positive:
            return "Negative / alarming"
        if positive > negative:
            return "Neutral-positive"
        return "Neutral"

    def fact_check_suggestions(self):
        return [
            "Check official government or organization websites.",
            "Compare the claim with at least two established news sources.",
            "Avoid forwarding until the source and date are verified.",
        ]

    def similar_news(self, tokens, label):
        records = json.loads(self.dataset_path.read_text(encoding="utf-8"))
        token_set = set(tokens)
        scored = []
        for record in records:
            record_tokens = set(tokenize(record["text"]))
            overlap = len(token_set & record_tokens)
            if overlap:
                scored.append((overlap, record["label"], record["text"]))
        scored.sort(reverse=True)
        return [
            {"label": item_label, "text": text}
            for _, item_label, text in scored[:3]
            if item_label == label
        ]

    def source_credibility(self, source_url):
        if not source_url:
            return {"score": 50, "summary": "No source URL provided; credibility is based only on text."}
        parsed = urlparse(source_url if "://" in source_url else "https://" + source_url)
        domain = parsed.netloc.lower().removeprefix("www.")
        if not domain:
            return {"score": 30, "summary": "Invalid URL format; source could not be verified."}
        if domain in TRUSTED_DOMAINS or any(domain.endswith("." + trusted) for trusted in TRUSTED_DOMAINS):
            return {"score": 90, "summary": f"Source domain {domain} is in the trusted reference list."}
        if any(hint in domain for hint in LOW_TRUST_HINTS):
            return {"score": 25, "summary": f"Source domain {domain} contains low-trust wording."}
        if domain.endswith((".gov", ".edu", ".ac.in", ".gov.in")):
            return {"score": 82, "summary": f"Source domain {domain} appears institutional."}
        if domain.endswith((".org", ".in", ".com")):
            return {"score": 58, "summary": f"Source domain {domain} requires manual cross-checking."}
        return {"score": 45, "summary": f"Source domain {domain} is unknown to the credibility list."}

    def _softmax(self, scores):
        highest = max(scores.values())
        exp_scores = {
            label: math.exp(score - highest)
            for label, score in scores.items()
        }
        total = sum(exp_scores.values())
        return {label: value / total for label, value in exp_scores.items()}

    def _signals(self, text, tokens, label):
        token_set = set(tokens)
        signals = []

        sensational_hits = sorted(token_set & SENSATIONAL_WORDS)
        source_hits = sorted(token_set & SOURCE_HINTS)

        if sensational_hits:
            signals.append("Sensational wording found: " + ", ".join(sensational_hits[:5]))
        if source_hits:
            signals.append("Credibility terms found: " + ", ".join(source_hits[:5]))
        if re.search(r"https?://|www\.", text):
            signals.append("Includes an external link for source checking.")
        if len(tokens) < 12:
            signals.append("Short text gives lower prediction reliability.")
        if text.count("!") >= 2:
            signals.append("Multiple exclamation marks can indicate clickbait style.")
        if not signals:
            signals.append(
                "Prediction is mainly based on word patterns learned from the training data."
            )
        if label == "fake" and not sensational_hits:
            signals.append("Cross-check this claim with official or established sources.")

        return signals
