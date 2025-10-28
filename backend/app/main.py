from fastapi import FastAPI

app = FastAPI(title="Tickets API")

@app.get("/health")
async def health():
    return {"status": "ok"}
