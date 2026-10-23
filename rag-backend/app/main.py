from fastapi import FastAPI

app = FastAPI(
    title="Portfolio RAG API",
    description="Backend API for the portfolio AI assistant",
    version="0.1.0",
)


@app.get("/")
def root():
    return {
        "message": "Portfolio RAG API is running",
        "status": "ok",
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
    }
