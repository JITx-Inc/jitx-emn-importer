# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

The `jitx-emn-importer` is a JITX Python library for importing EMN/IDF/BDF format files and converting them to JITX PCB design data. It parses mechanical board outline data, cutouts, keepouts, holes, notes, and placement information from CAD exports and generates complete JITX Python Board + Circuit + Design classes.

## Installation and Usage

```bash
pip install -e .          # Install package (requires jitx>=4.0)
pip install -e ".[dev]"   # With dev dependencies (pytest, ruff, pyright)
```

The main entry point is `import_emn()` which generates a Python file containing:
- A `Board` subclass with the board outline shape
- A `Circuit` subclass with categorized mechanical features (cutouts, keepouts, notes, placement)
- A `Design` subclass wiring them together

```bash
emn-import board.emn MyBoard board_design.py
```

## Architecture

### File Structure
```
jitx_emn_importer/
├── __init__.py         # Package exports
├── idf_parser.py       # Core EMN/IDF parsing engine
└── emn_importer.py     # Code generation and JITX feature conversion
tests/
├── conftest.py         # Shared fixtures (inline EMN data)
├── test_idf_parser.py  # Parser unit tests
├── test_geometry.py    # Arc/polygon geometry tests
├── test_emn_importer.py # Code generation tests
└── test_real_emn_files.py # Integration tests against real EMN files
    fixtures/real_emn/  # Real EMN files (unzip testEMNs.zip)
```

### Core Components

1. **idf_parser.py**: Low-level EMN/IDF file parsing
   - `IdfParser` class: Tokenizer, section parser, geometry converter
   - `idf_parser(filename)` → `IdfFile`: Main entry point
   - Supports IDF 2.0 and 3.0 formats with automatic detection
   - Handles arcs, circles, polygons, unit conversion (THOU→MM)
   - Key data structures: `IdfFile`, `IdfOutline`, `IdfHole`, `IdfNote`, `IdfPart`

2. **emn_importer.py**: High-level import and code generation
   - `import_emn(emn_file, class_name, output_file)`: Generates Board + Circuit + Design classes
   - `convert_emn_to_jitx_features(idf_file)` → `list[Feature]`: Returns actual JITX objects
   - `shape_to_python_code(shape)`: Single-line shape serialization
   - `shape_to_multiline_code(shape, indent)`: Multi-line formatted output
   - `_fmt(value)`: Rounds coordinates to 4 decimal places
   - `_generate_feature_code(idf)`: Returns features categorized by type

### Data Flow

```
EMN/IDF File → IdfParser → IdfFile → import_emn() → Board/Circuit/Design Python file
                                    → convert_emn_to_jitx_features() → JITX Feature objects
```

### Generated Code Structure

Features are grouped by type in the Circuit class:
- `self.cutouts` — board cutouts + drilled holes
- `self.route_keepouts` — copper pour restrictions
- `self.via_keepouts` — via placement restrictions
- `self.place_keepouts` — component placement guides
- `self.notes` — assembly text annotations
- `self.placement_markers` — component position markers

### Dependencies

- `jitx>=4.0` — Required. Provides shape primitives (Arc, Circle, Polygon, ArcPolygon), feature classes (Cutout, KeepOut, Custom), and design classes (Board, Circuit, Design).
- No mock/fallback classes — the package requires a working JITX installation.

### JITX API Reference

- **Shapes**: `jitx.shapes.primitive` — Arc, ArcPolygon, Circle, Polygon, Text
- **Features**: `jitx.feature` — Cutout, KeepOut, Custom
- **Layers**: `jitx.layerindex` — LayerSet, Side
- **Arc attributes**: `arc.center`, `arc.radius`, `arc.start`, `arc.arc` (NOT `start_angle`/`sweep_angle`)
- **Circle constructor**: `Circle(radius=...)` (keyword-only)
- **JITX API Docs**: https://docs.jitx.com/

## Development

### Running Checks

```bash
pytest tests/ -v                        # Run tests
ruff format jitx_emn_importer/ tests/   # Format
ruff check jitx_emn_importer/ tests/    # Lint
pyright jitx_emn_importer/              # Type check
```

### Integration Tests

Real EMN file tests require fixture files:
1. Unzip `testEMNs.zip` into `tests/fixtures/real_emn/`
2. Tests in `test_real_emn_files.py` will automatically discover and run against all `.emn` files

### Tool Configuration

Configured in `pyproject.toml`:
- **ruff**: line-length 100, py312 target, E/F/I/W rules, E501 ignored in tests
- **pyright**: py312
- **pytest**: verbose, short tracebacks
