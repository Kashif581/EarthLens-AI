
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ChatResponse(BaseModel):
    # Main response
    reply: str
    session_id: str

    # Map and preview
    preview_url: Optional[str] = None
    tile_url: Optional[str] = None
    bounds: Optional[List[List[float]]] = None
    visualization: Optional[Dict[str, Any]] = None

    # Analysis information
    analysis_title: Optional[str] = None
    region: Optional[str] = None
    satellite: Optional[str] = None
    resolution: Optional[str] = None
    dataset_info: Optional[Dict[str, Any]] = None
    methodology: Optional[str] = None
    stats: Optional[Dict[str, Any]] = None
    legend: Optional[Dict[str, str]] = None

    # Easy-to-understand report
    plain_language_summary: Optional[str] = None
    key_findings: List[str] = Field(default_factory=list)
    why_it_matters: Optional[str] = None
    recommended_actions: List[str] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)

    # Detailed explanation for technical users
    interpretation: Optional[str] = None
    technical_interpretation: Optional[str] = None

    # Export job
    job_id: Optional[str] = None


class JobStatus(BaseModel):
    job_id: str
    status: str
    output_url: Optional[str] = None
    message: str
