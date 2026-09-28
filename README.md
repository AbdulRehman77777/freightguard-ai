# FreightGuard AI

*LLM-Powered Freight Document Extraction and Validation*

## Project overview

FreightGuard AI is a production-minded Python CLI that converts unstructured freight documents into validated JSON and makes a conservative, deterministic approval decision. It accepts UTF-8 text and selectable-text PDFs, supports Groq and OpenAI Structured Outputs for field extraction, and keeps schema enforcement and business decisions in ordinary Python.

## Problem statement

Freight operations receive inconsistent rate confirmations and order agreements. Manual transcription is slow, while letting an LLM approve loads or silently repair totals is unsafe. FreightGuard AI preserves the source values, enforces a typed contract, identifies financial discrepancies, overweight shipments, and incomplete data, then returns either `APPROVED` or `FLAGGED_FOR_HUMAN_REVIEW` with auditable explanations.

## Features

- TXT and multi-page PDF text extraction with empty/scanned-document detection
- Selectable Groq or official OpenAI extraction using Structured Outputs and Pydantic
- Nullable extraction schema followed by a strict final schema
- Decimal-based rate reconciliation and a 45,000 lb weight rule
- Complete issue collection in deterministic order
- Safe handling for missing configuration, refusals, timeouts, API errors, and invalid output
- Machine-readable JSON plus readable terminal output
- Dependency-injected extraction service and mocked unit/integration tests

## Technology stack

Python 3.10+, official OpenAI Python SDK, Groq/OpenAI APIs, Pydantic v2, PyMuPDF, python-dotenv, and pytest.

## Architecture

```text
TXT / selectable PDF / raw text
              |
              v
       Document reader
              |
              v
  Selected LLM provider
   (Groq or OpenAI)
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
│   ├── extractor.py          # Groq/OpenAI services and provider factory
│   ├── pipeline.py           # Workflow orchestration
│   ├── schemas.py            # Extraction, strict, issue, and result models
│   └── validator.py          # Deterministic business rules
├── samples/
│   ├── freight_document.txt
│   ├── freight_document.pdf
│   ├── expected_output.json
│   └── actual_output.json
├── tests/
├── main.py
├── requirements.txt
├── .env.example
└── LICENSE
```

## Installation

Python 3.10 or newer is required.

```bash
git clone https://github.com/AbdulRehman77777/freightguard-ai.git
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

Keep `LLM_PROVIDER=groq` and replace the Groq placeholder for the default setup, or select `openai` and configure its key instead. Never commit `.env`.

## LLM providers

Groq is the default provider and uses its OpenAI-compatible endpoint at `https://api.groq.com/openai/v1` with `openai/gpt-oss-20b`. This path has been verified with a successful live extraction. OpenAI is an optional provider using the official endpoint, official Python SDK, and `client.responses.parse`; it is covered by mocked integration tests but could not be verified live because the available account previously returned `credit_balance_exhausted` / `insufficient_quota`.

Both services use the same extraction prompt and nullable `ExtractionFreightDocument` model. Provider selection changes only the API boundary: the strict final schema, deterministic business validation, decision engine, and public JSON result are shared.

## Environment configuration

| Variable | Required | Default | Purpose |
|---|---:|---|---|
| `LLM_PROVIDER` | No | `groq` | Extraction provider: `groq` or `openai` |
| `GROQ_API_KEY` | For Groq | none | Groq API credential |
| `GROQ_MODEL` | No | `openai/gpt-oss-20b` | Strict Structured Outputs-capable model |
| `GROQ_TIMEOUT_SECONDS` | No | `60` | Bounded request timeout (max 300) |
| `OPENAI_API_KEY` | For OpenAI | none | Official OpenAI API credential |
| `OPENAI_MODEL` | No | `gpt-4o-mini` | OpenAI Structured Outputs-capable model |
| `OPENAI_TIMEOUT_SECONDS` | No | `60` | Bounded request timeout (max 300) |
| `MAX_EXTRACTION_RETRIES` | No | `2` | SDK retries for transient errors (max 5) |

Only the selected provider's key is required. Invalid `LLM_PROVIDER` values fail safely before an API request. If a model is changed, choose one supported by that provider for schema-constrained Structured Outputs.

## Running the application

Text input:

```bash
python main.py --input samples/freight_document.txt
```

Select Groq (the default) or OpenAI in `.env`, or for one command on macOS/Linux:

```bash
LLM_PROVIDER=groq python main.py --input samples/freight_document.txt
LLM_PROVIDER=openai python main.py --input samples/freight_document.txt
```

On PowerShell:

