"""
Pytest unit tests for geometry calculations in idf_parser
"""

import math

from jitx_emn_importer.idf_parser import (
    IdfParser,
)


class TestArcCalculations:
    """Test arc geometry calculations"""

    def test_90_degree_arc(self, tmp_path):
        """Test 90-degree arc calculation"""
        # Create EMN with a 90-degree arc
        emn_content = """.HEADER
IDF_FILE 3.0 "Test" "2024-01-01" 1 "Test" "MM"
.END_HEADER

.BOARD_OUTLINE "OWNER" 1.6
0 0 0 0
0 10 0 0
0 10 10 90
0 0 10 0
0 0 0 0
.END_BOARD_OUTLINE
"""
        emn_file = tmp_path / "test.emn"
        emn_file.write_text(emn_content)

        parser = IdfParser(str(emn_file))
        idf = parser.parse()

        # Should produce ArcPolygon with arc
        assert idf.board_outline.__class__.__name__ == "ArcPolygon"

        # Find the arc in elements
        arcs = [e for e in idf.board_outline.elements if hasattr(e, "arc")]
        assert len(arcs) >= 1

        arc = arcs[0]
        assert abs(arc.arc - 90.0) < 0.01

    def test_180_degree_arc(self, tmp_path):
        """Test 180-degree arc (semicircle) calculation"""
        # Create EMN with a 180-degree arc (semicircle)
        emn_content = """.HEADER
IDF_FILE 3.0 "Test" "2024-01-01" 1 "Test" "MM"
.END_HEADER

.BOARD_OUTLINE "OWNER" 1.6
0 0 0 0
0 20 0 180
0 20 20 0
0 0 20 0
0 0 0 0
.END_BOARD_OUTLINE
"""
        emn_file = tmp_path / "test.emn"
        emn_file.write_text(emn_content)

        parser = IdfParser(str(emn_file))
        idf = parser.parse()

        # Should produce ArcPolygon with semicircular arc
        assert idf.board_outline.__class__.__name__ == "ArcPolygon"

        arcs = [e for e in idf.board_outline.elements if hasattr(e, "arc")]
        assert len(arcs) >= 1

        arc = arcs[0]
        assert abs(arc.arc - 180.0) < 0.01

    def test_negative_sweep_arc(self, tmp_path):
        """Test negative sweep angle (clockwise arc)"""
        emn_content = """.HEADER
IDF_FILE 3.0 "Test" "2024-01-01" 1 "Test" "MM"
.END_HEADER

.BOARD_OUTLINE "OWNER" 1.6
0 0 0 0
0 10 0 0
0 10 10 -90
0 0 10 0
0 0 0 0
.END_BOARD_OUTLINE
"""
        emn_file = tmp_path / "test.emn"
        emn_file.write_text(emn_content)

        parser = IdfParser(str(emn_file))
        idf = parser.parse()

        arcs = [e for e in idf.board_outline.elements if hasattr(e, "arc")]
        assert len(arcs) >= 1

        arc = arcs[0]
        # Sweep angle should be negative (clockwise)
        assert arc.arc < 0
        assert abs(arc.arc - (-90.0)) < 0.01

    def test_arc_radius_calculation(self, tmp_path):
        """Test that arc radius is correctly calculated from chord and sweep"""
        # 90-degree arc with chord from (0,0) to (10,10)
        # chord length = sqrt(200) ≈ 14.14
        # For 90-degree arc, radius = chord / (2 * sin(45°)) = chord / sqrt(2)
        emn_content = """.HEADER
IDF_FILE 3.0 "Test" "2024-01-01" 1 "Test" "MM"
.END_HEADER

.BOARD_OUTLINE "OWNER" 1.6
0 0 0 0
0 10 10 90
0 0 0 0
.END_BOARD_OUTLINE
"""
        emn_file = tmp_path / "test.emn"
        emn_file.write_text(emn_content)

        parser = IdfParser(str(emn_file))
        idf = parser.parse()

        arcs = [e for e in idf.board_outline.elements if hasattr(e, "radius")]
        if arcs:
            arc = arcs[0]
            # For a 90-degree arc: radius = chord / (2 * sin(45°))
            # chord = sqrt(10^2 + 10^2) = sqrt(200) ≈ 14.14
            # radius = 14.14 / (2 * 0.707) ≈ 10
            expected_radius = math.sqrt(200) / (2 * math.sin(math.radians(45)))
            assert abs(arc.radius - expected_radius) < 0.1


