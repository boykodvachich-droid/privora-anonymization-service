from time import perf_counter
from fastapi import FastAPI
from app.schemas import AnonymizeRequest, AnonymizeResponse
from app.anonymizer.engine import AnonymizationEngine

app = FastAPI(
    title="DataMask API",
    description="Service for detecting and masking sensitive information in text.",
    version="0.1.0",
)
engine = AnonymizationEngine()

@app.get("/health")
def health():
    return {"status": "ok", "service": "datamask"}

@app.post("/api/v1/anonymize", response_model=AnonymizeResponse)
def anonymize(payload: AnonymizeRequest):
    started = perf_counter()
    result, detected = engine.anonymize(payload.text)
    elapsed_ms = round((perf_counter() - started) * 1000, 3)
    return AnonymizeResponse(
        anonymized_text=result,
        detected=detected,
        processing_time_ms=elapsed_ms,
    )
