"""
Pytest unit tests for emn_importer module
"""

import ast

from jitx_emn_importer.emn_importer import (
    _fmt,
    _generate_feature_code,
    convert_emn_to_jitx_features,
    determine_layer_set,
    import_emn,
    indent_text,
    sanitize_identifier,
    shape_to_multiline_code,
    shape_to_python_code,
)
from jitx_emn_importer.idf_parser import (
    Arc,
    ArcPolygon,
    Circle,
    IdfFile,
    IdfHeader,
    IdfOutline,
    Polygon,
    idf_parser,
)


class TestSanitizeIdentifier:
    """Test Python identifier sanitization"""

    def test_simple_name(self):
        assert sanitize_identifier("MyBoard") == "MyBoard"

    def test_with_spaces(self):
        assert sanitize_identifier("My Board") == "My_Board"

    def test_with_hyphens(self):
        assert sanitize_identifier("my-board-v2") == "my_board_v2"

    def test_starting_with_number(self):
        assert sanitize_identifier("123board") == "_123board"

    def test_special_characters(self):
        assert sanitize_identifier("board@v1.2") == "board_v1_2"

    def test_empty_string(self):
        result = sanitize_identifier("")
        assert result.startswith("_")


class TestIndentText:
    """Test text indentation"""

    def test_single_level(self):
        result = indent_text("line1\nline2", 1)
        assert result == "    line1\n    line2"

    def test_double_level(self):
        result = indent_text("line1", 2)
        assert result == "        line1"

    def test_empty_lines(self):
        result = indent_text("line1\n\nline2", 1)
        lines = result.split("\n")
        assert lines[0] == "    line1"
        assert lines[1] == ""
        assert lines[2] == "    line2"


class TestFmt:
    """Test float formatting helper"""

    def test_rounds_to_4_decimals(self):
        assert _fmt(10.123456789) == "10.1235"

    def test_preserves_whole_numbers(self):
        assert _fmt(10.0) == "10.0"

    def test_strips_trailing_zeros(self):
        assert _fmt(10.1000) == "10.1"

    def test_negative_values(self):
        assert _fmt(-3.14159) == "-3.1416"

    def test_zero(self):
        assert _fmt(0.0) == "0.0"


class TestShapeToPythonCode:
    """Test shape to Python code conversion"""

    def test_circle_code(self):
        circle = Circle(radius=5.0)
        code = shape_to_python_code(circle)
        assert code == "Circle(radius=5.0)"

    def test_polygon_code(self):
        polygon = Polygon([(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)])
        code = shape_to_python_code(polygon)
        assert "Polygon([" in code
        assert "(0.0, 0.0)" in code
        assert "(10.0, 0.0)" in code

    def test_arc_polygon_code(self):
        arc = Arc((5, 5), 5.0, 0.0, 90.0)
        arc_polygon = ArcPolygon([(0, 0), arc, (10, 10)])
        code = shape_to_python_code(arc_polygon)
        assert "ArcPolygon([" in code
        assert "Arc((" in code

    def test_circle_with_center_emits_at(self):
        circle = Circle(radius=5.0)
        circle._center = (10.0, 20.0)
        code = shape_to_python_code(circle)
        assert ".at(10.0, 20.0)" in code

    def test_circle_at_origin_no_at(self):
        circle = Circle(radius=5.0)
        circle._center = (0.0, 0.0)
        code = shape_to_python_code(circle)
        assert ".at" not in code

    def test_circle_without_center_no_at(self):
        circle = Circle(radius=5.0)
        code = shape_to_python_code(circle)
        assert ".at" not in code

    def test_coordinates_are_rounded(self):
        polygon = Polygon([(1.23456789, 2.34567891)])
        code = shape_to_python_code(polygon)
        assert "1.2346" in code
        assert "2.3457" in code


