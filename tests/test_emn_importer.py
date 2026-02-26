"""
Pytest unit tests for emn_importer module
"""

import ast

from jitx_emn_importer.emn_importer import (
    convert_emn_to_jitx_features,
    convert_idf_to_layer_code,
    determine_layer_set,
    generate_board_python_code,
    import_emn,
    import_emn_to_design_class,
    indent_text,
    sanitize_identifier,
    shape_to_python_code,
)
from jitx_emn_importer.idf_parser import (
    Arc,
    ArcPolygon,
    Circle,
    IdfFile,
    IdfOutline,
    Polygon,
    idf_parser,
)


class TestSanitizeIdentifier:
    """Test Python identifier sanitization"""

    def test_simple_name(self):
        """Test simple valid identifier"""
        assert sanitize_identifier("MyBoard") == "MyBoard"

    def test_with_spaces(self):
        """Test name with spaces"""
        assert sanitize_identifier("My Board") == "My_Board"

    def test_with_hyphens(self):
        """Test name with hyphens"""
        assert sanitize_identifier("my-board-v2") == "my_board_v2"

    def test_starting_with_number(self):
        """Test name starting with number"""
        assert sanitize_identifier("123board") == "_123board"

    def test_special_characters(self):
        """Test name with special characters"""
        assert sanitize_identifier("board@v1.2") == "board_v1_2"

    def test_empty_string(self):
        """Test empty string"""
        result = sanitize_identifier("")
        assert result.startswith("_")


class TestIndentText:
    """Test text indentation"""

    def test_single_level(self):
        """Test single level indentation"""
        result = indent_text("line1\nline2", 1)
        assert result == "    line1\n    line2"

    def test_double_level(self):
        """Test double level indentation"""
        result = indent_text("line1", 2)
        assert result == "        line1"

    def test_empty_lines(self):
        """Test that empty lines are not indented"""
        result = indent_text("line1\n\nline2", 1)
        lines = result.split("\n")
        assert lines[0] == "    line1"
        assert lines[1] == ""  # Empty line should not be indented
        assert lines[2] == "    line2"


class TestShapeToPythonCode:
    """Test shape to Python code conversion"""

    def test_circle_code(self):
        """Test circle code generation"""
        circle = Circle(radius=5.0)
        code = shape_to_python_code(circle)
        assert code == "Circle(radius=5.0)"

    def test_polygon_code(self):
        """Test polygon code generation"""
        polygon = Polygon([(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)])
        code = shape_to_python_code(polygon)
        assert "Polygon([" in code
        assert "(0, 0)" in code
        assert "(10, 0)" in code

    def test_arc_polygon_code(self):
        """Test arc polygon code generation with proper Arc serialization"""
        arc = Arc((5, 5), 5.0, 0.0, 90.0)
        arc_polygon = ArcPolygon([(0, 0), arc, (10, 10)])
        code = shape_to_python_code(arc_polygon)

        assert "ArcPolygon([" in code
        assert "(0, 0)" in code
        assert "Arc((" in code
        assert "(10, 10)" in code


class TestDetermineLayerSet:
    """Test layer set determination"""

    def test_top_layer(self):
        """Test TOP layer"""
        assert determine_layer_set("TOP") == "LayerSet(0)"
        assert determine_layer_set("COMPONENT") == "LayerSet(0)"

    def test_bottom_layer(self):
        """Test BOTTOM layer"""
        assert determine_layer_set("BOTTOM") == "LayerSet(-1)"
        assert determine_layer_set("SOLDER") == "LayerSet(-1)"

    def test_all_layers(self):
        """Test ALL layers"""
        assert determine_layer_set("ALL") == "LayerSet.all()"
        assert determine_layer_set("BOTH") == "LayerSet.all()"
        assert determine_layer_set("") == "LayerSet.all()"

    def test_case_insensitive(self):
        """Test case insensitivity"""
        assert determine_layer_set("top") == "LayerSet(0)"
        assert determine_layer_set("Top") == "LayerSet(0)"
        assert determine_layer_set("TOP") == "LayerSet(0)"

    def test_unknown_defaults_to_all(self):
        """Test unknown layer defaults to all"""
        assert determine_layer_set("UNKNOWN") == "LayerSet.all()"


