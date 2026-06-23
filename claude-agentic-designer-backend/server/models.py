"""Pydantic models for the API surface."""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ReferenceFile(BaseModel):
    id: str
    name: str
    # "upload" = local file copied into the library; "sharepoint" = M365/Graph URL
    source: str = Field(default="upload")  # upload | sharepoint
    role: str = Field(default="example")  # master | example
    enabled: bool = True
    # For uploads: relative path under references/. For sharepoint: the share URL.
    path: Optional[str] = None
    url: Optional[str] = None
    size: Optional[int] = None
    content_type: Optional[str] = None
    added_at: float = Field(default_factory=time.time)
    # Local cache path once a sharepoint file has been downloaded.
    cached_path: Optional[str] = None


class ReferenceLibrary(BaseModel):
    files: List[ReferenceFile] = Field(default_factory=list)


class AddSharePointRequest(BaseModel):
    url: str
    name: Optional[str] = None
    role: str = "example"


class ToggleRequest(BaseModel):
    enabled: bool


class UpdateReferenceRequest(BaseModel):
    role: Optional[str] = None
    name: Optional[str] = None


class EventModel(BaseModel):
    run_id: str
    type: str
    seq: int = 0
    ts: float = Field(default_factory=time.time)
    agent: Optional[str] = None
    level: str = "info"
    message: str = ""
    data: Dict[str, Any] = Field(default_factory=dict)


class RunSummary(BaseModel):
    run_id: str
    created_at: float
    doc_type: Optional[str] = None
    status: str = "running"  # running | passed | revise | error
    score: Optional[float] = None
    iterations: int = 0
    artifact: Optional[str] = None
    renders: List[str] = Field(default_factory=list)
