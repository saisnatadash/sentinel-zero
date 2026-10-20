"""Request and record models for the analysis API."""
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

Category = Literal["water_odour", "water_colour", "diarrhoea_symptoms", "other"]


class Report(BaseModel):
    """A single community report. Coordinates are approximate and should be coarsened for privacy."""

    id: str
    text: str = Field(max_length=1000)
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    timestamp: datetime
    locality: str
    source_id: str
    category: Category = "other"
    event_flag: Optional[str] = None  # e.g. "community_feast"


class LabResult(BaseModel):
    """An independent laboratory result. Used as external evidence, never as a substitute for it."""

    id: str
    locality: str
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    timestamp: datetime
    result: Literal["positive", "negative"]
    agent: str = "unspecified"


class AnalysisRequest(BaseModel):
    reports: list[Report] = Field(default_factory=list, max_length=5000)
    lab_results: list[LabResult] = Field(default_factory=list, max_length=500)
