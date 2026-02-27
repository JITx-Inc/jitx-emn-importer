"""
JITX EMN/IDF Importer

A JITX Python library for importing EMN/IDF/BDF format files and converting them
to JITX-compatible PCB design data. Parses mechanical board outline data, cutouts,
keepouts, holes, notes, and placement information from CAD exports into JITX
Python geometry and layer specifications.

Main functions:
- import_emn: Import EMN file and generate Board + Circuit + Design classes
- idf_parser: Parse EMN/IDF file to structured data
- convert_emn_to_jitx_features: Convert parsed data to JITX feature objects
"""

from .emn_importer import (
    convert_emn_to_jitx_features,
    import_emn,
)
from .idf_parser import (
    IdfException,
    IdfFile,
    IdfHeader,
    IdfHole,
    IdfNote,
    IdfOutline,
    IdfPart,
    find_refdes,
    idf_parser,
)

__version__ = "1.0.0"
__author__ = "JITX Inc."
__description__ = "EMN/IDF importer for JITX Python"

__all__ = [
    # Parser classes and functions
    "IdfFile",
    "IdfHeader",
    "IdfOutline",
    "IdfHole",
    "IdfNote",
    "IdfPart",
    "IdfException",
    "idf_parser",
    "find_refdes",
    # Importer functions
    "import_emn",
    "convert_emn_to_jitx_features",
]
