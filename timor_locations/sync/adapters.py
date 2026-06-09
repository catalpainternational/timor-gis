"""Per-provider configuration: how to read a provider's shapefiles and which of
its columns carry the name / code / parent for each administrative level.

Adding a new provider (or a new vintage of an existing one) is a config change
here, not a code change in the pipeline. Each level lists the source layer and a
field map onto the pipeline's canonical vocabulary
(``name``, ``code``, ``post``, ``municipality``, ``suco``).
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class LevelSpec:
    layer_file: str  # filename of the shapefile within the source dir
    fields: dict  # canonical-key -> provider column name


@dataclass(frozen=True)
class ProviderSpec:
    key: str
    description: str
    levels: dict = field(default_factory=dict)  # "suco"/"aldeia"/... -> LevelSpec


PROVIDERS = {
    "intl2024": ProviderSpec(
        key="intl2024",
        description="INTL (via PNDS) 2024 administrative boundary set, WGS84 / UTM 51S.",
        levels={
            "municipality": LevelSpec(
                layer_file="Municipio_2024.shp",
                fields={"name": "MUNICIPIO", "code": "NewMunCode"},
            ),
            "post": LevelSpec(
                layer_file="Post-Admin2024.shp",
                fields={"name": "P_ADMIN", "code": "NewPostAdC", "municipality": "MUNICIPIO"},
            ),
            "suco": LevelSpec(
                layer_file="Suco.shp",
                fields={
                    "name": "SUCO",
                    "code": "NewSucoCod",
                    "post": "P_ADMIN",
                    "municipality": "MUNICIPIO",
                },
            ),
            "aldeia": LevelSpec(
                layer_file="Aldeia_2024.shp",
                fields={
                    "name": "ALDEIA",
                    "code": "NewAldCode",
                    "suco": "SUCO",
                    "post": "P_ADMIN",
                    "municipality": "MUNICIPIO",
                },
            ),
        },
    ),
}
