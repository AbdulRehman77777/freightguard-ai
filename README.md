# FreightGuard AI

FreightGuard AI is a production-minded Python CLI that converts unstructured freight documents into validated JSON and makes a conservative, deterministic approval decision. It accepts UTF-8 text and selectable-text PDFs, uses OpenAI Structured Outputs only for field extraction, and keeps schema enforcement and business decisions in ordinary Python.

## Problem statement

Freight operations receive inconsistent rate confirmations and order agreements. Manual transcription is slow, while letting an LLM approve loads or silently repair totals is unsafe. FreightGuard AI preserves the source values, enforces a typed contract, identifies financial discrepancies, overweight shipments, and incomplete data, then returns either `APPROVED` or `FLAGGED_FOR_HUMAN_REVIEW` with auditable explanations.

## Features

- TXT and multi-page PDF text extraction with empty/scanned-document detection
- Prompt-injection-aware OpenAI extraction using native Pydantic Structured Outputs
- Nullable extraction schema followed by a strict final schema
- Decimal-based rate reconciliation and a 45,000 lb weight rule
- Complete issue collection in deterministic order
- Safe handling for missing configuration, refusals, timeouts, API errors, and invalid output
- Machine-readable JSON plus readable terminal output
- Dependency-injected extraction service and mocked unit/integration tests

## Technology stack

Python 3.10+, OpenAI Python SDK, Pydantic v2, PyMuPDF, python-dotenv, pytest, and ReportLab (only for regenerating the included selectable-text sample PDF).

## Architecture

```text
TXT / selectable PDF / raw text
              |
              v
       Document reader
              |
              v
 OpenAI Structured Outputs
 (nullable extraction model)
              |
              v
 Strict FreightDocument schema
              |
              v
 Deterministic validators
  - rate reconciliation
  - weight threshold
  - completeness
              |
              v
     Decision engine
              |
              v
 JSON + terminal presentation
```

The LLM is deliberately limited to interpreting document text. It cannot approve a document and is explicitly instructed not to repair inconsistent amounts. Pydantic owns data contracts; pure Python owns all business decisions.

## Repository structure

```text
freightguard-ai/
├── freight_agent/
│   ├── config.py             # Environment-backed settings
│   ├── decision.py           # APPROVED / human-review decision
│   ├── document_reader.py    # TXT and PDF readers
│   ├── exceptions.py         # Safe domain exceptions
│   ├── extractor.py          # OpenAI Responses API integration
│   ├── pipeline.py           # Workflow orchestration
│   ├── schemas.py            # Extraction, strict, issue, and result models
│   └── validator.py          # Deterministic business rules
├── samples/
│   ├── freight_document.txt
│   ├── freight_document.pdf
│   └── expected_output.json
├── scripts/create_sample_pdf.py
├── tests/
├── main.py
├── requirements.txt
├── .env.example
└── LICENSE
```

## Installation

Python 3.10 or newer is required.

```bash
git clone <repository-url>
cd freightguard-ai
python -m venv .venv
```

Activate the environment on macOS/Linux:

```bash
source .venv/bin/activate
```

On Windows:

```powershell
.venv\Scripts\activate
```

Then install and configure:

```bash
pip install -r requirements.txt
cp .env.example .env
```

Replace the placeholder in `.env` with a valid OpenAI API key. Never commit `.env`.

## Configuration

| Variable | Required | Default | Purpose |
|---|---:|---|---|
| `OPENAI_API_KEY` | Yes | none | OpenAI API credential |
| `OPENAI_MODEL` | No | `gpt-4o-mini` | Structured Outputs-capable model |
| `OPENAI_TIMEOUT_SECONDS` | No | `60` | Bounded request timeout (max 300) |
| `MAX_EXTRACTION_RETRIES` | No | `2` | SDK retries for transient errors (max 5) |

`gpt-4o-mini` supports Structured Outputs and the Responses API parsing interface used here. If the model is changed, choose one that supports schema-constrained structured output.

## Running the application

Text input:

```bash
python main.py --input samples/freight_document.txt
```

PDF input:

```bash
python main.py --input samples/freight_document.pdf
```

Save the full result:

```bash
python main.py --input samples/freight_document.txt --output samples/actual_output.json
```

Exit code `0` means approved, `1` means processed but flagged for review, and `2` means the input/output file operation failed. A flagged business result is valid output, not a crash.

Library callers can use `process_document(raw_text)` or instantiate `FreightProcessingPipeline` with a custom extraction service.

## Running tests

Tests never call the live API. They mock the extraction boundary and cover schema constraints, PDF/TXT reading, LLM failures and refusals, rate precision, weight boundaries, incomplete records, decisions, CLI output, and end-to-end orchestration.

