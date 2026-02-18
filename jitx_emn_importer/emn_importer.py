"""
EMN/IDF Importer for JITX Python

High-level import interface that converts parsed IDF data to JITX Python-compatible
layer specifications and generates Python code for board definitions.

Port from Stanza emn-importer.stanza to Python for use with JITX Python API.
"""

import logging
import re
from typing import Any
from io import StringIO

logger = logging.getLogger(__name__)

# Type hints for JITX classes (will be imported or mocked)
Circle = Any
Text = Any
Cutout = Any
KeepOut = Any
Custom = Any
LayerSet = Any
Side = Any
Anchor = Any

# Try to import JITX Python classes, fall back to mocks if not available
try:
    from jitx.shapes.primitive import Circle, Text  # type: ignore
    from jitx.feature import Cutout, KeepOut, Custom  # type: ignore
    from jitx.layerindex import LayerSet, Side  # type: ignore
    from jitx.anchor import Anchor  # type: ignore
    JITX_AVAILABLE = True
except ImportError:
    # Mock classes for when JITX Python is not available
    JITX_AVAILABLE = False

    class _PositionedShape:
        """Mock positioned shape that tracks location"""
        def __init__(self, shape: Any, x: float, y: float):
            self.shape = shape
            self.x = x
            self.y = y

        def __repr__(self) -> str:
            return f"{self.shape!r}.at({self.x}, {self.y})"

    class Circle:  # type: ignore
        def __init__(self, radius: float):
            self.radius = radius

        def at(self, x: float, y: float) -> _PositionedShape:
            return _PositionedShape(self, x, y)

        def __repr__(self) -> str:
            return f"Circle(radius={self.radius})"

    class Text:  # type: ignore
        def __init__(self, text: str, size: float = 1.0, anchor: Any = None):
            self.text = text
            self.size = size
            self.anchor = anchor

        def at(self, x: float, y: float) -> _PositionedShape:
            return _PositionedShape(self, x, y)

        def __repr__(self) -> str:
            anchor_str = f'Anchor.{self.anchor}' if isinstance(self.anchor, str) else self.anchor
            return f'Text("{self.text}", size={self.size}, anchor={anchor_str})'

    class Cutout:  # type: ignore
        def __init__(self, shape: Any):
            self.shape = shape

        def __repr__(self) -> str:
            return f"Cutout({self.shape!r})"

    class KeepOut:  # type: ignore
        def __init__(self, shape: Any, layers: Any = None, pour: bool = False, via: bool = False):
            self.shape = shape
            self.layers = layers
            self.pour = pour
            self.via = via

        def __repr__(self) -> str:
            return f"KeepOut({self.shape!r}, layers={self.layers!r}, pour={self.pour}, via={self.via})"

    class Custom:  # type: ignore
        def __init__(self, shape: Any, name: str = "Custom"):
            self.shape = shape
            self.name = name

        def __repr__(self) -> str:
            return f'Custom({self.shape!r}, name="{self.name}")'

    class LayerSet:  # type: ignore
        def __init__(self, *args: Any):
            self.layers = args

        @classmethod
        def all(cls) -> 'LayerSet':
            return cls("ALL")

        def __repr__(self) -> str:
            if len(self.layers) == 1 and self.layers[0] == "ALL":
                return "LayerSet.all()"
            return f"LayerSet({', '.join(map(str, self.layers))})"

    class Side:  # type: ignore
        Top = "Top"
        Bottom = "Bottom"

    class Anchor:  # type: ignore
        SW = "SW"
        C = "C"

# Import parser with fallback
try:
    from .idf_parser import IdfFile, idf_parser
except ImportError:
    # For standalone usage
    from idf_parser import IdfFile, idf_parser  # type: ignore


def sanitize_identifier(name: str) -> str:
    """Sanitize a string to be a valid Python identifier"""
    # If it starts with a letter or underscore, use as-is
    if name and (name[0].isalpha() or name[0] == '_'):
        # Replace invalid characters with underscores
        sanitized = re.sub(r'[^a-zA-Z0-9_]', '_', name)
        return sanitized
    else:
        # Prepend underscore if it doesn't start with letter/underscore
        sanitized = re.sub(r'[^a-zA-Z0-9_]', '_', name)
        return f"_{sanitized}"


def indent_text(text: str, levels: int = 1) -> str:
    """Indent text by the specified number of levels (4 spaces each)"""
    indent = "    " * levels
    lines = text.split('\n')
    indented_lines = [indent + line if line.strip() else line for line in lines]
    return '\n'.join(indented_lines)


