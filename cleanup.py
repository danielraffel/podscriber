import os
import shutil
import requests
from config import REPO_ROOT, PODCAST_AUDIO_FOLDER, PODCAST_HISTORY_FILE, TRANSCRIBED_FOLDER, CHROMADB_DB_PATH, GITHUB_USERNAME, GITHUB_TOKEN, GITHUB_REPO_NAME

# Function to display help message
def show_help():
    help_message = """
    Usage: cleanup.py [options]

    Options:
      --no-delete-chromadb    Skip deleting the Chromadb directory
      --no-delete-chromahash  Skip deleting the Chroma hash file
      --no-delete-git         Skip deleting the .git directory
      --no-delete-history     Skip deleting the podcast history file
      --no-delete-audio       Skip deleting files in the podcast audio folder
      --no-delete-transcribed Skip deleting files in the transcribed folder
      --no-delete-repo        Skip deleting the GitHub repository
      -h, --help              Show this help message
    """
    print(help_message)
    exit(0)

# Default flags (all operations enabled)
DELETE_GIT = True
DELETE_CHROMADB = True
DELETE_CHROMAHASH = True
DELETE_HISTORY = True
DELETE_AUDIO = True
DELETE_TRANSCRIBED = True
DELETE_REPO = True

# Parse command-line arguments
import sys
for arg in sys.argv[1:]:
    if arg in ("-h", "--help"):
        show_help()
    elif arg == "--no-delete-chromadb":
        DELETE_CHROMADB = False
    elif arg == "--no-delete-chromahash":
        DELETE_CHROMAHASH = False
    elif arg == "--no-delete-git":
        DELETE_GIT = False
    elif arg == "--no-delete-history":
        DELETE_HISTORY = False
    elif arg == "--no-delete-audio":
        DELETE_AUDIO = False
    elif arg == "--no-delete-transcribed":
        DELETE_TRANSCRIBED = False
    elif arg == "--no-delete-repo":
        DELETE_REPO = False
    else:
        print(f"Unknown option: {arg}")
        show_help()

# Expand user paths
REPO_ROOT = os.path.expanduser(REPO_ROOT)
PODCAST_AUDIO_FOLDER = os.path.expanduser(PODCAST_AUDIO_FOLDER)
TRANSCRIBED_FOLDER = os.path.expanduser(TRANSCRIBED_FOLDER)
PODCAST_HISTORY_FILE = os.path.expanduser(PODCAST_HISTORY_FILE)
CHROMA_HASH_FILE = os.path.join(REPO_ROOT, "chroma_hashes.txt")

# Delete specific files and directories based on flags
if DELETE_GIT:
    git_path = os.path.join(REPO_ROOT, ".git")
    print(f"Deleting {git_path}")
    shutil.rmtree(git_path, ignore_errors=True)

if DELETE_CHROMADB:
    print(f"Deleting all files and directories within {CHROMADB_DB_PATH}")
    shutil.rmtree(CHROMADB_DB_PATH, ignore_errors=True)

if DELETE_CHROMAHASH:
    print(f"Deleting {CHROMA_HASH_FILE}")
    if os.path.exists(CHROMA_HASH_FILE):
        os.remove(CHROMA_HASH_FILE)

if DELETE_HISTORY:
    print(f"Deleting {PODCAST_HISTORY_FILE}")
    if os.path.exists(PODCAST_HISTORY_FILE):
        os.remove(PODCAST_HISTORY_FILE)

if DELETE_AUDIO:
    print(f"Deleting all files and directories within {PODCAST_AUDIO_FOLDER}")
    shutil.rmtree(PODCAST_AUDIO_FOLDER, ignore_errors=True)

if DELETE_TRANSCRIBED:
    print(f"Deleting all files and directories within {TRANSCRIBED_FOLDER}")
    shutil.rmtree(TRANSCRIBED_FOLDER, ignore_errors=True)

if DELETE_REPO:
    REPO_URL = f"https://github.com/{GITHUB_USERNAME}/{GITHUB_REPO_NAME}"
    print(f"Checking if repository exists at {REPO_URL}")

    # Check if the repository exists
    response = requests.get(REPO_URL, auth=(GITHUB_USERNAME, GITHUB_TOKEN))
    if response.status_code == 200:
        print(f"Repository {GITHUB_REPO_NAME} exists. Deleting...")
        delete_response = requests.delete(REPO_URL, auth=(GITHUB_USERNAME, GITHUB_TOKEN))
        if delete_response.status_code == 204:
            print(f"Repository {GITHUB_REPO_NAME} deleted.")
        else:
            print(f"Failed to delete repository: {delete_response.status_code}")
    else:
        print(f"Repository {GITHUB_REPO_NAME} does not exist.")
