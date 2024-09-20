import os
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
import html
import re
import subprocess
import shutil
import hashlib
import chromadb
import inspect

# Import configuration
from config import (
    RSS_FEED_URL, PODCAST_AUDIO_FOLDER, WHISPER_MODEL_PATH,
    WHISPER_EXECUTABLE, TRANSCRIBED_FOLDER, AUTO_OVERWRITE, GITHUB_REPO_CHECK,
    GITHUB_REPO_NAME, ENABLE_GITHUB_COMMIT, UPDATE_HTML_LINKS,
    GITHUB_USERNAME, GITHUB_TOKEN, GITHUB_REPO_PRIVATE, DEBUG_MODE_LIMIT, 
    REPO_ROOT, ENABLE_GITHUB_PAGES,
    WHISPER_SETUP, WHISPER_ROOT,CHROMADB_DB_PATH, TOKENIZERS_PARALLELISM,
    USE_EXISTING_DATA, APP_ENTRY, JINJA_TEMPLATES
)

# Ensure the APP_ENTRY, JINJA_TEMPLATES, pyproject.toml, and config.py (from repo_root_config.py) are copied into the Git repository.
def ensure_files_copied():
    """Ensure the APP_ENTRY, JINJA_TEMPLATES, pyproject.toml, and config.py (from repo_root_config.py) are copied into the Git repository."""
    app_entry_copy = os.path.join(REPO_ROOT, "main.py")
    jinja_templates_copy = os.path.join(REPO_ROOT, "templates")
    config_copy = os.path.join(REPO_ROOT, "config.py")
    pyproject_copy = os.path.join(REPO_ROOT, "pyproject.toml")
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_source = os.path.join(script_dir, "repo_root_config.py")
    pyproject_source = os.path.join(script_dir, "pyproject.toml")

    # Copy APP_ENTRY file to the repository
    if not os.path.exists(app_entry_copy) or os.path.getmtime(app_entry_copy) < os.path.getmtime(APP_ENTRY):
        shutil.copy(APP_ENTRY, app_entry_copy)
        print(f"Copied {APP_ENTRY} to {app_entry_copy}")
        run_git_command(["git", "add", app_entry_copy], REPO_ROOT)  # Add to git
        run_git_command(["git", "commit", "-m", "Update main.py"], REPO_ROOT)  # Commit changes
    else:
        print(f"{app_entry_copy} already exists and is up-to-date.")

    # Copy JINJA_TEMPLATES directory to the repository
    if not os.path.exists(jinja_templates_copy):
        shutil.copytree(JINJA_TEMPLATES, jinja_templates_copy)
        print(f"Copied {JINJA_TEMPLATES} to {jinja_templates_copy}")
        run_git_command(["git", "add", jinja_templates_copy], REPO_ROOT)  # Add to git
        run_git_command(["git", "commit", "-m", "Update templates"], REPO_ROOT)  # Commit changes
    else:
        print(f"{jinja_templates_copy} already exists.")

    # Copy repo_root_config.py to the repository as config.py
    if not os.path.exists(config_copy) or os.path.getmtime(config_copy) < os.path.getmtime(config_source):
        shutil.copy(config_source, config_copy)
        print(f"Copied {config_source} to {config_copy}")
        run_git_command(["git", "add", config_copy], REPO_ROOT)  # Add to git
        run_git_command(["git", "commit", "-m", "Update config.py"], REPO_ROOT)  # Commit changes
    else:
        print(f"{config_copy} already exists and is up-to-date.")

    # Copy pyproject.toml to the repository
    if not os.path.exists(pyproject_copy) or os.path.getmtime(pyproject_copy) < os.path.getmtime(pyproject_source):
        shutil.copy(pyproject_source, pyproject_copy)
        print(f"Copied {pyproject_source} to {pyproject_copy}")
        run_git_command(["git", "add", pyproject_copy], REPO_ROOT)  # Add to git
        run_git_command(["git", "commit", "-m", "Update pyproject.toml"], REPO_ROOT)  # Commit changes
    else:
        print(f"{pyproject_copy} already exists and is up-to-date.")