class TestShapeToMultilineCode:
    """Test multi-line shape formatting"""

    def test_polygon_multiline(self):
        polygon = Polygon([(0, 0), (10, 0), (10, 10), (0, 0)])
        code = shape_to_multiline_code(polygon, indent=1)
        lines = code.split("\n")
        assert lines[0] == "Polygon(["
        assert "    (0.0, 0.0)," in lines[1]
        assert lines[-1].endswith("])")

    def test_arc_polygon_multiline(self):
        arc = Arc((5, 5), 5.0, 0.0, 90.0)
        arc_polygon = ArcPolygon([(0, 0), arc, (10, 10)])
        code = shape_to_multiline_code(arc_polygon, indent=1)
        assert "ArcPolygon([" in code
        assert "Arc((" in code
        assert code.count("\n") >= 3  # At least one line per element

    def test_circle_stays_single_line(self):
        circle = Circle(radius=5.0)
        code = shape_to_multiline_code(circle, indent=1)
        assert "\n" not in code


class TestDetermineLayerSet:
    """Test layer set determination"""

    def test_top_layer(self):
        assert determine_layer_set("TOP") == "LayerSet(0)"
        assert determine_layer_set("COMPONENT") == "LayerSet(0)"

    def test_bottom_layer(self):
        assert determine_layer_set("BOTTOM") == "LayerSet(-1)"
        assert determine_layer_set("SOLDER") == "LayerSet(-1)"

    def test_all_layers(self):
        assert determine_layer_set("ALL") == "LayerSet.all()"
        assert determine_layer_set("BOTH") == "LayerSet.all()"
        assert determine_layer_set("") == "LayerSet.all()"

    def test_case_insensitive(self):
        assert determine_layer_set("top") == "LayerSet(0)"
        assert determine_layer_set("Top") == "LayerSet(0)"

    def test_unknown_defaults_to_all(self):
        assert determine_layer_set("UNKNOWN") == "LayerSet.all()"


class TestGenerateFeatureCode:
    """Test categorized feature code generation"""

    def test_with_holes(self, temp_emn_file_with_holes):
        idf = idf_parser(str(temp_emn_file_with_holes))
        features = _generate_feature_code(idf)
        assert len(features["cutouts"]) == 3
        assert all("Cutout" in c for c in features["cutouts"])

    def test_with_notes(self, tmp_path, emn_with_notes):
        emn_file = tmp_path / "test.emn"
        emn_file.write_text(emn_with_notes)
        idf = idf_parser(str(emn_file))
        features = _generate_feature_code(idf)
        assert len(features["notes"]) == 3
        assert all("Assembly Notes" in n for n in features["notes"])

    def test_with_keepouts(self, tmp_path, emn_with_keepouts):
        emn_file = tmp_path / "test.emn"
        emn_file.write_text(emn_with_keepouts)
        idf = idf_parser(str(emn_file))
        features = _generate_feature_code(idf)
        assert len(features["route_keepouts"]) == 1
        assert len(features["via_keepouts"]) == 1

    def test_no_layer_calls(self, temp_emn_complete):
        idf = idf_parser(str(temp_emn_complete))
        features = _generate_feature_code(idf)
        for category in features.values():
            for item in category:
                assert "layer(" not in item


