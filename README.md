# JITX EMN/IDF Importer

A JITX Python library for importing EMN/IDF/BDF format files and converting them to JITX-compatible PCB design data. This library parses mechanical board outline data, cutouts, keepouts, holes, notes, and placement information from CAD exports and generates JITX Python geometry and layer specifications.

## Features

- **Complete EMN/IDF/BDF parsing**: Handles all standard sections including board outlines, cutouts, keepouts, holes, notes, and component placement
- **JITX Python compatibility**: Generates proper JITX Python layer specifications using Cutout, KeepOut, and Custom features
- **Flexible output formats**: Can generate standalone helper functions or complete JITX Design classes
- **Geometry conversion**: Converts EMN geometry (including arcs and complex polygons) to JITX primitive shapes
- **Unit handling**: Automatic conversion between THOU and MM units
- **Clean code generation**: Produces readable, well-commented Python code

## Installation

```bash
# Install from source (when package is available)
pip install jitx-emn-importer

# Or install directly from this directory
pip install -e .
```

## Usage

### Command Line Interface

```bash
# Generate helper functions
python -m emn_importer board.emn MyBoard output.py

# Generate complete Design class
python -m emn_importer board.emn MyBoard output.py --design-class
```

### Python API

```python
from jitx_emn_importer import import_emn, import_emn_to_design_class, idf_parser

# Parse EMN file to structured data
idf_data = idf_parser("board.emn")
print(f"Board has {len(idf_data.holes)} holes and {len(idf_data.notes)} notes")

# Generate helper functions
import_emn("board.emn", "MyBoard", "board_helpers.py")

# Generate complete Design class  
import_emn_to_design_class("board.emn", "MyBoard", "board_design.py")
```

### Generated Code Example

The library generates clean JITX Python code:

```python
"""
Generated JITX Python board definition from EMN/IDF import
Package: MyBoard
"""

from jitx import *
from jitx.shapes.primitive import Circle, Text, Polygon, ArcPolygon
from jitx.feature import Cutout, KeepOut, Custom
from jitx.layerindex import LayerSet, Side
from jitx.anchor import Anchor

# Board outline shape
emn_board_outline = Polygon([(0.0, 0.0), (100.0, 0.0), (100.0, 50.0), (0.0, 50.0)])

def emn_module():
    """Generated mechanical data from EMN/IDF import"""
    layer(Cutout(Circle(radius=1.0).at(10.0, 10.0)))
    layer(KeepOut(Circle(radius=5.0), layers=LayerSet.all(), pour=True, via=False))
    layer(Custom(Text("COMPONENT AREA", size=1.5, anchor=Anchor.SW).at(20.0, 30.0), name="Assembly Notes"))

# Example usage in a JITX design:
# 
# from jitx.board import Board
# from jitx.circuit import Circuit
# from jitx.design import Design
# 
# class MyBoard(Board):
#     shape = emn_board_outline
# 
# class MyCircuit(Circuit):
#     def __init__(self):
#         super().__init__()
#         emn_module()  # Add mechanical features
# 
# class MyDesign(Design):
#     board = MyBoard()
#     circuit = MyCircuit()
```

## Supported EMN/IDF Features

| Feature | EMN Section | JITX Output | Description |
|---------|-------------|-------------|-------------|
| Board Outline | `.BOARD_OUTLINE` | Board.shape | Main board perimeter |
| Board Cutouts | `.BOARD_OUTLINE` (cutouts) | `Cutout()` | Slots and complex cutouts |  
| Drilled Holes | `.DRILLED_HOLES` | `Cutout(Circle())` | Through holes |
| Route Keepouts | `.ROUTE_KEEPOUT` | `KeepOut(pour=True)` | Copper pour restrictions |
| Via Keepouts | `.VIA_KEEPOUT` | `KeepOut(via=True)` | Via placement restrictions |
| Place Keepouts | `.PLACE_KEEPOUT` | `Custom()` | Component placement guides |
| Notes | `.NOTES` | `Custom(Text())` | Assembly text annotations |
| Component Placement | `.PLACEMENT` | `Custom(Text())` | Component position markers |

## Architecture

The library consists of two main modules:

### idf_parser.py
- Low-level EMN/IDF file parsing
- Geometry conversion (arcs, circles, polygons)
- Unit conversion (THOU ↔ MM)
- Data structure definitions

### emn_importer.py  
- High-level import interface
- JITX Python code generation
- Layer specification mapping
- Design class templates

## Development

The library was ported from the original Stanza implementation to ensure compatibility with JITX Python while maintaining all parsing capabilities.

### Key Conversion Points:
- **Stanza → Python**: Converted functional Stanza code to object-oriented Python
- **Geometry**: Maps Stanza shapes to JITX Python primitive shapes  
- **Layers**: Converts Stanza layer specs to JITX Python feature classes
- **Code Generation**: Produces idiomatic Python instead of Stanza syntax

### Dependencies:
- JITX Python API (shapes, features, layer specifications)
- Python 3.8+ standard library

## Examples

See the `examples/` directory for sample EMN files and their generated outputs.

## Contributing

This library is part of the JITX ecosystem. For issues and contributions:
1. Check existing issues on GitHub
2. Follow JITX coding standards  
3. Include test cases for new features
4. Update documentation as needed

## License

This project is licensed under the MIT License - see the LICENSE file for details.