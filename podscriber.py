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

from config import (
    RSS_FEED_URL, PODCAST_AUDIO_FOLDER, PODCAST_HISTORY_FILE, WHISPER_MODEL_PATH,
    WHISPER_EXECUTABLE, TRANSCRIBED_FOLDER, AUTO_OVERWRITE, GITHUB_REPO_CHECK,
    GITHUB_REPO_NAME, ENABLE_GITHUB_COMMIT, UPDATE_HTML_LINKS,
    GITHUB_USERNAME, GITHUB_TOKEN, GITHUB_REPO_PRIVATE, DEBUG_MODE_LIMIT, 
    REPO_ROOT, ENABLE_GITHUB_PAGES,
    WHISPER_SETUP, WHISPER_ROOT,CHROMADB_DB_PATH, TOKENIZERS_PARALLELISM
)

# Set Hugging Face Tokenizers environment variable
os.environ["TOKENIZERS_PARALLELISM"] = TOKENIZERS_PARALLELISM

# Configuration and Constants
REPO_ROOT = os.path.expanduser(REPO_ROOT)
PODCAST_AUDIO_FOLDER = os.path.expanduser(PODCAST_AUDIO_FOLDER)
PODCAST_HISTORY_FILE = os.path.expanduser(PODCAST_HISTORY_FILE)
TRANSCRIBED_FOLDER = os.path.join(REPO_ROOT, "transcribed")
CHROMADB_DB_PATH = os.path.expanduser(CHROMADB_DB_PATH)

# Setup ChromaDB Persistent Client
client = chromadb.PersistentClient(path=CHROMADB_DB_PATH)

# Access the podcasts collection
podcast_collection = client.get_or_create_collection(name="podcasts")

# Check the heartbeat to ensure connection
client.heartbeat()

# Example usage of resetting the database if necessary (destructive)
# client.reset()

