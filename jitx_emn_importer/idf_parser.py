"""
IDF/EMN Parser for JITX Python

Converts EMN/IDF/BDF format files to JITX-compatible geometry data structures.
Parses mechanical board outline data, cutouts, keepouts, holes, notes, and placement information.

For use with JITX Python API.
"""

import logging
import math
from dataclasses import dataclass

from jitx.shapes.primitive import Arc, ArcPolygon, Circle, Polygon

logger = logging.getLogger(__name__)

# Epsilons for floating-point comparisons.
# _EPSILON: degenerate-geometry threshold (zero-length chord, sin=0).
# _CLOSURE_EPSILON: tolerance for considering a polygon already closed.
_EPSILON = 1e-10
_CLOSURE_EPSILON = 1e-6


class IdfException(Exception):
    """Exception for IDF parsing errors"""


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
    outline: Polygon | ArcPolygon | Circle
    cutouts: list[Polygon | ArcPolygon | Circle]


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
    parts: list[IdfPart]


@dataclass
class IdfFile:
    """Complete parsed IDF file data"""

    header: IdfHeader
    board_outline: Polygon | ArcPolygon | Circle
    board_cutouts: tuple[Polygon | ArcPolygon | Circle, ...]
    other_outlines: tuple[IdfOutline, ...]
    route_outlines: tuple[IdfOutline, ...]
    place_outlines: tuple[IdfOutline, ...]
    route_keepouts: tuple[IdfOutline, ...]
    via_keepouts: tuple[IdfOutline, ...]
    place_keepouts: tuple[IdfOutline, ...]
    holes: tuple[IdfHole, ...]
    notes: tuple[IdfNote, ...]
    placement: tuple[IdfPart, ...]


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

    def _find_section_end(self, tokens: list[str], match_str: str) -> int:
        """Find the position of the section end marker"""
        try:
            return tokens.index(match_str)
        except ValueError:
            raise IdfException(f"{match_str} not found.")

    def _tokenize_line(self, line: str) -> list[str]:
        """Tokenize a line, splitting on whitespace outside of double-quoted regions.

        IDF/EMN does not specify a quote-escape syntax; an embedded `"` ends the token.
        """
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
                elif char in (" ", "\t"):
                    if current_token:
                        tokens.append(current_token)
                        current_token = ""
                else:
                    current_token += char
            i += 1

        if current_token:
            tokens.append(current_token)

        return tokens

    @staticmethod
    def _warn_trailing(section: str, i: int, total: int, record_size: int) -> None:
        """Warn if there are leftover tokens that don't form a complete record."""
        remaining = total - i
        if remaining > 0:
            logger.warning(
                "%s has %d trailing token(s) (expected multiple of %d)",
                section,
                remaining,
                record_size,
            )

    def _parse_loop_points(self, tokens: list[str]) -> list[LoopPoint]:
        """Parse loop point data; coordinates are unit-converted later in _points_to_geometry."""
        points = []
        i = 0
        while i + 3 < len(tokens):
            point = LoopPoint(
                id=self.loop_id_seq,
                loop_n=int(tokens[i]),
                x=float(tokens[i + 1]),
                y=float(tokens[i + 2]),
                angle=float(tokens[i + 3]),
            )
            points.append(point)
            self.loop_id_seq += 1
            i += 4
        self._warn_trailing("Loop points", i, len(tokens), 4)
        return points

    def _parse_holes(self, tokens: list[str], idf_version: float = 3.0) -> list[IdfHole]:
        """Parse hole data from tokens"""
        holes = []
        i = 0
        if idf_version < 3.0:
            # IDF 2.0: 5 fields per hole (dia, x, y, plating, assoc)
            while i + 4 < len(tokens):
                hole = IdfHole(
                    dia=float(tokens[i]) * self.ucnv,
                    x=float(tokens[i + 1]) * self.ucnv,
                    y=float(tokens[i + 2]) * self.ucnv,
                    plating=tokens[i + 3],
                    assoc=tokens[i + 4],
                    type="",
                    owner="",
                )
                holes.append(hole)
                i += 5
            self._warn_trailing("DRILLED_HOLES (IDF 2.0)", i, len(tokens), 5)
        else:
            # IDF 3.0: 7 fields per hole
            while i + 6 < len(tokens):
                hole = IdfHole(
                    dia=float(tokens[i]) * self.ucnv,
                    x=float(tokens[i + 1]) * self.ucnv,
                    y=float(tokens[i + 2]) * self.ucnv,
                    plating=tokens[i + 3],
                    assoc=tokens[i + 4],
                    type=tokens[i + 5],
                    owner=tokens[i + 6],
                )
                holes.append(hole)
                i += 7
            self._warn_trailing("DRILLED_HOLES (IDF 3.0)", i, len(tokens), 7)
        return holes

    def _parse_notes(self, tokens: list[str]) -> list[IdfNote]:
        """Parse note data from tokens"""
        notes = []
        i = 0
        while i + 4 < len(tokens):
            note = IdfNote(
                x=float(tokens[i]) * self.ucnv,
                y=float(tokens[i + 1]) * self.ucnv,
                height=float(tokens[i + 2]) * self.ucnv,
                length=float(tokens[i + 3]) * self.ucnv,
                text=tokens[i + 4],
            )
            notes.append(note)
            i += 5
        self._warn_trailing("NOTES", i, len(tokens), 5)
        return notes

    def _parse_placement(self, tokens: list[str]) -> list[IdfPart]:
        """Parse placement data from tokens"""
        parts = []
        i = 0
        while i + 8 < len(tokens):
            part = IdfPart(
                package=tokens[i],
                partnumber=tokens[i + 1],
                refdes=tokens[i + 2],
                x=float(tokens[i + 3]) * self.ucnv,
                y=float(tokens[i + 4]) * self.ucnv,
                offset=float(tokens[i + 5]) * self.ucnv,
                angle=float(tokens[i + 6]),
                side=tokens[i + 7],
                status=tokens[i + 8],
            )
            parts.append(part)
            i += 9
        self._warn_trailing("PLACEMENT", i, len(tokens), 9)
        return parts

    def _points_to_geometry(
        self, loop_points: list[LoopPoint]
    ) -> list[Polygon | ArcPolygon | Circle]:
        """Convert loop points to JITX geometry objects.

        Applies unit conversion (self.ucnv) and dispatches each point on its
        angle: 0 = straight-line, +/-360 = full circle, otherwise = arc.
        """
        if not loop_points:
            return []

        loops: dict[int, list[LoopPoint]] = {}
        for point in loop_points:
            loops.setdefault(point.loop_n, []).append(point)

        geometries = []
        # Iterate in ascending loop_n order so the outer outline (loop 0)
        # always comes first regardless of file ordering.
        for loop_num, points in sorted(loops.items()):
            points.sort(key=lambda p: p.id)
            if not points:
                continue

            elements: list[tuple | Arc] = []
            first_point = (points[0].x * self.ucnv, points[0].y * self.ucnv)
            current_point = first_point

            for point in points:
                if point.angle == 0.0:
                    new_point = (point.x * self.ucnv, point.y * self.ucnv)
                    elements.append(new_point)
                    current_point = new_point
                elif abs(point.angle) == 360.0:
                    # Full circle: chord between current and next point is the diameter.
                    new_point = (point.x * self.ucnv, point.y * self.ucnv)
                    dist = math.hypot(
                        current_point[0] - new_point[0], current_point[1] - new_point[1]
                    )
                    if dist > 0:
                        cx = (current_point[0] + new_point[0]) / 2.0
                        cy = (current_point[1] + new_point[1]) / 2.0
                        circle = Circle(radius=dist / 2.0)
                        circle._center = (cx, cy)  # type: ignore[reportAttributeAccessIssue]
                        geometries.append(circle)
                    current_point = new_point
                else:
                    arc = self._arc_from_chord(
                        current_point,
                        point.x * self.ucnv,
                        point.y * self.ucnv,
                        point.angle,
                        loop_num,
                    )
                    if arc is not None:
                        elements.append(arc)
                    current_point = (point.x * self.ucnv, point.y * self.ucnv)

            # Close the loop if the geometric endpoint differs from the start.
            # Use current_point (not elements[-1]) so a trailing arc closes too.
            if elements and (
                abs(current_point[0] - first_point[0]) > _CLOSURE_EPSILON
                or abs(current_point[1] - first_point[1]) > _CLOSURE_EPSILON
            ):
                elements.append(first_point)

            if any(isinstance(e, Arc) for e in elements):
                geometries.append(ArcPolygon(elements))
            else:
                poly_points = [e for e in elements if isinstance(e, tuple)]
                if len(poly_points) >= 3:
                    geometries.append(Polygon(poly_points))

        return geometries

    def _arc_from_chord(
        self,
        start: tuple[float, float],
        xn: float,
        yn: float,
        angle: float,
        loop_num: int,
    ) -> Arc | None:
        """Construct a JITX Arc from a chord (start->end) and a sweep angle.

        Geometry: the arc center lies on the perpendicular bisector of the chord,
        offset from the midpoint by `sqrt(radius^2 - (chord/2)^2)`. The sign of
        that offset selects between the two possible centers, determined by:
          - direction_sign: +1 for CCW (angle > 0), -1 for CW
          - major_arc_sign: +1 for minor arc (|angle| <= 180), -1 for major
        Returns None on degenerate input (logged as a warning).
        """
        xp, yp = start
        chord = math.hypot(xn - xp, yn - yp)
        if chord < _EPSILON:
            logger.warning(
                "Arc segment in loop %d has zero or near-zero length, skipping", loop_num
            )
            return None

        sin_half = math.sin(math.radians(angle / 2.0))
        if abs(sin_half) < _EPSILON:
            logger.warning("Arc segment in loop %d has invalid angle %s, skipping", loop_num, angle)
            return None

        half_chord = chord / 2.0
        radius = abs(half_chord / sin_half)

        radius_sq_minus_h2 = radius**2 - half_chord**2
        if radius_sq_minus_h2 < -_CLOSURE_EPSILON:
            logger.warning(
                "Arc segment in loop %d has invalid geometry (radius too small), skipping",
                loop_num,
            )
            return None

        chord_dx = (xn - xp) / chord
        chord_dy = (yn - yp) / chord
        midpoint_to_center = math.sqrt(max(0.0, radius_sq_minus_h2))
        major_arc_sign = -1.0 if abs(angle) > 180.0 else 1.0
        direction_sign = -1.0 if angle < 0 else 1.0
        offset = midpoint_to_center * major_arc_sign * direction_sign

        xm = (xp + xn) / 2.0
        ym = (yp + yn) / 2.0
        xc = xm - chord_dy * offset
        yc = ym + chord_dx * offset

        start_ang = math.degrees(math.atan2(yp - yc, xp - xc)) % 360.0
        return Arc((xc, yc), radius, start_ang, angle)

    def parse(self) -> IdfFile:
        """Parse the IDF file and return structured data"""
        with open(self.filename, "r") as f:
            content = f.read()

        # Normalize line endings and tokenize
        lines = content.replace("\r\n", "\n").split("\n")
        tokens = []
        for line in lines:
            tokens.extend(self._tokenize_line(line.strip()))

        # Empty strings are not filtered: quoted "" is a valid token in placement records.

        headers = []
        board_outlines = []
        panel_outlines = []
        other_outlines = []
        route_outlines = []
        place_outlines = []
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
                end_pos = self._find_section_end(tokens[i + 1 :], ".END_HEADER")
                header_tokens = tokens[i + 1 : i + 1 + end_pos]

                header = IdfHeader(
                    filetype=header_tokens[0],
                    idf_version=float(header_tokens[1]),
                    source_system=header_tokens[2],
                    date=header_tokens[3],
                    version=int(header_tokens[4]),
                    name=header_tokens[5],
                    units=header_tokens[6],
                )
                headers.append(header)

                # Set unit conversion
                if header.units == "THOU":
                    self.ucnv = 0.0254  # thou to mm
                elif header.units == "MM":
                    self.ucnv = 1.0
                else:
                    logger.warning("Unknown units: %s, assuming MM", header.units)
                    self.ucnv = 1.0

                i = i + 1 + end_pos + 1

            elif token in [".BOARD_OUTLINE", ".PANEL_OUTLINE"]:
                end_marker = (
                    ".END_PANEL_OUTLINE" if token == ".PANEL_OUTLINE" else ".END_BOARD_OUTLINE"
                )
                end_pos = self._find_section_end(tokens[i + 1 :], end_marker)
                section_tokens = tokens[i + 1 : i + 1 + end_pos]

                if headers and headers[0].idf_version < 3.0:
                    # IDF 2.0: no owner field, just thickness then loop points
                    owner = ""
                    thickness = float(section_tokens[0])
                    loop_tokens = section_tokens[1:]
                else:
                    # IDF 3.0: owner and thickness then loop points
                    owner = section_tokens[0]
                    thickness = float(section_tokens[1])
                    loop_tokens = section_tokens[2:]

                loop_points = self._parse_loop_points(loop_tokens)
                geometries = self._points_to_geometry(loop_points)

                if geometries:
                    outline = geometries[0]
                    cutouts = geometries[1:] if len(geometries) > 1 else []

                    parsed = IdfOutline(
                        owner=owner,
                        ident=token,
                        thickness=thickness,
                        layers="",
                        outline=outline,
                        cutouts=cutouts,
                    )
                    if token == ".PANEL_OUTLINE":
                        panel_outlines.append(parsed)
                    else:
                        board_outlines.append(parsed)

                i = i + 1 + end_pos + 1

            elif token == ".OTHER_OUTLINE":
                end_pos = self._find_section_end(tokens[i + 1 :], ".END_OTHER_OUTLINE")
                section_tokens = tokens[i + 1 : i + 1 + end_pos]

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
                        cutouts=cutouts,
                    )
                    other_outlines.append(other_outline)

                i = i + 1 + end_pos + 1

            elif token == ".ROUTE_OUTLINE":
                end_pos = self._find_section_end(tokens[i + 1 :], ".END_ROUTE_OUTLINE")
                section_tokens = tokens[i + 1 : i + 1 + end_pos]

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
                        cutouts=[],
                    )
                    route_outlines.append(route_outline)

                i = i + 1 + end_pos + 1

            elif token == ".PLACE_OUTLINE":
                end_pos = self._find_section_end(tokens[i + 1 :], ".END_PLACE_OUTLINE")
                section_tokens = tokens[i + 1 : i + 1 + end_pos]

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
                        cutouts=[],
                    )
                    place_outlines.append(place_outline)

                i = i + 1 + end_pos + 1

            elif token == ".ROUTE_KEEPOUT":
                end_pos = self._find_section_end(tokens[i + 1 :], ".END_ROUTE_KEEPOUT")
                section_tokens = tokens[i + 1 : i + 1 + end_pos]

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
                        cutouts=[],
                    )
                    route_keepouts.append(route_keepout)

                i = i + 1 + end_pos + 1

            elif token == ".VIA_KEEPOUT":
                end_pos = self._find_section_end(tokens[i + 1 :], ".END_VIA_KEEPOUT")
                section_tokens = tokens[i + 1 : i + 1 + end_pos]

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
                        cutouts=[],
                    )
                    via_keepouts.append(via_keepout)

                i = i + 1 + end_pos + 1

            elif token == ".PLACE_KEEPOUT":
                end_pos = self._find_section_end(tokens[i + 1 :], ".END_PLACE_KEEPOUT")
                section_tokens = tokens[i + 1 : i + 1 + end_pos]

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
                        cutouts=[],
                    )
                    place_keepouts.append(place_keepout)

                i = i + 1 + end_pos + 1

            elif token == ".DRILLED_HOLES":
                end_pos = self._find_section_end(tokens[i + 1 :], ".END_DRILLED_HOLES")
                section_tokens = tokens[i + 1 : i + 1 + end_pos]
                version = headers[0].idf_version if headers else 3.0
                holes.extend(self._parse_holes(section_tokens, idf_version=version))

                i = i + 1 + end_pos + 1

            elif token == ".NOTES":
                end_pos = self._find_section_end(tokens[i + 1 :], ".END_NOTES")
                section_tokens = tokens[i + 1 : i + 1 + end_pos]
                notes.extend(self._parse_notes(section_tokens))

                i = i + 1 + end_pos + 1

            elif token == ".PLACEMENT":
                end_pos = self._find_section_end(tokens[i + 1 :], ".END_PLACEMENT")
                section_tokens = tokens[i + 1 : i + 1 + end_pos]
                placement.extend(self._parse_placement(section_tokens))

                i = i + 1 + end_pos + 1

            else:
                # For unknown section markers (starting with "."), try to find
                # matching .END_* and skip the entire section
                if token.startswith(".") and not token.startswith(".END_"):
                    end_marker = ".END_" + token[1:]
                    try:
                        end_pos = self._find_section_end(tokens[i + 1 :], end_marker)
                        logger.info("Skipping unknown section %s (%d tokens)", token, end_pos)
                        i = i + 1 + end_pos + 1
                    except IdfException:
                        # No matching end marker found, skip just this token
                        logger.debug("Skipping unknown token: %s", token)
                        i += 1
                else:
                    i += 1

        if len(headers) != 1:
            raise IdfException(f"Expected exactly 1 header, found {len(headers)}")

        # Prefer .BOARD_OUTLINE; fall back to .PANEL_OUTLINE when only the panel is present.
        if board_outlines and panel_outlines:
            logger.warning(
                "File contains both .BOARD_OUTLINE and .PANEL_OUTLINE; using .BOARD_OUTLINE"
            )
            primary_outlines = board_outlines
        elif board_outlines:
            primary_outlines = board_outlines
        elif panel_outlines:
            primary_outlines = panel_outlines
        else:
            raise IdfException("No board outline or panel outline found")

        if len(primary_outlines) != 1:
            raise IdfException(
                f"Expected exactly 1 board/panel outline, found {len(primary_outlines)}"
            )

        outline = primary_outlines[0].outline
        if outline is None:
            raise IdfException("Board outline has no geometry")

        if hasattr(outline, "elements"):
            num_elements = len(outline.elements)
            if num_elements < 3:
                logger.warning(
                    "Board outline has only %d elements (expected at least 3)", num_elements
                )

        return IdfFile(
            header=headers[0],
            board_outline=primary_outlines[0].outline,
            board_cutouts=tuple(primary_outlines[0].cutouts),
            other_outlines=tuple(other_outlines),
            route_outlines=tuple(route_outlines),
            place_outlines=tuple(place_outlines),
            route_keepouts=tuple(route_keepouts),
            via_keepouts=tuple(via_keepouts),
            place_keepouts=tuple(place_keepouts),
            holes=tuple(holes),
            notes=tuple(notes),
            placement=tuple(placement),
        )


def find_refdes(idf_file: IdfFile, refdes: str) -> IdfPart | None:
    """Find a component by reference designator"""
    for part in idf_file.placement:
        if part.refdes == refdes:
            return part
    return None


def idf_parser(filename: str) -> IdfFile:
    """Parse an IDF file and return structured data"""
    parser = IdfParser(filename)
    return parser.parse()
