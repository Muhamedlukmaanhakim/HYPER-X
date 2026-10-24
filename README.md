# AI Truth Inspector — RAG Evaluation & Failure Diagnosis Platform

> **"Trust, but verify."**

A production-grade developer tool and benchmarking platform built for AI/ML engineers, students, and hackathon judges to evaluate Retrieval-Augmented Generation (RAG) systems and explain **WHY** answers fail.

Instead of treating RAG pipelines as black boxes, AI Truth Inspector measures factual evidence grounding, calculates transparent deterministic retrieval metrics on local embeddings, classifies failure modes using a pure 8-step decision tree, runs controlled retrieval-time failure injections, and compares configurations on identical test sets with statistical rigor.

---

## 1. Key Capabilities

- **Zero-Cost Demo Mode:** Ships with a deterministic sample document (`sample_document.txt`) and a multi-type test suite. Runs real local embeddings and deterministic metrics with **zero API keys** and zero external costs.
- **Strict Grounded Ingestion & Parsing:** Extracts text from **PDF** (PyMuPDF with page-level preservation), **DOCX**, and **TXT** (with encoding fallback). Detects scanned/image-only PDFs and flags OCR limitations without crashing.
- **Pure Local Embeddings & Vector Store:** Dense local embeddings via `sentence-transformers` (`all-MiniLM-L6-v2`) cached in memory; persistent vector indexing using `ChromaDB` with cosine distance and configuration collection isolation.
- **Deterministic Metrics (No LLM Cost or Bias):**
  - **Recall@K:** Fraction of expected evidence pieces retrieved in top-K context.
  - **Cross-Chunking Evidence Mapping:** Robust page + text-span token overlap (ratio ≥ 0.50) so evaluations remain fair even when chunking parameters change.
  - **Hit Rate@K & MRR:** Mean Reciprocal Rank of the first relevant retrieved chunk.
  - **Normalized Match (Token F1) & Exact Match:** Token-level precision and recall.
  - **Numeric Match (with 1% Tolerance):** Number extraction and numeric equivalence.
  - **Citation Correctness & Abstention Sentinel:** Validates bracketed citations (`[Page X]` or `[chunk_id]`) and tests sentinel abstention (`INSUFFICIENT_EVIDENCE`) on unanswerable questions.
- **Pure 8-Step Failure Diagnosis Decision Tree:** Deterministic root-cause analysis backed by empirical facts. Categorizes cases into exact slugs (`retrieval_miss`, `incomplete_or_irrelevant_context`, `unsupported_answer`, `incorrect_despite_relevant_context`, `citation_error`, `unanswerable_answered`, `needs_review`, `pass`).
- **4-Panel Failure Detail View:**
  1. *Measured Observations* (empirical facts, scores, answers)
  2. *Rule-Based Classification* (which rule fired and actionable debugging recommendation)
  3. *Retrieved Evidence Passages* (side-by-side passage viewer with similarity scores)
  4. *Human-Verified Conclusion* (reviewer can override category and attach notes without mutating rule output)
- **Controlled Failure Injection:** Simulates retrieval degradation (drops relevant chunk, injects distractors, reduces top-K, truncates context) in-memory at retrieval time without corrupting the index. All simulated runs are badged `SIMULATED`.
- **Side-by-Side Configuration Comparison:** Evaluates candidate vs. baseline runs on identical test sets; highlights regressions as prominently as improvements; warns if sample size is small ($n < 20$).
- **Export & Auditability:** Full CSV export of per-case run results and high-level summary distributions.
- **Editorial Neo-Brutalist Design:** High-contrast aesthetic with `#F5F3ED` paper background, `#171717` ink borders, `#C6FF4D` lime brand accent, hard offset shadows (`4px 4px 0 #171717`), and Space Grotesk / JetBrains Mono typography.

---

## 2. Architecture & Tech Stack

```
ai-truth-inspector/
├── frontend/                     # React 19 + TypeScript + Vite + Tailwind CSS
│   ├── src/
│   │   ├── components/ui/        # Reusable Neo-Brutalist components (Button, Card, Badge, Modal, etc.)
│   │   ├── components/domain/    # Domain components (Navbar, FailureCategoryChart)
│   │   ├── pages/                # Dashboard, Documents, Playground, TestCases, Runner, Results, Compare, Settings
│   │   ├── lib/                  # api.ts (REST client), types.ts (TypeScript interfaces)
│   │   └── index.css             # Design tokens & @fontsource typography
│   └── package.json
├── backend/                      # Python 3.11+ / 3.13 FastAPI Service
│   ├── app/
│   │   ├── api/routers/          # documents, rag, testcases, evaluations, comparisons, settings, exports, jobs
│   │   ├── core/                 # config, security (redaction), logging, consistent errors
│   │   ├── models/               # SQLAlchemy 2.x SQLite models
│   │   ├── schemas/              # Pydantic v2 validation models
│   │   ├── services/             # ingestion, chunking, embeddings, vectorstore, rag, diagnosis, failure_injection, reports
│   │   └── main.py               # FastAPI app lifespan & CORS
│   ├── tests/                    # Pytest unit & integration test suite
│   ├── requirements.txt
│   └── pytest.ini
├── data/
│   ├── sample/                   # Deterministic sample document & test cases
│   ├── uploads/                  # Uploaded document files (gitignored)
│   └── chroma/                   # ChromaDB persistent vector database (gitignored)
├── .env.example                  # Secret template
├── .gitignore
└── README.md
```

