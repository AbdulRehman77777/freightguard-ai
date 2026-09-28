"""FreightGuard AI command-line entry point."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from freight_agent.document_reader import read_document
from freight_agent.exceptions import DocumentReadError
from freight_agent.pipeline import process_document
from freight_agent.schemas import DecisionStatus, ProcessingResult


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Extract and validate freight documents.")
    parser.add_argument("--input", required=True, help="Path to a UTF-8 .txt or selectable-text .pdf file")
    parser.add_argument("--output", help="Optional path for the JSON processing result")
    return parser


def render_terminal(result: ProcessingResult) -> str:
    lines = ["Document processing result", f"Final decision: {result.status.value}", ""]
    payload = result.document.model_dump() if result.document else result.partial_document
    lines.extend(["Extracted document information", json.dumps(payload, indent=2) if payload else "Unavailable", ""])
    lines.append("Validation issues")
    if result.issues:
        lines.extend(f"- [{issue.severity.value}] {issue.code}: {issue.message}" for issue in result.issues)
    else:
        lines.append("- None")
    lines.extend(["", f"Summary: {result.summary}"])
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        raw_text = read_document(args.input)
    except DocumentReadError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    result = process_document(raw_text)
    print(render_terminal(result))
    json_output = result.model_dump_json(indent=2, exclude_none=True)
    if args.output:
        output_path = Path(args.output)
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(json_output + "\n", encoding="utf-8")
        except OSError as exc:
            print(f"Error: unable to write output file: {exc}", file=sys.stderr)
            return 2
        print(f"\nJSON saved to: {output_path}")
    return 0 if result.status == DecisionStatus.APPROVED else 1


if __name__ == "__main__":
    raise SystemExit(main())
