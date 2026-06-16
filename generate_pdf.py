from fpdf import FPDF
from datetime import datetime

pdf = FPDF()
pdf.add_page()
pdf.set_font("Arial", "B", 20)
pdf.cell(0, 15, "FAKE NEWS DETECTION SYSTEM", ln=True, align="C")
pdf.set_font("Arial", "I", 12)
pdf.cell(0, 10, "Complete Project Documentation", ln=True, align="C")
pdf.set_font("Arial", "", 10)
pdf.cell(0, 8, f"Generated: {datetime.now().strftime('%B %d, %Y')}", ln=True, align="C")
pdf.ln(5)

sections = [
    ("1. PROJECT OVERVIEW", [
        "* AI-powered fake news detection system built with Flask",
        "* Real-time news credibility analysis using Machine Learning",
        "* User authentication, prediction history, and admin dashboard",
        "* Deployed on cloud platforms (Render/Vercel)"
    ]),
    
    ("2. HOW IT WORKS", [
        "User Input Processing:",
        "  - User submits news text or URL through web interface",
        "  - System extracts and sanitizes the input",
        "",
        "ML Detection Engine:",
        "  - Tokenizes text into individual words",
        "  - Applies TF-IDF vectorization for feature extraction",
        "  - Multinomial Naive Bayes classifier predicts fake/real",
        "  - Analyzes keyword patterns and source credibility",
        "",
        "Result Generation:",
        "  - Displays prediction label (Fake/Real)",
        "  - Shows confidence percentage (0-100%)",
        "  - Provides explanation signals for the prediction",
        "  - Stores result in SQLite database"
    ]),
    
    ("3. TECHNOLOGIES & LANGUAGES", [
        "BACKEND:",
        "  * Python 3.x - Core backend logic",
        "  * Flask 3.0.3 - Web framework",
        "  * Gunicorn 22.0.0 - WSGI server",
        "  * SQLite - Database",
        "  * Scikit-learn - ML library (Naive Bayes)",
        "  * NLTK - Natural Language Processing",
        "",
        "FRONTEND:",
        "  * HTML5 - Page structure",
        "  * CSS3 - Responsive styling",
        "  * JavaScript - Client-side interactivity",
        "",
        "AUTHENTICATION:",
        "  * JWT tokens - API authentication",
        "  * bcrypt - Password hashing",
        "  * Session cookies - Web authentication"
    ]),
    
    ("4. KEY FUNCTIONALITIES", [
        "User Management:",
        "  - Register/Login with email & password",
        "  - Role-based access (Admin/User)",
        "  - Password reset via email token",
        "  - Profile management",
        "",
        "News Verification:",
        "  - Submit text or URL for analysis",
        "  - Real-time ML prediction",
        "  - Confidence scoring",
        "  - Source credibility assessment",
        "",
        "History & Reporting:",
        "  - View all past predictions",
        "  - Filter by fake/real/date",
        "  - Save important reports",
        "  - Export to CSV/PDF",
        "",
        "Admin Dashboard:",
        "  - Analytics & user statistics",
        "  - User management & role assignment",
        "  - Report moderation",
        "  - Dataset management for ML",
        "  - Model monitoring",
        "  - Activity logs"
    ]),
]

for section_title, content in sections:
    pdf.set_font("Arial", "B", 13)
    pdf.cell(0, 10, section_title, ln=True)
    pdf.set_font("Arial", "", 10)
    for line in content:
        if line.startswith("  "):
            pdf.set_x(20)
            pdf.cell(0, 7, line, ln=True)
        elif line == "":
            pdf.ln(2)
        else:
            pdf.set_x(10)
            pdf.cell(0, 7, line, ln=True)
    pdf.ln(3)

pdf.add_page()
pdf.set_font("Arial", "B", 13)
pdf.cell(0, 10, "5. ADVANTAGES", ln=True)
pdf.set_font("Arial", "", 10)

