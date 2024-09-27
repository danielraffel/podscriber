import os
import shutil
import requests
import sys
import re
from config import REPO_ROOT, PODCAST_AUDIO_FOLDER, PODCAST_HISTORY_FILE, TRANSCRIBED_FOLDER, CHROMADB_DB_PATH, GITHUB_USERNAME, GITHUB_TOKEN, GITHUB_REPO_NAME

# Function to display help message
def show_help():
    """
    Display usage instructions and available options for the cleanup script.
    Exits the program after showing the help message.
    """
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
      --reset                 Delete the entire local repo folder and remote GitHub repo
      --reset-local-only      Delete only the local repo folder, leave GitHub repo intact
      --reset-local-deploy-keys Reset deploy keys in config.txt and remove local key files
      -h, --help              Show this help message
    """
    print(help_message)
    exit(0)

# Helper function to delete a folder
def delete_folder(path):
    """
    Attempt to delete a folder at the given path.
    Prints success or failure messages.
    """
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
    """
    Attempt to delete a file at the given path.
    Prints success or failure messages.
    """
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
    """
    Delete all files and subdirectories within a folder, keeping the folder itself.
    Prints progress messages for each deleted item.
    """
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

# Function to delete the entire local repo folder
def delete_local_repo():
    """
    Delete the entire local repository folder.
    This function removes the entire REPO_ROOT directory and its contents.
    """
    try:
        shutil.rmtree(REPO_ROOT)
        print(f"Deleted entire local repository: {REPO_ROOT}")
    except Exception as e:
        print(f"Failed to delete local repository: {e}")

# Function to delete the remote GitHub repo
def delete_remote_repo():
    """
    Delete the remote GitHub repository.
    This function uses the GitHub API to delete the remote repository.
    """
    REPO_URL = f"https://api.github.com/repos/{GITHUB_USERNAME}/{GITHUB_REPO_NAME}"
    print(f"Attempting to delete remote repository: {REPO_URL}")

    response = requests.delete(REPO_URL, auth=(GITHUB_USERNAME, GITHUB_TOKEN))
    if response.status_code == 204:
        print(f"Remote repository {GITHUB_REPO_NAME} deleted successfully.")
    else:
        print(f"Failed to delete remote repository: {response.status_code}")

# New function to reset deploy keys
def reset_deploy_keys():
    """
    Reset the PUBLIC_SSH_KEY and PRIVATE_SSH_KEY values in config.py to their default values
    and remove the corresponding key files from the local machine.
    """
    # If you want to reset the deploy keys in the repo_root config.py file, uncomment the following line:
    # config_file = os.path.join(REPO_ROOT, 'config.py')
    config_file = os.path.join(os.path.dirname(__file__), 'config.py')  # Change to current directory
    if not os.path.exists(config_file):
        print(f"Config file not found: {config_file}")
        return

    with open(config_file, 'r') as f:
        config_content = f.read()

    # Update config values
    config_content = re.sub(r'PUBLIC_SSH_KEY\s*=\s*"[^"]*"', f'PUBLIC_SSH_KEY = "~/.ssh/{GITHUB_REPO_NAME}_randomstring.pub"', config_content)
    config_content = re.sub(r'PRIVATE_SSH_KEY\s*=\s*"[^"]*"', f'PRIVATE_SSH_KEY = "~/.ssh/{GITHUB_REPO_NAME}_randomstring"', config_content)

    with open(config_file, 'w') as f:
        f.write(config_content)

    print("Updated config.py with default deploy key values")

    # Remove existing key files
    public_key_path = os.path.expanduser(f"~/.ssh/{GITHUB_REPO_NAME}_*.pub")
    private_key_path = os.path.expanduser(f"~/.ssh/{GITHUB_REPO_NAME}_*")

    keys_removed = False  # Track if any keys were removed

    for key_path in [public_key_path, private_key_path]:
        matching_files = [f for f in os.listdir(os.path.dirname(key_path)) if os.path.basename(key_path).replace('*', '') in f]
        for file in matching_files:
            full_path = os.path.join(os.path.dirname(key_path), file)
            os.remove(full_path)
            print(f"Removed key file: {full_path}")
            keys_removed = True

    if not keys_removed:
        print("No SSH key files found to remove.")

# Default flags
DELETE_GIT = True
DELETE_CHROMADB = True
DELETE_CHROMAHASH = True
DELETE_HISTORY = True
DELETE_AUDIO = True
DELETE_TRANSCRIBED = True
DELETE_REPO = True
RESET = False
RESET_LOCAL_ONLY = False
RESET_DEPLOY_KEYS = False

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
    elif arg == "--reset":
        RESET = True
    elif arg == "--reset-local-only":
        RESET_LOCAL_ONLY = True
    elif arg == "--reset-local-deploy-keys":
        RESET_DEPLOY_KEYS = True
    else:
        print(f"Unknown option: {arg}")
        show_help()

# Expand user paths to ensure full path resolution
REPO_ROOT = os.path.expanduser(REPO_ROOT)
PODCAST_AUDIO_FOLDER = os.path.expanduser(PODCAST_AUDIO_FOLDER)
TRANSCRIBED_FOLDER = os.path.expanduser(TRANSCRIBED_FOLDER)
PODCAST_HISTORY_FILE = os.path.expanduser(PODCAST_HISTORY_FILE)
CHROMA_HASH_FILE = os.path.join(REPO_ROOT, "chroma_hashes.txt")

# Check flags and perform actions
if RESET:
    # If reset flag is set, delete both local and remote repositories and reset deploy keys
    delete_local_repo()
    delete_remote_repo()
    reset_deploy_keys()
elif RESET_LOCAL_ONLY:
    # If reset-local-only flag is set, only delete the local repository
    delete_local_repo()
elif RESET_DEPLOY_KEYS:
    # If reset-deploy-keys flag is set, only reset the deploy keys
    reset_deploy_keys()
else:
    # Perform individual deletion operations based on flags
    if DELETE_GIT:
        delete_folder(os.path.join(REPO_ROOT, ".git"))
    if DELETE_CHROMADB:
        delete_folder(CHROMADB_DB_PATH)
    if DELETE_CHROMAHASH:
        delete_file(CHROMA_HASH_FILE)
    if DELETE_HISTORY:
        delete_file(PODCAST_HISTORY_FILE)
    if DELETE_AUDIO:
        delete_folder_contents(PODCAST_AUDIO_FOLDER)
    if DELETE_TRANSCRIBED:
        delete_folder_contents(TRANSCRIBED_FOLDER)
    if DELETE_REPO:
        delete_remote_repo()

print("Cleanup completed.")