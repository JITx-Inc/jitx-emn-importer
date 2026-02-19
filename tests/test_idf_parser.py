"""
Pytest unit tests for idf_parser module
"""

import pytest
import math
from jitx_emn_importer.idf_parser import (
    IdfParser,
    IdfFile,
    IdfHeader,
    IdfHole,
    IdfNote,
    IdfPart,
    IdfException,
    idf_parser,
    find_refdes,
)


class TestIdfParserBasics:
    """Test basic parser functionality"""

    def test_parse_simple_rectangle(self, temp_emn_file):
        """Test parsing a simple rectangular board"""
        idf = idf_parser(str(temp_emn_file))

        assert idf.header.filetype == "IDF_FILE"
        assert idf.header.idf_version == 3.0
        assert idf.header.units == "MM"
        assert idf.header.name == "TestBoard"

        # Board outline should be a Polygon (no arcs)
        assert idf.board_outline.__class__.__name__ == "Polygon"
        assert len(idf.board_outline.elements) >= 4

    def test_parse_with_holes(self, temp_emn_file_with_holes):
        """Test parsing drilled holes section"""
        idf = idf_parser(str(temp_emn_file_with_holes))

        assert len(idf.holes) == 3

        # Check first hole
        hole = idf.holes[0]
        assert hole.dia == 2.0
        assert hole.x == 10.0
        assert hole.y == 10.0
        assert hole.plating == "PTH"

        # Check third hole (NPTH)
        hole3 = idf.holes[2]
        assert hole3.dia == 3.0
        assert hole3.plating == "NPTH"
        assert hole3.assoc == "MTG"

    def test_parse_with_notes(self, tmp_path, emn_with_notes):
        """Test parsing notes section"""
        emn_file = tmp_path / "test.emn"
        emn_file.write_text(emn_with_notes)

        idf = idf_parser(str(emn_file))

        assert len(idf.notes) == 3

        note = idf.notes[0]
        assert note.text == "KEEP OUT AREA"
        assert note.x == 15.0
        assert note.y == 25.0
        assert note.height == 1.5

    def test_parse_with_placement(self, tmp_path, emn_with_placement):
        """Test parsing component placement"""
        emn_file = tmp_path / "test.emn"
        emn_file.write_text(emn_with_placement)

        idf = idf_parser(str(emn_file))

        assert len(idf.placement) == 3

        # Check first part (resistor)
        r1 = idf.placement[0]
        assert r1.refdes == "R1"
        assert r1.package == "0603"
        assert r1.partnumber == "R0603_10K"
        assert r1.side == "TOP"

        # Check capacitor on bottom
        c1 = idf.placement[2]
        assert c1.refdes == "C1"
        assert c1.side == "BOTTOM"
        assert c1.angle == 90.0


class TestUnitConversion:
    """Test unit conversion functionality"""

    def test_thou_to_mm(self, temp_emn_file_thou):
        """Test THOU to mm conversion"""
        idf = idf_parser(str(temp_emn_file_thou))

        # Original board is 4000 x 2000 THOU
        # 1 thou = 0.0254 mm
        # So 4000 thou = 101.6 mm, 2000 thou = 50.8 mm
        elements = idf.board_outline.elements

        # Find the max x and y coordinates
        xs = [e[0] for e in elements]
        ys = [e[1] for e in elements]

        # Check conversion with tolerance
        assert abs(max(xs) - 101.6) < 0.01
        assert abs(max(ys) - 50.8) < 0.01

    def test_mm_unchanged(self, temp_emn_file):
        """Test MM units are unchanged"""
        idf = idf_parser(str(temp_emn_file))

        elements = idf.board_outline.elements

        xs = [e[0] for e in elements]
        ys = [e[1] for e in elements]

        # Original was 100x50 MM
        assert abs(max(xs) - 100.0) < 0.01
        assert abs(max(ys) - 50.0) < 0.01


class TestArcHandling:
    """Test arc and circle parsing"""

    def test_parse_with_arcs(self, temp_emn_file_with_arcs):
        """Test parsing arc segments (rounded corners)"""
        idf = idf_parser(str(temp_emn_file_with_arcs))

        # Board with rounded corners should produce ArcPolygon
        assert idf.board_outline.__class__.__name__ == "ArcPolygon"

        # Should have mix of points and arcs
        elements = idf.board_outline.elements
        has_arc = any(hasattr(e, 'center') for e in elements)
        has_point = any(isinstance(e, tuple) for e in elements)

        assert has_arc, "ArcPolygon should contain at least one Arc"
        assert has_point, "ArcPolygon should contain at least one point tuple"

    def test_full_circle(self, tmp_path, emn_with_circle):
        """Test that 360-degree arc creates Circle object"""
        emn_file = tmp_path / "test.emn"
        emn_file.write_text(emn_with_circle)

        idf = idf_parser(str(emn_file))

        # A 360-degree arc should produce a Circle
        assert idf.board_outline.__class__.__name__ == "Circle"
        assert idf.board_outline.radius == 25.0  # Distance 0,25 to 50,25 = 50, radius = 25