```powershell
$env:LLM_PROVIDER="groq"; python main.py --input samples/freight_document.txt
$env:LLM_PROVIDER="openai"; python main.py --input samples/freight_document.txt
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

The document artifacts are deliberately distinguished:

| Artifact | Provenance | Verification |
|---|---|---|
| `samples/freight_document.txt` | Plain-text test fixture preserving the supplied case content | Reader and mocked pipeline tests |
| `samples/freight_document.pdf` | Reconstructed selectable-text fixture created from that content | PDF reader tests; not the original upload |
| `samples/original_document.pdf` | Reserved path for the byte-for-byte employer-supplied `Document.pdf` | Not present: `Document.pdf` was not available anywhere in the workspace |
| `samples/expected_output.json` | Deterministic expected result | Compared in automated tests |
| `samples/actual_output.json` | Successful live Groq result for the text fixture | Exactly matches expected output |

No substitute has been created or labeled as the original. If `Document.pdf` becomes available, it should be copied byte-for-byte to `samples/original_document.pdf`, verified with the existing reader, and processed live before adding `actual_output_pdf.json`.

A live Groq request using `openai/gpt-oss-20b` successfully extracted the supplied text fixture. The checked-in `samples/actual_output.json` exactly matches `samples/expected_output.json`: it preserves `total_pay` as `2800.0`, reports `RATE_MISMATCH` and `OVERWEIGHT_LOAD`, and returns `FLAGGED_FOR_HUMAN_REVIEW`.

## Business validation rules

| Rule | Severity | Behavior |
|---|---|---|
| `RATE_MISMATCH` | `ERROR` | Linehaul plus fuel must equal the explicitly stated total. Values are compared as `Decimal` amounts at cent precision and never rewritten. |
| `OVERWEIGHT_LOAD` | `WARNING` | Weight above 45,000 lbs is flagged; exactly 45,000 lbs is allowed. |
| `INCOMPLETE_DATA` | `ERROR` | Missing, blank, ambiguous, or structurally invalid required fields are reported. |

The supplied case has a $250 discrepancy (`$2,200 + $350 = $2,550`, versus the stated `$2,800`) and exceeds the weight threshold by 1,800 lbs (`46,800 lbs`). Both independent issues are returned, producing `FLAGGED_FOR_HUMAN_REVIEW` while preserving `total_pay` as `2800.0`.

Any error or warning produces `FLAGGED_FOR_HUMAN_REVIEW`. Only a complete record with no issues is `APPROVED`. Extraction or processing failures are represented by `EXTRACTION_FAILED` or `PROCESSING_ERROR` and can never be approved.

## Error handling and security

The raw document is sent as a separate user message and is treated as untrusted data. The system prompt instructs the model not to follow embedded instructions. Files are read only from the caller-supplied path; document content is never executed or used to construct paths. Credentials remain in environment configuration and error messages do not expose keys or provider payloads.

The SDK uses a bounded timeout and bounded retries. Authentication failures, rate limits, timeouts, connection errors, refusals, absent parsed output, unsupported formats, unreadable files, and empty/scanned PDFs produce controlled failures. OCR is not performed in this lightweight version.

## Architecture and scalability note

The application uses provider-native Structured Outputs through `client.responses.parse`, with `ExtractionFreightDocument` supplied as the native Pydantic `text_format`. Groq uses its OpenAI-compatible base URL while OpenAI uses the official endpoint; both constrain the response to the same strict JSON Schema and return the same typed model. This is materially safer than asking for arbitrary JSON in a prompt and manually decoding it. The prompt requires faithful source values, nulls for unavailable data, and no commentary, but prompt text is not the enforcement mechanism—the API schema is.

Validation then moves from the nullable extraction model—which allows genuinely missing or ambiguous values to be represented as `null` without hallucination—to strict `FreightDocument`. The final schema rejects missing fields, extras, type coercion, blanks, malformed locations and ZIPs, negative/non-finite money, and negative weight, so missing or invalid data cannot be approved. Independent deterministic Python rules reconcile money with `Decimal`, enforce the weight limit, and make the decision; the LLM does not calculate replacement totals or approve documents. For production scale, PDFs would land in object storage such as Amazon S3 and produce jobs in a durable queue such as Amazon SQS. Horizontally scalable workers would perform PDF text extraction, use OCR as a fallback for scanned pages, call the LLM extractor, apply Pydantic and business validation, persist results, and route flagged records to human review. This is a scaling design, not infrastructure implemented by the current synchronous CLI.

At 100,000 documents per day the average arrival rate is about 1.16 documents per second, but capacity planning must cover spikes, page count and OCR complexity, LLM latency, and provider quotas. Workers should use exponential backoff for transient failures, bounded retries, dead-letter queues for repeated failures, and idempotency keys based on stable upload/job identifiers to prevent duplicate billing and results. Operational monitoring should track queue depth, latency, extraction/validation failure rates, review rate, token usage, and cost while logging only safe document-processing metadata—not credentials or unnecessary document content.

## Limitations and future improvements

- Scanned/image-only PDFs need an OCR service before extraction.
- The original uploaded `Document.pdf` is unavailable locally; the checked-in PDF is a reconstructed selectable-text fixture and has been tested only as such.
- Live LLM calls require a key for the selected provider and depend on provider availability, quota, and rate limits.
- OpenAI is implemented and mock-tested, but live OpenAI verification remains unavailable due to insufficient API quota.
- The CLI processes one document at a time; batch queues and persistence are future production concerns.
- Live quality depends on the configured model and should be measured with a versioned evaluation corpus.
- Additional currencies, unit conversion, carrier compliance checks, and confidence/review tooling can be added as explicit deterministic policies.
- For reproducibility in regulated deployments, pin an exact model snapshot after evaluation rather than relying indefinitely on an alias.
