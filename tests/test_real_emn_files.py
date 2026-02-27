"""
Integration tests for real-world EMN files.

Tests parsing, code generation, and feature conversion against real-world EMN
files in both IDF 2.0 and IDF 3.0 formats. These tests are optional and will
be skipped if fixture files are not present in tests/fixtures/real_emn/.
"""

import ast
import time
from pathlib import Path

import pytest

from jitx_emn_importer.emn_importer import (
    convert_emn_to_jitx_features,
    import_emn,
)
from jitx_emn_importer.idf_parser import IdfFile, idf_parser

REAL_EMN_DIR = Path(__file__).parent / "fixtures" / "real_emn"

# All EMN files expected in the fixture directory
ALL_EMN_FILES = sorted(REAL_EMN_DIR.glob("*.emn")) if REAL_EMN_DIR.exists() else []


def emn_id(path: Path) -> str:
    return path.name


# Skip entire module if fixtures are missing
pytestmark = pytest.mark.skipif(
    not ALL_EMN_FILES,
    reason="Real EMN fixtures not available (unzip testEMNs.zip into tests/fixtures/real_emn/)",
)


class TestParseNoCrash:
    """idf_parser() returns IdfFile without exception for all files"""

    @pytest.mark.parametrize("emn_file", ALL_EMN_FILES, ids=emn_id)
    def test_parse_no_crash(self, emn_file):
        result = idf_parser(str(emn_file))
        assert isinstance(result, IdfFile)


class TestBoardOutlineValid:
    """Board outline is a valid geometry type with sufficient elements"""

    @pytest.mark.parametrize("emn_file", ALL_EMN_FILES, ids=emn_id)
    def test_board_outline_valid(self, emn_file):
        result = idf_parser(str(emn_file))
        outline = result.board_outline
        class_name = type(outline).__name__
        assert class_name in ("Polygon", "ArcPolygon", "Circle"), (
            f"Unexpected outline type: {class_name}"
        )
        if hasattr(outline, "elements"):
            assert len(outline.elements) >= 3, f"Outline has only {len(outline.elements)} elements"
        elif hasattr(outline, "radius"):
            assert outline.radius > 0


class TestGeneratedCodeValidSyntax:
    """import_emn() output passes ast.parse()"""

    @pytest.mark.parametrize("emn_file", ALL_EMN_FILES, ids=emn_id)
    def test_generated_code_valid_syntax(self, emn_file, tmp_path):
        output = tmp_path / f"{emn_file.stem}_design.py"
        import_emn(str(emn_file), emn_file.stem, str(output))
        assert output.exists()
        code = output.read_text()
        assert code, "Generated code is empty"
        ast.parse(code)


class TestImportRoundtrip:
    """import_emn() creates a non-empty, valid Python file with proper structure"""

    @pytest.mark.parametrize("emn_file", ALL_EMN_FILES, ids=emn_id)
    def test_import_roundtrip(self, emn_file, tmp_path):
        output = tmp_path / f"{emn_file.stem}_board.py"
        import_emn(str(emn_file), emn_file.stem, str(output))
        assert output.exists()
        code = output.read_text()
        assert len(code) > 0
        ast.parse(code)
        # Generated code should have proper JITX classes, not layer() calls
        assert "Board" in code
        assert "Circuit" in code
        assert "Design" in code
        assert "layer(" not in code


class TestFeatureConversion:
    """convert_emn_to_jitx_features() returns a list without crash"""

    @pytest.mark.parametrize("emn_file", ALL_EMN_FILES, ids=emn_id)
    def test_feature_conversion(self, emn_file):
        idf = idf_parser(str(emn_file))
        features = convert_emn_to_jitx_features(idf)
        assert isinstance(features, list)


class TestLargeFilePerformance:
    """Large EMN files parse within 30 seconds"""

    @pytest.mark.parametrize(
        "filename",
        ["353A814.emn", "360a409-1.emn"],
        ids=lambda x: x,
    )
    def test_large_file_performance(self, filename):
        emn_file = REAL_EMN_DIR / filename
        if not emn_file.exists():
            pytest.skip(f"{filename} not available")

        start = time.monotonic()
        result = idf_parser(str(emn_file))
        elapsed = time.monotonic() - start

        assert isinstance(result, IdfFile)
        assert elapsed < 30.0, f"Parsing {filename} took {elapsed:.1f}s (limit: 30s)"


class TestSectionCounts:
    """Spot-check hole/keepout/placement counts on specific files"""

    def test_353A814_counts(self):
        emn_file = REAL_EMN_DIR / "353A814.emn"
        if not emn_file.exists():
            pytest.skip("353A814.emn not available")
        r = idf_parser(str(emn_file))
        assert len(r.holes) == 49
        assert len(r.placement) == 897
        assert len(r.route_keepouts) == 2521
        assert len(r.via_keepouts) == 126
        assert len(r.place_keepouts) == 32

    def test_360a409_counts(self):
        emn_file = REAL_EMN_DIR / "360a409-1.emn"
        if not emn_file.exists():
            pytest.skip("360a409-1.emn not available")
        r = idf_parser(str(emn_file))
        assert len(r.board_cutouts) == 48
        assert len(r.holes) == 99
        assert len(r.place_keepouts) == 365
        assert len(r.place_outlines) == 12

    def test_352a900_counts(self):
        emn_file = REAL_EMN_DIR / "352a900-1.emn"
        if not emn_file.exists():
            pytest.skip("352a900-1.emn not available")
        r = idf_parser(str(emn_file))
        assert len(r.board_cutouts) == 1
        assert len(r.holes) == 66
        assert len(r.notes) == 7
        assert len(r.placement) == 5
        assert len(r.place_keepouts) == 6

    def test_squarecut_has_cutout(self):
        emn_file = REAL_EMN_DIR / "squarecut.emn"
        if not emn_file.exists():
            pytest.skip("squarecut.emn not available")
        r = idf_parser(str(emn_file))
        assert type(r.board_outline).__name__ == "Polygon"
        assert len(r.board_cutouts) == 1

    def test_f16_idf_v2(self):
        """IDF 2.0 file: verify header, outline, and holes parse correctly"""
        emn_file = REAL_EMN_DIR / "f16_amcii_hio_rev1.emn"
        if not emn_file.exists():
            pytest.skip("f16_amcii_hio_rev1.emn not available")
        r = idf_parser(str(emn_file))
        assert r.header.idf_version == 2.0
        assert r.header.units == "THOU"
        assert r.header.name == "F16_AMCII_6U_PWB"
        assert type(r.board_outline).__name__ == "ArcPolygon"
        assert len(r.holes) == 3
        assert r.holes[0].plating == "NPTH"
        assert r.holes[0].assoc == "BOARD"
