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
