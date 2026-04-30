"""JITX EMN/IDF importer: parses CAD mechanical exports into JITX Board/Circuit/Design classes.

See the README for usage. Public API is enumerated in ``__all__`` below.
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
