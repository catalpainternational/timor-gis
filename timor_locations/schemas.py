from typing import Literal
from pydantic import BaseModel

class AreaOut(BaseModel):
    """
    List Municipalities, Admin Posts and Sucos
    """
    type: Literal["Municipality", "Administrative Post", "Suco"]
    pcode: int
    name: str
    parent: int | None = None