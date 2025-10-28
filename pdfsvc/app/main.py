from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from io import BytesIO
import qrcode

app = FastAPI(title="PDF/QR Service")

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/qr/{text}")
def qr_png(text: str):
    img = qrcode.make(text)
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return StreamingResponse(buf, media_type="image/png")