advantages = [
    "* Fast Detection: Real-time prediction using lightweight ML model",
    "* User-Friendly: Clean, intuitive web interface for analysis",
    "* Scalable: Deployed on cloud platforms with auto-scaling",
    "* Data Privacy: SQLite local storage, no third-party APIs",
    "* Historical Tracking: Complete audit trail of predictions",
    "* Admin Controls: Full moderation and user management",
    "* API Available: REST endpoints for programmatic access",
    "* Cost-Effective: Open-source libraries, minimal dependencies",
    "* Multi-Format Support: Accept text, URLs, and uploaded files",
    "* Exportable: CSV and PDF report generation",
    "* Mobile-Responsive: Works on desktop, tablet, and mobile",
    "* Secure: JWT authentication, password hashing, CSRF protection"
]

for adv in advantages:
    pdf.set_x(10)
    pdf.cell(0, 7, adv, ln=True)

pdf.ln(3)
pdf.set_font("Arial", "B", 13)
pdf.cell(0, 10, "6. DISADVANTAGES", ln=True)
pdf.set_font("Arial", "", 10)

disadvantages = [
    "* Limited Training Data: Model trained on limited dataset samples",
    "* Language Bias: Primarily optimized for English text",
    "* No Real-Time Web Scraping: Cannot auto fetch latest news",
    "* False Positives/Negatives: Naive Bayes has inherent limitations",
    "* Static Features: Doesn't use advanced deep learning models",
    "* Database Constraints: SQLite limited for very large deployments",
    "* No Fact-Checking: Doesn't verify against external databases",
    "* Single ML Model: Relies on one algorithm (Multinomial Naive Bayes)",
    "* Manual Dataset Updates: Requires periodic retraining",
    "* No Multi-Language: English-only tokenization",
    "* Limited Explanation: Basic signal-based reasoning",
    "* No Real-time Updates: Predictions based on static models"
]

for dis in disadvantages:
    pdf.set_x(10)
    pdf.cell(0, 7, dis, ln=True)

pdf.add_page()
pdf.set_font("Arial", "B", 13)
pdf.cell(0, 10, "7. PROJECT STRUCTURE", ln=True)
pdf.set_font("Arial", "", 9)

structure = """
fake-news-detection-system/
|-- app.py                      # Main Flask entry point
|-- application/                # Core package
|   |-- __init__.py            # Package init
|   |-- auth.py                # Authentication logic
|   |-- detector.py            # ML prediction engine
|   |-- storage.py             # Database layer
|   |-- static/                # CSS & assets
|   |   -- styles.css
|   -- templates/              # HTML templates
|       |-- app_shell.html     # Base layout
|       |-- auth.html          # Login/signup
|       |-- index.html         # Dashboard
|       |-- forgot.html        # Password reset
|       -- reset.html
|-- data/
|   |-- training_data.json     # ML training set
|   -- predictions.db          # SQLite DB
|-- docs/                      # Documentation
|-- tests/                     # Unit tests
|-- requirements.txt           # Dependencies
-- vercel.json                # Deployment config
"""

pdf.set_font("Courier", "", 8)
for line in structure.split('\n'):
    pdf.cell(0, 5, line, ln=True)

pdf.add_page()
pdf.set_font("Arial", "B", 13)
pdf.cell(0, 10, "8. INSTALLATION & DEPLOYMENT", ln=True)
pdf.set_font("Arial", "", 10)

install_steps = [
    "LOCAL INSTALLATION:",
    "  1. Clone: git clone https://github.com/.../fake-news-detection",
    "  2. Install: pip install -r requirements.txt",
    "  3. Run: python app.py",
    "  4. Access: http://localhost:8000",
    "",
    "CLOUD DEPLOYMENT (Render/Vercel):",
    "  1. Push code to GitHub",
    "  2. Connect repository",
    "  3. Build: pip install -r requirements.txt",
    "  4. Start: gunicorn app:app",
    "  5. Deploy and access live URL",
    "",
    "DEFAULT ADMIN:",
    "  Email: admin@example.com",
    "  Password: admin123",
    "  (CHANGE IN PRODUCTION)"
]

for step in install_steps:
    if step.startswith("  "):
        pdf.set_x(15)
        pdf.cell(0, 6, step, ln=True)
    elif step == "":
        pdf.ln(1)
    else:
        pdf.set_x(10)
        pdf.cell(0, 7, step, ln=True)