```bash
python -m pytest -v
```

## Sample input and output

The included sample states a `$2,200.00` linehaul rate, `$350.00` fuel surcharge, `$2,800.00` total, and `46,800 lbs` gross weight. The expected result is checked into `samples/expected_output.json` and contains:

```json
{
  "status": "FLAGGED_FOR_HUMAN_REVIEW",
  "issues": [
    {"code": "RATE_MISMATCH", "severity": "ERROR"},
    {"code": "OVERWEIGHT_LOAD", "severity": "WARNING"}
  ]
}
```

The expected fixture is the deterministic target, not a claim of a live API run. `samples/actual_output.json` is intentionally gitignored and should only be created by an authenticated execution.

## Business validation rules

1. `RATE_MISMATCH` (`ERROR`): linehaul plus fuel must equal the explicitly stated total. Values are converted through `Decimal(str(value))`, normalized to cents, and never rewritten.
2. `OVERWEIGHT_LOAD` (`WARNING`): weights above 45,000 lbs are flagged. Exactly 45,000 lbs is allowed.
3. `INCOMPLETE_DATA` (`ERROR`): missing, blank, ambiguous, or structurally invalid required fields are listed. Checks that lack operands are skipped rather than calculated with invented defaults.

Any error or warning produces `FLAGGED_FOR_HUMAN_REVIEW`. Only a complete record with no issues is `APPROVED`. Extraction or processing failures are represented by `EXTRACTION_FAILED` or `PROCESSING_ERROR` and can never be approved.

## Error handling and security

The raw document is sent as a separate user message and is treated as untrusted data. The system prompt instructs the model not to follow embedded instructions. Files are read only from the caller-supplied path; document content is never executed or used to construct paths. Credentials remain in environment configuration and error messages do not expose keys or provider payloads.

The SDK uses a bounded timeout and bounded retries. Authentication failures, rate limits, timeouts, connection errors, refusals, absent parsed output, unsupported formats, unreadable files, and empty/scanned PDFs produce controlled failures. OCR is not performed in this lightweight version.

## How strict JSON output is ensured

The application uses OpenAI Structured Outputs through `client.responses.parse` with `ExtractionFreightDocument` supplied as the native Pydantic `text_format`. This constrains the API response to the declared schema and returns a typed model, which is materially safer than asking for JSON in a prompt and manually decoding arbitrary text. The extraction prompt additionally requires faithful source values, nulls for unavailable data, and no commentary, but prompt text is not the enforcement mechanism—the API schema is.

Validation has two stages. The extraction model deliberately allows nulls so the model can report genuinely absent or ambiguous source information without hallucinating. The result is then validated against strict `FreightDocument`, which rejects missing fields, extras, blanks, malformed locations and ZIPs, negative/non-finite money, and negative weight. Incomplete data remains available as `partial_document` but cannot be approved. Independent deterministic Python rules reconcile money with `Decimal`, enforce the weight limit, and create the final decision; the LLM does not participate in those rules.

## Scaling to 100,000 PDFs per day

The current implementation is intentionally a synchronous CLI; it does not claim to implement a distributed processing platform. A production design would upload PDFs to object storage such as Amazon S3, emit ingestion events into a durable queue such as SQS, and use horizontally scaled workers. Workers would extract selectable text, route scanned pages through OCR, preprocess and classify documents, call a separately rate-limited LLM extraction service, apply the same Pydantic and deterministic validation layers, and persist structured results and validation outcomes. Flagged documents would enter a human-review queue.

At 100,000 documents per day the average arrival rate is about 1.16 documents per second, but capacity planning must cover spikes, page count and OCR complexity, LLM latency, and provider quotas. Workers should use exponential backoff for transient failures, bounded retries, dead-letter queues for repeated failures, and idempotency keys based on stable upload/job identifiers to prevent duplicate billing and results. Operational monitoring should track queue depth, latency, extraction/validation failure rates, review rate, token usage, and cost while logging only safe document-processing metadata—not credentials or unnecessary document content.

## Limitations and future improvements

- Scanned/image-only PDFs need an OCR service before extraction.
- The CLI processes one document at a time; batch queues and persistence are future production concerns.
- Live quality depends on the configured model and should be measured with a versioned evaluation corpus.
- Additional currencies, unit conversion, carrier compliance checks, and confidence/review tooling can be added as explicit deterministic policies.
- For reproducibility in regulated deployments, pin an exact model snapshot after evaluation rather than relying indefinitely on an alias.

## Regenerating the sample PDF

The checked-in PDF is selectable text. To regenerate it from the canonical text fixture:

```bash
python scripts/create_sample_pdf.py
```
