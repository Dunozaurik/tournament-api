from fastapi import FastAPI
from fastapi.responses import PlainTextResponse

app = FastAPI(title="Tournament API")

@app.get("/health", response_class=PlainTextResponse)
def health():
    return "ok"