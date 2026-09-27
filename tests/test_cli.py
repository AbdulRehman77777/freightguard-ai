import json

from freight_agent.schemas import DecisionStatus, ProcessingResult
from main import main


def test_cli_writes_output(monkeypatch, tmp_path):
    source = tmp_path / "input.txt"
    output = tmp_path / "result.json"
    source.write_text("freight", encoding="utf-8")
    result = ProcessingResult(status=DecisionStatus.APPROVED, issues=[], summary="Approved")
    monkeypatch.setattr("main.process_document", lambda text: result)
    assert main(["--input", str(source), "--output", str(output)]) == 0
    assert json.loads(output.read_text())["status"] == "APPROVED"