pdf.set_font("Arial", "B", 13)
pdf.cell(0, 10, "9. API ENDPOINTS", ln=True)
pdf.set_font("Arial", "", 9)

endpoints = [
    "POST /api/login - Authentication (get JWT token)",
    "POST /api/verify-news - Submit news for detection",
    "GET /api/history - Retrieve prediction history",
    "POST /predict - Web form news submission",
    "GET /history - View past predictions",
    "GET /admin - Admin dashboard",
    "POST /profile - Update user profile",
    "GET /export/csv - Export predictions as CSV",
    "GET /export/pdf - Export single report as PDF"
]

for ep in endpoints:
    pdf.set_x(10)
    pdf.cell(0, 6, ep, ln=True)

pdf.add_page()
pdf.set_font("Arial", "B", 13)
pdf.cell(0, 10, "10. MACHINE LEARNING MODEL DETAILS", ln=True)
pdf.set_font("Arial", "", 10)

ml_details = [
    "Algorithm: Multinomial Naive Bayes Classifier",
    "",
    "Feature Extraction:",
    "  - Tokenization: Text split into individual words",
    "  - TF-IDF Vectorization: Term frequency calculation",
    "  - Vocabulary Size: ~5000+ unique words from training",
    "",
    "Training Process:",
    "  - Dataset: 2000+ labeled news samples (fake/real)",
    "  - Classes: Binary (Fake / Real)",
    "  - Probability calculation based on word frequencies",
    "",
    "Prediction Output:",
    "  - Label: Predicted class (Fake/Real)",
    "  - Confidence: Probability percentage (0-100%)",
    "  - Explanation: Top keywords influencing prediction"
]

for detail in ml_details:
    if detail.startswith("  "):
        pdf.set_x(15)
        pdf.cell(0, 6, detail, ln=True)
    elif detail == "":
        pdf.ln(1)
    else:
        pdf.set_x(10)
        pdf.cell(0, 7, detail, ln=True)

pdf.set_font("Arial", "B", 13)
pdf.ln(2)
pdf.cell(0, 10, "11. SECURITY FEATURES", ln=True)
pdf.set_font("Arial", "", 10)

security = [
    "* Password Hashing: bcrypt with salt for secure storage",
    "* JWT Tokens: Stateless authentication for API",
    "* Session Cookies: HttpOnly flag prevents XSS attacks",
    "* CSRF Protection: Form tokens for state-changing requests",
    "* SQL Injection Prevention: Parameterized queries",
    "* Rate Limiting: 120 requests per minute per IP",
    "* User Role-Based Access: Admin/User permission levels",
    "* Data Validation: Input sanitization before processing",
    "* Email Verification: Token-based password reset",
    "* Activity Logging: Complete audit trail of actions"
]

for sec in security:
    pdf.set_x(10)
    pdf.cell(0, 6, sec, ln=True)

pdf.set_font("Arial", "B", 13)
pdf.ln(2)
pdf.cell(0, 10, "12. FUTURE IMPROVEMENTS", ln=True)
pdf.set_font("Arial", "", 10)

future = [
    "* Deep Learning: Implement LSTM/Transformer models",
    "* Multi-Language: Support for 50+ languages",
    "* External APIs: Integrate fact-checking databases",
    "* Real-time Scraping: Auto-fetch and analyze breaking news",
    "* Advanced NLP: Sentiment analysis, entity recognition",
    "* Ensemble Models: Combine multiple ML algorithms",
    "* Database: Migrate to PostgreSQL for scaling",
    "* Mobile App: Native iOS/Android applications",
    "* Real-time Alerts: Notify users of trending fake news",
    "* Source Verification: Cross-reference with trusted sources"
]

for imp in future:
    pdf.set_x(10)
    pdf.cell(0, 6, imp, ln=True)

pdf.output("Fake_News_Detection_System_Complete_Documentation.pdf")
print("PDF created successfully!")
print("File: Fake_News_Detection_System_Complete_Documentation.pdf")
