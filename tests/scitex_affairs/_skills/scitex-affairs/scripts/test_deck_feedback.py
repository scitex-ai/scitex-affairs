"""Exercise native deck evidence, edit detection, and immutable output files."""
import importlib.util
import json
from pathlib import Path
from zipfile import ZipFile

import pytest


@pytest.fixture
def tool():
    root = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").is_file())
    source = root / "src/scitex_affairs/_skills/scitex-affairs/scripts/deck_feedback.py"
    spec = importlib.util.spec_from_file_location("affairs_deck_feedback", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def make_deck(path, text):
    with ZipFile(path, "w") as archive:
        archive.writestr("ppt/presentation.xml", '<p:presentation xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><p:sldIdLst><p:sldId id="256" r:id="rId1"/></p:sldIdLst></p:presentation>')
        archive.writestr("ppt/_rels/presentation.xml.rels", '<Relationships><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide1.xml"/></Relationships>')
        archive.writestr("ppt/slides/slide1.xml", f'<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><p:cSld><p:spTree><p:sp><p:nvSpPr><p:cNvPr id="2" name="SCITEX_TITLE"/></p:nvSpPr><p:txBody><a:p><a:r><a:t>{text}</a:t></a:r></a:p></p:txBody></p:sp></p:spTree></p:cSld></p:sld>')


def test_snapshot_preserves_deck_and_detects_text_edit(tool, tmp_path):
    before = tmp_path / "before.pptx"
    after = tmp_path / "after.pptx"
    make_deck(before, "Original title")
    make_deck(after, "Revised title")
    original = before.read_bytes()
    baseline = tool.snapshot(before)
    assert before.read_bytes() == original
    assert not tool.compare(baseline, tool.snapshot(before))["changed_slides"]
    diff = tool.compare(baseline, tool.snapshot(after))
    assert not diff["identity_caution"]
    assert diff["changed_slides"][0]["changes"]["title"]["after"] == "Revised title"
    assert diff["changed_slides"][0]["changed_shapes"][0]["changes"]["text"]["after"] == ["Revised title"]


def test_cli_json_and_existing_baseline_protection(tool, tmp_path, monkeypatch, capsys):
    deck = tmp_path / "deck.pptx"
    baseline = tmp_path / "baseline.json"
    make_deck(deck, "Evidence")
    monkeypatch.setattr("sys.argv", ["deck_feedback.py", "snapshot", str(deck), "--output", str(baseline)])
    assert tool.main() == 0
    assert json.loads(capsys.readouterr().out)["slides"] == 1
    original = baseline.read_bytes()
    assert tool.main() == 2
    captured = capsys.readouterr()
    assert captured.err and not captured.out
    assert baseline.read_bytes() == original