def shape_to_python_code(shape: Any, var_name: str | None = None) -> str:
    """Convert a JITX shape to Python code string

    Note: ArcPolygon conversion is incomplete and will require manual editing.
    ArcPolygon elements contain mixed Arc and point tuples which cannot be
    easily serialized to Python code.
    """
    if hasattr(shape, '__class__'):
        class_name = shape.__class__.__name__

        if class_name == "Circle":
            center = getattr(shape, '_center', None)
            if center and (abs(center[0]) > 1e-10 or abs(center[1]) > 1e-10):
                return f"Circle(radius={shape.radius}).at({center[0]}, {center[1]})"
            return f"Circle(radius={shape.radius})"
        elif class_name == "ArcPolygon":
            # ArcPolygon contains mixed Arc objects and point tuples
            elements_code = []
            for elem in shape.elements:
                if isinstance(elem, tuple):
                    # Point tuple
                    elements_code.append(f"({elem[0]}, {elem[1]})")
                elif hasattr(elem, 'center') and hasattr(elem, 'radius'):
                    # Arc object - serialize with center, radius, start_angle, sweep_angle
                    center = elem.center
                    elements_code.append(
                        f"Arc(({center[0]}, {center[1]}), {elem.radius}, "
                        f"{elem.start_angle}, {elem.sweep_angle})"
                    )
                else:
                    # Unknown element type - add comment
                    elements_code.append(f"# Unknown element: {type(elem).__name__}")
            return f"ArcPolygon([{', '.join(elements_code)}])"
        elif class_name == "Polygon" and hasattr(shape, 'elements'):
            # JITX Polygon uses 'elements' parameter
            elements_str = ', '.join([f"({p[0]}, {p[1]})" for p in shape.elements])
            return f"Polygon([{elements_str}])"
        elif hasattr(shape, 'elements') and shape.elements:
            # Handle other shapes with elements - check if all are tuples
            if all(isinstance(e, tuple) for e in shape.elements):
                elements_str = ', '.join([f"({p[0]}, {p[1]})" for p in shape.elements])
                return f"{class_name}([{elements_str}])"
            else:
                # Complex shape with non-tuple elements
                return f"{class_name}([])  # TODO: Complex shape - manual editing required"
        else:
            return f"{class_name}()"  # fallback
    else:
        return str(shape)


def determine_layer_set(layers_str: str) -> str:
    """Determine LayerSet specification from EMN layer string"""
    if not layers_str or layers_str.upper() in ["", "ALL", "BOTH"]:
        return "LayerSet.all()"
    elif layers_str.upper() in ["TOP", "COMPONENT"]:
        return "LayerSet(0)"
    elif layers_str.upper() in ["BOTTOM", "SOLDER"]:
        return "LayerSet(-1)"
    else:
        # Default to all layers for unknown specifications
        return "LayerSet.all()"


def convert_idf_to_layer_code(idf: IdfFile) -> tuple[list[str], list[str]]:
    """
    Convert IDF data structures to JITX layer specification code.
    Returns tuple of (layer_statements, variable_definitions)
    """
    layer_statements = []
    variable_definitions = []
    
    # Board cutouts
    for cutout in idf.board_cutouts:
        shape_code = shape_to_python_code(cutout)
        layer_statements.append(f"layer(Cutout({shape_code}))")
    
    # Holes as cutouts
    for hole in idf.holes:
        layer_statements.append(
            f"layer(Cutout(Circle(radius={hole.dia * 0.5}).at({hole.x}, {hole.y})))"
        )
    
    # Route keepouts (copper keepouts)
    for keepout in idf.route_keepouts:
        layer_set = determine_layer_set(keepout.layers)
        shape_code = shape_to_python_code(keepout.outline)
        layer_statements.append(
            f"layer(KeepOut({shape_code}, layers={layer_set}, pour=True, via=False))"
        )
    
    # Via keepouts
    for keepout in idf.via_keepouts:
        shape_code = shape_to_python_code(keepout.outline)
        layer_statements.append(
            f"layer(KeepOut({shape_code}, layers=LayerSet.all(), pour=False, via=True))"
        )
    
    # Place keepouts as custom layers
    for keepout in idf.place_keepouts:
        shape_code = shape_to_python_code(keepout.outline)
        layer_statements.append(
            f"layer(Custom({shape_code}, name=\"Placement Keepout\"))"
        )
    
    # Notes as custom text layers
    for note in idf.notes:
        # Clean up text by removing control characters
        text = note.text.replace(chr(1), "").replace(chr(2), "")
        # Escape quotes in text
        text_escaped = text.replace('"', '\\"')
        layer_statements.append(
            f"layer(Custom(Text(\"{text_escaped}\", size={note.height}, anchor=Anchor.SW).at({note.x}, {note.y}), name=\"Assembly Notes\"))"
        )
    
    # Placement as custom text markers
    for part in idf.placement:
        ref_escaped = part.refdes.replace('"', '\\"')
        layer_statements.append(
            f"layer(Custom(Text(\"{ref_escaped}\", size=1.0, anchor=Anchor.C).at({part.x}, {part.y}), name=\"Component Placement\"))"
        )
    
    return layer_statements, variable_definitions