class TestImportEmn:
    """Test import_emn function (generates Design classes)"""

    def test_creates_output_file(self, temp_emn_file, tmp_path):
        output_file = tmp_path / "output.py"
        import_emn(str(temp_emn_file), "TestBoard", str(output_file))
        assert output_file.exists()
        assert len(output_file.read_text()) > 0

    def test_output_is_valid_python(self, temp_emn_file, tmp_path):
        output_file = tmp_path / "output.py"
        import_emn(str(temp_emn_file), "TestBoard", str(output_file))
        ast.parse(output_file.read_text())

    def test_sanitizes_class_name(self, temp_emn_file, tmp_path):
        output_file = tmp_path / "output.py"
        import_emn(str(temp_emn_file), "My Board v2", str(output_file))
        content = output_file.read_text()
        assert "My_Board_v2" in content

    def test_contains_board_class(self, temp_emn_file, tmp_path):
        output_file = tmp_path / "output.py"
        import_emn(str(temp_emn_file), "TestBoard", str(output_file))
        content = output_file.read_text()
        assert "class TestBoardBoard(Board):" in content
        assert "shape = " in content

    def test_contains_circuit_class(self, temp_emn_file, tmp_path):
        output_file = tmp_path / "output.py"
        import_emn(str(temp_emn_file), "TestBoard", str(output_file))
        content = output_file.read_text()
        assert "class TestBoardCircuit(Circuit):" in content

    def test_contains_design_class(self, temp_emn_file, tmp_path):
        output_file = tmp_path / "output.py"
        import_emn(str(temp_emn_file), "TestBoard", str(output_file))
        content = output_file.read_text()
        assert "class TestBoardDesign(Design):" in content

    def test_no_layer_calls(self, temp_emn_file, tmp_path):
        output_file = tmp_path / "output.py"
        import_emn(str(temp_emn_file), "TestBoard", str(output_file))
        content = output_file.read_text()
        assert "layer(" not in content

    def test_no_emn_module(self, temp_emn_file, tmp_path):
        output_file = tmp_path / "output.py"
        import_emn(str(temp_emn_file), "TestBoard", str(output_file))
        content = output_file.read_text()
        assert "emn_module" not in content

    def test_board_outline_is_multiline(self, temp_emn_file, tmp_path):
        output_file = tmp_path / "output.py"
        import_emn(str(temp_emn_file), "TestBoard", str(output_file))
        content = output_file.read_text()
        # Board shape should be multiline (Polygon with elements on separate lines)
        assert "Polygon([\n" in content


class TestCompleteImport:
    """Test complete import workflow with all feature types"""

    def test_complete_file_import(self, temp_emn_complete, tmp_path):
        output_file = tmp_path / "complete.py"
        import_emn(str(temp_emn_complete), "Complete", str(output_file))
        content = output_file.read_text()

        # Valid Python
        ast.parse(content)

        # Has all class definitions
        assert "class CompleteBoard" in content
        assert "class CompleteCircuit" in content
        assert "class CompleteDesign" in content

        # Has categorized features
        assert "self.cutouts" in content
        assert "Cutout" in content
        assert "Assembly Notes" in content
        assert "KeepOut" in content
        assert "Component Placement" in content

        # No layer() calls
        assert "layer(" not in content


class TestLayerAliases:
    """Regression: convert_emn_to_jitx_features must handle COMPONENT/SOLDER aliases"""

    def _make_idf_with_keepout(self, layer_str):
        outline = Polygon([(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)])
        header = IdfHeader("IDF_FILE", 3.0, "test", "2024", 1, "test", "MM")
        keepout = IdfOutline(
            owner="OWNER",
            ident=".ROUTE_KEEPOUT",
            thickness=0.0,
            layers=layer_str,
            outline=outline,
            cutouts=[],
        )
        return IdfFile(
            header=header,
            board_outline=Polygon([(0, 0), (100, 0), (100, 50), (0, 50), (0, 0)]),
            board_cutouts=(),
            other_outlines=(),
            route_outlines=(),
            place_outlines=(),
            route_keepouts=(keepout,),
            via_keepouts=(),
            place_keepouts=(),
            holes=(),
            notes=(),
            placement=(),
        )

    def test_component_maps_to_top(self):
        idf = self._make_idf_with_keepout("COMPONENT")
        features = convert_emn_to_jitx_features(idf)
        assert len(features) == 1
        keepout = features[0]
        assert list(keepout.layers.ranges) == [(0, 0)]

    def test_solder_maps_to_bottom(self):
        idf = self._make_idf_with_keepout("SOLDER")
        features = convert_emn_to_jitx_features(idf)
        assert len(features) == 1
        keepout = features[0]
        assert list(keepout.layers.ranges) == [(-1, -1)]