### Technology Decisions:
- **Backend:** Python 3.11+ / 3.13, FastAPI, Pydantic v2, SQLAlchemy 2.x with SQLite (`truth_inspector.db`).
- **Extraction:** PyMuPDF (`fitz`), `python-docx`, robust encoding fallback for plain text.
- **Embeddings:** `sentence-transformers` (`all-MiniLM-L6-v2`) — runs 100% locally on CPU, $0.00 cost.
- **Vector Database:** `ChromaDB` persistent client with cosine distance.
- **LLM Provider:** Anthropic Python SDK (`anthropic`), supporting Claude 3.5 Sonnet / Haiku with exponential retry backoff.
- **Frontend:** React 19, TypeScript, Vite, Tailwind CSS, `@fontsource/space-grotesk`, `@fontsource/jetbrains-mono`, Lucide Icons, Recharts.

---

## 3. Quick Start & Setup

### Prerequisites
- Python 3.11, 3.12, or 3.13 installed
- Node.js v18+ and npm installed

### Step 1: Clone & Configure Environment
```bash
git clone <repo-url> ai-truth-inspector
cd ai-truth-inspector

# Copy environment template
cp .env.example backend/.env
```

### Step 2: Backend Setup
```bash
# Windows (PowerShell)
python -m venv backend\.venv
backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt

# Linux / macOS
python3 -m venv backend/.venv
source backend/.venv/bin/activate
pip install -r backend/requirements.txt
```

### Step 3: Frontend Setup
```bash
cd frontend
npm install
cd ..
```

---

## 4. Running the Platform Locally

### Launch Backend Server (Port 8000)
```bash
# Windows
backend\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --app-dir backend

# Linux / macOS
backend/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --app-dir backend
```
Backend health check: `http://127.0.0.1:8000/api/health`
Interactive Swagger Docs: `http://127.0.0.1:8000/docs`

### Launch Frontend Dev Server (Port 5173)
```bash
cd frontend
npm run dev
```
Open `http://127.0.0.1:5173` in your browser.

---

## 5. API Key Setup (Google Gemini & Anthropic)

The application runs in **Demo Mode** out of the box with zero keys. To enable live LLM generation and the optional LLM judge using your Gemini API key:

