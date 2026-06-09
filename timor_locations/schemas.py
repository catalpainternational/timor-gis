from typing import Literal

from pydantic import BaseModel


class AreaOut(BaseModel):
    """
    List Municipalities, Admin Posts and Sucos
    """

    type: Literal["Municipality", "Administrative Post", "Suco"]
    pcode: str
    name: str
    parent: str | None = None


# The following models are derived from the TopoJSON spec: https://github.com/topojson/topojson-specification/blob/master/README.md  # noqa: E501
# A position is represented by an array of numbers. There must be at least two elements, and may be more
position = list[int]


class Transform(BaseModel):
    scale: tuple[float, float]
    translate: tuple[float, float]


class Topology(BaseModel):
    type: Literal[
        "Topology",
        "Point",
        "MultiPoint",
        "LineString",
        "MultiLineString",
        "Polygon",
        "MultiPolygon",
        "GeometryCollection",
    ]
    bbox: list[float] | None = None
    arcs: list[list[position]]
    objects: dict
    transform: Transform
