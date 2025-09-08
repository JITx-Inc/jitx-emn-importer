#!/usr/bin/env python3
"""
Simple test script for the EMN importer that works without JITX Python installed.
This demonstrates the parsing capabilities and shows generated code structure.
"""

import sys
import os
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from idf_parser import idf_parser, IdfFile
from emn_importer import import_emn, import_emn_to_design_class


def create_test_emn():
    """Create a simple test EMN file"""
    test_content = """.HEADER
IDF_FILE 3.0 "Test System" "2024-01-01" 1 "Test Board" "MM"
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
.END_DRILLED_HOLES

.NOTES
15 25 1.5 12 "KEEP OUT AREA"
5 5 1.0 6 "TEST PT"
.END_NOTES

.PLACEMENT
"0603" "R0603_10K" "R1" 20 10 0 0 "TOP" "PLACED"
"SOIC8" "IC_OPAMP" "U1" 30 20 0 0 "TOP" "PLACED"
.END_PLACEMENT
"""
    
    with open("test_board.emn", "w") as f:
        f.write(test_content)
    
    return "test_board.emn"


def test_parsing():
    """Test the EMN parsing functionality"""
    print("🔍 Testing EMN Parser")
    print("=" * 40)
    
    # Create test file
    emn_file = create_test_emn()
    print(f"✓ Created test EMN file: {emn_file}")
    
    try:
        # Parse the EMN file
        idf_data = idf_parser(emn_file)
        
        print(f"✓ Successfully parsed EMN file!")
        print(f"  - File type: {idf_data.header.filetype}")
        print(f"  - Version: {idf_data.header.idf_version}")
        print(f"  - Units: {idf_data.header.units}")
        print(f"  - Board name: {idf_data.header.name}")
        print(f"  - Board outline type: {type(idf_data.board_outline).__name__}")
        print(f"  - Holes: {len(idf_data.holes)}")
        print(f"  - Notes: {len(idf_data.notes)}")
        print(f"  - Components: {len(idf_data.placement)}")
        
        # Show some details
        if idf_data.holes:
            hole = idf_data.holes[0]
            print(f"  - First hole: ⌀{hole.dia}mm at ({hole.x}, {hole.y})")
        
        if idf_data.notes:
            note = idf_data.notes[0]
            print(f"  - First note: '{note.text}' at ({note.x}, {note.y})")
        
        if idf_data.placement:
            part = idf_data.placement[0]
            print(f"  - First part: {part.refdes} ({part.package}) at ({part.x}, {part.y})")
        
        return idf_data
        
    except Exception as e:
        print(f"❌ Error parsing EMN file: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_code_generation():
    """Test the code generation functionality"""
    print("\n🏗️  Testing Code Generation")
    print("=" * 40)
    
    emn_file = "test_board.emn"
    
    try:
        # Generate helper functions
        print("📝 Generating helper functions...")
        import_emn(emn_file, "TestBoard", "test_board_helpers.py")
        print("✓ Generated test_board_helpers.py")
        
        # Show a snippet of generated content
        with open("test_board_helpers.py", "r") as f:
            lines = f.readlines()
        
        print("\n📄 Generated helper file preview (first 20 lines):")
        print("-" * 50)
        for i, line in enumerate(lines[:20], 1):
            print(f"{i:2d}: {line.rstrip()}")
        print("-" * 50)
        
        # Generate complete Design class
        print("\n📝 Generating complete Design class...")
        import_emn_to_design_class(emn_file, "TestBoard", "test_board_design.py")
        print("✓ Generated test_board_design.py")
        
        # Show a snippet of Design class
        with open("test_board_design.py", "r") as f:
            content = f.read()
        
        # Find the class definitions
        lines = content.split('\n')
        class_start = -1
        for i, line in enumerate(lines):
            if line.startswith('class TestBoardBoard(Board):'):
                class_start = i
                break
        
        if class_start >= 0:
            print(f"\n📄 Generated Design class preview (lines {class_start+1}-{class_start+15}):")
            print("-" * 50)
            for i in range(class_start, min(class_start + 15, len(lines))):
                print(f"{i+1:2d}: {lines[i]}")
            print("-" * 50)
        
        return True
        
    except Exception as e:
        print(f"❌ Error generating code: {e}")
        import traceback
        traceback.print_exc()
        return False


def cleanup():
    """Clean up test files"""
    files_to_remove = [
        "test_board.emn", 
        "test_board_helpers.py", 
        "test_board_design.py"
    ]
    
    removed = []
    for file in files_to_remove:
        try:
            os.remove(file)
            removed.append(file)
        except FileNotFoundError:
            pass
        except Exception as e:
            print(f"⚠️  Could not remove {file}: {e}")
    
    if removed:
        print(f"\n🧹 Cleaned up: {', '.join(removed)}")


def main():
    """Main test function"""
    print("🚀 JITX EMN/IDF Importer Test")
    print("=============================")
    
    # Test parsing
    idf_data = test_parsing()
    
    # Test code generation if parsing worked
    if idf_data:
        success = test_code_generation()
        
        if success:
            print("\n✅ All tests passed!")
            print("\n💡 The EMN importer successfully:")
            print("   • Parsed EMN file format")
            print("   • Extracted board geometry and features")  
            print("   • Generated JITX Python code")
            print("   • Created both helper functions and Design classes")
        else:
            print("\n⚠️  Parsing succeeded but code generation failed")
    else:
        print("\n❌ Tests failed - could not parse EMN file")
    
    # Cleanup
    cleanup()
    
    return 0 if idf_data else 1


if __name__ == "__main__":
    sys.exit(main())