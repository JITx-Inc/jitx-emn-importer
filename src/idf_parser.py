"""
IDF/EMN Parser for JITX Python

Converts EMN/IDF/BDF format files to JITX-compatible geometry data structures.
Parses mechanical board outline data, cutouts, keepouts, holes, notes, and placement information.

Port from Stanza idf-parser.stanza to Python for use with JITX Python API.
"""

from dataclasses import dataclass
from typing import List, Tuple, Union, Optional
import math

from jitx.shapes.primitive import Circle, Arc, Polygon, ArcPolygon


class IdfException(Exception):
    """Exception for IDF parsing errors"""
    pass


@dataclass
class IdfHeader:
    """IDF file header information"""
    filetype: str
    idf_version: float
    source_system: str
    date: str
    version: int
    name: str
    units: str


@dataclass
class IdfOutline:
    """IDF outline (board, panel, keepout, etc.)"""
    owner: str
    ident: str  # board/panel/route/place_outline identifier or keepout identifier
    thickness: float  # height field for place outlines, 0.0 for no depth
    layers: str  # side for place outlines/keepouts, empty for via keepouts or board outline
    outline: Union[Polygon, ArcPolygon, Circle]
    cutouts: List[Union[Polygon, ArcPolygon, Circle]]


@dataclass
class IdfHole:
    """IDF drilled hole specification"""
    dia: float
    x: float
    y: float
    plating: str
    assoc: str
    type: str
    owner: str


@dataclass
class IdfNote:
    """IDF text annotation"""
    x: float
    y: float
    height: float
    length: float
    text: str


@dataclass
class IdfPart:
    """IDF component placement data"""
    package: str
    partnumber: str
    refdes: str
    x: float
    y: float
    offset: float
    angle: float
    side: str
    status: str


@dataclass
class IdfPlacement:
    """IDF placement group"""
    ident: str
    parts: List[IdfPart]


@dataclass
class IdfFile:
    """Complete parsed IDF file data"""
    header: IdfHeader
    board_outline: Union[Polygon, ArcPolygon, Circle]
    board_cutouts: Tuple[Union[Polygon, ArcPolygon, Circle], ...]
    other_outlines: Tuple[IdfOutline, ...]
    route_outlines: Tuple[IdfOutline, ...]
    route_keepouts: Tuple[IdfOutline, ...]
    via_keepouts: Tuple[IdfOutline, ...]
    place_keepouts: Tuple[IdfOutline, ...]
    holes: Tuple[IdfHole, ...]
    notes: Tuple[IdfNote, ...]
    placement: Tuple[IdfPart, ...]


@dataclass
class LoopPoint:
    """Internal structure for loop points during parsing"""
    id: int
    loop_n: int
    x: float
    y: float
    angle: float


