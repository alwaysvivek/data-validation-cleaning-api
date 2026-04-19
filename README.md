# 🧹 Data Validation & Cleaning API

A FastAPI-based service that cleans, validates, and standardizes raw datasets into structured, production-ready data — powered by Pandas and optionally enhanced with Groq AI.

---

## 🔴 Problem

Raw datasets are messy and unreliable:
- Missing values scattered across columns
- Duplicate rows inflating metrics
- Inconsistent formatting (dates, names, categories)
- Mixed data types within columns
- Leading/trailing whitespace corruption

Manual cleaning is tedious, error-prone, and doesn't scale.

## ✅ Solution

An API-based validation + cleaning pipeline that:
1. **Validates** — scans for nulls, duplicates, mixed types, and formatting issues
2. **Scores** — computes a data quality score (0–100, letter-graded)
3. **Cleans** — applies configurable cleaning operations via Pandas
4. **Exports** — returns clean data as JSON, CSV, or Excel

> *"I built it so non-technical users can upload Excel and get clean data back — no code required."*

## 📤 Output

- **JSON** — structured, API-ready data with full quality reports
- **CSV** — cleaned tabular download
- **Excel** — `.xlsx` file download for business users

---

## ⚡ Features

| Feature | Description |
|---------|-------------|
| **Data Quality Score** | 0–100 score based on null %, duplicates, and type consistency (A–F grade) |
| **Preview Endpoint** | See first 10 rows + column types before processing |
| **Configurable Cleaning** | Control null handling, dedup, whitespace, column naming, date conversion |
| **Row Limiting** | Process only first N rows for large datasets |
| **Multi-format Export** | JSON (default), CSV, or Excel — controlled via query param |
| **Processing Metrics** | `X-Processing-Time-Ms` header on every response |
| **Structured Errors** | Consistent JSON error format with codes and timestamps |
| **Groq AI (Optional)** | LLM-powered cleaning suggestions, value standardization, and data profiling |
| **Request Logging** | Every request logged with method, path, status, and duration |

---

## 🚀 Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/your-username/data-validation-cleaning-api.git
cd data-validation-cleaning-api
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure (Optional — for AI features)

```bash
cp .env.example .env
# Edit .env and add your GROQ_API_KEY
```

### 3. Run

```bash
uvicorn app.main:app --reload
```

### 4. Open Docs

Visit **http://localhost:8000/docs** for the interactive Swagger UI.

---

## 📡 API Reference

### Core Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check — returns version and Groq availability |
| `POST` | `/api/v1/preview/file` | Upload a file → get first 10 rows, column types, quality score |
| `POST` | `/api/v1/process` | Send JSON data → validate, clean, score, export |
| `POST` | `/api/v1/process/file` | Upload a file → validate, clean, score, export |

### AI Endpoints (requires `GROQ_API_KEY`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/ai/suggest` | Upload file → get AI cleaning suggestions |
| `POST` | `/api/v1/ai/standardize` | Send messy values → get standardized mapping |
| `POST` | `/api/v1/ai/profile` | Upload file → get natural-language quality summary |

### Query Parameters for `/process`

| Param | Values | Default | Description |
|-------|--------|---------|-------------|
| `format` | `json`, `csv`, `excel` | `json` | Output format |
| `limit` | integer ≥ 1 | none | Process only first N rows |

---

## 📋 Usage Examples

### Preview a Dataset

```bash
curl -X POST http://localhost:8000/api/v1/preview/file \
  -F "file=@messy_data.csv"
```

### Process JSON Data

```bash
curl -X POST "http://localhost:8000/api/v1/process" \
  -H "Content-Type: application/json" \
  -d '{
    "data": [
      {"name": "  Alice  ", "age": 30, "city": "NY"},
      {"name": "Bob", "age": null, "city": "New York"},
      {"name": "  Alice  ", "age": 30, "city": "NY"}
    ],
    "options": {
      "handle_nulls": "fill_mode",
      "remove_duplicates": true,
      "standardize_columns": true
    }
  }'
```

### Upload Excel → Download Cleaned CSV

```bash
curl -X POST "http://localhost:8000/api/v1/process/file?format=csv" \
  -F "file=@messy_data.xlsx" \
  -o cleaned_data.csv
```

### Upload Excel → Download Cleaned Excel

```bash
curl -X POST "http://localhost:8000/api/v1/process/file?format=excel" \
  -F "file=@messy_data.xlsx" \
  -o cleaned_data.xlsx
```

### Process Only First 100 Rows

```bash
curl -X POST "http://localhost:8000/api/v1/process/file?limit=100" \
  -F "file=@large_dataset.csv"
```

### AI: Get Cleaning Suggestions

```bash
curl -X POST http://localhost:8000/api/v1/ai/suggest \
  -F "file=@messy_data.csv"
```

### AI: Standardize Messy Values

```bash
curl -X POST http://localhost:8000/api/v1/ai/standardize \
  -H "Content-Type: application/json" \
  -d '{"values": ["NY", "New York", "new york", "N.Y."], "context": "US states"}'
```

---

## 📊 Data Quality Score

Every response includes a quality score computed from three dimensions:

| Dimension | Weight | Measures |
|-----------|--------|----------|
| **Null Score** | 40% | Percentage of non-null cells |
| **Duplicate Score** | 30% | Percentage of unique rows |
| **Consistency Score** | 30% | Type consistency within columns |

**Grading:**

| Grade | Score Range |
|-------|-------------|
| A | 90 – 100 |
| B | 75 – 89 |
| C | 60 – 74 |
| D | 40 – 59 |
| F | 0 – 39 |

The `/process` endpoint returns **both** before and after scores so you can see the improvement.

---

## 🧹 Cleaning Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `remove_duplicates` | bool | `true` | Remove duplicate rows |
| `handle_nulls` | string | `"drop"` | Strategy: `drop`, `fill_mean`, `fill_median`, `fill_mode`, `fill_empty` |
| `strip_whitespace` | bool | `true` | Trim leading/trailing whitespace |
| `standardize_columns` | bool | `true` | Rename columns to `snake_case` |
| `remove_empty_rows` | bool | `true` | Drop rows where all values are null |
| `convert_dates` | bool | `true` | Auto-detect and convert date columns |

---

## 🧪 Tests

```bash
pytest tests/ -v
```

---

## 🛠 Tech Stack

- **FastAPI** — async web framework
- **Pydantic v2** — data validation and serialization
- **Pandas** — data cleaning engine
- **openpyxl** — Excel read/write
- **Groq** — LLM API for AI-powered features
- **pytest + httpx** — testing

---

## 📁 Project Structure

```
├── app/
│   ├── main.py              # FastAPI app entry point
│   ├── config.py             # Settings (env-based)
│   ├── errors.py             # Structured error handling
│   ├── middleware.py          # Timing + logging middleware
│   ├── routes/
│   │   ├── health.py         # GET /health
│   │   ├── process.py        # /process, /preview
│   │   └── ai.py             # /ai/* endpoints
│   ├── models/
│   │   ├── requests.py       # Input schemas
│   │   └── responses.py      # Output schemas
│   └── services/
│       ├── validator.py       # Validation + quality scoring
│       ├── cleaner.py         # Pandas cleaning engine
│       ├── file_handler.py    # CSV/Excel I/O
│       └── ai_service.py      # Groq LLM integration
├── tests/
├── requirements.txt
├── .env.example
└── README.md
```

---

## 📜 License

MIT
