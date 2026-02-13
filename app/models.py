from pydantic import BaseModel
from typing import List

class PredictionResult(BaseModel):
    class_name: str
    confidence: float

class TopPredictions(BaseModel):
    predictions: List[PredictionResult]