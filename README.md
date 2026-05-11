# ⚖️ Legalassist AI

**Dismantling the Information Barrier in the Judiciary.**

Legalassist AI is an advanced, AI-powered platform designed to empower citizens by providing instant clarity on complex judicial judgments. By converting jargon-heavy legal documents into simple, actionable summaries in multiple languages, we bridge the gap between the judiciary and the common citizen.

---

## 🚀 Key Features

### 🔍 Judgment Simplification
- **Instant Summaries**: Converts long, complex PDF judgments into three key, easy-to-understand points.
- **Multilingual Support**: Supports English, Hindi, Bengali, and Urdu to ensure accessibility for a diverse population.
- **Actionable Advice**: Automatically identifies the next steps, appeal possibilities, and deadlines.

### 📝 One-Click Drafting Center
- **Automated Legal Drafts**: Generate formal legal notices or appeal drafts based on the judgment analysis.
- **Interactive Editing**: Review and edit AI-generated drafts directly in the browser.
- **Professional Export**: Download finalized drafts as high-quality PDF documents.

### 📊 Analytics & Predictions
- **Appeal Success Estimator**: Get a probability score for appeal success based on similar historical cases.
- **Regional Trends**: Visualize success rates and timelines across different jurisdictions, courts, and judges.
- **Community Driven**: Contribute anonymized case outcomes to improve predictions for all users.

### 💾 Case & Deadline Management
- **Centralized Case History**: Track all your processed judgments and legal documents in one place.
- **Automated Deadlines**: Never miss an appeal date with auto-generated deadline tracking and notifications.
- **Secure Storage**: Encrypted storage for your legal information.

### 📞 Localized Legal Help
- **State-wise Directory**: Find local legal aid authorities, law clinics, and NGOs in your state.
- **Cost Estimates**: Get an idea of typical appeal costs in your region.

---

## 🛠️ CLI Tool for Batch Processing

For legal aid teams and organizations handling large volumes of judgments, Legalassist AI provides a robust Command-Line Interface.

### Installation
```bash
pip install -r requirements.txt
```

### Quick Start
```bash
# Process a single file
python cli.py process --file judgment.pdf --language Hindi

# Batch process a folder
python cli.py batch --folder ./documents --output results.csv --workers 4
```

*For more details on CLI usage, see the [CLI section](#cli-commands-full).*

---

## 💻 Getting Started (Web App)

### 1. Initialize Database
```bash
python -c "from database import init_db; init_db()"
```

### 2. Set Environment Variables
Copy `.env.example` to `.env` and fill in your API keys (OpenRouter/OpenAI).

### 3. Start the Application
```bash
streamlit run app.py
```

---

## 🏗️ Project Structure

For a detailed breakdown of the file structure and working principles, please refer to [INSTRUCTIONS.md](./INSTRUCTIONS.md).

---

## 🛡️ Privacy & Security
- **Anonymization**: All analytics data is strictly anonymized. No case numbers or personal names are stored in the public trends database.
- **Data Protection**: Your private documents and case history are protected by secure authentication.

---

## 🤝 Contributing
We welcome contributions! Please see [CONTRIBUTING.md](./CONTRIBUTING.md) for guidelines.

---

## 📄 License
This project is licensed under the MIT License - see the [LICENSE](./LICENSE) file for details.
