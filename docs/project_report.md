# Fake News Detecting System

## Abstract

Fake news spreads rapidly through social media, messaging platforms, and online news portals. Manual verification is time-consuming, and users often struggle to identify misleading content before sharing it. The Fake News Detecting System is a Python-based application that analyzes news text and predicts whether it is likely to be fake or real.

The system uses a lightweight Naive Bayes text classification approach with a browser-based interface. Users can paste a headline or article, submit it for analysis, and view the predicted label, confidence score, probability values, and important language signals. The system also stores recent predictions using SQLite.

## 1. Introduction

Fake news detection is an important application of natural language processing. The objective of this project is to provide a simple and understandable system that can classify suspicious news content and help users think critically before trusting or forwarding information.

### 1.1 Objective

The main objectives are:

- To develop a Python web application for fake news prediction.
- To classify text as fake or real using learned word patterns.
- To display confidence scores and explanation signals.
- To maintain prediction history for review.
- To create a project that is easy to run without external dependencies.

### 1.2 Problem Statement

Online misinformation can influence public opinion, health decisions, financial behavior, and social harmony. Many users do not have time to verify every message manually. A software system is required to provide quick preliminary analysis of news text and highlight suspicious patterns.

### 1.3 Software Requirements

- Operating System: Windows, Linux, or macOS
- Language: Python 3.10 or above
- Database: SQLite
- Browser: Chrome, Edge, Firefox, or similar
- Libraries: Python standard library

### 1.4 Hardware Requirements

- Processor: Intel i3 or above
- RAM: 4 GB minimum
- Disk Space: 100 MB minimum
- Network: Required only for external source verification

## 2. Feasibility Study

### Technical Feasibility

The system is technically feasible because it uses Python's standard library, SQLite, and a compact classifier. No heavy framework is required.

### Operational Feasibility

The interface is simple: users paste text and click the analyze button. Results are shown immediately.

### Economic Feasibility

The project has no paid dependency. It can run locally on a normal computer.

## 3. Literature Survey

Fake news detection systems commonly use natural language processing, machine learning, source credibility analysis, and user behavior patterns. Classical models such as Naive Bayes, Logistic Regression, and Support Vector Machines are widely used for text classification. Modern systems may use transformer-based models, but they need larger datasets and higher computing power.

This project uses Naive Bayes because it is easy to explain, fast, and suitable for academic demonstration.

## 4. System Analysis

### 4.1 Existing System

In the existing manual approach, users verify news by searching different websites, checking official sources, or waiting for fact-checking organizations.

### 4.1.1 Disadvantages

- Manual verification takes time.
- Users may trust forwarded messages without checking sources.
- Fact-checking may not be available for every local claim.
- Suspicious language patterns are not always obvious.

### 4.2 Proposed System

The proposed system accepts news text, processes it, predicts a category, and stores the prediction. It also highlights signals such as sensational words, source hints, short text, and clickbait punctuation.

### 4.2.1 Advantages

- Simple browser-based interaction.
- Fast prediction.
- Local SQLite history.
- No external package installation.
- Easy to understand and extend.

### 4.3 Functional Requirements

- User can enter news text.
- System can classify the text.
- System can show fake and real probability.
- System can store prediction history.
- User can view recent analysis history.

### 4.4 Non-Functional Requirements

- Usability: Interface should be clear and responsive.
- Reliability: The app should handle short or empty input.
- Maintainability: Code should be modular.
- Portability: The app should run on any machine with Python.

## 5. System Design

### 5.1 Architecture

The system follows a three-layer design:

- Presentation Layer: HTML and CSS user interface.
- Application Layer: Python HTTP server and request handling.
- Data Layer: JSON training data and SQLite prediction history.

### 5.2 Modules

- `app.py`: Starts the server and handles routes.
- `app/detector.py`: Tokenization, model training, prediction, and explanation.
- `app/storage.py`: SQLite prediction storage.
- `data/training_data.json`: Sample labeled news dataset.
- `app/templates/index.html`: Web page layout.
- `app/static/styles.css`: Styling.

### 5.3 Use Case Diagram Description

Actor: User

Use cases:

- Enter news content.
- Submit for prediction.
- View classification result.
- View confidence score.
- View recent prediction history.

### 5.4 Class Diagram Description

Main classes:

- `FakeNewsDetector`: Trains the model and predicts labels.
- `PredictionStore`: Stores and retrieves prediction history.
- `FakeNewsRequestHandler`: Handles browser requests.

### 5.5 Sequence Flow

1. User opens the web application.
2. User enters news text.
3. Server sends text to the detector.
4. Detector returns label, confidence, and signals.
5. Server stores the prediction in SQLite.
6. Result and history are displayed to the user.

## 6. Implementation

The classifier uses tokenization and Multinomial Naive Bayes. During training, the system counts word occurrences for fake and real classes. During prediction, it calculates class probabilities using prior probability and word likelihood with smoothing.

The web application is implemented with `http.server` from the Python standard library. SQLite is used to save prediction records.

## 7. Software Environment

- Python: 3.10+
- Database: SQLite
- Frontend: HTML5, CSS3
- Backend: Python standard library

## 8. System Testing

### Test Cases

| Test Case | Input | Expected Result |
| --- | --- | --- |
| Fake sensational text | "Shocking secret miracle cure..." | Fake |
| Official report text | "According to official ministry data..." | Real |
| Empty text | Blank input | Prompt for longer text |
| History storage | Submit valid text | Prediction appears in history |

Run tests:

```powershell
python -m unittest discover tests
```

## 9. Screens

Screens to capture for final record:

- Home page
- Text input form
- Fake news prediction result
- Real news prediction result
- Analysis history table

## 10. Conclusion

The Fake News Detecting System provides a working academic demonstration of text-based misinformation detection. It combines a Python classifier, a browser interface, and SQLite storage. The project can be improved further by adding a large real-world dataset, source credibility scoring, user login, admin dashboards, and advanced NLP models.

## 11. References

- Python Documentation: https://docs.python.org/3/
- SQLite Documentation: https://www.sqlite.org/docs.html
- Naive Bayes Text Classification: https://en.wikipedia.org/wiki/Naive_Bayes_classifier
- Press Information Bureau Fact Check: https://www.pib.gov.in/factcheck.aspx