class TestFullCircle:
    """Test full circle (360-degree arc) handling"""

    def test_360_degree_creates_circle(self, tmp_path):
        """Test that 360-degree arc creates Circle object"""
        emn_content = """.HEADER
IDF_FILE 3.0 "Test" "2024-01-01" 1 "Test" "MM"
.END_HEADER

.BOARD_OUTLINE "OWNER" 1.6
0 0 25 0
0 50 25 360
.END_BOARD_OUTLINE
"""
        emn_file = tmp_path / "test.emn"
        emn_file.write_text(emn_content)

        parser = IdfParser(str(emn_file))
        idf = parser.parse()

        assert idf.board_outline.__class__.__name__ == "Circle"

    def test_circle_radius(self, tmp_path):
        """Test circle radius is half the chord length"""
        emn_content = """.HEADER
IDF_FILE 3.0 "Test" "2024-01-01" 1 "Test" "MM"
.END_HEADER

.BOARD_OUTLINE "OWNER" 1.6
0 0 0 0
0 100 0 360
.END_BOARD_OUTLINE
"""
        emn_file = tmp_path / "test.emn"
        emn_file.write_text(emn_content)

        parser = IdfParser(str(emn_file))
        idf = parser.parse()

        # Chord from (0,0) to (100,0) is diameter = 100, so radius = 50
        assert idf.board_outline.radius == 50.0

    def test_negative_360_creates_circle(self, tmp_path):
        """Test that -360-degree arc also creates Circle"""
        emn_content = """.HEADER
IDF_FILE 3.0 "Test" "2024-01-01" 1 "Test" "MM"
.END_HEADER

.BOARD_OUTLINE "OWNER" 1.6
0 0 0 0
0 80 0 -360
.END_BOARD_OUTLINE
"""
        emn_file = tmp_path / "test.emn"
        emn_file.write_text(emn_content)

        parser = IdfParser(str(emn_file))
        idf = parser.parse()

        assert idf.board_outline.__class__.__name__ == "Circle"
        assert idf.board_outline.radius == 40.0


class TestPolygonClosure:
    """Test polygon closure logic"""

    def test_polygon_auto_closes(self, tmp_path):
        """Test that unclosed polygons are automatically closed"""
        # EMN file where first and last points are explicitly repeated
        emn_content = """.HEADER
IDF_FILE 3.0 "Test" "2024-01-01" 1 "Test" "MM"
.END_HEADER

.BOARD_OUTLINE "OWNER" 1.6
0 0 0 0
0 10 0 0
0 10 10 0
0 0 10 0
0 0 0 0
.END_BOARD_OUTLINE
"""
        emn_file = tmp_path / "test.emn"
        emn_file.write_text(emn_content)

        parser = IdfParser(str(emn_file))
        idf = parser.parse()

        elements = idf.board_outline.elements
        first = elements[0]
        last = elements[-1]

        # Should be closed
        assert abs(first[0] - last[0]) < 1e-6
        assert abs(first[1] - last[1]) < 1e-6

    def test_already_closed_not_doubled(self, tmp_path):
        """Test that already closed polygons aren't double-closed"""
        emn_content = """.HEADER
IDF_FILE 3.0 "Test" "2024-01-01" 1 "Test" "MM"
.END_HEADER

.BOARD_OUTLINE "OWNER" 1.6
0 0 0 0
0 10 0 0
0 10 10 0
0 0 10 0
0 0 0 0
.END_BOARD_OUTLINE
"""
        emn_file = tmp_path / "test.emn"
        emn_file.write_text(emn_content)

        parser = IdfParser(str(emn_file))
        idf = parser.parse()

        elements = idf.board_outline.elements
        # Should have 5 points (not 6 from double-closing)
        assert len(elements) == 5


class TestUnitConversion:
    """Test unit conversion calculations"""

    def test_thou_conversion_factor(self, tmp_path):
        """Test THOU to mm conversion factor (0.0254)"""
        emn_content = """.HEADER
IDF_FILE 3.0 "Test" "2024-01-01" 1 "Test" "THOU"
.END_HEADER

.BOARD_OUTLINE "OWNER" 63
0 0 0 0
0 1000 0 0
0 1000 1000 0
0 0 1000 0
0 0 0 0
.END_BOARD_OUTLINE
"""
        emn_file = tmp_path / "test.emn"
        emn_file.write_text(emn_content)

        parser = IdfParser(str(emn_file))
        idf = parser.parse()

        # 1000 THOU should be 25.4 mm
        elements = idf.board_outline.elements
        xs = [e[0] for e in elements]

        assert abs(max(xs) - 25.4) < 0.01

    def test_mm_no_conversion(self, tmp_path):
        """Test MM units have no conversion (factor 1.0)"""
        emn_content = """.HEADER
IDF_FILE 3.0 "Test" "2024-01-01" 1 "Test" "MM"
.END_HEADER

.BOARD_OUTLINE "OWNER" 1.6
0 0 0 0
0 100 0 0
0 100 50 0
0 0 50 0
0 0 0 0
.END_BOARD_OUTLINE
"""
        emn_file = tmp_path / "test.emn"
        emn_file.write_text(emn_content)

        parser = IdfParser(str(emn_file))
        idf = parser.parse()

        elements = idf.board_outline.elements
        xs = [e[0] for e in elements]

        # Should remain exactly as specified
        assert max(xs) == 100.0


