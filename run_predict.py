from application.detector import FakeNewsDetector
import json
f = FakeNewsDetector('data/training_data.json').train()
print(json.dumps(f.predict('Taj mahal india lo undi'), indent=2))