class IdfParser:
    """Parser for IDF/EMN format files"""
    
    def __init__(self, filename: str):
        self.filename = filename
        self.ucnv = 1.0  # unit conversion factor
        self.loop_id_seq = 0
    
    def _find_section_end(self, tokens: List[str], match_str: str) -> int:
        """Find the position of the section end marker"""
        try:
            return tokens.index(match_str)
        except ValueError:
            raise IdfException(f"{match_str} not found.")
    
    def _tokenize_line(self, line: str) -> List[str]:
        """Tokenize a line, handling quotes properly"""
        tokens = []
        i = 0
        in_quote = False
        current_token = ""
        
        while i < len(line):
            char = line[i]
            
            if in_quote:
                if char == '"':
                    tokens.append(current_token)
                    current_token = ""
                    in_quote = False
                else:
                    current_token += char
            else:
                if char == '"':
                    in_quote = True
                elif char == ' ':
                    if current_token:
                        tokens.append(current_token)
                        current_token = ""
                else:
                    current_token += char
            i += 1
        
        if current_token:
            tokens.append(current_token)
        
        return tokens
    
    def _parse_loop_points(self, tokens: List[str]) -> List[LoopPoint]:
        """Parse loop point data from tokens"""
        points = []
        i = 0
        while i + 3 < len(tokens):
            point = LoopPoint(
                id=self.loop_id_seq,
                loop_n=int(tokens[i]),
                x=float(tokens[i+1]),
                y=float(tokens[i+2]),
                angle=float(tokens[i+3])
            )
            points.append(point)
            self.loop_id_seq += 1
            i += 4
        return points
    
    def _parse_holes(self, tokens: List[str]) -> List[IdfHole]:
        """Parse hole data from tokens"""
        holes = []
        i = 0
        while i + 6 < len(tokens):
            hole = IdfHole(
                dia=float(tokens[i]) * self.ucnv,
                x=float(tokens[i+1]) * self.ucnv,
                y=float(tokens[i+2]) * self.ucnv,
                plating=tokens[i+3],
                assoc=tokens[i+4],
                type=tokens[i+5],
                owner=tokens[i+6]
            )
            holes.append(hole)
            i += 7
        return holes
    
    def _parse_notes(self, tokens: List[str]) -> List[IdfNote]:
        """Parse note data from tokens"""
        notes = []
        i = 0
        while i + 4 < len(tokens):
            note = IdfNote(
                x=float(tokens[i]) * self.ucnv,
                y=float(tokens[i+1]) * self.ucnv,
                height=float(tokens[i+2]) * self.ucnv,
                length=float(tokens[i+3]) * self.ucnv,
                text=tokens[i+4]
            )
            notes.append(note)
            i += 5
        return notes
    
    def _parse_placement(self, tokens: List[str]) -> List[IdfPart]:
        """Parse placement data from tokens"""
        parts = []
        i = 0
        while i + 8 < len(tokens):
            part = IdfPart(
                package=tokens[i],
                partnumber=tokens[i+1],
                refdes=tokens[i+2],
                x=float(tokens[i+3]) * self.ucnv,
                y=float(tokens[i+4]) * self.ucnv,
                offset=float(tokens[i+5]) * self.ucnv,
                angle=float(tokens[i+6]),
                side=tokens[i+7],
                status=tokens[i+8]
            )
            parts.append(part)
            i += 9
        return parts
    
    def _points_to_geometry(self, loop_points: List[LoopPoint]) -> List[Union[Polygon, ArcPolygon, Circle]]:
        """Convert loop points to JITX geometry objects"""
        if not loop_points:
            return []
        
        # Group by loop number
        loops = {}
        for point in loop_points:
            if point.loop_n not in loops:
                loops[point.loop_n] = []
            loops[point.loop_n].append(point)
        
        geometries = []
        for points in loops.values():
            # Sort by id to ensure correct order
            points.sort(key=lambda p: p.id)
            
            # Build geometry elements
            elements = []
            current_point = (points[0].x * self.ucnv, points[0].y * self.ucnv)
            
            for point in points:
                if point.angle == 0.0:
                    # Straight line point
                    new_point = (point.x * self.ucnv, point.y * self.ucnv)
                    elements.append(new_point)
                    current_point = new_point
                elif abs(point.angle) == 360.0:
                    # Full circle
                    new_point = (point.x * self.ucnv, point.y * self.ucnv)
                    dist = math.sqrt((current_point[0] - new_point[0])**2 + 
                                   (current_point[1] - new_point[1])**2)
                    circle = Circle(radius=dist)
                    geometries.append(circle)
                    current_point = new_point
                    continue  # Don't add to elements, return as separate circle
                else:
                    # Arc segment
                    xp, yp = current_point
                    xn = point.x * self.ucnv
                    yn = point.y * self.ucnv
                    angle = point.angle
                    
                    # Calculate arc parameters
                    dist = math.sqrt((xp - xn)**2 + (yp - yn)**2)
                    if dist == 0:
                        continue
                        
                    xm = (xp + xn) / 2.0
                    ym = (yp + yn) / 2.0
                    
                    rise_x = (xn - xp) / dist
                    rise_y = (yn - yp) / dist
                    
                    half_sw_ang = math.radians(angle / 2.0)
                    if abs(math.sin(half_sw_ang)) < 1e-10:  # Avoid division by zero
                        continue
                        
                    dist_over_2 = dist / 2.0
                    radius = abs(dist_over_2 / math.sin(half_sw_ang))
                    
                    over180 = -1.0 if abs(angle) > 180.0 else 1.0
                    negative = -1.0 if angle < 0 else 1.0
                    
                    dist_m_to_c = math.sqrt(max(0, radius**2 - dist_over_2**2))
                    xc = xm - rise_y * dist_m_to_c * over180 * negative
                    yc = ym + rise_x * dist_m_to_c * over180 * negative
                    
                    start_ang = math.degrees(math.atan2(yp - yc, xp - xc))
                    if start_ang < 0:
                        start_ang += 360.0
                    elif start_ang > 360:
                        start_ang -= 360.0
                    
                    arc = Arc((xc, yc), radius, start_ang, angle)
                    elements.append(arc)
                    current_point = (xn, yn)
            
            # Create geometry based on elements
            if len(elements) == 1 and isinstance(elements[0], Circle):
                geometries.append(elements[0])
            elif any(isinstance(e, Arc) for e in elements):
                # Has arcs - create ArcPolygon
                geometries.append(ArcPolygon(elements))
            else:
                # Only points - create regular Polygon
                points = [e for e in elements if isinstance(e, tuple)]
                if len(points) >= 3:
                    geometries.append(Polygon(points))
        
        return geometries
    
    def parse(self) -> IdfFile:
        """Parse the IDF file and return structured data"""
        with open(self.filename, 'r') as f:
            content = f.read()
        
        # Normalize line endings and tokenize
        lines = content.replace('\r\n', '\n').split('\n')
        tokens = []
        for line in lines:
            tokens.extend(self._tokenize_line(line.strip()))
        
        # Remove empty tokens
        tokens = [t for t in tokens if t]
        
        # Initialize collections
        headers = []
        board_outlines = []
        other_outlines = []
        route_outlines = []
        route_keepouts = []
        via_keepouts = []
        place_keepouts = []
        holes = []
        notes = []
        placement = []
        
        i = 0
        while i < len(tokens):
            token = tokens[i]
            
            if token == ".HEADER":
                end_pos = self._find_section_end(tokens[i+1:], ".END_HEADER")
                header_tokens = tokens[i+1:i+1+end_pos]
                
                header = IdfHeader(
                    filetype=header_tokens[0],
                    idf_version=float(header_tokens[1]),
                    source_system=header_tokens[2],
                    date=header_tokens[3],
                    version=int(header_tokens[4]),
                    name=header_tokens[5],
                    units=header_tokens[6]
                )
                headers.append(header)
                
                # Set unit conversion
                if header.units == "THOU":
                    self.ucnv = 0.0254  # thou to mm
                elif header.units == "MM":
                    self.ucnv = 1.0
                else:
                    print(f"Unknown units: {header.units}, assuming MM")
                    self.ucnv = 1.0
                
                i = i + 1 + end_pos + 1
            
            elif token in [".BOARD_OUTLINE", ".PANEL_OUTLINE"]:
                end_pos = self._find_section_end(tokens[i+1:], ".END_BOARD_OUTLINE")
                section_tokens = tokens[i+1:i+1+end_pos]
                
                loop_tokens = section_tokens[2:]  # Skip owner and thickness
                loop_points = self._parse_loop_points(loop_tokens)
                geometries = self._points_to_geometry(loop_points)
                
                if geometries:
                    outline = geometries[0]
                    cutouts = geometries[1:] if len(geometries) > 1 else []
                    
                    board_outline = IdfOutline(
                        owner=section_tokens[0],
                        ident=token,
                        thickness=float(section_tokens[1]),
                        layers="",
                        outline=outline,
                        cutouts=cutouts
                    )
                    board_outlines.append(board_outline)
                
                i = i + 1 + end_pos + 1
            
            elif token == ".OTHER_OUTLINE":
                end_pos = self._find_section_end(tokens[i+1:], ".END_OTHER_OUTLINE")
                section_tokens = tokens[i+1:i+1+end_pos]
                
                loop_tokens = section_tokens[4:]  # Skip owner, ident, thickness, layers
                loop_points = self._parse_loop_points(loop_tokens)
                geometries = self._points_to_geometry(loop_points)
                
                if geometries:
                    outline = geometries[0]
                    cutouts = geometries[1:] if len(geometries) > 1 else []
                    
                    other_outline = IdfOutline(
                        owner=section_tokens[0],
                        ident=section_tokens[1],
                        thickness=float(section_tokens[2]),
                        layers=section_tokens[3],
                        outline=outline,
                        cutouts=cutouts
                    )
                    other_outlines.append(other_outline)
                
                i = i + 1 + end_pos + 1
            
            elif token == ".ROUTE_OUTLINE":
                end_pos = self._find_section_end(tokens[i+1:], ".END_ROUTE_OUTLINE")
                section_tokens = tokens[i+1:i+1+end_pos]
                
                loop_tokens = section_tokens[2:]  # Skip owner and layers
                loop_points = self._parse_loop_points(loop_tokens)
                geometries = self._points_to_geometry(loop_points)
                
                if geometries:
                    route_outline = IdfOutline(
                        owner=section_tokens[0],
                        ident=token,
                        thickness=0.0,
                        layers=section_tokens[1],
                        outline=geometries[0],
                        cutouts=[]
                    )
                    route_outlines.append(route_outline)
                
                i = i + 1 + end_pos + 1
            
            elif token == ".PLACE_OUTLINE":
                end_pos = self._find_section_end(tokens[i+1:], ".END_PLACE_OUTLINE")
                section_tokens = tokens[i+1:i+1+end_pos]
                
                loop_tokens = section_tokens[3:]  # Skip owner, layers, thickness
                loop_points = self._parse_loop_points(loop_tokens)
                geometries = self._points_to_geometry(loop_points)
                
                if geometries:
                    place_outline = IdfOutline(
                        owner=section_tokens[0],
                        ident=token,
                        thickness=float(section_tokens[2]),
                        layers=section_tokens[1],
                        outline=geometries[0],
                        cutouts=[]
                    )
                    route_outlines.append(place_outline)  # Note: Stanza code adds to route-outlines
                
                i = i + 1 + end_pos + 1
            
            elif token == ".ROUTE_KEEPOUT":
                end_pos = self._find_section_end(tokens[i+1:], ".END_ROUTE_KEEPOUT")
                section_tokens = tokens[i+1:i+1+end_pos]
                
                loop_tokens = section_tokens[2:]  # Skip owner and layers
                loop_points = self._parse_loop_points(loop_tokens)
                geometries = self._points_to_geometry(loop_points)
                
                if geometries:
                    route_keepout = IdfOutline(
                        owner=section_tokens[0],
                        ident=".ROUTE_KEEPOUT",
                        thickness=0.0,
                        layers=section_tokens[1],
                        outline=geometries[0],
                        cutouts=[]
                    )
                    route_keepouts.append(route_keepout)
                
                i = i + 1 + end_pos + 1
            
            elif token == ".VIA_KEEPOUT":
                end_pos = self._find_section_end(tokens[i+1:], ".END_VIA_KEEPOUT")
                section_tokens = tokens[i+1:i+1+end_pos]
                
                loop_tokens = section_tokens[1:]  # Skip owner
                loop_points = self._parse_loop_points(loop_tokens)
                geometries = self._points_to_geometry(loop_points)
                
                if geometries:
                    via_keepout = IdfOutline(
                        owner=section_tokens[0],
                        ident=".VIA_KEEPOUT",
                        thickness=0.0,
                        layers="",
                        outline=geometries[0],
                        cutouts=[]
                    )
                    via_keepouts.append(via_keepout)
                
                i = i + 1 + end_pos + 1
            
            elif token == ".PLACE_KEEPOUT":
                end_pos = self._find_section_end(tokens[i+1:], ".END_PLACE_KEEPOUT")
                section_tokens = tokens[i+1:i+1+end_pos]
                
                loop_tokens = section_tokens[3:]  # Skip owner, layers, thickness
                loop_points = self._parse_loop_points(loop_tokens)
                geometries = self._points_to_geometry(loop_points)
                
                if geometries:
                    place_keepout = IdfOutline(
                        owner=section_tokens[0],
                        ident=".PLACE_KEEPOUT",
                        thickness=float(section_tokens[2]),
                        layers=section_tokens[1],
                        outline=geometries[0],
                        cutouts=[]
                    )
                    place_keepouts.append(place_keepout)
                
                i = i + 1 + end_pos + 1
            
            elif token == ".DRILLED_HOLES":
                end_pos = self._find_section_end(tokens[i+1:], ".END_DRILLED_HOLES")
                section_tokens = tokens[i+1:i+1+end_pos]
                holes.extend(self._parse_holes(section_tokens))
                
                i = i + 1 + end_pos + 1
            
            elif token == ".NOTES":
                end_pos = self._find_section_end(tokens[i+1:], ".END_NOTES")
                section_tokens = tokens[i+1:i+1+end_pos]
                notes.extend(self._parse_notes(section_tokens))
                
                i = i + 1 + end_pos + 1
            
            elif token == ".PLACEMENT":
                end_pos = self._find_section_end(tokens[i+1:], ".END_PLACEMENT")
                section_tokens = tokens[i+1:i+1+end_pos]
                placement.extend(self._parse_placement(section_tokens))
                
                i = i + 1 + end_pos + 1
            
            elif token == "":
                i += 1
            else:
                # Skip unknown sections
                i += 1
        
        # Validate parsed data
        if len(headers) != 1:
            raise IdfException(f"Expected exactly 1 header, found {len(headers)}")
        
        if len(board_outlines) != 1:
            raise IdfException(f"Expected exactly 1 board outline, found {len(board_outlines)}")
        
        return IdfFile(
            header=headers[0],
            board_outline=board_outlines[0].outline,
            board_cutouts=tuple(board_outlines[0].cutouts),
            other_outlines=tuple(other_outlines),
            route_outlines=tuple(route_outlines),
            route_keepouts=tuple(route_keepouts),
            via_keepouts=tuple(via_keepouts),
            place_keepouts=tuple(place_keepouts),
            holes=tuple(holes),
            notes=tuple(notes),
            placement=tuple(placement)
        )


def find_refdes(idf_file: IdfFile, refdes: str) -> Optional[IdfPart]:
    """Find a component by reference designator"""
    for part in idf_file.placement:
        if part.refdes == refdes:
            return part
    return None


def idf_parser(filename: str) -> IdfFile:
    """Parse an IDF file and return structured data"""
    parser = IdfParser(filename)
    return parser.parse()