"""
JITX EMN/IDF Importer

A JITX Python library for importing EMN/IDF/BDF format files and converting them 
to JITX-compatible PCB design data. Parses mechanical board outline data, cutouts, 
keepouts, holes, notes, and placement information from CAD exports into JITX 
Python geometry and layer specifications.

Main functions:
- import_emn: Import EMN file and generate Python helper functions
- import_emn_to_design_class: Import EMN file and generate complete Design class
- idf_parser: Parse EMN/IDF file to structured data
- convert_emn_to_jitx_features: Convert parsed data to JITX feature objects
"""

from .idf_parser import (
    IdfFile,
    IdfHeader, 
    IdfOutline,
    IdfHole,
    IdfNote,
    IdfPart,
    IdfException,
    idf_parser,
    find_refdes
)

from .emn_importer import (
    import_emn,
    import_emn_to_design_class,
    convert_emn_to_jitx_features,
    generate_board_python_code
)

__version__ = "1.0.0"
__author__ = "JITX Inc."
__description__ = "EMN/IDF importer for JITX Python"

__all__ = [
    # Parser classes and functions
    "IdfFile", "IdfHeader", "IdfOutline", "IdfHole", "IdfNote", "IdfPart",
    "IdfException", "idf_parser", "find_refdes",
    
    # Importer functions  
    "import_emn", "import_emn_to_design_class", 
    "convert_emn_to_jitx_features", "generate_board_python_code"
]