class TestConvertIdfToLayerCode:
    """Test IDF to layer code conversion"""

    def test_with_holes(self, temp_emn_file_with_holes):
        """Test conversion with drilled holes"""
        idf = idf_parser(str(temp_emn_file_with_holes))
        layer_stmts, var_defs = convert_idf_to_layer_code(idf)

        # Should have layer statements for holes
        hole_stmts = [s for s in layer_stmts if "Cutout" in s and "Circle" in s]
        assert len(hole_stmts) == 3  # 3 holes

    def test_with_notes(self, tmp_path, emn_with_notes):
        """Test conversion with notes"""
        emn_file = tmp_path / "test.emn"
        emn_file.write_text(emn_with_notes)

        idf = idf_parser(str(emn_file))
        layer_stmts, var_defs = convert_idf_to_layer_code(idf)

        # Should have layer statements for notes
        note_stmts = [s for s in layer_stmts if "Assembly Notes" in s]
        assert len(note_stmts) == 3  # 3 notes

    def test_with_keepouts(self, tmp_path, emn_with_keepouts):
        """Test conversion with keepouts"""
        emn_file = tmp_path / "test.emn"
        emn_file.write_text(emn_with_keepouts)

        idf = idf_parser(str(emn_file))
        layer_stmts, var_defs = convert_idf_to_layer_code(idf)

        # Should have layer statements for keepouts
        keepout_stmts = [s for s in layer_stmts if "KeepOut" in s]
        assert len(keepout_stmts) == 2  # 1 route + 1 via


class TestGenerateBoardPythonCode:
    """Test board Python code generation"""

    def test_generates_valid_python(self, temp_emn_file):
        """Test that generated code is valid Python syntax"""
        idf = idf_parser(str(temp_emn_file))
        code = generate_board_python_code(idf, "TestBoard")

        # Should parse without syntax errors
        ast.parse(code)

    def test_contains_board_outline(self, temp_emn_file):
        """Test that generated code contains board outline"""
        idf = idf_parser(str(temp_emn_file))
        code = generate_board_python_code(idf, "TestBoard")

        assert "emn_board_outline" in code
        assert "Polygon" in code

    def test_contains_imports(self, temp_emn_file):
        """Test that generated code contains required imports"""
        idf = idf_parser(str(temp_emn_file))
        code = generate_board_python_code(idf, "TestBoard")

        assert "from jitx" in code
        assert "Circle" in code
        assert "Polygon" in code

    def test_contains_emn_module(self, temp_emn_file):
        """Test that generated code contains emn_module function"""
        idf = idf_parser(str(temp_emn_file))
        code = generate_board_python_code(idf, "TestBoard")

        assert "def emn_module():" in code


class TestImportEmn:
    """Test import_emn function"""

    def test_creates_output_file(self, temp_emn_file, tmp_path):
        """Test that import_emn creates output file"""
        output_file = tmp_path / "output.py"

        import_emn(str(temp_emn_file), "TestBoard", str(output_file))

        assert output_file.exists()
        content = output_file.read_text()
        assert len(content) > 0

    def test_output_is_valid_python(self, temp_emn_file, tmp_path):
        """Test that output file is valid Python"""
        output_file = tmp_path / "output.py"

        import_emn(str(temp_emn_file), "TestBoard", str(output_file))

        content = output_file.read_text()
        ast.parse(content)  # Should not raise

    def test_sanitizes_package_name(self, temp_emn_file, tmp_path):
        """Test that package name is sanitized"""
        output_file = tmp_path / "output.py"

        import_emn(str(temp_emn_file), "My Board v2", str(output_file))

        content = output_file.read_text()
        assert "My_Board_v2" in content