class TestBoardCutouts:
    """Test board cutout parsing"""

    def test_parse_with_cutout(self, tmp_path, emn_with_cutout):
        """Test parsing board outline with cutout"""
        emn_file = tmp_path / "test.emn"
        emn_file.write_text(emn_with_cutout)

        idf = idf_parser(str(emn_file))

        # Should have one cutout (loop 1)
        assert len(idf.board_cutouts) == 1

        cutout = idf.board_cutouts[0]
        assert cutout.__class__.__name__ == "Polygon"

        # Check cutout is in expected area (40-60, 20-30)
        elements = cutout.elements
        xs = [e[0] for e in elements]
        ys = [e[1] for e in elements]

        assert 39.0 < min(xs) < 41.0
        assert 59.0 < max(xs) < 61.0


class TestKeepouts:
    """Test keepout parsing"""

    def test_parse_keepouts(self, tmp_path, emn_with_keepouts):
        """Test parsing route and via keepouts"""
        emn_file = tmp_path / "test.emn"
        emn_file.write_text(emn_with_keepouts)

        idf = idf_parser(str(emn_file))

        # Should have one route keepout and one via keepout
        assert len(idf.route_keepouts) == 1
        assert len(idf.via_keepouts) == 1

        # Route keepout should be on TOP layer
        route_keepout = idf.route_keepouts[0]
        assert route_keepout.layers == "TOP"

        # Via keepout has no layer specification
        via_keepout = idf.via_keepouts[0]
        assert via_keepout.layers == ""


class TestErrorHandling:
    """Test error handling and edge cases"""

    def test_missing_header_raises(self, tmp_path):
        """Test that missing header raises IdfException"""
        emn_content = """.BOARD_OUTLINE "TEST_OWNER" 1.6
0 0 0 0
0 100 0 0
0 100 50 0
0 0 50 0
0 0 0 0
.END_BOARD_OUTLINE
"""
        emn_file = tmp_path / "test.emn"
        emn_file.write_text(emn_content)

        with pytest.raises(IdfException, match="Expected exactly 1 header"):
            idf_parser(str(emn_file))

    def test_missing_board_outline_raises(self, tmp_path):
        """Test that missing board outline raises IdfException"""
        emn_content = """.HEADER
IDF_FILE 3.0 "Test System" "2024-01-01" 1 "TestBoard" "MM"
.END_HEADER
"""
        emn_file = tmp_path / "test.emn"
        emn_file.write_text(emn_content)

        with pytest.raises(IdfException, match="Expected exactly 1 board outline"):
            idf_parser(str(emn_file))

    def test_file_not_found(self, tmp_path):
        """Test that non-existent file raises FileNotFoundError"""
        with pytest.raises(FileNotFoundError):
            idf_parser(str(tmp_path / "nonexistent.emn"))


class TestFindRefdes:
    """Test find_refdes helper function"""

    def test_find_existing_refdes(self, tmp_path, emn_with_placement):
        """Test finding an existing reference designator"""
        emn_file = tmp_path / "test.emn"
        emn_file.write_text(emn_with_placement)

        idf = idf_parser(str(emn_file))

        part = find_refdes(idf, "U1")
        assert part is not None
        assert part.refdes == "U1"
        assert part.package == "SOIC8"

    def test_find_nonexistent_refdes(self, tmp_path, emn_with_placement):
        """Test finding a non-existent reference designator"""
        emn_file = tmp_path / "test.emn"
        emn_file.write_text(emn_with_placement)

        idf = idf_parser(str(emn_file))

        part = find_refdes(idf, "X999")
        assert part is None


class TestCompleteFile:
    """Test parsing a complete EMN file with all features"""

    def test_parse_complete_file(self, temp_emn_complete):
        """Test parsing a file with all feature types"""
        idf = idf_parser(str(temp_emn_complete))

        # Header
        assert idf.header.filetype == "IDF_FILE"
        assert idf.header.units == "MM"

        # Board outline
        assert idf.board_outline is not None

        # Features
        assert len(idf.holes) == 2
        assert len(idf.notes) == 1
        assert len(idf.placement) == 2
        assert len(idf.route_keepouts) == 1

        # Note content
        assert idf.notes[0].text == "CENTER NOTE"

        # Placement
        refdes_list = [p.refdes for p in idf.placement]
        assert "R1" in refdes_list
        assert "U1" in refdes_list


