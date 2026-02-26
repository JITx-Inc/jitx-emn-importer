"""
EMN/IDF Importer for JITX Python

High-level import interface that converts parsed IDF data to JITX Python-compatible
layer specifications and generates Python code for board definitions.

Port from Stanza emn-importer.stanza to Python for use with JITX Python API.
"""

import logging
import re
from io import StringIO
from typing import Any

from jitx.anchor import Anchor
from jitx.feature import Custom, Cutout, KeepOut
from jitx.layerindex import LayerSet
from jitx.shapes.primitive import Arc, ArcPolygon, Circle, Polygon, Text

from .idf_parser import IdfFile, idf_parser

logger = logging.getLogger(__name__)


def sanitize_identifier(name: str) -> str:
    """Sanitize a string to be a valid Python identifier"""
    # If it starts with a letter or underscore, use as-is
    if name and (name[0].isalpha() or name[0] == "_"):
        # Replace invalid characters with underscores
        sanitized = re.sub(r"[^a-zA-Z0-9_]", "_", name)
        return sanitized
    else:
        # Prepend underscore if it doesn't start with letter/underscore
        sanitized = re.sub(r"[^a-zA-Z0-9_]", "_", name)
        return f"_{sanitized}"


def indent_text(text: str, levels: int = 1) -> str:
    """Indent text by the specified number of levels (4 spaces each)"""
    indent = "    " * levels
    lines = text.split("\n")
    indented_lines = [indent + line if line.strip() else line for line in lines]
    return "\n".join(indented_lines)


def shape_to_python_code(shape: Any, var_name: str | None = None) -> str:
    """Convert a JITX shape to Python code string"""
    if isinstance(shape, Circle):
        center = getattr(shape, "_center", None)
        if center and (abs(center[0]) > 1e-10 or abs(center[1]) > 1e-10):
            return f"Circle(radius={shape.radius}).at({center[0]}, {center[1]})"
        return f"Circle(radius={shape.radius})"
    elif isinstance(shape, ArcPolygon):
        elements_code = []
        for elem in shape.elements:
            if isinstance(elem, tuple):
                elements_code.append(f"({elem[0]}, {elem[1]})")
            elif isinstance(elem, Arc):
                center = elem.center
                elements_code.append(
                    f"Arc(({center[0]}, {center[1]}), {elem.radius}, {elem.start}, {elem.arc})"
                )
            else:
                elements_code.append(f"# Unknown element: {type(elem).__name__}")
        return f"ArcPolygon([{', '.join(elements_code)}])"
    elif isinstance(shape, Polygon):
        elements_str = ", ".join([f"({p[0]}, {p[1]})" for p in shape.elements])
        return f"Polygon([{elements_str}])"
    elif hasattr(shape, "elements") and shape.elements:
        class_name = shape.__class__.__name__
        if all(isinstance(e, tuple) for e in shape.elements):
            elements_str = ", ".join([f"({p[0]}, {p[1]})" for p in shape.elements])
            return f"{class_name}([{elements_str}])"
        else:
            return f"{class_name}([])  # TODO: Complex shape - manual editing required"
    elif hasattr(shape, "__class__"):
        return f"{shape.__class__.__name__}()"
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
        layer_statements.append(f'layer(Custom({shape_code}, name="Placement Keepout"))')

    # Notes as custom text layers
    for note in idf.notes:
        # Clean up text by removing control characters
        text = note.text.replace(chr(1), "").replace(chr(2), "")
        # Escape quotes in text
        text_escaped = text.replace('"', '\\"')
        text_shape = f'Text("{text_escaped}", size={note.height}, anchor=Anchor.SW)'
        text_at = f"{text_shape}.at({note.x}, {note.y})"
        layer_statements.append(f'layer(Custom({text_at}, name="Assembly Notes"))')

    # Placement as custom text markers
    for part in idf.placement:
        ref_escaped = part.refdes.replace('"', '\\"')
        text_shape = f'Text("{ref_escaped}", size=1.0, anchor=Anchor.C)'
        text_at = f"{text_shape}.at({part.x}, {part.y})"
        layer_statements.append(f'layer(Custom({text_at}, name="Component Placement"))')

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
    with open(output_filename, "w") as f:
        f.write(python_code)

    logger.info("Successfully imported %s to %s", emn_filename, output_filename)
    logger.info("Package name: %s", package_name)
    logger.info("Board outline: %s", type(idf.board_outline).__name__)
    logger.info(
        "Features: %d cutouts, %d holes, %d notes, %d parts",
        len(idf.board_cutouts),
        len(idf.holes),
        len(idf.notes),
        len(idf.placement),
    )


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
    output.write('    """Complete design from EMN/IDF import"""\n')
    output.write(f"    board = {clean_class}Board()\n")
    output.write(f"    circuit = {clean_class}Circuit()\n")

    # Write to file
    with open(output_filename, "w") as f:
        f.write(output.getvalue())

    logger.info("Successfully imported %s to %s", emn_filename, output_filename)
    logger.info("Generated Design class: %sDesign", clean_class)
    logger.info("Board outline: %s", type(idf.board_outline).__name__)
    logger.info(
        "Features: %d cutouts, %d holes, %d notes, %d parts",
        len(idf.board_cutouts),
        len(idf.holes),
        len(idf.notes),
        len(idf.placement),
    )


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
        if hasattr(hole_circle, "at"):
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

        features.append(KeepOut(route_keepout.outline, layers=layer_set, pour=True, via=False))

    # Via keepouts
    for via_keepout in idf_file.via_keepouts:
        features.append(
            KeepOut(
                via_keepout.outline,
                layers=LayerSet.all(),  # Via keepouts span all layers
                pour=False,
                via=True,
            )
        )

    # Place keepouts as custom layers
    for place_keepout in idf_file.place_keepouts:
        features.append(Custom(place_keepout.outline, name="Placement Keepout"))

    # Notes as custom text layers
    for note in idf_file.notes:
        # Clean up text by removing control characters
        text = note.text.replace(chr(1), "").replace(chr(2), "")
        text_shape = Text(text, size=note.height, anchor=Anchor.SW)
        if hasattr(text_shape, "at"):
            text_shape = text_shape.at(note.x, note.y)
        features.append(Custom(text_shape, name="Assembly Notes"))

    # Placement information as custom markers
    for part in idf_file.placement:
        marker_text = Text(part.refdes, size=1.0, anchor=Anchor.C)
        if hasattr(marker_text, "at"):
            marker_text = marker_text.at(part.x, part.y)
        features.append(Custom(marker_text, name="Component Placement"))

    return features


def main():
    """Command-line interface for EMN/IDF importer"""
    import argparse

    parser = argparse.ArgumentParser(
        prog="emn-import",
        description="Import EMN/IDF/BDF files and generate JITX Python code",
    )
    parser.add_argument("emn_file", help="Path to the EMN/IDF/BDF file to import")
    parser.add_argument("package_name", help="Name for the generated package/class")
    parser.add_argument("output_file", help="Output Python file path")
    parser.add_argument(
        "--design-class",
        action="store_true",
        dest="design_class",
        help="Generate a complete Design class instead of just helper functions",
    )

    args = parser.parse_args()

    if args.design_class:
        import_emn_to_design_class(args.emn_file, args.package_name, args.output_file)
    else:
        import_emn(args.emn_file, args.package_name, args.output_file)


if __name__ == "__main__":
    main()
