from fastapi import FastAPI
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from podscriber import get_podcast_entries
from config import CHROMADB_DB_PATH
import chromadb
from starlette.requests import Request
import os

app = FastAPI()

# Set up Jinja2 templates directory
templates = Jinja2Templates(directory="templates")

# Configuration and Constants
CHROMADB_DB_PATH = os.path.expanduser(CHROMADB_DB_PATH)

# Global variable to store ChromaDB client and collection
client = None
podcast_collection = None

@app.on_event("startup")
async def startup_event():
    global client, podcast_collection
    client = chromadb.PersistentClient(path=CHROMADB_DB_PATH)
    podcast_collection = client.get_or_create_collection(name="podcasts")
    client.heartbeat()
    print("ChromaDB initialized.")

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    entries = get_podcast_entries(podcast_collection)  # Fetch dynamic data from ChromaDB
    return templates.TemplateResponse("index.html", {"request": request, "entries": entries})
