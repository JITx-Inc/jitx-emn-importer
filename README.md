# JITX EMN/IDF Importer

A JITX Python library for importing EMN/IDF/BDF format files and converting them to JITX-compatible PCB design data. This library parses mechanical board outline data, cutouts, keepouts, holes, notes, and placement information from CAD exports and generates complete JITX Python Board + Circuit + Design classes.

## Features

- **Complete EMN/IDF/BDF parsing**: Handles all standard sections including board outlines, cutouts, keepouts, holes, notes, and component placement
- **IDF 2.0 and 3.0 support**: Parses both IDF format versions with automatic detection
- **JITX Python compatibility**: Generates proper JITX Python classes using Cutout, KeepOut, and Custom features
- **Geometry conversion**: Converts EMN geometry (including arcs and complex polygons) to JITX primitive shapes
- **Unit handling**: Automatic conversion between THOU and MM units
- **Readable output**: Multi-line formatted shapes, rounded coordinates (4 decimal places), and features grouped by type

## Installation

```bash
# Install from source
pip install -e .

# Or with development dependencies
pip install -e ".[dev]"
```

Requires `jitx>=4.0` (installed automatically as a dependency).

## Usage

### Command Line Interface

```bash
# Generate Board + Circuit + Design classes
emn-import board.emn MyBoard output.py

# Or use as a Python module
python -m jitx_emn_importer.emn_importer board.emn MyBoard output.py
```

### Python API

```python
from jitx_emn_importer import import_emn, idf_parser

# Parse EMN file to structured data
idf_data = idf_parser("board.emn")
print(f"Board has {len(idf_data.holes)} holes and {len(idf_data.notes)} notes")

# Generate complete Design classes
import_emn("board.emn", "MyBoard", "board_design.py")
```

### Generated Code Example

The library generates clean, readable JITX Python code:

```python
"""
Generated JITX Design from EMN/IDF import: MyBoard
"""

from jitx.anchor import Anchor
from jitx.board import Board
from jitx.circuit import Circuit
from jitx.design import Design
from jitx.feature import Custom, Cutout, KeepOut
from jitx.layerindex import LayerSet
from jitx.shapes.primitive import Arc, ArcPolygon, Circle, Polygon, Text


class MyBoardBoard(Board):
    shape = Polygon([
        (0.0, 0.0),
        (100.0, 0.0),
        (100.0, 50.0),
        (0.0, 50.0),
        (0.0, 0.0),
    ])


class MyBoardCircuit(Circuit):
    def __init__(self):
        super().__init__()

        # Board cutouts and drilled holes
        self.cutouts = [
            Cutout(Circle(radius=1.0).at(10.0, 10.0)),
        ]

        # Route keepouts (copper pour restrictions)
        self.route_keepouts = [
            KeepOut(Circle(radius=5.0), layers=LayerSet.all(), pour=True, via=False),
        ]

        # Assembly notes
        self.notes = [
            Custom(Text("COMPONENT AREA", size=1.5, anchor=Anchor.SW).at(20.0, 30.0), name="Assembly Notes"),
        ]


class MyBoardDesign(Design):
    board = MyBoardBoard()
    circuit = MyBoardCircuit()
```

### Programmatic Feature Access

For direct access to JITX feature objects (without code generation):

```python
from jitx_emn_importer import idf_parser, convert_emn_to_jitx_features

idf = idf_parser("board.emn")
features = convert_emn_to_jitx_features(idf)

# Use features directly in a Circuit
from jitx.circuit import Circuit

class MyCircuit(Circuit):
    def __init__(self):
        super().__init__()
        self.mechanical = features
```

## Supported EMN/IDF Features

| Feature | EMN Section | JITX Output | Description |
|---------|-------------|-------------|-------------|
| Board Outline | `.BOARD_OUTLINE` | `Board.shape` | Main board perimeter |
| Panel Outline | `.PANEL_OUTLINE` | `Board.shape` | Panel board perimeter |
| Board Cutouts | `.BOARD_OUTLINE` (cutouts) | `Cutout()` | Slots and complex cutouts |
| Drilled Holes | `.DRILLED_HOLES` | `Cutout(Circle())` | Through holes |
| Route Keepouts | `.ROUTE_KEEPOUT` | `KeepOut(pour=True)` | Copper pour restrictions |
| Via Keepouts | `.VIA_KEEPOUT` | `KeepOut(via=True)` | Via placement restrictions |
| Place Keepouts | `.PLACE_KEEPOUT` | `Custom()` | Component placement guides |
| Place Outlines | `.PLACE_OUTLINE` | Parsed (IdfOutline) | Component placement areas |
| Notes | `.NOTES` | `Custom(Text())` | Assembly text annotations |
| Component Placement | `.PLACEMENT` | `Custom(Text())` | Component position markers |

## Architecture

The library consists of two main modules:

### idf_parser.py
- Low-level EMN/IDF file parsing (IDF 2.0 and 3.0)
- Geometry conversion (arcs, circles, polygons)
- Unit conversion (THOU to MM)
- Data structure definitions

### emn_importer.py
- High-level import interface
- JITX Python code generation (Board + Circuit + Design classes)
- Multi-line shape formatting with coordinate rounding
- Feature categorization (cutouts, keepouts by type, notes, placement)

## Development

### Dependencies
- `jitx>=4.0` — JITX Python API (shapes, features, layer specifications)
- Python 3.12+

### Running Tests

```bash
# Install with development dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Format and lint
ruff format jitx_emn_importer/ tests/
ruff check jitx_emn_importer/ tests/

# Type check
pyright jitx_emn_importer/
```

### Integration Tests

Real-world EMN file tests require fixture files. Unzip `testEMNs.zip` into `tests/fixtures/real_emn/` to enable them.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
