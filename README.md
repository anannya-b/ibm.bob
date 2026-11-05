# 💰 FinLit AI – Digital Financial Literacy Agent

An AI-powered RAG (Retrieval-Augmented Generation) agent that helps Indian users understand digital financial tools, detect online scams, plan budgets, and make smarter financial decisions. Powered by **IBM Granite** via **IBM watsonx.ai**.

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🤖 **AI Chat** | Conversational Q&A powered by IBM Granite 13B |
| 📚 **RAG Pipeline** | Answers grounded in a curated India-specific knowledge base |
| 🚨 **Fraud Detector** | Real-time scam signal detection on every message |
| 🌐 **Multilingual** | English, Hindi, Bengali, Tamil, Telugu, Marathi, Gujarati |
| 📊 **Budget Calculator** | 50/30/20 rule with visual breakdown and personalized tips |
| 🏦 **EMI Calculator** | Standard EMI formula with total interest breakdown |
| 📈 **Interest Explainer** | SI vs CI comparison + RBI-informed rate safety assessment |
| 💬 **Session Memory** | Keeps last 5 conversation turns for context continuity |
| 🔄 **Graceful Fallback** | Rule-based RAG response if LLM is unavailable |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend (Browser)                   │
│   index.html · style.css · app.js                          │
│   Chat UI · Budget Modal · EMI Modal · Fraud Banner        │
└─────────────────────────┬───────────────────────────────────┘
                          │ REST API (HTTP/JSON)
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                   FastAPI Backend (main.py)                 │
│                                                             │
│  POST /chat ─────────┐                                      │
│  POST /budget        │                                      │
│  POST /emi           │                                      │
│  POST /interest      │                                      │
│  GET  /health        │                                      │
└──────────────────────┼──────────────────────────────────────┘
                       │
        ┌──────────────┼──────────────────┐
        ▼              ▼                  ▼
┌──────────────┐ ┌───────────┐  ┌────────────────────┐
│rag_pipeline  │ │granite_llm│  │translator.py        │
│(LangChain +  │ │(watsonx.ai│  │(deep-translator +   │
│ ChromaDB +   │ │ IBM Granite│ │ langdetect)         │
│ MiniLM-L6-v2)│ │)          │  └────────────────────┘
└──────┬───────┘ └───────────┘
       │
       ▼
┌──────────────┐  ┌──────────────────┐  ┌──────────────────┐
│knowledge_base│  │fraud_detector.py │  │budget_calculator │
│  .txt files  │  │(keyword + regex) │  │interest_explainer│
└──────────────┘  └──────────────────┘  └──────────────────┘
```

---

## 📋 Prerequisites

- Python **3.10+**
- pip 23+
- An **IBM Cloud** account (free Lite plan works)
- A **watsonx.ai** project on IBM Cloud

---

## 🚀 Setup Instructions

### 1. Clone / Download the project

```bash
# If using git
git clone <your-repo-url>
cd financial-literacy-agent
```

### 2. Set up Python virtual environment

```bash
cd backend
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (macOS/Linux)
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

> ⏱️ First run downloads the `sentence-transformers/all-MiniLM-L6-v2` model (~90 MB). This is cached locally for subsequent runs.

### 4. Configure environment variables

```bash
# Copy the example file
cp ../.env.example .env   # macOS/Linux
copy ..\.env.example .env  # Windows

# Edit .env and fill in your credentials
notepad .env   # Windows
nano .env      # macOS/Linux
```

Required variables in `.env`:
```
WATSONX_API_KEY=your_ibm_cloud_api_key
WATSONX_PROJECT_ID=your_watsonx_project_id
WATSONX_URL=https://us-south.ml.cloud.ibm.com
```

### 5. Get IBM watsonx.ai Credentials