# Initialize ChromaDB globally so we can use it in FastAPI
client = chromadb.PersistentClient(path=os.path.expanduser(CHROMADB_DB_PATH))
podcast_collection = client.get_or_create_collection(name="podcasts")
client.heartbeat()

# Set Hugging Face Tokenizers environment variable
os.environ["TOKENIZERS_PARALLELISM"] = TOKENIZERS_PARALLELISM

# Configuration and Constants
REPO_ROOT = os.path.expanduser(REPO_ROOT)
PODCAST_AUDIO_FOLDER = os.path.expanduser(PODCAST_AUDIO_FOLDER)
TRANSCRIBED_FOLDER = os.path.join(REPO_ROOT, "transcribed")
CHROMADB_DB_PATH = os.path.expanduser(CHROMADB_DB_PATH)

# Get podcast entries from ChromaDB
def get_podcast_entries():
    global podcast_collection

    # Query all documents from the ChromaDB collection
    results = podcast_collection.get()

    # Initialize an empty list to store the entries
    entries = []

    # Check if results contain documents
    if 'documents' in results and len(results['documents']) > 0:
        documents = results['documents']
        ids = results['ids']
        metadatas = results.get('metadatas', [])
        
        # Loop through each document and metadata
        for document, guid, metadata in zip(documents, ids, metadatas):
            # Extract metadata fields, with defaults for missing data
            podcast_name = metadata.get("podcast_name", "Unknown Podcast")
            episode_title = metadata.get("episode_title", "Unknown Episode")
            listen_date = metadata.get("listenDate", "Unknown Date")
            transcript_url = metadata.get("transcript_url", "#")
            mp3_url = metadata.get("mp3_url", "#")  
            link = metadata.get("link", "#")  

            # Append each entry as a dictionary
            entries.append({
                "podcast_name": podcast_name,
                "episode_title": episode_title,
                "listen_date": listen_date,
                "transcript_url": transcript_url,  
                "mp3_url": mp3_url,
                "link": link,
                "guid": guid
            })

    return entries