### Using Google Gemini (Recommended & Default):
1. Obtain an API key from [Google AI Studio](https://aistudio.google.com/app/apikey) (or copy your existing key).
2. Open `backend/.env` and configure:
   ```env
   LLM_PROVIDER=gemini
   GEMINI_API_KEY=AIzaSy...
   LLM_MODEL=gemini-1.5-flash
   ```
   *(Supported models: `gemini-1.5-flash`, `gemini-2.0-flash`, `gemini-1.5-pro`)*
3. Navigate to **Settings** in the web UI and click **"Test Connection"**.

### Using Anthropic Claude:
1. Open `backend/.env` and configure:
   ```env
   LLM_PROVIDER=anthropic
   ANTHROPIC_API_KEY=sk-ant-api03-...
   LLM_MODEL=claude-3-5-sonnet-20241022
   ```
2. Navigate to **Settings** in the web UI and click **"Test Connection"**.

**Security Guarantee:** Keys are stored **ONLY** in backend `.env` variables. Secrets are redacted automatically from all logs and error messages (`KEY_PATTERN` matches `AIzaSy...` and `sk-...`), and are **never** editable or visible in the browser UI.

---

## 6. Failure Diagnosis Decision Tree

When an evaluation run executes, each test case is diagnosed by a pure, deterministic decision function evaluated in strict sequential order:

```
[Test Case Result]
        │
        ├─► 1. Expected evidence missing for answerable case? ──► [needs_review]
        │
        ├─► 2. Unanswerable question but system answered? ──────► [unanswerable_answered]
        │
        ├─► 3. Zero expected evidence chunks in top-K context? ──► [retrieval_miss]
        │
        ├─► 4. Partial evidence retrieved & answer inaccurate? ─► [incomplete_or_irrelevant_context]
        │
        ├─► 5. Evidence present but answer has ungrounded claims?► [unsupported_answer]
        │
        ├─► 6. Evidence fully retrieved, but answer incorrect? ──► [incorrect_despite_relevant_context]
        │
        ├─► 7. Answer correct but citations missing or wrong? ───► [citation_error]
        │
        ├─► 8. Signal conflict or model judge parse error? ─────► [needs_review]
        │
        └─► Correct answer, verified citations, grounded context ─► [pass]
```

### Exact Slugs & Explanations
1. `retrieval_miss`: The retriever failed to surface any annotated ground-truth passage in the top-K context.
2. `incomplete_or_irrelevant_context`: Only a subset of multi-passage evidence was retrieved, or context was flooded with distractors, leading to an incomplete answer.
3. `unsupported_answer`: The retriever surfaced evidence, but the model hallucinated statements not supported by context.
4. `incorrect_despite_relevant_context`: 100% of required evidence was present in context, but the LLM made a synthesis or reasoning error.
5. `citation_error`: The answer is factually correct, but the model cited invalid chunk IDs, wrong pages, or omitted citations.
6. `unanswerable_answered`: The question is unanswerable from the corpus, but the system generated a speculative answer instead of outputting `INSUFFICIENT_EVIDENCE`.
7. `needs_review`: Ambiguous ground truth annotations, missing evidence tags, or judge formatting errors.
8. `pass`: Retrieval succeeded, answer is grounded, and citations are verified.

---

## 7. Mathematical Metric Definitions

| Metric | Type | Mathematical Formula | Limitations |
| :--- | :--- | :--- | :--- |
| **Retrieval Recall@K** | Deterministic | $\frac{\sum_{i=1}^{\|E\|} \mathbb{I}(\text{evidence}_i \in \text{topK})}{\|E\|}$ | Requires annotated evidence spans. Cross-chunking uses span-overlap ratio $\ge 0.50$. |
| **Hit Rate@K** | Deterministic | $\mathbb{I}(\text{Recall@K} > 0)$ | Binary flag; does not measure whether *all* multi-passage chunks were retrieved. |
| **MRR** | Deterministic | $\frac{1}{\min_{c \in E} \text{rank}(c)}$ | Focuses strictly on the rank of the first relevant passage. |
| **Exact Match (EM)** | Deterministic | $\mathbb{I}(\text{norm}(p) == \text{norm}(r))$ | Overly strict on phrasing differences. |
| **Token F1** | Deterministic | $\frac{2 \cdot P \cdot R}{P + R}$ over bag-of-words | Does not penalize factual contradictions with high vocabulary overlap. |
| **Numeric Match** | Deterministic | $\forall n_r \in N_{\text{ref}}, \exists n_p \in N_{\text{pred}} : \frac{\|n_p - n_r\|}{\max(\|n_r\|, 10^{-9})} \le 0.01$ | Validates quantities and rates; does not parse dimensional units. |
| **Citation Correctness** | Deterministic | $\frac{\text{citations} \cap \text{evidence}}{\text{total citations}}$ | Requires model to use bracketed notation `[Page X]` or `[chunk_id]`. |
| **Abstention Correctness**| Deterministic | $\mathbb{I}(\text{should\_abstain} == \text{abstained})$ | Binary test for the sentinel `INSUFFICIENT_EVIDENCE`. |
| **Model Judge** | Model-Judged | Structured JSON score $\in [0.0, 1.0]$ with rationale | LLM judges can be subjective; treated as indicative, never ground truth. |

---

## 8. Automated Test Execution

All backend unit and integration tests are automated with pytest.

### Run Backend Test Suite:
```bash
# Windows
backend\.venv\Scripts\python.exe -m pytest backend\tests -v

# Linux / macOS
backend/.venv/bin/pytest backend/tests -v
```

### Verified Test Outcome:
```
backend/tests/test_chunking.py::test_chunk_pages_preserves_page_numbers_and_stable_ids PASSED
backend/tests/test_chunking.py::test_chunking_overlap PASSED
backend/tests/test_chunking.py::test_chunking_token_and_char_estimates PASSED
backend/tests/test_diagnosis.py::test_rule_1_missing_expected_evidence_gives_needs_review PASSED
backend/tests/test_diagnosis.py::test_rule_2_unanswerable_answered_gives_unanswerable_answered PASSED
backend/tests/test_diagnosis.py::test_rule_3_retrieval_miss PASSED
backend/tests/test_diagnosis.py::test_rule_4_incomplete_or_irrelevant_context PASSED
backend/tests/test_diagnosis.py::test_rule_5_unsupported_answer PASSED
backend/tests/test_diagnosis.py::test_rule_6_incorrect_despite_relevant_context PASSED
backend/tests/test_diagnosis.py::test_rule_7_citation_error PASSED
backend/tests/test_diagnosis.py::test_pass_case PASSED
backend/tests/test_failure_injection.py::test_failure_injection_removes_relevant_chunk PASSED
backend/tests/test_failure_injection.py::test_failure_injection_injects_distractors PASSED
backend/tests/test_failure_injection.py::test_failure_injection_disabled_does_nothing PASSED
backend/tests/test_integration_slice.py::test_full_vertical_slice_integration PASSED
backend/tests/test_metrics.py::test_recall_at_k_hand_computed_fixture PASSED
backend/tests/test_metrics.py::test_hit_rate_at_k_and_mrr PASSED
backend/tests/test_metrics.py::test_evidence_mapping_across_chunkings PASSED
backend/tests/test_metrics.py::test_match_metrics PASSED
backend/tests/test_metrics.py::test_citation_and_abstention_correctness PASSED

======================= 20 passed in 14.27s =======================
```

### Run Frontend Typecheck & Build:
```bash
cd frontend
npm run build
```
Build verification: `✓ built in 1.43s` with zero TypeScript errors.

---

## 9. 3–5 Minute Hackathon Demo Script

Follow this sequence to demo the full platform to judges in under 5 minutes:

1. **Dashboard & Philosophy (0:00 - 0:45)**
   - Open `http://127.0.0.1:5173`.
   - Point out the headline **"Trust, but verify."** and the yellow **DEMO MODE** banner explaining zero API cost.
   - Click **"Load Sample Data"** to load the multi-page Acme Corp engineering policy and deterministic benchmark test set.
2. **Interactive Playground & Provenance (0:45 - 1:30)**
   - Click **Playground** in the navigation bar.
   - Click the preset query: *"What is the standard API rate limit for Tier 1 consumers?"*
   - Click **Ask**. Point out the side-by-side view: the grounded answer with `[Page 2]` citation on the left, and the exact retrieved passage with similarity score on the right.
   - Click the unanswerable query: *"What is the liquid nitrogen cooling temperature for Acme Corp's quantum processor fleet?"*
   - Show how the system abstains cleanly with `INSUFFICIENT_EVIDENCE` instead of hallucinating.
3. **Run Evaluation: Baseline vs. Simulated Failure (1:30 - 2:45)**
   - Navigate to **Run Eval**.
   - Click the prominent green button **"Run Baseline"**. Show the instant computation of Recall@K, MRR, and Pass Rate.
   - Return to **Run Eval** and click **"Run Injected Failure"**.
   - Show how the failure injection simulates dropping relevant chunks and adding distractors without touching the underlying ChromaDB index.
   - Show the resulting run badged prominently with purple **SIMULATED**.
4. **Failure Diagnosis & 4-Panel Root Cause (2:45 - 3:45)**
   - Open the simulated run results and click **"Diagnose"** on a failed case.
   - Walk through the 4 distinct diagnostic panels:
     1. *Measured Observations:* Empirical facts and recall score (0.0).
     2. *Rule-Based Classification:* Rule 3 fired (`retrieval_miss`) with actionable recommendations.
     3. *Retrieved Evidence Passages:* Visual evidence that context only contained distractors.
     4. *Human-Verified Conclusion:* Select an override category, add a note (e.g., *"Confirmed distractor noise"*), and click **Save Reviewer Override**.
5. **Configuration Comparison Matrix (3:45 - 4:30)**
   - Click **Compare** in the navbar.
   - Select Baseline Run (A) and Perturbed Run (B).
   - Click **Execute Side-by-Side Comparison**.
   - Show the red delta badges highlighting regressions prominently (`-83.3% Recall`, `5 Regressed Cases`).
   - Point out the statistical caution notice ($n < 20$).
   - Click **Export Case CSV** on the Results page to show clean, comma-separated audit data.

---

## 10. Honest Disclosures & Limitations

- **OCR Limitations:** Optical Character Recognition is not supported. Scanned, flattened image PDFs contain no extractable text layer and will be flagged with a warning rather than silently crashing.
- **Sample Size & Statistical Noise:** Small benchmark datasets ($n < 20$) are subject to statistical variance; observed metric deltas between configurations may reflect noise rather than structural superiority.
- **Embedding Language Scope:** The default local embedding model `all-MiniLM-L6-v2` is optimized for English technical prose. Multi-lingual corpora may require a multilingual model (e.g. `paraphrase-multilingual-MiniLM-L12-v2`).
- **LLM Judge Fallibility:** When LLM judges are enabled, model verdicts are indicative rather than absolute ground truth. Deterministic metrics remain the primary source of truth.

---

## 11. Deviations

- **Custom Metrics vs. Heavy Ragas:** Rather than bundling the heavy, frequently breaking Ragas library with dozens of conflicting dependency constraints, AI Truth Inspector uses custom, transparent, unit-tested deterministic metric implementations (Recall@K, Hit Rate, MRR, Token F1, numeric match, citation parser). This guarantees zero flaky failures, zero external API costs during local runs, and complete mathematical transparency for every number shown.