class TestImportEmnToDesignClass:
    """Test import_emn_to_design_class function"""

    def test_creates_output_file(self, temp_emn_file, tmp_path):
        """Test that import_emn_to_design_class creates output file"""
        output_file = tmp_path / "design.py"

        import_emn_to_design_class(str(temp_emn_file), "TestBoard", str(output_file))

        assert output_file.exists()

    def test_output_is_valid_python(self, temp_emn_file, tmp_path):
        """Test that output file is valid Python"""
        output_file = tmp_path / "design.py"

        import_emn_to_design_class(str(temp_emn_file), "TestBoard", str(output_file))

        content = output_file.read_text()
        ast.parse(content)  # Should not raise

    def test_contains_board_class(self, temp_emn_file, tmp_path):
        """Test that output contains Board class"""
        output_file = tmp_path / "design.py"

        import_emn_to_design_class(str(temp_emn_file), "TestBoard", str(output_file))

        content = output_file.read_text()
        assert "class TestBoardBoard(Board):" in content

    def test_contains_circuit_class(self, temp_emn_file, tmp_path):
        """Test that output contains Circuit class"""
        output_file = tmp_path / "design.py"

        import_emn_to_design_class(str(temp_emn_file), "TestBoard", str(output_file))

        content = output_file.read_text()
        assert "class TestBoardCircuit(Circuit):" in content

    def test_contains_design_class(self, temp_emn_file, tmp_path):
        """Test that output contains Design class"""
        output_file = tmp_path / "design.py"

        import_emn_to_design_class(str(temp_emn_file), "TestBoard", str(output_file))

        content = output_file.read_text()
        assert "class TestBoardDesign(Design):" in content


class TestCompleteImport:
    """Test complete import workflow"""

    def test_complete_file_import(self, temp_emn_complete, tmp_path):
        """Test importing a complete EMN file"""
        output_file = tmp_path / "complete.py"

        import_emn(str(temp_emn_complete), "CompleteBoard", str(output_file))

        content = output_file.read_text()

        # Should have all feature types
        assert "emn_board_outline" in content
        assert "Cutout" in content  # For holes
        assert "Assembly Notes" in content  # For notes
        assert "KeepOut" in content  # For keepouts
        assert "Component Placement" in content  # For placement

    def test_design_class_complete_import(self, temp_emn_complete, tmp_path):
        """Test importing to Design class"""
        output_file = tmp_path / "design.py"

        import_emn_to_design_class(str(temp_emn_complete), "Complete", str(output_file))

        content = output_file.read_text()

        # Should have all class definitions
        assert "class CompleteBoard" in content
        assert "class CompleteCircuit" in content
        assert "class CompleteDesign" in content

        # Verify valid Python
        ast.parse(content)


class TestLayerAliases:
    """Regression: Bug 2.6 — convert_emn_to_jitx_features must handle COMPONENT/SOLDER aliases"""

    def _make_idf_with_keepout(self, layer_str):
        """Helper: build an IdfFile with one route keepout on the given layer"""
        outline = Polygon([(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)])
        from jitx_emn_importer.idf_parser import IdfHeader

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
        """COMPONENT layer alias should map to LayerSet(0) like TOP"""
        idf = self._make_idf_with_keepout("COMPONENT")
        features = convert_emn_to_jitx_features(idf)
        # Should have one keepout feature
        assert len(features) == 1
        keepout = features[0]
        assert list(keepout.layers.ranges) == [(0, 0)]

    def test_solder_maps_to_bottom(self):
        """SOLDER layer alias should map to LayerSet(-1) like BOTTOM"""
        idf = self._make_idf_with_keepout("SOLDER")
        features = convert_emn_to_jitx_features(idf)
        assert len(features) == 1
        keepout = features[0]
        assert list(keepout.layers.ranges) == [(-1, -1)]


class TestCircleCenterInCode:
    """Regression: Bug 2.5 — shape_to_python_code must emit .at() for off-origin circles"""

    def test_circle_with_center_emits_at(self):
        """Circle with non-zero center should generate .at() call"""
        circle = Circle(radius=5.0)
        circle._center = (10.0, 20.0)
        code = shape_to_python_code(circle)
        assert ".at(10.0, 20.0)" in code

    def test_circle_at_origin_no_at(self):
        """Circle at origin should not generate .at() call"""
        circle = Circle(radius=5.0)
        circle._center = (0.0, 0.0)
        code = shape_to_python_code(circle)
        assert ".at" not in code

    def test_circle_without_center_no_at(self):
        """Circle without _center attribute should not generate .at() call"""
        circle = Circle(radius=5.0)
        code = shape_to_python_code(circle)
        assert ".at" not in code
