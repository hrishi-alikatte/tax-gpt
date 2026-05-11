# VaudTaxAI

**English-first, Vaud-only tax filing copilot for C-permit expat employees in Canton Vaud, Switzerland.**

VaudTaxAI is a bounded copilot designed to help taxpayers navigate the Vaud tax process. It simplifies document extraction, identifies missing declarations or deductions, and explains requirements using official Vaud sources.

## 🚀 Key Features

- **Profile Intake**: Captures basic taxpayer profile (C-permit, employee status).
- **Document Extraction**: Automated extraction of values from tax documents (e.g., Certificates of Salary) with a **mandatory user confirmation gate**.
- **Completeness Engine**: Deterministic detection of missing documents or obvious deductions based on the taxpayer's profile.
- **Source-Grounded Explanations**: RAG-based Q&A using official Vaud 2025 Instructions with mandatory inline citations.
- **Field Mapping**: Maps English concepts to official VaudTax / French field names and codes.

## 🏗️ Architecture & Philosophy

VaudTaxAI follows a strict **AI vs. Deterministic responsibility split**:

| Layer | Implementation | Rationale |
|-------|----------------|-----------|
| **Field Extraction** | LLM (Structured Pydantic) | Flexible extraction from various document formats. |
| **User Confirmation** | Deterministic UI | Ensuring user accountability for every extracted value. |
| **Completeness Rules** | Deterministic (Python) | Rules are transparent, testable, and cited. |
| **Tax Computation** | **None** | Out of scope. We do not calculate final tax liability. |
| **Submission** | **None** | Out of scope. We do not file on behalf of users. |

For more details, see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) and [docs/DOMAIN_MODEL.md](docs/DOMAIN_MODEL.md).

## 🛡️ Privacy & Safety

- **Data Privacy**: No real user financial documents are ever committed to the repository. The application is designed to handle PII locally.
- **No Hallucinations**: Every tax fact and completeness rule is grounded in official sources (e.g., Vaud 2025 Instructions).
- **No Legal Advice**: The product is a copilot, not an autonomous filer or a legal/fiduciary advisor.

## 🛠️ Getting Started

### Prerequisites
- Python 3.10+
- [Flet](https://flet.dev/) (for UI)
- API Keys for Azure OpenAI or Groq (see `.env.example`)

### Installation
1. Clone the repository.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Set up your environment variables:
   ```bash
   cp .env.example .env
   # Add your API keys to .env
   ```

### Running the Application
```bash
python main.py
```

### Running Tests
```bash
pytest
```

## 🧪 Demo Mode
To see the full pipeline in action without uploading real documents, run the demo runner:
```bash
python -m demo.runner --scenario expat_c_permit_basic
```

## 📄 License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
