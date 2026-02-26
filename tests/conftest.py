"""
Pytest fixtures for jitx_emn_importer tests
"""

from pathlib import Path

import pytest


@pytest.fixture
def real_emn_dir():
    """Path to the directory containing real-world EMN test files"""
    path = Path(__file__).parent / "fixtures" / "real_emn"
    if not path.exists():
        pytest.skip("Real EMN fixtures not available (unzip testEMNs.zip)")
    return path


@pytest.fixture
def simple_emn_content():
    """Simple rectangular board EMN content in MM units"""
    return """.HEADER
IDF_FILE 3.0 "Test System" "2024-01-01" 1 "TestBoard" "MM"
.END_HEADER

.BOARD_OUTLINE "TEST_OWNER" 1.6
0 0 0 0
0 100 0 0
0 100 50 0
0 0 50 0
0 0 0 0
.END_BOARD_OUTLINE
"""


@pytest.fixture
def emn_with_holes():
    """EMN content with drilled holes"""
    return """.HEADER
IDF_FILE 3.0 "Test System" "2024-01-01" 1 "TestBoard" "MM"
.END_HEADER

.BOARD_OUTLINE "TEST_OWNER" 1.6
0 0 0 0
0 50 0 0
0 50 30 0
0 0 30 0
0 0 0 0
.END_BOARD_OUTLINE

.DRILLED_HOLES
2.0 10 10 "PTH" "VIA" "THRU" "OWNER1"
1.5 40 20 "PTH" "VIA" "THRU" "OWNER1"
3.0 25 15 "NPTH" "MTG" "THRU" "OWNER2"
.END_DRILLED_HOLES
"""


@pytest.fixture
def emn_with_notes():
    """EMN content with text annotations"""
    return """.HEADER
IDF_FILE 3.0 "Test System" "2024-01-01" 1 "TestBoard" "MM"
.END_HEADER

.BOARD_OUTLINE "TEST_OWNER" 1.6
0 0 0 0
0 50 0 0
0 50 30 0
0 0 30 0
0 0 0 0
.END_BOARD_OUTLINE

.NOTES
15 25 1.5 12 "KEEP OUT AREA"
5 5 1.0 6 "TEST PT"
30 15 2.0 10 "REV A"
.END_NOTES
"""


@pytest.fixture
def emn_with_placement():
    """EMN content with component placement"""
    return """.HEADER
IDF_FILE 3.0 "Test System" "2024-01-01" 1 "TestBoard" "MM"
.END_HEADER

.BOARD_OUTLINE "TEST_OWNER" 1.6
0 0 0 0
0 50 0 0
0 50 30 0
0 0 30 0
0 0 0 0
.END_BOARD_OUTLINE

.PLACEMENT
"0603" "R0603_10K" "R1" 20 10 0 0 "TOP" "PLACED"
"SOIC8" "IC_OPAMP" "U1" 30 20 0 0 "TOP" "PLACED"
"0402" "C0402_100NF" "C1" 15 8 0 90 "BOTTOM" "PLACED"
.END_PLACEMENT
"""


@pytest.fixture
def emn_with_arcs():
    """EMN content with arc segments (rounded corners)"""
    return """.HEADER
IDF_FILE 3.0 "Test System" "2024-01-01" 1 "TestBoard" "MM"
.END_HEADER

.BOARD_OUTLINE "TEST_OWNER" 1.6
0 0 0 0
0 45 0 0
0 50 5 90
0 50 25 0
0 45 30 90
0 5 30 0
0 0 25 90
0 0 5 0
0 5 0 90
0 0 0 0
.END_BOARD_OUTLINE
"""


@pytest.fixture
def emn_thou_units():
    """EMN content with THOU (mils) units"""
    return """.HEADER
IDF_FILE 3.0 "Test System" "2024-01-01" 1 "TestBoard" "THOU"
.END_HEADER

.BOARD_OUTLINE "TEST_OWNER" 63
0 0 0 0
0 4000 0 0
0 4000 2000 0
0 0 2000 0
0 0 0 0
.END_BOARD_OUTLINE
"""


