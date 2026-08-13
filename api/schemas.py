"""Pydantic request/response models for the M4.2 REST API. Plain
primitives only -- see api/canonical.py's module docstring for why."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel

DetectorName = Literal["classical", "ml"]


class HealthResponse(BaseModel):
    status: str
    classical_detector_available: bool
    ml_detector_available: bool


class ModelInfoResponse(BaseModel):
    ml_model_version: Optional[str]
    ml_checkpoint_exists: bool
    ml_model_input_size: Optional[int]
    ml_heatmap_size: Optional[int]
    classical_detector: str


class ImageInfo(BaseModel):
    width: int
    height: int


class Detection(BaseModel):
    x: float
    y: float


class DetectResponse(BaseModel):
    success: bool
    detector: DetectorName
    model_version: Optional[str]
    image: ImageInfo
    detections: list[Detection]
    count: int
    processing_ms: float


class GraphSummary(BaseModel):
    nodes: int
    edges: int
    distinct_edges: int


class AnalyzeResponse(BaseModel):
    success: bool
    detector: DetectorName
    model_version: Optional[str]
    dots: list[Detection]
    dot_count: int
    processing_ms: float
    graph: GraphSummary
    motifs: dict
    validity: dict


class ReconstructResponse(BaseModel):
    success: bool
    detector: DetectorName
    model_version: Optional[str]
    processing_ms: float
    graph: GraphSummary
    reconstruction: dict


class DetectorComparisonSide(BaseModel):
    detector: DetectorName
    model_version: Optional[str]
    detections: list[Detection]
    count: int
    processing_ms: float
    error: Optional[str] = None


class CompareDetectorsResponse(BaseModel):
    success: bool
    image: ImageInfo
    classical: DetectorComparisonSide
    ml: DetectorComparisonSide
    agreement: dict


class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    detail: Optional[str] = None
