import os
import shutil
import requests
import sys
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

# Helper function to delete a folder
def delete_folder(path):
    if os.path.exists(path):
        try:
            shutil.rmtree(path)
            print(f"Deleted: {path}")
        except Exception as e:
            print(f"Failed to delete {path}: {e}")
    else:
        print(f"Path does not exist: {path}")

# Helper function to delete a file
def delete_file(path):
    if os.path.exists(path):
        try:
            os.remove(path)
            print(f"Deleted: {path}")
        except Exception as e:
            print(f"Failed to delete {path}: {e}")
    else:
        print(f"File does not exist: {path}")

# Helper function to delete contents of a folder but not the folder itself
def delete_folder_contents(path):
    if os.path.exists(path):
        try:
            for root, dirs, files in os.walk(path):
                for file in files:
                    file_path = os.path.join(root, file)
                    os.remove(file_path)
                    print(f"Deleted file: {file_path}")
                for dir in dirs:
                    dir_path = os.path.join(root, dir)
                    shutil.rmtree(dir_path)
                    print(f"Deleted directory: {dir_path}")
        except Exception as e:
            print(f"Failed to delete contents of {path}: {e}")
    else:
        print(f"Path does not exist: {path}")

# Default flags (all operations enabled)
DELETE_GIT = True
DELETE_CHROMADB = True
DELETE_CHROMAHASH = True
DELETE_HISTORY = True
DELETE_AUDIO = True
DELETE_TRANSCRIBED = True
DELETE_REPO = True

# Parse command-line arguments
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
    delete_folder(os.path.join(REPO_ROOT, ".git"))

if DELETE_CHROMADB:
    delete_folder(CHROMADB_DB_PATH)

if DELETE_CHROMAHASH:
    delete_file(CHROMA_HASH_FILE)

if DELETE_HISTORY:
    delete_file(PODCAST_HISTORY_FILE)

if DELETE_AUDIO:
    delete_folder_contents(PODCAST_AUDIO_FOLDER)  # Only delete contents

if DELETE_TRANSCRIBED:
    delete_folder_contents(TRANSCRIBED_FOLDER)  # Only delete contents

if DELETE_REPO:
    REPO_URL = f"https://api.github.com/repos/{GITHUB_USERNAME}/{GITHUB_REPO_NAME}"
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