@pytest.fixture
def emn_with_cutout():
    """EMN content with board cutout"""
    return """.HEADER
IDF_FILE 3.0 "Test System" "2024-01-01" 1 "TestBoard" "MM"
.END_HEADER

.BOARD_OUTLINE "TEST_OWNER" 1.6
0 0 0 0
0 100 0 0
0 100 50 0
0 0 50 0
0 0 0 0
1 40 20 0
1 60 20 0
1 60 30 0
1 40 30 0
1 40 20 0
.END_BOARD_OUTLINE
"""


@pytest.fixture
def emn_with_keepouts():
    """EMN content with route and via keepouts"""
    return """.HEADER
IDF_FILE 3.0 "Test System" "2024-01-01" 1 "TestBoard" "MM"
.END_HEADER

.BOARD_OUTLINE "TEST_OWNER" 1.6
0 0 0 0
0 100 0 0
0 100 50 0
0 0 50 0
0 0 0 0
.END_BOARD_OUTLINE

.ROUTE_KEEPOUT "OWNER" "TOP"
0 10 10 0
0 20 10 0
0 20 20 0
0 10 20 0
0 10 10 0
.END_ROUTE_KEEPOUT

.VIA_KEEPOUT "OWNER"
0 50 25 0
0 60 25 0
0 60 35 0
0 50 35 0
0 50 25 0
.END_VIA_KEEPOUT
"""


@pytest.fixture
def emn_with_circle():
    """EMN content with a circular feature (360-degree arc)"""
    return """.HEADER
IDF_FILE 3.0 "Test System" "2024-01-01" 1 "TestBoard" "MM"
.END_HEADER

.BOARD_OUTLINE "TEST_OWNER" 1.6
0 0 25 0
0 50 25 360
.END_BOARD_OUTLINE
"""


@pytest.fixture
def emn_complete():
    """Complete EMN file with all feature types"""
    return """.HEADER
IDF_FILE 3.0 "Test System" "2024-01-01" 1 "TestBoard" "MM"
.END_HEADER

.BOARD_OUTLINE "TEST_OWNER" 1.6
0 0 0 0
0 100 0 0
0 100 50 0
0 0 50 0
0 0 0 0
.END_BOARD_OUTLINE

.DRILLED_HOLES
2.0 10 10 "PTH" "VIA" "THRU" "OWNER1"
1.5 90 40 "PTH" "VIA" "THRU" "OWNER1"
.END_DRILLED_HOLES

.NOTES
50 25 2.0 15 "CENTER NOTE"
.END_NOTES

.PLACEMENT
"0603" "R0603_10K" "R1" 20 10 0 0 "TOP" "PLACED"
"SOIC8" "IC_OPAMP" "U1" 70 30 0 0 "TOP" "PLACED"
.END_PLACEMENT

.ROUTE_KEEPOUT "OWNER" "ALL"
0 30 30 0
0 40 30 0
0 40 40 0
0 30 40 0
0 30 30 0
.END_ROUTE_KEEPOUT
"""


@pytest.fixture
def temp_emn_file(tmp_path, simple_emn_content):
    """Create a temporary EMN file with simple content"""
    emn_file = tmp_path / "test.emn"
    emn_file.write_text(simple_emn_content)
    return emn_file


@pytest.fixture
def temp_emn_file_with_holes(tmp_path, emn_with_holes):
    """Create a temporary EMN file with holes"""
    emn_file = tmp_path / "test_holes.emn"
    emn_file.write_text(emn_with_holes)
    return emn_file


@pytest.fixture
def temp_emn_file_with_arcs(tmp_path, emn_with_arcs):
    """Create a temporary EMN file with arcs"""
    emn_file = tmp_path / "test_arcs.emn"
    emn_file.write_text(emn_with_arcs)
    return emn_file


@pytest.fixture
def temp_emn_file_thou(tmp_path, emn_thou_units):
    """Create a temporary EMN file with THOU units"""
    emn_file = tmp_path / "test_thou.emn"
    emn_file.write_text(emn_thou_units)
    return emn_file


@pytest.fixture
def temp_emn_complete(tmp_path, emn_complete):
    """Create a temporary EMN file with all features"""
    emn_file = tmp_path / "test_complete.emn"
    emn_file.write_text(emn_complete)
    return emn_file
