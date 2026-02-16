# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

The `jitx-emn-importer` is a JITX library for importing EMN/IDF/BDF format files and converting them to JITX PCB design data. It parses mechanical board outline data, cutouts, keepouts, holes, notes, and placement information from CAD exports into JITX-compatible geometry.

## Installation and Usage

This is a JITX package managed by SLM (JITX package manager). Users install it via:
```
$SLM add -git JITx-Inc/jitx-emn-importer
```

The main entry point is the `import-emn` function which generates a `board.stanza` file containing:
- `emn-board-outline`: Board boundary geometry for use in `pcb-board` definitions
- `emn-module()`: Function containing mechanical data (cutouts, text, etc.) for instantiation in PCB modules

## Architecture

### Core Components

1. **idf-parser.stanza** (`src/idf-parser.stanza:1-417`): 
   - Low-level EMN/IDF file parsing engine
   - Defines data structures for IDF format elements (headers, outlines, holes, notes, placement)
   - Contains geometry conversion logic for arcs, circles, and polygons
   - Handles unit conversion (THOU to mm, MM units)
   - Main parsing function: `IdfParser(filename:String) -> IdfFile`

2. **emn-importer.stanza** (`src/emn-importer.stanza:1-74`):
   - High-level import interface 
   - Converts parsed IDF data to JITX layer specifications
   - Generates Stanza code output for board definitions
   - Main function: `import-emn(emn-filename, package-name, output-stanza-filename)`

### Data Flow

```
EMN/IDF File → IdfParser → IdfFile struct → Layer conversions → Generated Stanza code
```

### Key Data Structures

- `IdfFile`: Complete parsed IDF data including board outlines, cutouts, holes, notes, placement
- `IdfOutline`: Board/panel outlines and keepout regions with geometry and layer info  
- `IdfHole`: Drilled hole specifications with position and plating info
- `IdfNote`: Text annotations with position and formatting
- `IdfPart`: Component placement data with position, rotation, and side
- `Layer`: JITX layer specification pairing LayerIndex/LayerSpecifier with Shape geometry

### Geometry Handling

The parser handles complex EMN geometry including:
- Polygons with arc segments (`PolygonWithArcs`)
- Full circles (360-degree arcs)
- Arc calculations with center point derivation from chord and sweep angle
- Unit conversion between THOU and MM coordinate systems

## Development

### File Structure
```
src/
├── idf-parser.stanza    # Core EMN/IDF parsing logic
└── emn-importer.stanza  # High-level import interface
```

### Key Functions

**Parser Functions (`idf-parser.stanza`)**:
- `IdfParser(filename:String)`: Main parser entry point
- `loopt_PolygonWithArcs()`: Converts EMN loop data to JITX geometry
- `findarefdes()`: Finds component by reference designator

**Import Functions (`emn-importer.stanza`)**:
- `import-emn()`: Main import interface, generates output Stanza file
- Layer conversion functions for different EMN data types

### Dependencies

The project uses JITX standard libraries:
- `jitx`: Core JITX functionality
- `jitx/layer-specs`: Layer specification types
- `jitx/geometry/*`: Geometry utilities for arcs and measurements

### References

- **python-refs/**: Directory containing important Python syntax references for JITX development
- **JITX API Documentation**: https://docs-dev.jitx.com/en/0.1.3.dev421+g92ed63806/api/modules.html

### Testing

No automated test framework is present. Testing is done via the JITX REPL:
```
stanza> import emn-importer  
stanza> import-emn("test.emn", "test-package", "board.stanza")
```

Generated files can be validated by importing them into JITX projects and checking geometry rendering.