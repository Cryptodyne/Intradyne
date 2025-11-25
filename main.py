import uvicorn
from fastapi import FastAPI
from src.core.coordinator import Coordinator

app = FastAPI(title="INTRADYNE", version="1.1")
coordinator = Coordinator()

@app.get("/")
def read_root():
    return {"status": "ONLINE", "identity": "INTRADYNE v1.1", "mode": "HYBRID"}

@app.post("/analyze")
def analyze_market(data: dict):
    """
    Endpoint to trigger the analysis pipeline.
    """
    result = coordinator.run_pipeline(data)
    return {"status": "PROCESSED", "result": result}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