def generate_board_python_code(idf: IdfFile, package_name: str) -> str:
    """Generate Python code for a JITX board definition"""
    
    # Sanitize package name
    clean_package = sanitize_identifier(package_name)
    
    # Generate layer code
    layer_statements, variable_definitions = convert_idf_to_layer_code(idf)
    
    # Start building the output
    output = StringIO()
    
    # Header
    output.write(f'''"""
Generated JITX Python board definition from EMN/IDF import
Package: {clean_package}
"""

from jitx import *
from jitx.shapes.primitive import Arc, Circle, Text, Polygon, ArcPolygon
from jitx.feature import Cutout, KeepOut, Custom
from jitx.layerindex import LayerSet, Side
from jitx.anchor import Anchor

''')
    
    # Variable definitions if any
    if variable_definitions:
        output.write("# Shape definitions\n")
        for var_def in variable_definitions:
            output.write(f"{var_def}\n")
        output.write("\n")
    
    # Board outline
    output.write("# Board outline shape\n")
    board_outline_code = shape_to_python_code(idf.board_outline)
    output.write(f"emn_board_outline = {board_outline_code}\n\n")
    
    # EMN module function
    output.write("def emn_module():\n")
    output.write('    """Generated mechanical data from EMN/IDF import"""\n')
    
    if layer_statements:
        for statement in layer_statements:
            output.write(f"    {statement}\n")
    else:
        output.write("    # No mechanical features found\n")
        output.write("    pass\n")
    
    output.write("\n")
    
    # Example usage
    output.write("# Example usage in a JITX design:\n")
    output.write("# \n")
    output.write("# from jitx.board import Board\n")
    output.write("# from jitx.circuit import Circuit\n")
    output.write("# from jitx.design import Design\n")
    output.write("# \n")
    output.write("# class MyBoard(Board):\n")
    output.write("#     shape = emn_board_outline\n")
    output.write("# \n")
    output.write("# class MyCircuit(Circuit):\n")
    output.write("#     def __init__(self):\n")
    output.write("#         super().__init__()\n")
    output.write("#         emn_module()  # Add mechanical features\n")
    output.write("# \n")
    output.write("# class MyDesign(Design):\n")
    output.write("#     board = MyBoard()\n")
    output.write("#     circuit = MyCircuit()\n")
    
    return output.getvalue()


def import_emn(emn_filename: str, package_name: str, output_filename: str) -> None:
    """
    Import EMN/IDF file and generate Python code for JITX
    
    Args:
        emn_filename: Path to the EMN/IDF file to import
        package_name: Name for the generated package
        output_filename: Output Python file path
    """
    
    # Parse the IDF file
    idf = idf_parser(emn_filename)
    
    # Generate Python code
    python_code = generate_board_python_code(idf, package_name)
    
    # Write to file
    with open(output_filename, 'w') as f:
        f.write(python_code)
    
    logger.info("Successfully imported %s to %s", emn_filename, output_filename)
    logger.info("Package name: %s", package_name)
    logger.info("Board outline: %s", type(idf.board_outline).__name__)
    logger.info("Features: %d cutouts, %d holes, %d notes, %d parts",
                len(idf.board_cutouts), len(idf.holes), len(idf.notes), len(idf.placement))


def import_emn_to_design_class(emn_filename: str, class_name: str, output_filename: str) -> None:
    """
    Import EMN/IDF file and generate a complete JITX Design class
    
    Args:
        emn_filename: Path to the EMN/IDF file to import  
        class_name: Name for the generated Design class
        output_filename: Output Python file path
    """
    
    # Parse the IDF file
    idf = idf_parser(emn_filename)
    
    # Sanitize class name
    clean_class = sanitize_identifier(class_name)
    
    # Generate layer code
    layer_statements, variable_definitions = convert_idf_to_layer_code(idf)
    
    # Start building the output
    output = StringIO()
    
    # Header
    output.write(f'''"""
Generated JITX Python Design from EMN/IDF import
Design: {clean_class}
"""

from jitx import *
from jitx.shapes.primitive import Arc, Circle, Text, Polygon, ArcPolygon
from jitx.feature import Cutout, KeepOut, Custom
from jitx.layerindex import LayerSet, Side
from jitx.anchor import Anchor
from jitx.board import Board
from jitx.design import Design
from jitx.circuit import Circuit

''')
    
    # Variable definitions if any
    if variable_definitions:
        output.write("# Shape definitions\n")
        for var_def in variable_definitions:
            output.write(f"{var_def}\n")
        output.write("\n")
    
    # Board class
    board_outline_code = shape_to_python_code(idf.board_outline)
    output.write(f"class {clean_class}Board(Board):\n")
    output.write('    """Board definition from EMN/IDF import"""\n')
    output.write(f"    shape = {board_outline_code}\n\n")
    
    # Circuit class with mechanical features
    output.write(f"class {clean_class}Circuit(Circuit):\n")
    output.write('    """Main circuit with mechanical features from EMN/IDF"""\n')
    output.write("    \n")
    output.write("    def __init__(self):\n")
    output.write("        super().__init__()\n")
    
    if layer_statements:
        output.write("        # Mechanical features from EMN/IDF\n")
        for statement in layer_statements:
            output.write(f"        {statement}\n")
    else:
        output.write("        # No mechanical features found\n")
        output.write("        pass\n")
    
    output.write("\n")
    
    # Design class
    output.write(f"class {clean_class}Design(Design):\n")
    output.write(f'    """Complete design from EMN/IDF import"""\n')
    output.write(f"    board = {clean_class}Board()\n")
    output.write(f"    circuit = {clean_class}Circuit()\n")
    
    # Write to file
    with open(output_filename, 'w') as f:
        f.write(output.getvalue())
    
    logger.info("Successfully imported %s to %s", emn_filename, output_filename)
    logger.info("Generated Design class: %sDesign", clean_class)
    logger.info("Board outline: %s", type(idf.board_outline).__name__)
    logger.info("Features: %d cutouts, %d holes, %d notes, %d parts",
                len(idf.board_cutouts), len(idf.holes), len(idf.notes), len(idf.placement))


