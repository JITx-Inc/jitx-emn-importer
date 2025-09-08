#!/usr/bin/env python3
"""
Example usage of the JITX EMN/IDF importer

This script demonstrates how to use the EMN importer to parse EMN files
and generate JITX Python code. Since we don't have actual JITX Python
installed, this shows the API usage and generated code structure.
"""

import sys
from pathlib import Path

# Mock JITX imports for demonstration (since JITX Python may not be installed)
class MockShape:
    pass

class MockCircle(MockShape):
    def __init__(self, radius=None, center=None):
        if center:
            self.center = center
            self.radius = radius
        else:
            self.radius = radius
            self.center = None
    
    def at(self, x, y):
        self.center = (x, y)
        return self
    
    def __repr__(self):
        if self.center:
            return f"Circle(radius={self.radius}).at({self.center[0]}, {self.center[1]})"
        return f"Circle(radius={self.radius})"

class MockPolygon(MockShape):
    def __init__(self, points):
        self.points = points
    
    def __repr__(self):
        points_str = ', '.join([f"({p[0]}, {p[1]})" for p in self.points])
        return f"Polygon([{points_str}])"

class MockArcPolygon(MockShape):
    def __init__(self, elements):
        self.elements = elements
    
    def __repr__(self):
        return f"ArcPolygon({len(self.elements)} elements)"

class MockText(MockShape):
    def __init__(self, text, size=1.0, anchor=None):
        self.text = text
        self.size = size
        self.anchor = anchor
        self.position = None
    
    def at(self, x, y):
        self.position = (x, y)
        return self
    
    def __repr__(self):
        result = f'Text("{self.text}", size={self.size}'
        if self.anchor:
            result += f', anchor={self.anchor}'
        result += ')'
        if self.position:
            result += f'.at({self.position[0]}, {self.position[1]})'
        return result

class MockArc(MockShape):
    def __init__(self, center, radius, start, arc):
        self.center = center
        self.radius = radius
        self.start = start
        self.arc = arc
    
    def __repr__(self):
        return f"Arc({self.center}, {self.radius}, {self.start}, {self.arc})"

# Mock the JITX modules
import sys
from types import ModuleType

# Create mock modules
mock_shapes = ModuleType('jitx.shapes.primitive')
mock_shapes.Circle = MockCircle
mock_shapes.Polygon = MockPolygon
mock_shapes.ArcPolygon = MockArcPolygon 
mock_shapes.Arc = MockArc
mock_shapes.Text = MockText

mock_feature = ModuleType('jitx.feature')
mock_layerindex = ModuleType('jitx.layerindex')
mock_anchor = ModuleType('jitx.anchor')

# Add them to sys.modules
sys.modules['jitx.shapes.primitive'] = mock_shapes
sys.modules['jitx.feature'] = mock_feature
sys.modules['jitx.layerindex'] = mock_layerindex
sys.modules['jitx.anchor'] = mock_anchor

# Now import our modules
try:
    from idf_parser import idf_parser, IdfFile
    from emn_importer import import_emn, import_emn_to_design_class
except ImportError as e:
    print(f"Import error: {e}")
    print("This example script should be run from the dev_python directory")
    sys.exit(1)


def create_sample_emn_file():
    """Create a simple sample EMN file for testing"""
    sample_content = """.HEADER
IDF_FILE 3.0 "Test System" "2024-01-01" 1 "Sample Board" "MM"
.END_HEADER

.BOARD_OUTLINE "JITX_OWNER" 1.6
0 0 0 0
0 100 0 0  
0 100 50 0
0 0 50 0
0 0 0 0
.END_BOARD_OUTLINE

.DRILLED_HOLES
3.0 10 10 "PTH" "VIA" "THRU" "OWNER1"
2.0 90 40 "PTH" "VIA" "THRU" "OWNER1" 
.END_DRILLED_HOLES

.NOTES
20 30 2.0 15 "COMPONENT AREA"
10 45 1.0 8 "TEST POINT"
.END_NOTES

.PLACEMENT
"0805" "R0805_100K" "R1" 25 15 0 0 "TOP" "PLACED"
"SOT23" "BC847" "Q1" 75 35 0 90 "TOP" "PLACED"
.END_PLACEMENT
"""
    
    with open("sample.emn", "w") as f:
        f.write(sample_content)
    
    return "sample.emn"


def demonstrate_parser():
    """Demonstrate the IDF parser functionality"""
    print("=== IDF Parser Demo ===")
    
    emn_file = create_sample_emn_file()
    print(f"Created sample EMN file: {emn_file}")
    
    try:
        # Parse the file
        idf_data = idf_parser(emn_file)
        
        print(f"\nParsed EMN file successfully!")
        print(f"Header: {idf_data.header.filetype} v{idf_data.header.idf_version}")
        print(f"Units: {idf_data.header.units}")
        print(f"Board name: {idf_data.header.name}")
        
        print(f"\nBoard outline: {type(idf_data.board_outline).__name__}")
        print(f"Board cutouts: {len(idf_data.board_cutouts)}")
        print(f"Holes: {len(idf_data.holes)}")
        print(f"Notes: {len(idf_data.notes)}")
        print(f"Components: {len(idf_data.placement)}")
        
        # Show some details
        if idf_data.holes:
            print(f"\nFirst hole: {idf_data.holes[0].dia}mm at ({idf_data.holes[0].x}, {idf_data.holes[0].y})")
        
        if idf_data.notes:
            print(f"First note: '{idf_data.notes[0].text}' at ({idf_data.notes[0].x}, {idf_data.notes[0].y})")
        
        if idf_data.placement:
            part = idf_data.placement[0]
            print(f"First component: {part.refdes} ({part.package}) at ({part.x}, {part.y})")
        
        return idf_data
        
    except Exception as e:
        print(f"Error parsing EMN file: {e}")
        return None


def demonstrate_code_generation():
    """Demonstrate code generation functionality"""
    print("\n\n=== Code Generation Demo ===")
    
    emn_file = "sample.emn"
    
    try:
        # Generate helper functions
        print("Generating helper functions...")
        import_emn(emn_file, "SampleBoard", "sample_board_helpers.py")
        
        # Show generated content
        with open("sample_board_helpers.py", "r") as f:
            content = f.read()
            
        print(f"\nGenerated helper functions ({len(content)} characters):")
        print("=" * 50)
        print(content)
        print("=" * 50)
        
        # Generate Design class
        print("\n\nGenerating complete Design class...")
        import_emn_to_design_class(emn_file, "SampleBoard", "sample_board_design.py")
        
        # Show generated content
        with open("sample_board_design.py", "r") as f:
            content = f.read()
            
        print(f"\nGenerated Design class ({len(content)} characters):")
        print("=" * 50)
        print(content)
        print("=" * 50)
        
    except Exception as e:
        print(f"Error generating code: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Main demonstration function"""
    print("JITX EMN/IDF Importer - Example Usage")
    print("=====================================")
    
    # Demonstrate parsing
    idf_data = demonstrate_parser()
    
    if idf_data:
        # Demonstrate code generation
        demonstrate_code_generation()
    
    # Clean up
    import os
    try:
        os.remove("sample.emn")
        os.remove("sample_board_helpers.py") 
        os.remove("sample_board_design.py")
        print("\nCleaned up temporary files.")
    except:
        pass
    
    print("\nDemo completed!")


if __name__ == "__main__":
    main()