# Check if git is installed and error out if not
def check_git_installed():
    """Ensure git is installed on the system."""
    try:
        subprocess.run(["git", "--version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print("Git is installed.")
    except subprocess.CalledProcessError:
        print("Git is not installed. Please install git before running the script.")
        exit(1)

# Ensure that each Git command checks for successful execution and handles failures appropriately
def run_git_command(command, cwd):
    result = subprocess.run(command, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Git command {' '.join(command)} failed with error: {result.stderr}")
        return False
    return True

# Check if SSH connection to GitHub is properly configured using SSH key
def check_github_ssh_connection():
    """Check if SSH connection to GitHub is properly configured."""
    try:
        result = subprocess.run(
            ["ssh", "-T", "git@github.com"], 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE
        )
        response = result.stdout.decode('utf-8') + result.stderr.decode('utf-8')
        if "successfully authenticated" in response.lower():
            print("SSH connection to GitHub is properly configured.")
            return True
        elif "are you sure you want to continue connecting" in response.lower():
            print("SSH key fingerprint not recognized. Try connecting manually to accept the new fingerprint.")
            return False
        else:
            print("SSH connection to GitHub failed. Please configure your SSH keys properly.")
            print(f"SSH response: {response}")
            return False
    except Exception as e:
        print(f"SSH connection to GitHub encountered an error: {e}")
        return False

# Check if the GitHub repository exists, and create it if not
def check_create_github_repo(repo_name):
    """Check if the GitHub repository exists, and create it if not."""
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    url = f"https://api.github.com/repos/{GITHUB_USERNAME}/{repo_name}"
    
    response = requests.get(url, headers=headers)
    if response.status_code == 404:
        print(f"Repository {repo_name} not found. Creating new repository...")
        create_repo_url = "https://api.github.com/user/repos"
        data = {
            "name": repo_name,
            "private": GITHUB_REPO_PRIVATE  # Use the setting from the config file
        }
        create_response = requests.post(create_repo_url, headers=headers, json=data)
        create_response.raise_for_status()
        print(f"Repository {repo_name} created successfully.")
    else:
        print(f"Repository {repo_name} exists.")

# Check if the directory is a Git repository and return the result
def is_git_repo(repo_root):
    """Check if the directory is a Git repository."""
    return os.path.exists(os.path.join(repo_root, ".git"))

# Initialize the local Git repository or pull changes if it already exists
def initialize_local_git_repo(repo_root):
    """Initialize the local Git repository or pull changes if it already exists."""
    if not os.path.exists(repo_root):
        print(f"Cloning repository into {repo_root}...")
        if not run_git_command(["git", "clone", f"git@github.com:{GITHUB_USERNAME}/{GITHUB_REPO_NAME}.git", repo_root], cwd="."):
            print("Failed to clone repository.")
            return
    else:
        if is_git_repo(repo_root):
            print(f"Git repository already initialized in {repo_root}, pulling latest changes.")
            if not run_git_command(["git", "pull", "origin", "main"], cwd=repo_root):
                print("Failed to pull latest changes.")
                return
        else:
            print(f"Directory {repo_root} exists but is not a git repository. Initializing as git repository.")
            if not run_git_command(["git", "init"], cwd=repo_root):
                print("Failed to initialize git repository.")
                return
            if not run_git_command(["git", "remote", "add", "origin", f"git@github.com:{GITHUB_USERNAME}/{GITHUB_REPO_NAME}.git"], cwd=repo_root):
                print("Failed to add remote origin.")
                return
            # Check if the remote has any commits
            result = subprocess.run(["git", "ls-remote", "--heads", "origin"], cwd=repo_root, capture_output=True, text=True)
            if result.stdout.strip():
                # Remote repository has commits, pull them
                if not run_git_command(["git", "pull", "origin", "main"], cwd=repo_root):
                    print("Failed to pull from remote repository.")
                    return
                print("Pulled existing main branch from remote.")
            else:
                # Remote is empty, create initial commit and push
                create_initial_commit(repo_root)
                print("Created and pushed initial commit to main branch.")

# Create the initial commit in the local Git repository and push it to the remote repository if it's empty
def create_initial_commit(repo_root):
    """Create the initial commit in the local Git repository."""
    readme_path = os.path.join(repo_root, "README.md")
    try:
        with open(readme_path, "w") as f:
            f.write(f"# {GITHUB_REPO_NAME}\n\nThis repository contains podcast archives.")
        if not run_git_command(["git", "add", "README.md"], repo_root):
            print("Failed to add README.md to Git.")
            return
        if not run_git_command(["git", "commit", "-m", "Initial commit"], repo_root):
            print("Failed to commit README.md.")
            return
        if not run_git_command(["git", "branch", "-M", "main"], repo_root):
            print("Failed to rename branch to main.")
            return
        if not run_git_command(["git", "push", "-u", "origin", "main"], repo_root):
            print("Failed to push initial commit to remote.")
            return
        print("Initial commit created and pushed successfully.")
    except Exception as e:
        print(f"Error during initial commit: {e}")

# Check if GitHub Pages is already enabled
def check_github_pages_enabled():
    """Check if GitHub Pages is already enabled."""
    url = f"https://api.github.com/repos/{GITHUB_USERNAME}/{GITHUB_REPO_NAME}/pages"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    response = requests.get(url, headers=headers)
    return response.status_code == 200

# Enable GitHub Pages for the repository
def enable_github_pages():
    """Enable GitHub Pages for the repository."""
    if check_github_pages_enabled():
        print(f"GitHub Pages is already enabled for {GITHUB_REPO_NAME}.")
        return

    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    url = f"https://api.github.com/repos/{GITHUB_USERNAME}/{GITHUB_REPO_NAME}/pages"
    
    data = {
        "source": {
            "branch": "main",
            "path": "/"
        }
    }
    
    response = requests.post(url, headers=headers, json=data)
    if response.status_code in [201, 204]:
        print(f"GitHub Pages enabled for repository {GITHUB_REPO_NAME}.")
    else:
        print(f"Failed to enable GitHub Pages: {response.status_code} - {response.text}")

# Calculate the SHA-256 hash of the local chroma_db directory so we can compare it to the remote repo
def file_hash(filepath):
    """Calculate the SHA-256 hash of the given file."""
    sha256 = hashlib.sha256()
    with open(filepath, 'rb') as f:
        for block in iter(lambda: f.read(4096), b''):
            sha256.update(block)
    return sha256.hexdigest()

# Pull a file from GitHub and save it locally
def pull_github_file(repo_name, filepath, destination):
    """Pull a file from GitHub and save it locally."""
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3.raw"
    }
    url = f"https://raw.githubusercontent.com/{GITHUB_USERNAME}/{repo_name}/main/{filepath}"
    
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    
    with open(destination, 'wb') as f:
        f.write(response.content)
    
    print(f"Pulled {filepath} from GitHub and saved to {destination}.")

# Check if the repository has an initial commit
def has_initial_commit(repo_root):
    """Check if the repository has an initial commit."""
    result = subprocess.run(
        ["git", "rev-parse", "--verify", "HEAD"],
        cwd=repo_root,
        capture_output=True,
        text=True
    )
    return result.returncode == 0

# Commit changes to the database directory, HTML file, and new transcribed files
def commit_database_and_files(db_path, new_files):
    """Commit changes to the database directory, new transcribed files, symlinked APP_ENTRY, and JINJA_TEMPLATES folder."""

    if db_path and not os.path.exists(db_path):
        print(f"Error: Database path {db_path} does not exist.")
        return False

    try:
        has_commit = has_initial_commit(REPO_ROOT)

        if not has_commit:
            print("No initial commit found. Creating initial commit.")
            create_initial_commit(REPO_ROOT)

        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True
        ).stdout
        if status.strip():
            if not run_git_command(["git", "stash"], cwd=REPO_ROOT):
                print("Failed to stash changes.")
                return False
        else:
            print("No changes to stash.")

        if not run_git_command(["git", "pull", "--rebase", "origin", "main"], cwd=REPO_ROOT):
            print("Failed to pull latest changes.")
            return False

        result = subprocess.run(
            ["git", "stash", "pop"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            if "No stash entries found" in result.stderr or "No stash entries found" in result.stdout:
                print("No stash entries to pop.")
            else:
                print(f"Error during git stash pop: {result.stderr}")
                return False
            
        

        # Add the ChromaDB database directory
        if db_path:
            print(f"Adding to Git: {os.path.relpath(db_path, REPO_ROOT)}")
            if not run_git_command(
                ["git", "add", os.path.relpath(db_path, REPO_ROOT)],
                cwd=REPO_ROOT
            ):
                print("Failed to add database directory to Git.")
                return False

        if os.path.exists(TRANSCRIBED_FOLDER):
            print(f"Adding to Git: {os.path.relpath(TRANSCRIBED_FOLDER, REPO_ROOT)}")
            if not run_git_command(
                ["git", "add", os.path.relpath(TRANSCRIBED_FOLDER, REPO_ROOT)],
                cwd=REPO_ROOT
            ):
                print("Failed to add transcribed folder to Git.")
                return False

        hash_file = os.path.join(REPO_ROOT, 'chroma_hashes.txt')
        if os.path.exists(hash_file):
            print(f"Adding to Git: {os.path.relpath(hash_file, REPO_ROOT)}")
            if not run_git_command(
                ["git", "add", os.path.relpath(hash_file, REPO_ROOT)],
                cwd=REPO_ROOT
            ):
                print("Failed to add chroma_hashes.txt to Git.")
                return False

        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True
        ).stdout
        if status.strip():
            if not run_git_command(
                ["git", "commit", "-m", "Update database, APP_ENTRY symlink, JINJA_TEMPLATES symlink, and podcast files"],
                cwd=REPO_ROOT
            ):
                print("Failed to commit changes.")
                return False
            if not run_git_command(["git", "push", "origin", "main"], cwd=REPO_ROOT):
                print("Failed to push changes to remote.")
                return False
            print("Database, APP_ENTRY symlink, JINJA_TEMPLATES symlink, and podcast files committed and pushed.")
            return True
        else:
            print("No changes to commit.")
            return False

    except Exception as e:
        print(f"Failed to commit changes: {e}")
        return False

# Add the podcast metadata and transcript to the ChromaDB collection
def add_podcast_to_db_chroma(metadata, mp3_url, transcript_name, transcript_text):
    global podcast_collection
    # Construct the GitHub transcript URL
    transcript_github_url = f"https://raw.githubusercontent.com/{GITHUB_USERNAME}/{GITHUB_REPO_NAME}/main/transcribed/{normalize_folder_name(metadata['podcast_name'])}/{transcript_name}"
    
    # Update the metadata with the mp3_url and transcript_url
    metadata['mp3_url'] = mp3_url  # Store the mp3 URL in the metadata
    metadata['transcript_url'] = transcript_github_url  # Store the transcript GitHub URL in the metadata
    
    # Add the document to ChromaDB with the transcript and metadata
    document = f"{metadata['podcast_name']} - {metadata['episode_title']}\nTranscript: {transcript_text}"
    
    podcast_collection.upsert(
        documents=[document],  # Add the transcript text
        ids=[metadata['guid']],  # Use the GUID as the document ID
        metadatas=[metadata]  # Store the metadata, including transcript URL
    )
    print(f"Data committed to ChromaDB with transcript URL: {transcript_github_url}")

# Generate SHA-256 hashes for all files in the ChromaDB directory and save them
def generate_chroma_hashes(db_path, repo_root, hash_file):
    """Generate SHA-256 hashes for all files in the ChromaDB directory and save them."""
    hashes = []
    for root, dirs, files in os.walk(db_path):
        for file in files:
            file_path = os.path.join(root, file)
            # Generate a path relative to the repository root
            file_rel_path = os.path.relpath(file_path, repo_root).replace('\\', '/')
            file_hash_value = file_hash(file_path)
            hashes.append(f"{file_rel_path}:{file_hash_value}")
    # Sort the hashes to ensure consistent order
    hashes.sort()
    with open(hash_file, 'w', newline='\n') as f:
        f.write("\n".join(hashes))
    print(f"ChromaDB hashes generated and saved to {hash_file}.")

# Compare local and remote hash files to determine if pulling is necessary
def compare_chroma_hashes(local_hash_file, remote_hash_file):
    """Compare local and remote hash files to determine if pulling is necessary."""
    with open(local_hash_file, 'r') as f:
        local_hashes = set(line.strip() for line in f)
    with open(remote_hash_file, 'r') as f:
        remote_hashes = set(line.strip() for line in f)
    if local_hashes == remote_hashes:
        print("Local ChromaDB files are up-to-date.")
        return True
    else:
        print("Local ChromaDB files differ from remote.")
        # Debugging: Print the differences
        print("Differences:")
        print("In local but not in remote:")
        for line in local_hashes - remote_hashes:
            print(line)
        print("In remote but not in local:")
        for line in remote_hashes - local_hashes:
            print(line)
        return False

# Pull the latest ChromaDB files from the GitHub repository and sync the local database
def check_and_sync_chromadb(repo_name, db_path, remote_db_dir):
    """Pull the latest ChromaDB files from the GitHub repository and sync the local database."""
    print("Syncing ChromaDB from remote repository...")
    # Pull the latest database files from GitHub
    if not run_git_command(["git", "fetch", "origin"], cwd=REPO_ROOT):
        print("Failed to fetch from remote repository.")
        return False

    # Reset the local database directory to match the remote
    if not run_git_command(["git", "checkout", f"origin/main", "--", remote_db_dir], cwd=REPO_ROOT):
        print("Failed to checkout database directory from remote repository.")
        return False

    print("ChromaDB files synced from remote repository.")
    return True

# Check if sync is necessary by comparing local and remote hashes
def pull_and_sync_chromadb_if_necessary(repo_name, db_path, hash_file, remote_db_dir):
    """Check if sync is necessary by comparing local and remote hashes."""
    remote_hash_file = os.path.join(REPO_ROOT, 'remote_chroma_hashes.txt')

    # Check if the remote hash file exists
    try:
        pull_github_file(repo_name, os.path.basename(hash_file), remote_hash_file)
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            print(f"Remote hash file does not exist. Skipping sync.")
            return
        else:
            raise  # Re-raise the error if it's not a 404

    # If the file was found, proceed with the comparison
    if compare_chroma_hashes(hash_file, remote_hash_file):
        print("No sync needed.")
    else:
        check_and_sync_chromadb(repo_name, db_path, remote_db_dir)

    os.remove(remote_hash_file)  # Clean up the temporary remote hash file

# Process the RSS feed, download new MP3 files, transcribe them, and store data in ChromaDB
def process_feed(feed_url, download_folder, debug=True):
    global podcast_collection
    """Process the RSS feed, download new MP3 files, transcribe them, and store data in ChromaDB."""
    
    if USE_EXISTING_DATA and os.path.exists(CHROMADB_DB_PATH) and os.path.exists(TRANSCRIBED_FOLDER):
        print("Using existing ChromaDB and transcript data.")
        return []  # No new files to delete

    if debug:
        print(f"Fetching feed from {feed_url}")
    
    response = requests.get(feed_url)
    response.raise_for_status()

    root = ET.fromstring(response.content)

    new_files = []  # This will now store tuples of (mp3_file_path, wav_file_path)

    # Adjust the limit for the first run if no existing data
    limit = 1 if not os.path.exists(CHROMADB_DB_PATH) else DEBUG_MODE_LIMIT

    for item in root.findall('./channel/item')[:limit]:
        full_title = item.find('title').text
        pubDate = item.find('pubDate').text
        guid = item.find('guid').text
        link = item.find('link').text
        enclosure = item.find('enclosure')

        # Extract podcast and episode titles
        try:
            podcast_name, episode_title = extract_podcast_and_episode(full_title)
            if not podcast_name or not episode_title:
                print(f"Skipping due to missing podcast or episode title: {full_title}")
                continue
        except Exception as e:
            print(f"Error extracting podcast and episode from title '{full_title}': {e}")
            continue

        # Use pubDate as listenDate
        listenDate = pubDate if pubDate else datetime.now().strftime("%a, %d %b %Y %H:%M:%S %z")
        
        if enclosure is not None:
            mp3_url = enclosure.get('url')
            if mp3_url:
                if debug:
                    print(f"Enclosure URL found: {mp3_url}")
                
                # Construct metadata dictionary
                metadata = {
                    "podcast_name": podcast_name,
                    "episode_title": episode_title,
                    "listenDate": listenDate,
                    "guid": guid if guid else mp3_url,
                    "link": link if link else ""
                }
                
                # Check if the guid already exists in the collection
                existing_doc = podcast_collection.get(ids=[guid])
                already_processed = len(existing_doc['ids']) > 0

                if already_processed:
                    if debug:
                        print(f"File already processed: {mp3_url}")
                    continue

                try:
                    # Download the MP3 file
                    mp3_file_path, filename = download_file(mp3_url, download_folder, full_title)
                    
                    # Transcribe using Whisper
                    transcript_file, transcript_text = transcribe_with_whisper(mp3_file_path, metadata)

                    # Organize the transcript file and get the new path
                    new_transcript_path = organize_podcast_files(podcast_name, episode_title, transcript_file)

                    if debug:
                        print(f"Organized file: Transcript={new_transcript_path}")

                    # Save podcast metadata into the ChromaDB, including transcript text and transcript URL
                    add_podcast_to_db_chroma(metadata, mp3_url, os.path.basename(new_transcript_path), transcript_text)

                    # Add both the MP3 and WAV file paths to new_files for deletion later
                    wav_file = mp3_file_path.replace('.mp3', '.wav')
                    new_files.append((mp3_file_path, wav_file))  # Append tuple with MP3 and WAV paths

                    if debug:
                        print(f"Downloaded, transcribed, and saved: {mp3_url} as {filename} with transcript {new_transcript_path}")
                    
                except Exception as e:
                    if debug:
                        print(f"Failed to process {mp3_url}: {e}")
        else:
            if debug:
                print(f"No enclosure found for {full_title}")

    return new_files  # Now returns tuples of (mp3_file_path, wav_file_path)

# Format the date to 'Month Day, Year' for TXT files
def format_date_long(date_str):
    """Format the date to 'Month Day, Year' for TXT files."""
    date_obj = datetime.strptime(date_str, "%a, %d %b %Y %H:%M:%S %z")
    return date_obj.strftime("%B %d, %Y")

# Format the date to 'MM/DD/YYYY' for HTML files
def format_date_short(date_str):
    """Format the date to 'MM/DD/YYYY' for HTML files."""
    date_obj = datetime.strptime(date_str, "%a, %d %b %Y %H:%M:%S %z")
    return date_obj.strftime("%m/%d/%Y")

# Extract the podcast and episode titles from the full title
def extract_podcast_and_episode(title):
    """Extract the podcast and episode titles from the full title."""
    # Log the title before processing
    print(f"Processing title: {title}")
    
    # Split the title into parts based on the first colon
    parts = title.split(": ", 1)  # Split only on the first colon
    
    if len(parts) == 2:
        podcast_name = parts[0].strip()  # The first part before the colon is the podcast name
        episode_title = parts[1].strip()  # The second part is the episode title
    else:
        # Fallback for unexpected formats, use the entire title as both name and title
        podcast_name = title.strip()
        episode_title = "Unknown Episode"
    
    # Log the results after processing
    print(f"Extracted podcast_name: {podcast_name}, episode_title: {episode_title}")
    
    return podcast_name, episode_title

# Normalize folder names by replacing spaces with underscores and removing non-alphanumeric characters
def normalize_folder_name(title):
    """Normalize folder names by replacing spaces with underscores and removing non-alphanumeric characters."""
    return re.sub(r'[^\w\s-]', '', title).replace(" ", "_").strip("_")

# Download the file from the URL and save it to the folder with a readable filename
def download_file(url, folder, title):
    """Download the file from the URL and save it to the folder with a readable filename."""
    # Ensure the folder exists
    if not os.path.exists(folder):
        os.makedirs(folder, exist_ok=True)
    
    filename = re.sub(r'[^\w\s-]', '', title).replace(" ", "_").strip("_")
    
    # Ensure the filename ends with '.mp3'
    if not filename.endswith(".mp3"):
        filename += ".mp3"

    mp3_file_path = os.path.join(folder, filename)
    
    print(f"Downloading {url} to {mp3_file_path}")
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(mp3_file_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    return mp3_file_path, filename

# Transcribe the audio using Whisper and save to a text file
def transcribe_with_whisper(file_path, metadata):
    """Transcribe audio using Whisper and save to a text file."""
    wav_file = file_path.replace('.mp3', '.wav')
    
    # Ensure the TRANSCRIBED_FOLDER exists before any file writing
    if not os.path.exists(TRANSCRIBED_FOLDER):
        os.makedirs(TRANSCRIBED_FOLDER, exist_ok=True)
    
    try:
        # Convert mp3 to wav using ffmpeg
        overwrite_option = "-y" if AUTO_OVERWRITE else ""
        conversion_command = f"ffmpeg {overwrite_option} -i \"{file_path}\" -ar 16000 -ac 1 -c:a pcm_s16le \"{wav_file}\""
        os.system(conversion_command)
        
        # Prepare transcription file path
        transcription_file = os.path.join(TRANSCRIBED_FOLDER, os.path.basename(file_path).replace('.mp3', ''))
        
        # Transcribe using Whisper and capture the output with word timestamps
        transcription_command = f"{WHISPER_EXECUTABLE} -m {WHISPER_MODEL_PATH} -f \"{wav_file}\" -otxt --output-file \"{transcription_file}\""
        subprocess.run(transcription_command, shell=True, check=True)
        
        # Check if the transcription file was created
        txt_file = transcription_file + ".txt"
        if not os.path.exists(txt_file):
            print(f"Warning: Transcription file {txt_file} was not created.")
            return None, None
        
        # Read the transcription content
        with open(txt_file, "r") as f:
            transcript_text = f.read()
        
        # Add metadata to the transcription file
        with open(txt_file, "r+") as f:
            original_content = f.read()
            f.seek(0)
            original_title = metadata['episode_title']
            f.write(f"{original_title}\n{metadata['link']}\n\n")
            f.write(original_content)
        
        return txt_file, transcript_text

    except Exception as e:
        print(f"Error during transcription: {e}")
        return None, None

# Organize podcast transcript files into folders and return the new file path
def organize_podcast_files(podcast_name, episode_title, transcript_file):
    """Organize podcast transcript files into folders and return the new file path."""
    normalized_podcast_name = normalize_folder_name(podcast_name)
    normalized_episode_title = normalize_folder_name(episode_title)

    podcast_folder = os.path.join(TRANSCRIBED_FOLDER, normalized_podcast_name)

    # Ensure the podcast folder exists before attempting to move the file
    if not os.path.exists(podcast_folder):
        os.makedirs(podcast_folder, exist_ok=True)

    new_transcript_path = os.path.join(podcast_folder, f"{normalized_episode_title}.txt")
    shutil.move(transcript_file, new_transcript_path)

    return new_transcript_path

# Check if Whisper is installed by verifying the existence of key files
def check_whisper_installed():
    """Check if Whisper is installed by verifying the existence of key files."""
    whisper_exec = os.path.expanduser(WHISPER_EXECUTABLE)
    whisper_model = os.path.expanduser(WHISPER_MODEL_PATH)
    whisper_root = os.path.expanduser(WHISPER_ROOT)

    if os.path.isdir(whisper_root) and os.path.isfile(whisper_exec) and os.path.isfile(whisper_model):
        print("Whisper is installed and ready to use.")
        return True
    else:
        print("Whisper is not fully installed.")
        return False

# Main script execution
if __name__ == "__main__":
    print("Starting podcast transcription process...")
    
    check_git_installed()
    print("Git check completed.")

    if ENABLE_GITHUB_COMMIT and GITHUB_USERNAME != "your_github_username":
        if check_github_ssh_connection():
            print("GitHub SSH connection successful.")
        else:
            print("GitHub SSH connection failed. Exiting.")
            exit(1)

    if GITHUB_REPO_CHECK:
        check_create_github_repo(GITHUB_REPO_NAME)
        print("GitHub repository check completed.")

    # Initialize the local Git repository
    initialize_local_git_repo(REPO_ROOT)

    # Ensure APP_ENTRY and JINJA_TEMPLATES are copied to the Git repository
    ensure_files_copied()
    
    # Generate and compare hashes before syncing
    hash_file = os.path.join(REPO_ROOT, 'chroma_hashes.txt')
    generate_chroma_hashes(CHROMADB_DB_PATH, REPO_ROOT, hash_file)

    pull_and_sync_chromadb_if_necessary(GITHUB_REPO_NAME, CHROMADB_DB_PATH, hash_file, os.path.relpath(CHROMADB_DB_PATH, REPO_ROOT))

    try:
        new_files = process_feed(RSS_FEED_URL, PODCAST_AUDIO_FOLDER, debug=True)
        print("RSS feed processing completed.")

        # Regenerate the chroma hashes after updating the database
        generate_chroma_hashes(CHROMADB_DB_PATH, REPO_ROOT, hash_file)

        if ENABLE_GITHUB_COMMIT:

            # Print the function signature to verify the arguments
            print(f"Function signature of commit_database_and_files: {inspect.signature(commit_database_and_files)}")
            print(f"Arguments being passed: CHROMADB_DB_PATH={CHROMADB_DB_PATH}, new_files={new_files}")

            upload_successful = commit_database_and_files(CHROMADB_DB_PATH, new_files)
            if upload_successful:
                print("Files successfully uploaded to GitHub.")
            else:
                print("No changes to upload to GitHub.")
   
    finally:
        # Always attempt to delete MP3 and WAV files after processing
        for mp3_file, wav_file in new_files:
            if os.path.exists(mp3_file):
                os.remove(mp3_file)
                print(f"Deleted MP3 file: {mp3_file}")
            if os.path.exists(wav_file):
                os.remove(wav_file)
                print(f"Deleted WAV file: {wav_file}")

    try:
        subprocess.run(["git", "fetch", "origin"], cwd=REPO_ROOT, check=True)
        # Check if origin/main exists before resetting
        result = subprocess.run(["git", "rev-parse", "--verify", "origin/main"], cwd=REPO_ROOT, capture_output=True, text=True)
        if result.returncode == 0:
            subprocess.run(["git", "reset", "--hard", "origin/main"], cwd=REPO_ROOT, check=True)
        else:
            print("origin/main does not exist. Skipping git reset.")
    except subprocess.CalledProcessError as e:
        print(f"Git command failed: {e}")

    if ENABLE_GITHUB_PAGES:
        enable_github_pages()

    print("Script completed successfully.")
