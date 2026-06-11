"""Resolve aldeia → suco links using sukus.gpkg (INTL Suco.shp) as pcode authority."""

from __future__ import annotations

from importlib import resources

from django.contrib.gis.gdal import DataSource
from django.contrib.gis.geos import GEOSGeometry, Point

SUKUS_GPKG = resources.files("timor_locations.data").joinpath("sukus.gpkg")


class SucoIndex:
    """In-memory suco polygons keyed on SUCOCODE from the canonical sukus layer."""

    __slots__ = ("_by_pcode",)

    def __init__(self) -> None:
        self._by_pcode: dict[str, tuple[GEOSGeometry, str]] = {}

    @classmethod
    def from_sukus_gpkg(cls) -> SucoIndex:
        index = cls()
        ds = DataSource(str(SUKUS_GPKG))
        layer = ds[0]
        for feat in layer:
            pcode = str(feat.get("SUCOCODE"))
            name = str(feat.get("SUCONAME"))
            # Store GEOS geometries so resolve works against model instances loaded from PostGIS.
            index._by_pcode[pcode] = (GEOSGeometry(feat.geom.wkt), name)
        return index

    def known_pcodes(self) -> frozenset[str]:
        return frozenset(self._by_pcode)

    def suco_name(self, pcode: str) -> str:
        return self._by_pcode[pcode][1]

    def resolve_pcode(
        self,
        aldeia_geom: GEOSGeometry,
        attr_pcode: str | None,
        attr_suco_name: str | None = None,
    ) -> str:
        """Map an aldeia to the suco SUCOCODE from sukus.gpkg.

        Trust ``NewSucoCod`` when it exists in sukus and the aldeia layer's ``SUCO`` name
        matches. Otherwise fall back to spatial containment — upstream INTL aldeia exports
        carry stale/swapped codes in reorganized posts (see aldeia_suco_pcode_remap.csv).
        """
        if attr_pcode and attr_pcode in self._by_pcode:
            if attr_suco_name is None or attr_suco_name.strip().lower() == self.suco_name(attr_pcode).strip().lower():
                return attr_pcode

        centroid: Point = aldeia_geom.centroid
        containing = [pcode for pcode, (geom, _name) in self._by_pcode.items() if geom.contains(centroid)]
        if len(containing) == 1:
            return containing[0]
        if len(containing) > 1:
            return max(
                containing,
                key=lambda pcode: aldeia_geom.intersection(self._by_pcode[pcode][0]).area,
            )
        if attr_pcode and attr_pcode in self._by_pcode:
            return attr_pcode
        raise ValueError(f"No sukus suco contains aldeia centroid; attr NewSucoCod={attr_pcode!r}")
