"""Coverage: a circle of COVERAGE_RADIUS_KM around each of the 8 cells, built with shapely in
a local metric projection (azimuthal equidistant centered on the corridor), and AOI checks."""

from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache

from pyproj import Transformer
from shapely.geometry import Point, Polygon, mapping
from shapely.ops import transform, unary_union

from ..providers.base import CellInfo, load_cells

CENTER_LAT, CENTER_LON = -17.4, -68.1
LOCAL_CRS = f"+proj=aeqd +lat_0={CENTER_LAT} +lon_0={CENTER_LON} +datum=WGS84 +units=m +no_defs"
TO_LOCAL = Transformer.from_crs("EPSG:4326", LOCAL_CRS, always_xy=True)
TO_WGS84 = Transformer.from_crs(LOCAL_CRS, "EPSG:4326", always_xy=True)

MIN_VERTICES, MAX_VERTICES = 3, 12
AOI_MIN_AREA_KM2 = 0.01  # 1 hectare
AOI_MAX_AREA_KM2 = 2000.0
# Tolerance for points drawn on a polygonal approximation of the circles in the app.
TOLERANCE_M = 150.0


class AoiValidationError(ValueError):
    pass


@dataclass(frozen=True)
class Coverage:
    radius_km: float
    circles: dict[str, Polygon]  # local metric coordinates
    union: Polygon
    check_area: Polygon  # union plus the tolerance


def to_local(geom):
    return transform(TO_LOCAL.transform, geom)


def to_wgs84(geom):
    return transform(TO_WGS84.transform, geom)


def cell_point(cell: CellInfo) -> Point:
    return to_local(Point(cell.lon, cell.lat))


@lru_cache(maxsize=8)
def build_coverage(radius_km: float) -> Coverage:
    circles = {c.point_id: cell_point(c).buffer(radius_km * 1000.0, quad_segs=64) for c in load_cells()}
    union = unary_union(list(circles.values()))
    return Coverage(radius_km, circles, union, union.buffer(TOLERANCE_M))


def coverage_geojson(radius_km: float) -> dict:
    """One Polygon feature per cell (the union of all of them is the coverage)."""
    cov = build_coverage(radius_km)
    features = []
    for cell in load_cells():
        ring = to_wgs84(cell_point(cell).buffer(radius_km * 1000.0, quad_segs=16))
        geom = mapping(ring)
        geom = {"type": "Polygon", "coordinates": [[[round(x, 6), round(y, 6)] for x, y in geom["coordinates"][0]]]}
        features.append({"type": "Feature", "geometry": geom, "properties": {"point_id": cell.point_id, "name": cell.name}})
    return {"type": "FeatureCollection", "features": features,
            "meta": {"radius_km": cov.radius_km, "union_area_km2": round(cov.union.area / 1e6, 1)}}


def validate_aoi_polygon(geometry: dict, radius_km: float) -> Polygon:
    """Validated AOI polygon in local metric coordinates; raises AoiValidationError."""
    if geometry.get("type") != "Polygon":
        raise AoiValidationError("polygon.type must be 'Polygon'")
    rings = geometry.get("coordinates") or []
    if len(rings) != 1:
        raise AoiValidationError("the polygon must have exactly one outer ring and no holes")
    ring = [tuple(map(float, pt)) for pt in rings[0]]
    for lon, lat in ring:
        if not (math.isfinite(lon) and math.isfinite(lat) and -180 <= lon <= 180 and -90 <= lat <= 90):
            raise AoiValidationError("coordinates must be [lon, lat] in degrees")
    if len(ring) < 4 or ring[0] != ring[-1]:
        raise AoiValidationError("the ring must be closed (first point equals last point)")
    distinct = len(set(ring[:-1]))
    if distinct != len(ring) - 1:
        raise AoiValidationError("the ring has repeated vertices")
    if not MIN_VERTICES <= distinct <= MAX_VERTICES:
        raise AoiValidationError(f"the polygon must have {MIN_VERTICES} to {MAX_VERTICES} distinct vertices")
    poly = to_local(Polygon(ring))
    if not poly.is_valid:
        raise AoiValidationError("the polygon is not valid (self-intersecting or degenerate)")
    area_km2 = poly.area / 1e6
    if not AOI_MIN_AREA_KM2 <= area_km2 <= AOI_MAX_AREA_KM2:
        raise AoiValidationError(f"the polygon area must be between {AOI_MIN_AREA_KM2} and {AOI_MAX_AREA_KM2} km2")
    cov = build_coverage(radius_km)
    if not cov.check_area.contains(poly):
        raise AoiValidationError("the polygon must be entirely inside the coverage of the 8 cells")
    if not cov.check_area.contains(poly.centroid):
        raise AoiValidationError("the polygon centroid must be inside the coverage")
    return poly


def candidate_cells(poly_local: Polygon, radius_km: float) -> list[tuple[str, float]]:
    """(point_id, distance_km) of every cell whose circle contains the AOI centroid."""
    centroid = poly_local.centroid
    limit = radius_km * 1000.0 + TOLERANCE_M
    out = []
    for cell in load_cells():
        d = centroid.distance(cell_point(cell))
        if d <= limit:
            out.append((cell.point_id, d / 1000.0))
    return sorted(out, key=lambda t: t[1])
