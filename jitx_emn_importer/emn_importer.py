"""
EMN/IDF Importer for JITX Python

High-level import interface that converts parsed IDF data to JITX Python-compatible
board definitions. Generates complete Board + Circuit + Design classes from EMN/IDF
mechanical data.
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

# Coordinate precision for generated code (decimal places)
_PRECISION = 4


def _fmt(value: float) -> str:
    """Format a float for code generation: round and strip trailing zeros."""
    rounded = round(value, _PRECISION)
    # Use 'g' format to strip trailing zeros, but ensure at least one decimal
    s = f"{rounded:.{_PRECISION}f}".rstrip("0").rstrip(".")
    # Ensure there's always a decimal point for float literals
    if "." not in s:
        s += ".0"
    return s


def sanitize_identifier(name: str) -> str:
    """Sanitize a string to be a valid Python identifier"""
    if name and (name[0].isalpha() or name[0] == "_"):
        sanitized = re.sub(r"[^a-zA-Z0-9_]", "_", name)
        return sanitized
    else:
        sanitized = re.sub(r"[^a-zA-Z0-9_]", "_", name)
        return f"_{sanitized}"


def indent_text(text: str, levels: int = 1) -> str:
    """Indent text by the specified number of levels (4 spaces each)"""
    indent = "    " * levels
    lines = text.split("\n")
    indented_lines = [indent + line if line.strip() else line for line in lines]
    return "\n".join(indented_lines)


def _point_to_code(p: tuple) -> str:
    """Format a point tuple for code generation."""
    return f"({_fmt(p[0])}, {_fmt(p[1])})"


def _arc_to_code(arc: Arc) -> str:
    """Format an Arc for code generation."""
    c = arc.center
    return (
        f"Arc(({_fmt(c[0])}, {_fmt(c[1])}), {_fmt(arc.radius)}, {_fmt(arc.start)}, {_fmt(arc.arc)})"
    )


def shape_to_python_code(shape: Any) -> str:
    """Convert a JITX shape to a single-line Python code string."""
    if isinstance(shape, Circle):
        center = getattr(shape, "_center", None)
        if center and (abs(center[0]) > 1e-10 or abs(center[1]) > 1e-10):
            return f"Circle(radius={_fmt(shape.radius)}).at({_fmt(center[0])}, {_fmt(center[1])})"
        return f"Circle(radius={_fmt(shape.radius)})"
    elif isinstance(shape, ArcPolygon):
        parts = []
        for elem in shape.elements:
            if isinstance(elem, tuple):
                parts.append(_point_to_code(elem))
            elif isinstance(elem, Arc):
                parts.append(_arc_to_code(elem))
            else:
                parts.append(f"# Unknown: {type(elem).__name__}")
        return f"ArcPolygon([{', '.join(parts)}])"
    elif isinstance(shape, Polygon):
        elements_str = ", ".join(_point_to_code(p) for p in shape.elements)
        return f"Polygon([{elements_str}])"
    elif hasattr(shape, "__class__"):
        return f"{shape.__class__.__name__}()"
    else:
        return str(shape)


def shape_to_multiline_code(shape: Any, indent: int = 0) -> str:
    """Convert a JITX shape to multi-line Python code, one element per line."""
    prefix = "    " * indent

    if isinstance(shape, Circle):
        center = getattr(shape, "_center", None)
        if center and (abs(center[0]) > 1e-10 or abs(center[1]) > 1e-10):
            return f"Circle(radius={_fmt(shape.radius)}).at({_fmt(center[0])}, {_fmt(center[1])})"
        return f"Circle(radius={_fmt(shape.radius)})"
    elif isinstance(shape, ArcPolygon):
        lines = ["ArcPolygon(["]
        for elem in shape.elements:
            if isinstance(elem, tuple):
                lines.append(f"{prefix}    {_point_to_code(elem)},")
            elif isinstance(elem, Arc):
                lines.append(f"{prefix}    {_arc_to_code(elem)},")
            else:
                lines.append(f"{prefix}    # Unknown: {type(elem).__name__}")
        lines.append(f"{prefix}])")
        return "\n".join(lines)
    elif isinstance(shape, Polygon):
        lines = ["Polygon(["]
        for p in shape.elements:
            lines.append(f"{prefix}    {_point_to_code(p)},")
        lines.append(f"{prefix}])")
        return "\n".join(lines)
    else:
        return shape_to_python_code(shape)


def determine_layer_set(layers_str: str) -> str:
    """Determine LayerSet specification from EMN layer string"""
    if not layers_str or layers_str.upper() in ["", "ALL", "BOTH"]:
        return "LayerSet.all()"
    elif layers_str.upper() in ["TOP", "COMPONENT"]:
        return "LayerSet(0)"
    elif layers_str.upper() in ["BOTTOM", "SOLDER"]:
        return "LayerSet(-1)"
    else:
        return "LayerSet.all()"


def _generate_feature_code(idf: IdfFile) -> dict[str, list[str]]:
    """Generate categorized feature code strings from IDF data.

    Returns a dict with keys: cutouts, route_keepouts, via_keepouts,
    place_keepouts, notes, placement. Each value is a list of Python
    code strings (one per feature, no leading indent).
    """
    result: dict[str, list[str]] = {
        "cutouts": [],
        "route_keepouts": [],
        "via_keepouts": [],
        "place_keepouts": [],
        "notes": [],
        "placement": [],
    }

    # Board cutouts
    for cutout in idf.board_cutouts:
        shape_code = shape_to_python_code(cutout)
        result["cutouts"].append(f"Cutout({shape_code})")

    # Holes as cutouts
    for hole in idf.holes:
        r = _fmt(hole.dia * 0.5)
        result["cutouts"].append(f"Cutout(Circle(radius={r}).at({_fmt(hole.x)}, {_fmt(hole.y)}))")

    # Route keepouts
    for keepout in idf.route_keepouts:
        layer_set = determine_layer_set(keepout.layers)
        shape_code = shape_to_python_code(keepout.outline)
        result["route_keepouts"].append(
            f"KeepOut({shape_code}, layers={layer_set}, pour=True, via=False)"
        )

    # Via keepouts
    for keepout in idf.via_keepouts:
        shape_code = shape_to_python_code(keepout.outline)
        result["via_keepouts"].append(
            f"KeepOut({shape_code}, layers=LayerSet.all(), pour=False, via=True)"
        )

    # Place keepouts
    for keepout in idf.place_keepouts:
        shape_code = shape_to_python_code(keepout.outline)
        result["place_keepouts"].append(f'Custom({shape_code}, name="Placement Keepout")')

    # Notes
    for note in idf.notes:
        text = note.text.replace(chr(1), "").replace(chr(2), "")
        text_escaped = text.replace('"', '\\"')
        h = _fmt(note.height)
        x = _fmt(note.x)
        y = _fmt(note.y)
        result["notes"].append(
            f'Custom(Text("{text_escaped}", size={h}, anchor=Anchor.SW).at({x}, {y}),'
            f' name="Assembly Notes")'
        )

    # Placement markers
    for part in idf.placement:
        ref_escaped = part.refdes.replace('"', '\\"')
        x = _fmt(part.x)
        y = _fmt(part.y)
        result["placement"].append(
            f'Custom(Text("{ref_escaped}", size=1.0, anchor=Anchor.C).at({x}, {y}),'
            f' name="Component Placement")'
        )

    return result


def _write_feature_list(output: StringIO, items: list[str], attr_name: str, indent: str) -> None:
    """Write a list of feature code strings as a self.attr assignment."""
    if not items:
        return
    if len(items) == 1:
        output.write(f"{indent}self.{attr_name} = [{items[0]}]\n")
    else:
        output.write(f"{indent}self.{attr_name} = [\n")
        for item in items:
            output.write(f"{indent}    {item},\n")
        output.write(f"{indent}]\n")


def import_emn(emn_filename: str, class_name: str, output_filename: str) -> None:
    """
    Import EMN/IDF file and generate a complete JITX Design (Board + Circuit + Design).

    Args:
        emn_filename: Path to the EMN/IDF file to import
        class_name: Name prefix for the generated classes
        output_filename: Output Python file path
    """
    idf = idf_parser(emn_filename)
    clean_class = sanitize_identifier(class_name)
    features = _generate_feature_code(idf)

    output = StringIO()

    # Header and imports
    output.write(f'"""\nGenerated JITX Design from EMN/IDF import: {clean_class}\n"""\n\n')
    output.write("from jitx.anchor import Anchor\n")
    output.write("from jitx.board import Board\n")
    output.write("from jitx.circuit import Circuit\n")
    output.write("from jitx.design import Design\n")
    output.write("from jitx.feature import Custom, Cutout, KeepOut\n")
    output.write("from jitx.layerindex import LayerSet\n")
    output.write("from jitx.shapes.primitive import Arc, ArcPolygon, Circle, Polygon, Text\n")
    output.write("\n\n")

    # Board class with multi-line shape
    output.write(f"class {clean_class}Board(Board):\n")
    shape_code = shape_to_multiline_code(idf.board_outline, indent=1)
    output.write(f"    shape = {shape_code}\n")
    output.write("\n\n")

    # Circuit class with categorized features
    output.write(f"class {clean_class}Circuit(Circuit):\n")
    output.write("    def __init__(self):\n")
    output.write("        super().__init__()\n")

    ind = "        "
    has_features = False

    if features["cutouts"]:
        output.write(f"\n{ind}# Board cutouts and drilled holes\n")
        _write_feature_list(output, features["cutouts"], "cutouts", ind)
        has_features = True

    if features["route_keepouts"]:
        output.write(f"\n{ind}# Route keepouts (copper pour restrictions)\n")
        _write_feature_list(output, features["route_keepouts"], "route_keepouts", ind)
        has_features = True

    if features["via_keepouts"]:
        output.write(f"\n{ind}# Via keepouts\n")
        _write_feature_list(output, features["via_keepouts"], "via_keepouts", ind)
        has_features = True

    if features["place_keepouts"]:
        output.write(f"\n{ind}# Placement keepouts\n")
        _write_feature_list(output, features["place_keepouts"], "place_keepouts", ind)
        has_features = True

    if features["notes"]:
        output.write(f"\n{ind}# Assembly notes\n")
        _write_feature_list(output, features["notes"], "notes", ind)
        has_features = True

    if features["placement"]:
        output.write(f"\n{ind}# Component placement markers\n")
        _write_feature_list(output, features["placement"], "placement_markers", ind)
        has_features = True

    if not has_features:
        output.write(f"{ind}pass\n")

    output.write("\n\n")

    # Design class
    output.write(f"class {clean_class}Design(Design):\n")
    output.write(f"    board = {clean_class}Board()\n")
    output.write(f"    circuit = {clean_class}Circuit()\n")

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
    Convert parsed EMN data to actual JITX feature objects (not code strings).
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
        if route_keepout.layers.upper() in ("TOP", "COMPONENT"):
            layer_set = LayerSet(0)
        elif route_keepout.layers.upper() in ("BOTTOM", "SOLDER"):
            layer_set = LayerSet(-1)
        else:
            layer_set = LayerSet.all()

        features.append(KeepOut(route_keepout.outline, layers=layer_set, pour=True, via=False))

    # Via keepouts
    for via_keepout in idf_file.via_keepouts:
        features.append(
            KeepOut(
                via_keepout.outline,
                layers=LayerSet.all(),
                pour=False,
                via=True,
            )
        )

    # Place keepouts
    for place_keepout in idf_file.place_keepouts:
        features.append(Custom(place_keepout.outline, name="Placement Keepout"))

    # Notes
    for note in idf_file.notes:
        text = note.text.replace(chr(1), "").replace(chr(2), "")
        text_shape = Text(text, size=note.height, anchor=Anchor.SW)
        if hasattr(text_shape, "at"):
            text_shape = text_shape.at(note.x, note.y)
        features.append(Custom(text_shape, name="Assembly Notes"))

    # Placement markers
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
    parser.add_argument("class_name", help="Name prefix for the generated classes")
    parser.add_argument("output_file", help="Output Python file path")

    args = parser.parse_args()
    import_emn(args.emn_file, args.class_name, args.output_file)


if __name__ == "__main__":
    main()