class TestPolygonClosure:
    """Test that polygons are properly closed"""

    def test_polygon_is_closed(self, temp_emn_file):
        """Test that polygon first and last points match"""
        idf = idf_parser(str(temp_emn_file))

        elements = idf.board_outline.elements
        first = elements[0]
        last = elements[-1]

        # First and last points should be the same (closed polygon)
        assert abs(first[0] - last[0]) < 1e-6
        assert abs(first[1] - last[1]) < 1e-6


class TestTabDelimitedInput:
    """Regression: Bug 2.1 — tokenizer must handle tab-separated fields"""

    def test_tab_separated_tokens(self, tmp_path):
        """Tabs between fields should be treated as whitespace"""
        emn_content = ".HEADER\nIDF_FILE\t3.0\t\"Test\"\t\"2024-01-01\"\t1\t\"Board\"\t\"MM\"\n.END_HEADER\n\n.BOARD_OUTLINE\t\"OWNER\"\t1.6\n0\t0\t0\t0\n0\t10\t0\t0\n0\t10\t10\t0\n0\t0\t10\t0\n0\t0\t0\t0\n.END_BOARD_OUTLINE\n"
        emn_file = tmp_path / "tabs.emn"
        emn_file.write_text(emn_content)
        idf = idf_parser(str(emn_file))
        assert idf.header.units == "MM"
        assert idf.board_outline.__class__.__name__ == "Polygon"

    def test_mixed_tabs_and_spaces(self, tmp_path):
        """Mixed tabs and spaces should both work"""
        emn_content = ".HEADER\nIDF_FILE 3.0\t\"Test\" \"2024-01-01\"\t1 \"Board\"\t\"MM\"\n.END_HEADER\n\n.BOARD_OUTLINE \"OWNER\" 1.6\n0 0\t0 0\n0 20\t0 0\n0 20\t20 0\n0 0\t20 0\n0 0\t0 0\n.END_BOARD_OUTLINE\n"
        emn_file = tmp_path / "mixed.emn"
        emn_file.write_text(emn_content)
        idf = idf_parser(str(emn_file))
        assert idf.header.units == "MM"


class TestEmptyQuotedStrings:
    """Regression: Bug 2.2 — empty quoted strings must not be filtered out"""

    def test_empty_partnumber_preserved(self, tmp_path):
        """Placement record with empty quoted part number should parse correctly"""
        emn_content = '.HEADER\nIDF_FILE 3.0 "Test" "2024-01-01" 1 "Board" "MM"\n.END_HEADER\n\n.BOARD_OUTLINE "OWNER" 1.6\n0 0 0 0\n0 10 0 0\n0 10 10 0\n0 0 10 0\n0 0 0 0\n.END_BOARD_OUTLINE\n\n.PLACEMENT\n"PKG" "" "R1" 5 5 0 0 "TOP" "PLACED"\n.END_PLACEMENT\n'
        emn_file = tmp_path / "empty_pn.emn"
        emn_file.write_text(emn_content)
        idf = idf_parser(str(emn_file))
        assert len(idf.placement) == 1
        assert idf.placement[0].partnumber == ""
        assert idf.placement[0].refdes == "R1"


class TestPanelOutlineEndMarker:
    """Regression: Bug 2.3 — PANEL_OUTLINE must use .END_PANEL_OUTLINE"""

    def test_panel_outline_parses(self, tmp_path):
        """PANEL_OUTLINE section with correct end marker should parse"""
        emn_content = '.HEADER\nIDF_FILE 3.0 "Test" "2024-01-01" 1 "Board" "MM"\n.END_HEADER\n\n.PANEL_OUTLINE "OWNER" 1.6\n0 0 0 0\n0 200 0 0\n0 200 100 0\n0 0 100 0\n0 0 0 0\n.END_PANEL_OUTLINE\n'
        emn_file = tmp_path / "panel.emn"
        emn_file.write_text(emn_content)
        idf = idf_parser(str(emn_file))
        assert idf.board_outline.__class__.__name__ == "Polygon"


class TestPlaceOutlinesSeparate:
    """Regression: Bug 2.4 — PLACE_OUTLINE collected in place_outlines, not route_outlines"""

    def test_place_outline_not_in_route(self, tmp_path):
        """PLACE_OUTLINE should go to place_outlines, not route_outlines"""
        emn_content = '.HEADER\nIDF_FILE 3.0 "Test" "2024-01-01" 1 "Board" "MM"\n.END_HEADER\n\n.BOARD_OUTLINE "OWNER" 1.6\n0 0 0 0\n0 100 0 0\n0 100 50 0\n0 0 50 0\n0 0 0 0\n.END_BOARD_OUTLINE\n\n.PLACE_OUTLINE "OWNER" "TOP" 5.0\n0 10 10 0\n0 20 10 0\n0 20 20 0\n0 10 20 0\n0 10 10 0\n.END_PLACE_OUTLINE\n'
        emn_file = tmp_path / "place.emn"
        emn_file.write_text(emn_content)
        idf = idf_parser(str(emn_file))
        assert len(idf.place_outlines) == 1
        assert len(idf.route_outlines) == 0