def convert_emn_to_jitx_features(idf_file: IdfFile) -> list[Any]:
    """
    Convert parsed EMN data to actual JITX feature objects (not just code strings).
    This can be used for direct programmatic access to the features.
    """
    features = []
    
    # Board cutouts
    for cutout_shape in idf_file.board_cutouts:
        features.append(Cutout(cutout_shape))
    
    # Holes
    for hole in idf_file.holes:
        hole_circle = Circle(radius=hole.dia * 0.5)
        if hasattr(hole_circle, 'at'):
            hole_circle = hole_circle.at(hole.x, hole.y)
        features.append(Cutout(hole_circle))
    
    # Route keepouts (copper keepouts)
    for route_keepout in idf_file.route_keepouts:
        # Determine layers based on EMN layer specification
        if route_keepout.layers.upper() in ("TOP", "COMPONENT"):
            layer_set = LayerSet(0)
        elif route_keepout.layers.upper() in ("BOTTOM", "SOLDER"):
            layer_set = LayerSet(-1)
        else:
            layer_set = LayerSet.all()  # Default to all layers
            
        features.append(KeepOut(
            route_keepout.outline,
            layers=layer_set,
            pour=True,
            via=False
        ))
    
    # Via keepouts
    for via_keepout in idf_file.via_keepouts:
        features.append(KeepOut(
            via_keepout.outline,
            layers=LayerSet.all(),  # Via keepouts span all layers
            pour=False,
            via=True
        ))
    
    # Place keepouts as custom layers
    for place_keepout in idf_file.place_keepouts:
        features.append(Custom(
            place_keepout.outline,
            name="Placement Keepout"
        ))
    
    # Notes as custom text layers
    for note in idf_file.notes:
        # Clean up text by removing control characters
        text = note.text.replace(chr(1), "").replace(chr(2), "")
        text_shape = Text(text, size=note.height, anchor=Anchor.SW)
        if hasattr(text_shape, 'at'):
            text_shape = text_shape.at(note.x, note.y)
        features.append(Custom(text_shape, name="Assembly Notes"))
    
    # Placement information as custom markers
    for part in idf_file.placement:
        marker_text = Text(part.refdes, size=1.0, anchor=Anchor.C)
        if hasattr(marker_text, 'at'):
            marker_text = marker_text.at(part.x, part.y)
        features.append(Custom(marker_text, name="Component Placement"))
    
    return features


def main():
    """Command-line interface for EMN/IDF importer"""
    import sys

    if len(sys.argv) < 4:
        print("Usage: python -m jitx_emn_importer.emn_importer <emn_file> <package_name> <output_file> [--design-class]")
        print("  or: emn-import <emn_file> <package_name> <output_file> [--design-class]")
        print("")
        print("Arguments:")
        print("  emn_file      : Path to the EMN/IDF/BDF file to import")
        print("  package_name  : Name for the generated package/class")
        print("  output_file   : Output Python file path")
        print("")
        print("Options:")
        print("  --design-class: Generate a complete Design class instead of just helper functions")
        sys.exit(1)

    emn_file = sys.argv[1]
    package_name = sys.argv[2]
    output_file = sys.argv[3]

    if "--design-class" in sys.argv:
        import_emn_to_design_class(emn_file, package_name, output_file)
    else:
        import_emn(emn_file, package_name, output_file)


if __name__ == "__main__":
    main()