1. **Create IBM Cloud account**: [cloud.ibm.com](https://cloud.ibm.com) (free Lite plan)
2. **Create API Key**: [cloud.ibm.com/iam/apikeys](https://cloud.ibm.com/iam/apikeys) → "Create an IBM Cloud API key"
3. **Create watsonx.ai project**:
   - Go to [dataplatform.cloud.ibm.com](https://dataplatform.cloud.ibm.com)
   - Create a new project
   - Copy the **Project ID** from the project settings
4. **Enable IBM Granite model**: In your project → "Manage" → "Associate service" → add watsonx.ai runtime

### 6. Start the backend

```bash
# From the backend/ directory
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Expected output:
```
INFO:     FinLit AI starting up — pre-loading RAG vector store…
INFO:     Loading embedding model: sentence-transformers/all-MiniLM-L6-v2
INFO:     Building vector store from knowledge base documents…  (first run only)
INFO:     Vector store built and persisted to ./chroma_db
INFO:     IBM Granite model initialized: ibm/granite-13b-chat-v2
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### 7. Open the frontend

Simply open `frontend/index.html` in your browser:

```bash
# macOS
open ../frontend/index.html

# Windows
start ..\frontend\index.html
```

Or serve it with any static file server:
```bash
# Python built-in server (from frontend/ directory)
python -m http.server 3000
# Then open: http://localhost:3000
```

---

## 🔌 API Documentation

### `POST /chat`
Main conversational chat endpoint.

**Request body:**
```json
{
  "message": "How do I use UPI safely?",
  "language": "en",
  "session_id": "optional-uuid-for-history"
}
```

**Response:**
```json
{
  "response": "UPI is safe when you follow these tips…",
  "fraud_warning": null,
  "sources_used": 3,
  "language": "en",
  "session_id": "abc123-…"
}
```

**Supported language codes:** `en`, `hi`, `bn`, `ta`, `te`, `mr`, `gu`, `auto`

---

### `POST /budget`
Calculate 50/30/20 budget breakdown.

**Request:**
```json
{ "monthly_income": 60000 }
```

**Response:**
```json
{
  "monthly_income": 60000,
  "needs": { "amount": 30000, "percentage": 50, "examples": […] },
  "wants": { "amount": 18000, "percentage": 30, "examples": […] },
  "savings": { "amount": 12000, "percentage": 20, "examples": […] },
  "summary": "…",
  "tips": ["…", "…"]
}
```

---

### `POST /emi`
Calculate Equated Monthly Instalment.

**Request:**
```json
{ "principal": 500000, "rate": 8.5, "tenure_months": 240 }
```

**Response:**
```json
{
  "emi": 4340.12,
  "total_payment": 1041629.0,
  "total_interest": 541629.0,
  "interest_percentage": 108.33,
  "amortization_summary": "…"
}
```

---

### `POST /interest`
Explain interest rates with SI vs CI comparison.

**Request:**
```json
{
  "loan_type": "home",
  "amount": 5000000,
  "rate": 8.5,
  "tenure_years": 20
}
```

**Response:**
```json
{
  "loan_name": "Home Loan",
  "simple_interest": { "interest_amount": 8500000.0, "total_repayment": 13500000.0 },
  "compound_interest": { "interest_amount": 15026526.0, "total_repayment": 20026526.0 },
  "rate_assessment": { "status": "safe", "message": "✅ 8.5% is within the safe range…" },
  "comparison_insight": "…",
  "recommendation": "…"
}
```

**Valid loan types:** `home`, `personal`, `education`, `car`, `gold`

---

### `GET /health`
```json
{ "status": "ok", "model": "ibm/granite-13b-chat-v2", "version": "1.0.0" }
```

---

### `DELETE /session/{session_id}`
Clear conversation history for a session.

---

### `GET /rebuild-index`
Force-rebuild the ChromaDB RAG index after adding new knowledge base files.

---

## 📁 Project Structure

```
financial-literacy-agent/
├── backend/
│   ├── main.py                  # FastAPI app & all endpoints
│   ├── rag_pipeline.py          # Document loading, chunking, ChromaDB
│   ├── granite_llm.py           # IBM Granite via watsonx.ai SDK
│   ├── translator.py            # deep-translator multilingual support
│   ├── fraud_detector.py        # Keyword/regex fraud signal detection
│   ├── budget_calculator.py     # 50/30/20 rule + EMI formula
│   ├── interest_explainer.py    # SI/CI calculation + RBI rate safety
│   ├── requirements.txt         # Python dependencies
│   ├── knowledge_base/
│   │   ├── upi_guide.txt        # UPI usage, safety, apps, limits
│   │   ├── scam_awareness.txt   # Online scam types, red flags, reporting
│   │   ├── interest_rates.txt   # RBI policy rates, loan/FD rates
│   │   ├── budgeting.txt        # 50/30/20, EPF/PPF/SIP, savings goals
│   │   └── personal_finance.txt # CIBIL, insurance, mutual funds, 80C
│   └── chroma_db/               # Auto-created vector store (gitignore this)
├── frontend/
│   ├── index.html               # Single-page chat UI
│   ├── style.css                # Modern responsive styling
│   └── app.js                   # Chat, calculators, fraud UI logic
├── .env.example                 # Environment variable template
└── README.md                    # This file
```

---

## 🔒 Security Notes

- **Never commit your `.env` file** — add it to `.gitignore`
- The fraud detector runs on **every** user message server-side
- Session data is stored **in-memory only** — cleared on server restart
- CORS is currently set to `allow_origins=["*"]` for development — restrict this in production

---

## 🛠️ Extending the Knowledge Base

1. Add new `.txt` files to `backend/knowledge_base/`
2. Hit the rebuild endpoint: `GET http://localhost:8000/rebuild-index`
3. The new content will be available for RAG retrieval immediately

---

## 🐛 Troubleshooting

| Problem | Solution |
|---------|----------|
| `WATSONX_API_KEY not set` | Ensure `.env` exists in `backend/` and has the key set |
| `ChromaDB collection is empty` | Run `GET /rebuild-index` or delete the `chroma_db/` folder |
| `sentence-transformers slow to load` | Normal on first run; model is cached at `~/.cache/huggingface/` |
| `CORS error in browser` | Ensure backend is running on port 8000 |
| `Translation fails` | `deep-translator` requires internet; check your connection |
| Frontend shows "Offline" | Start the backend with `uvicorn main:app --reload` |

---

## 📸 Screenshots

> _Add screenshots here after running the project._

- Chat interface with fraud warning banner
- Budget Calculator modal with 50/30/20 bars  
- EMI Calculator results

---

## 📜 License

MIT License – free to use, modify, and distribute.

---

## 🤝 Acknowledgements

- [IBM watsonx.ai](https://www.ibm.com/watsonx) – IBM Granite LLM
- [LangChain](https://langchain.com/) – RAG orchestration
- [ChromaDB](https://www.trychroma.com/) – Vector store
- [NPCI](https://www.npci.org.in/) & [RBI](https://www.rbi.org.in/) – Financial data sources