class TestCircleCenterPreserved:
    """Regression: Bug 2.5 — circle center position must be preserved"""

    def test_circle_has_center(self, tmp_path, emn_with_circle):
        """360-degree arc circle should store center point"""
        emn_file = tmp_path / "circle.emn"
        emn_file.write_text(emn_with_circle)
        idf = idf_parser(str(emn_file))
        circle = idf.board_outline
        assert circle.__class__.__name__ == "Circle"
        assert hasattr(circle, '_center')
        cx, cy = circle._center
        assert abs(cx - 25.0) < 0.01
        assert abs(cy - 25.0) < 0.01


class TestUnknownSectionSkipping:
    """Regression: Bug 2.7 — unknown sections should be skipped entirely"""

    def test_unknown_section_skipped(self, tmp_path):
        """File with unknown section should parse without error"""
        emn_content = '.HEADER\nIDF_FILE 3.0 "Test" "2024-01-01" 1 "Board" "MM"\n.END_HEADER\n\n.BOARD_OUTLINE "OWNER" 1.6\n0 0 0 0\n0 50 0 0\n0 50 30 0\n0 0 30 0\n0 0 0 0\n.END_BOARD_OUTLINE\n\n.CUSTOM_SECTION\nsome random data 123\nmore data here\n.END_CUSTOM_SECTION\n'
        emn_file = tmp_path / "unknown.emn"
        emn_file.write_text(emn_content)
        idf = idf_parser(str(emn_file))
        assert idf.board_outline.__class__.__name__ == "Polygon"


class TestIdfVersion2:
    """IDF 2.0 format support"""

    def test_idf2_header_parsed(self, tmp_path):
        """IDF 2.0 two-line header should parse correctly"""
        emn_content = '.HEADER\nBOARD_FILE 2.0 "TestCAD" 2024/01/01 1\nMyBoard THOU\n.END_HEADER\n\n.BOARD_OUTLINE\n62.5\n0 0 0 0\n0 1000 0 0\n0 1000 500 0\n0 0 500 0\n0 0 0 0\n.END_BOARD_OUTLINE\n'
        emn_file = tmp_path / "v2.emn"
        emn_file.write_text(emn_content)
        idf = idf_parser(str(emn_file))
        assert idf.header.idf_version == 2.0
        assert idf.header.units == "THOU"
        assert idf.header.name == "MyBoard"

    def test_idf2_board_outline_no_owner(self, tmp_path):
        """IDF 2.0 BOARD_OUTLINE has no owner field"""
        emn_content = '.HEADER\nBOARD_FILE 2.0 "TestCAD" 2024/01/01 1\nMyBoard MM\n.END_HEADER\n\n.BOARD_OUTLINE\n1.6\n0 0 0 0\n0 100 0 0\n0 100 50 0\n0 0 50 0\n0 0 0 0\n.END_BOARD_OUTLINE\n'
        emn_file = tmp_path / "v2_outline.emn"
        emn_file.write_text(emn_content)
        idf = idf_parser(str(emn_file))
        assert idf.board_outline.__class__.__name__ == "Polygon"
        elements = idf.board_outline.elements
        xs = [e[0] for e in elements]
        assert abs(max(xs) - 100.0) < 0.01

    def test_idf2_holes_5_fields(self, tmp_path):
        """IDF 2.0 DRILLED_HOLES have 5 fields (no type/owner)"""
        emn_content = '.HEADER\nBOARD_FILE 2.0 "TestCAD" 2024/01/01 1\nMyBoard MM\n.END_HEADER\n\n.BOARD_OUTLINE\n1.6\n0 0 0 0\n0 100 0 0\n0 100 50 0\n0 0 50 0\n0 0 0 0\n.END_BOARD_OUTLINE\n\n.DRILLED_HOLES\n2.0 10 15 PTH VIA\n3.0 50 25 NPTH MTG\n.END_DRILLED_HOLES\n'
        emn_file = tmp_path / "v2_holes.emn"
        emn_file.write_text(emn_content)
        idf = idf_parser(str(emn_file))
        assert len(idf.holes) == 2
        assert idf.holes[0].dia == 2.0
        assert idf.holes[0].x == 10.0
        assert idf.holes[0].plating == "PTH"
        assert idf.holes[0].type == ""
        assert idf.holes[0].owner == ""
        assert idf.holes[1].plating == "NPTH"
