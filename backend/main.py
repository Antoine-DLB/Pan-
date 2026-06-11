"""Far West Showdown — FastAPI application entrypoint."""

from fastapi import FastAPI

app = FastAPI(title="Far West Showdown")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