def check_git_installed():
    """Ensure git is installed on the system."""
    try:
        subprocess.run(["git", "--version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print("Git is installed.")
    except subprocess.CalledProcessError:
        print("Git is not installed. Please install git before running the script.")
        exit(1)

def check_github_ssh_connection():
    """Check if SSH connection to GitHub is properly configured."""
    try:
        result = subprocess.run(
            ["ssh", "-T", "git@github.com"], 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE
        )
        response = result.stdout.decode('utf-8') + result.stderr.decode('utf-8')
        if "You've successfully authenticated" in response:
            print("SSH connection to GitHub is properly configured.")
            return True
        else:
            print("SSH connection to GitHub failed. Please configure SSH key properly.")
            return False
    except Exception as e:
        print(f"SSH connection to GitHub encountered an error: {e}")
        return False

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

def is_git_repo(repo_root):
    """Check if the directory is a Git repository."""
    return os.path.exists(os.path.join(repo_root, ".git"))

def initialize_local_git_repo(repo_root):
    """Initialize the local Git repository or pull changes if it already exists."""
    if not os.path.exists(repo_root):
        os.makedirs(repo_root)

    if not is_git_repo(repo_root):
        print(f"Initializing local Git repository in {repo_root}...")
        subprocess.run(["git", "init"], cwd=repo_root, check=True)
        subprocess.run(["git", "remote", "add", "origin", f"git@github.com:{GITHUB_USERNAME}/{GITHUB_REPO_NAME}.git"], cwd=repo_root, check=True)

        # Check if the remote has any commits
        result = subprocess.run(["git", "ls-remote", "--heads", "origin"], cwd=repo_root, capture_output=True, text=True)

        if result.stdout.strip():
            # Remote repository has commits, pull them
            subprocess.run(["git", "pull", "origin", "main"], cwd=repo_root, check=True)
            print("Pulled existing main branch from remote.")
        else:
            # Remote is empty, create initial commit and push
            create_initial_commit(repo_root)
            print("Created and pushed initial commit to main branch.")
    else:
        print(f"Git repository already initialized in {repo_root}, pulling latest changes.")
        subprocess.run(["git", "pull", "origin", "main"], cwd=repo_root, check=True)

def create_initial_commit(repo_root):
    """Create the initial commit in the local Git repository."""
    with open(os.path.join(repo_root, "README.md"), "w") as f:
        f.write(f"# {GITHUB_REPO_NAME}\n\nThis repository contains podcast archives.")

    subprocess.run(["git", "add", "README.md"], cwd=repo_root, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo_root, check=True)
    subprocess.run(["git", "branch", "-M", "main"], cwd=repo_root, check=True)
    subprocess.run(["git", "push", "-u", "origin", "main"], cwd=repo_root, check=True)

def check_github_pages_enabled():
    """Check if GitHub Pages is already enabled."""
    url = f"https://api.github.com/repos/{GITHUB_USERNAME}/{GITHUB_REPO_NAME}/pages"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    response = requests.get(url, headers=headers)
    return response.status_code == 200

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
        # Construct the URL to the podcast archive
        history_filename = os.path.basename(PODCAST_HISTORY_FILE)
        archive_url = f"https://{GITHUB_USERNAME}.github.io/{GITHUB_REPO_NAME}/{history_filename}"
        print(f"GitHub Pages enabled for repository {GITHUB_REPO_NAME}.")
        print(f"Visit your site at: {archive_url}")
        
        # Update the README.md with the archive link
        update_readme_with_archive_link(REPO_ROOT, archive_url)
    else:
        print(f"Failed to enable GitHub Pages: {response.status_code} - {response.text}")

def update_readme_with_archive_link(repo_root, archive_url):
    """Update the README.md by replacing the existing description with the archive link."""
    readme_path = os.path.join(repo_root, "README.md")
    if os.path.exists(readme_path):
        with open(readme_path, "r+") as f:
            content = f.read()
            updated_content = re.sub(
                r'This repository contains podcast archives\.',
                f'You can access the podcast archive [here]({archive_url}).',
                content
            )
            f.seek(0)
            f.write(updated_content)
            f.truncate()
        print(f"Updated README.md with archive link: {archive_url}")
    else:
        with open(readme_path, "w") as f:
            f.write(f"# {GITHUB_REPO_NAME}\n\nYou can access the podcast archive [here]({archive_url}).\n")
        print(f"Created README.md and added archive link: {archive_url}")

    # Commit and push the updated README.md
    subprocess.run(["git", "add", "README.md"], cwd=repo_root, check=True)
    subprocess.run(["git", "commit", "-m", "Update README.md with podcast archive link"], cwd=repo_root, check=True)
    subprocess.run(["git", "push", "origin", "main"], cwd=repo_root, check=True)

def file_hash(filepath):
    """Calculate the SHA-256 hash of the given file."""
    sha256 = hashlib.sha256()
    with open(filepath, 'rb') as f:
        for block in iter(lambda: f.read(4096), b''):
            sha256.update(block)
    return sha256.hexdigest()

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

def commit_database_and_files(repo_root, db_path, history_file, new_files):
    """Commit changes to the database directory, HTML file, and new podcast files."""
    if not os.path.exists(history_file):
        print(f"Error: {history_file} does not exist.")
        return False

    if db_path and not os.path.exists(db_path):
        print(f"Error: Database path {db_path} does not exist.")
        return False

    try:
        # Stash any local changes before pulling
        subprocess.run(["git", "stash"], cwd=repo_root, check=True)
        subprocess.run(["git", "pull", "--rebase", "origin", "main"], cwd=repo_root, check=True)
        # Try to pop the stash, but continue even if there's nothing to pop
        result = subprocess.run(["git", "stash", "pop"], cwd=repo_root, check=False, capture_output=True, text=True)
        if result.returncode != 0:
            if "No stash entries found" in result.stderr or "No stash entries found" in result.stdout:
                print("No stash entries to pop.")
            else:
                print(f"Error during git stash pop: {result.stderr}")
                return False

        # Stage the entire ChromaDB database directory
        if db_path:
            print(f"Adding to Git: {os.path.relpath(db_path, repo_root)}")
            subprocess.run(["git", "add", os.path.relpath(db_path, repo_root)], cwd=repo_root, check=True)

        # Stage the HTML file and transcribed folder
        print(f"Adding to Git: {os.path.relpath(history_file, repo_root)}")
        subprocess.run(["git", "add", os.path.relpath(history_file, repo_root)], cwd=repo_root, check=True)

        if os.path.exists(TRANSCRIBED_FOLDER):
            print(f"Adding to Git: {os.path.relpath(TRANSCRIBED_FOLDER, repo_root)}")
            subprocess.run(["git", "add", os.path.relpath(TRANSCRIBED_FOLDER, repo_root)], cwd=repo_root, check=True)

        # Debugging: Print git status
        status_result = subprocess.run(["git", "status"], cwd=repo_root, capture_output=True, text=True)
        print(f"Git status output:\n{status_result.stdout}")

        # Check if there are any changes to commit
        status = subprocess.run(["git", "status", "--porcelain"], cwd=repo_root, capture_output=True, text=True).stdout
        if status.strip():
            subprocess.run(["git", "commit", "-m", "Update database, HTML, and podcast files"], cwd=repo_root, check=True)
            subprocess.run(["git", "push", "origin", "main"], cwd=repo_root, check=True)
            print("Database, HTML, and podcast files committed and pushed.")
            return True
        else:
            print("No changes to commit for the database, HTML, or podcast files.")
            return False

    except subprocess.CalledProcessError as e:
        print(f"Failed to commit changes: {e}")
        return False

# Database Operations using ChromaDB
def add_podcast_to_db_chroma(metadata, mp3_url, transcript_name, transcript_text):
    metadata['mp3_url'] = mp3_url  # Store the mp3_url in the metadata
    document = f"{metadata['podcast_name']} - {metadata['episode_title']}\nTranscript: {transcript_text}"
    
    podcast_collection.upsert(
        documents=[document],  # Add the text of the transcript with additional metadata as a document
        ids=[metadata['guid']],  # Use the GUID as the document ID
        metadatas=[metadata]  # Store the entire metadata dictionary
    )
    print("Data committed to ChromaDB.")

def generate_html_from_chroma_db(history_file):
    """Generate HTML file from ChromaDB collection."""
    print(f"Generating HTML from ChromaDB")
    
    # Start the HTML log (this will overwrite any existing content)
    start_html_log(history_file)
    
    # Retrieve all documents in the collection
    results = podcast_collection.get()

    if 'documents' in results and len(results['documents']) > 0:
        documents = results['documents']
        ids = results['ids']
        metadatas = results.get('metadatas', [])
    else:
        print("No documents found in ChromaDB.")
        return

    print(f"Found {len(documents)} podcast entries in ChromaDB.")
    
    for document, guid, metadata in zip(documents, ids, metadatas):
        # Extract metadata from the document
        podcast_name = metadata.get("podcast_name", "Unknown Podcast")
        episode_title = metadata.get("episode_title", "Unknown Episode")
        listen_date = metadata.get("listenDate", "Unknown Date")
        
        print(f"Adding podcast entry to HTML: Podcast={podcast_name}, Episode={episode_title}, GUID={guid}")
        save_downloaded_url(history_file, metadata, transcript_name=f"{normalize_folder_name(episode_title)}.txt")
    
    # End the HTML log properly
    end_html_log(history_file)
    print(f"HTML generation complete: {history_file}")

def generate_chroma_hashes(db_path, hash_file):
    """Generate SHA-256 hashes for all files in the ChromaDB directory and save them."""
    hashes = []
    for root, dirs, files in os.walk(db_path):
        for file in files:
            file_path = os.path.join(root, file)
            file_rel_path = os.path.relpath(file_path, db_path)
            file_hash_value = file_hash(file_path)
            hashes.append(f"{file_rel_path}:{file_hash_value}")
    
    with open(hash_file, 'w') as f:
        f.write("\n".join(hashes))

def compare_chroma_hashes(local_hash_file, remote_hash_file):
    """Compare local and remote hash files to determine if pulling is necessary."""
    with open(local_hash_file, 'r') as f:
        local_hashes = set(f.readlines())
    
    with open(remote_hash_file, 'r') as f:
        remote_hashes = set(f.readlines())
    
    if local_hashes == remote_hashes:
        print("Local ChromaDB files are up-to-date.")
        return True
    else:
        print("Local ChromaDB files differ from remote. Pulling latest from GitHub...")
        return False

def pull_and_sync_chromadb_if_necessary(repo_name, db_path, hash_file, remote_db_dir):
    """Check if sync is necessary by comparing local and remote hashes."""
    remote_hash_file = os.path.join(db_path, 'remote_chroma_hashes.txt')

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

def process_feed(feed_url, download_folder, history_file, debug=True):
    """Process the RSS feed, download new MP3 files, transcribe them, and store data in ChromaDB."""
    if debug:
        print(f"Fetching feed from {feed_url}")
    
    response = requests.get(feed_url)
    response.raise_for_status()

    root = ET.fromstring(response.content)

    new_files = []  # This will now store tuples of (mp3_file_path, wav_file_path)

    for item in root.findall('./channel/item')[:DEBUG_MODE_LIMIT]:
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

                    # Save podcast metadata into the ChromaDB, including transcript text
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

    # Ensure HTML is generated
    if new_files or debug:
        print("Generating HTML file...")
        generate_html_from_chroma_db(history_file)
    else:
        print("No new podcasts found, skipping HTML generation.")

    return new_files  # Now returns tuples of (mp3_file_path, wav_file_path)

# Date and Name Formatting Functions
def format_date_long(date_str):
    """Format the date to 'Month Day, Year' for TXT files."""
    date_obj = datetime.strptime(date_str, "%a, %d %b %Y %H:%M:%S %z")
    return date_obj.strftime("%B %d, %Y")

def format_date_short(date_str):
    """Format the date to 'MM/DD/YYYY' for HTML files."""
    date_obj = datetime.strptime(date_str, "%a, %d %b %Y %H:%M:%S %z")
    return date_obj.strftime("%m/%d/%Y")

def extract_podcast_and_episode(title):
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

def normalize_folder_name(title):
    """Normalize folder names by replacing spaces with underscores and removing non-alphanumeric characters."""
    return re.sub(r'[^\w\s-]', '', title).replace(" ", "_").strip("_")

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

# HTML Operations
def start_html_log(history_file):
    """Initialize the PodcastHistory file with a header, if it does not exist."""
    header = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Podcast &#x1F442; Archive</title>
    <style>
        table {
            width: 100%;
            border-collapse: collapse;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: white;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        th {
            background-color: #4a90e2;
            color: white;
            font-weight: 600;
            text-align: left;
            padding: 16px;
            text-transform: uppercase;
            font-size: 14px;
            letter-spacing: 0.5px;
        }
        td {
            padding: 16px;
            border-bottom: 1px solid #e0e0e0;
        }
        tr:last-child td {
            border-bottom: none;
        }
        tr:nth-child(even) {
            background-color: #f9f9f9;
        }
        tr:hover {
            background-color: #f0f0f0;
            transition: background-color 0.3s ease;
        }
        a {
            color: #2c3e50;
            text-decoration: none;
            border-bottom: 1px solid #3498db;
            transition: color 0.3s ease, border-bottom-color 0.3s ease;
        }

        a:hover {
            color: #3498db;
            border-bottom-color: #2c3e50;
        }

        a.no-underline {
            text-decoration: none;
            border-bottom: none; /* Removes the border underline */
        }

        a.no-underline:hover {
            text-decoration: none;
            border-bottom: none; /* Ensures no underline on hover as well */
        }
        h2 {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }
    </style>
    <script>
        function sortTable(n) {
          var table, rows, switching, i, x, y, shouldSwitch, dir, switchcount = 0;
          table = document.getElementById("podcastTable");
          switching = true;
          dir = "asc"; 
          while (switching) {
            switching = false;
            rows = table.rows;
            for (i = 1; i < (rows.length - 1); i++) {
              shouldSwitch = false;
              x = rows[i].getElementsByTagName("TD")[n];
              y = rows[i + 1].getElementsByTagName("TD")[n];
              if (dir == "asc") {
                if (x.innerHTML.toLowerCase() > y.innerHTML.toLowerCase()) {
                  shouldSwitch = true;
                  break;
                }
              } else if (dir == "desc") {
                if (x.innerHTML.toLowerCase() < y.innerHTML.toLowerCase()) {
                  shouldSwitch = true;
                  break;
                }
              }
            }
            if (shouldSwitch) {
              rows[i].parentNode.insertBefore(rows[i + 1], rows[i]);
              switching = true;
              switchcount ++;      
            } else {
              if (switchcount == 0 && dir == "asc") {
                dir = "desc";
                switching = true;
              }
            }
          }
        }
    </script>
</head>
<body>
    <h2>Podcast &#x1F442; Archive</h2>
    <table id="podcastTable">
        <tr>
            <th onclick="sortTable(0)">Podcast</th>
            <th onclick="sortTable(1)">Episode</th>
            <th onclick="sortTable(2)">Listen Date</th>
            <th>Transcript</th>
            <th>Stream</th>
        </tr>
        """
    with open(history_file, "w") as f:
        f.write(header)

def end_html_log(history_file):
    """Finalize the PodcastHistory file with a footer."""
    footer = """
    </table>
</body>
</html>
    """
    with open(history_file, "a") as f:
        f.write(footer)

def save_downloaded_url(history_file, metadata, transcript_name):
    """Save the downloaded URL and metadata to the PodcastHistory file."""
    print(f"Saving to HTML: {metadata['episode_title']}")

    # Construct the transcript URL on GitHub
    transcript_github_url = f"https://raw.githubusercontent.com/{GITHUB_USERNAME}/{GITHUB_REPO_NAME}/main/transcribed/{normalize_folder_name(metadata['podcast_name'])}/{transcript_name}"
    
    # Handle case where link might be None or empty
    if metadata.get('link'):
        pod_site_link = f"<a href=\"{html.escape(metadata['link'])}\" target=\"_blank\">Pod Site</a>"
    else:
        pod_site_link = "N/A"
    
    entry = f"""
<tr>
    <td><a href="{html.escape(metadata.get('link', ''))}" target="_blank">{html.escape(metadata['podcast_name'])}</a></td>
    <td><a href="{html.escape(metadata['guid'])}" target="_blank">{html.escape(metadata['episode_title'])}</a></td>
    <td>{html.escape(format_date_short(metadata['listenDate']))}</td>
    <td><a href="{transcript_github_url}" target="_blank" class="no-underline">&#x1F4C4;</a></td>
    <td><audio src="{metadata['mp3_url']}" controls></audio></td>
</tr>
    """
    with open(history_file, "a") as f:
        f.write(entry)

def update_html_links(history_file):
    """Update HTML file links to point to the appropriate locations, if necessary."""
    with open(history_file, 'r+') as f:
        content = f.read()
        # Update .txt links to point to the appropriate location
        content = re.sub(
            r'file://[^"]+\.txt',
            lambda match: match.group(0).replace('file://', f"https://raw.githubusercontent.com/{GITHUB_USERNAME}/{GITHUB_REPO_NAME}/main/transcribed/"),
            content
        )
        f.seek(0)
        f.write(content)
        f.truncate()

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

# Main Script Execution
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
    
    # Generate and compare hashes before syncing
    hash_file = os.path.join(REPO_ROOT, 'chroma_hashes.txt')
    generate_chroma_hashes(CHROMADB_DB_PATH, hash_file)
    
    pull_and_sync_chromadb_if_necessary(GITHUB_REPO_NAME, CHROMADB_DB_PATH, hash_file, os.path.relpath(CHROMADB_DB_PATH, REPO_ROOT))

    try:
        new_files = process_feed(RSS_FEED_URL, PODCAST_AUDIO_FOLDER, PODCAST_HISTORY_FILE, debug=True)
        print("RSS feed processing completed.")

        if ENABLE_GITHUB_COMMIT:
            upload_successful = commit_database_and_files(REPO_ROOT, CHROMADB_DB_PATH, PODCAST_HISTORY_FILE, new_files)
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

    subprocess.run(["git", "fetch", "origin"], cwd=REPO_ROOT, check=True)
    subprocess.run(["git", "reset", "--hard", "origin/main"], cwd=REPO_ROOT, check=True)
    print("Final fetch and reset to sync with remote completed.")

    if ENABLE_GITHUB_PAGES:
        enable_github_pages()
        print("GitHub Pages enabled.")

    print("Script completed successfully.")