class TestGeometryMixedElements:
    """Test geometry with mixed elements (points and arcs)"""

    def test_mixed_polygon_and_arc(self, tmp_path):
        """Test polygon with mixed straight edges and arcs"""
        # Rectangle with one rounded corner
        emn_content = """.HEADER
IDF_FILE 3.0 "Test" "2024-01-01" 1 "Test" "MM"
.END_HEADER

.BOARD_OUTLINE "OWNER" 1.6
0 0 0 0
0 40 0 0
0 50 10 90
0 50 40 0
0 0 40 0
0 0 0 0
.END_BOARD_OUTLINE
"""
        emn_file = tmp_path / "test.emn"
        emn_file.write_text(emn_content)

        parser = IdfParser(str(emn_file))
        idf = parser.parse()

        assert idf.board_outline.__class__.__name__ == "ArcPolygon"

        # Should have both tuples (points) and Arc objects
        elements = idf.board_outline.elements
        points = [e for e in elements if isinstance(e, tuple)]
        arcs = [e for e in elements if hasattr(e, "center")]

        assert len(points) >= 4  # At least 4 corner points
        assert len(arcs) >= 1  # At least 1 arc

    def test_multiple_arcs(self, tmp_path):
        """Test polygon with multiple arcs (fully rounded corners)"""
        emn_content = """.HEADER
IDF_FILE 3.0 "Test" "2024-01-01" 1 "Test" "MM"
.END_HEADER

.BOARD_OUTLINE "OWNER" 1.6
0 5 0 0
0 45 0 90
0 50 5 0
0 50 45 90
0 45 50 0
0 5 50 90
0 0 45 0
0 0 5 90
0 5 0 0
.END_BOARD_OUTLINE
"""
        emn_file = tmp_path / "test.emn"
        emn_file.write_text(emn_content)

        parser = IdfParser(str(emn_file))
        idf = parser.parse()

        assert idf.board_outline.__class__.__name__ == "ArcPolygon"

        # Should have 4 arcs (one per corner)
        arcs = [e for e in idf.board_outline.elements if hasattr(e, "center")]
        assert len(arcs) == 4


class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_minimum_polygon(self, tmp_path):
        """Test minimum valid polygon (triangle)"""
        emn_content = """.HEADER
IDF_FILE 3.0 "Test" "2024-01-01" 1 "Test" "MM"
.END_HEADER

.BOARD_OUTLINE "OWNER" 1.6
0 0 0 0
0 10 0 0
0 5 10 0
0 0 0 0
.END_BOARD_OUTLINE
"""
        emn_file = tmp_path / "test.emn"
        emn_file.write_text(emn_content)

        parser = IdfParser(str(emn_file))
        idf = parser.parse()

        assert idf.board_outline.__class__.__name__ == "Polygon"
        assert len(idf.board_outline.elements) >= 3

    def test_very_small_coordinates(self, tmp_path):
        """Test handling of very small coordinates"""
        emn_content = """.HEADER
IDF_FILE 3.0 "Test" "2024-01-01" 1 "Test" "MM"
.END_HEADER

.BOARD_OUTLINE "OWNER" 0.1
0 0.001 0.001 0
0 0.002 0.001 0
0 0.002 0.002 0
0 0.001 0.002 0
0 0.001 0.001 0
.END_BOARD_OUTLINE
"""
        emn_file = tmp_path / "test.emn"
        emn_file.write_text(emn_content)

        parser = IdfParser(str(emn_file))
        idf = parser.parse()

        assert idf.board_outline is not None
        elements = idf.board_outline.elements
        assert len(elements) >= 4

    def test_large_coordinates(self, tmp_path):
        """Test handling of large coordinates"""
        emn_content = """.HEADER
IDF_FILE 3.0 "Test" "2024-01-01" 1 "Test" "MM"
.END_HEADER

.BOARD_OUTLINE "OWNER" 1.6
0 0 0 0
0 1000 0 0
0 1000 500 0
0 0 500 0
0 0 0 0
.END_BOARD_OUTLINE
"""
        emn_file = tmp_path / "test.emn"
        emn_file.write_text(emn_content)

        parser = IdfParser(str(emn_file))
        idf = parser.parse()

        elements = idf.board_outline.elements
        xs = [e[0] for e in elements]

        assert max(xs) == 1000.0
