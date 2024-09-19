from fastapi import FastAPI, Response
from fastapi.responses import HTMLResponse
from config import PODCAST_HISTORY_FILE
import os

app = FastAPI()

@app.get("/", response_class=HTMLResponse)
def read_root():
    # Expand the user path for PODCAST_HISTORY_FILE
    expanded_path = os.path.expanduser(PODCAST_HISTORY_FILE)
    with open(expanded_path, "r") as f:
        html_content = f.read()
    return HTMLResponse(content=html_content, status_code=200)
