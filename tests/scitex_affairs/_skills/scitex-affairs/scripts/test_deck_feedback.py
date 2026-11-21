"""Exercise native deck evidence, edit detection, and immutable output files."""
import importlib.util
import json
import subprocess
import sys
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


def test_snapshot_preserves_original_bytes(tool, tmp_path):
    # Arrange
    deck = tmp_path / "source.pptx"
    make_deck(deck, "Original title")
    original = deck.read_bytes()
    # Act
    tool.snapshot(deck)
    # Assert
    assert deck.read_bytes() == original


def test_unchanged_deck_has_no_edits(tool, tmp_path):
    # Arrange
    deck = tmp_path / "source.pptx"
    make_deck(deck, "Original title")
    baseline = tool.snapshot(deck)
    # Act
    result = tool.compare(baseline, tool.snapshot(deck))
    # Assert
    assert result["changed_slides"] == []


def test_native_title_edit_is_detected(tool, tmp_path):
    # Arrange
    before = tmp_path / "before.pptx"
    after = tmp_path / "after.pptx"
    make_deck(before, "Original title")
    make_deck(after, "Revised title")
    # Act
    result = tool.compare(tool.snapshot(before), tool.snapshot(after))
    # Assert
    assert result["changed_slides"][0]["changed_shapes"][0]["changes"]["text"] == {
        "before": ["Original title"], "after": ["Revised title"]
    }


def test_cli_outputs_machine_readable_snapshot(tool, tmp_path):
    # Arrange
    deck = tmp_path / "deck.pptx"
    baseline = tmp_path / "baseline.json"
    make_deck(deck, "Evidence")
    command = [sys.executable, tool.__file__, "snapshot", str(deck), "--output", str(baseline)]
    # Act
    result = subprocess.run(command, capture_output=True, text=True)
    # Assert
    assert (result.returncode, json.loads(result.stdout)["slides"], result.stderr) == (0, 1, "")


def test_existing_baseline_is_preserved(tool, tmp_path):
    # Arrange
    deck = tmp_path / "deck.pptx"
    baseline = tmp_path / "baseline.json"
    make_deck(deck, "Evidence")
    command = [sys.executable, tool.__file__, "snapshot", str(deck), "--output", str(baseline)]
    subprocess.run(command, capture_output=True, check=True)
    original = baseline.read_bytes()
    # Act
    result = subprocess.run(command, capture_output=True, text=True)
    # Assert
    assert (result.returncode, baseline.read_bytes(), result.stdout, bool(result.stderr)) == (2, original, "", True)
