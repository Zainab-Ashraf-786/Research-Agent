# Quickstart Guide: Research Brief Agent

**Branch**: `001-research-brief-pipeline`  
**Date**: 2026-10-05

This guide provides step-by-step instructions to run, test, and evaluate the Research Brief Agent locally.

---

## 1. Setup & Environment

```bash
# 1. Clone or navigate to the repository
cd "C:\Users\Zainab Ashraf\OneDrive\Desktop\Research Brief Agent\ResearchBriefAgent"

# 2. Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\activate

# 3. Install pinned dependencies
pip install -r requirements.txt

# 4. Configure local environment variables
copy .env.example .env
```

Edit `.env` (optional for offline testing; required for live queries):
```env
LLM_BASE_URL="https://generativelanguage.googleapis.com/v1beta/openai/"
LLM_MODEL="gemini-2.5-flash"
LLM_API_KEY="your-gemini-api-key"
LLM_MIN_INTERVAL_SECONDS=2.0
TAVILY_API_KEY="tvly-your-tavily-key"
```

---

## 2. Running Automated Tests

Run the full unit test suite without needing live API keys:

```bash
pytest tests/ -v
```

This validates:
- `test_match_quote.py`: Exact numeric matching, negation preservation, and fuzzy text handling.
- `test_llm.py`: Pacing, backoff on transient errors, fast-fail on daily quota exhaustion, and JSON repair.
- `test_schemas.py`: Pydantic data serialization and schema constraints.
- `test_pipeline_mock.py`: End-to-end pipeline execution with mocked search and LLM calls, asserting call budget ($\le 7$) and confirming zero `os.environ` pollution.

---

## 3. Running the Streamlit Web Application

```bash
streamlit run app.py
```

### Modes Available:
1. **Example Briefs (Zero API Quota)**:
   - Select one of the 3 pre-saved research briefs from the sidebar dropdown.
   - Instantly renders the brief, summary metrics, verification badges, and expandable source quotes with zero API calls.
2. **Run Live (BYOK)**:
   - Enter your `LLM API Key` and `Tavily API Key` in the sidebar.
   - Choose your provider (Google Gemini, Groq, OpenRouter, or Custom).
   - Enter a research question and click **Generate Brief**.
   - Watch real-time stage progress and download the completed brief as Markdown.

---

## 4. Running the Evaluation Suite

```bash
python eval/run_eval.py
```

Outputs:
- **Verifier Accuracy**: Agreement rate against the 35 hand-labeled ground-truth claims (reported separately for 25 dev claims and 10 held-out claims).
- **Confusion Matrix**: Precision, recall, and false-`SUPPORTED` rates for `SUPPORTED`, `PARTIAL`, and `UNSUPPORTED` verdicts.
- **Pipeline Metrics**: Fact recall, citation rate, and average latency across 10 benchmark questions.
