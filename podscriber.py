import os
import urllib.request
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
import html
import re
import subprocess
import sqlite3
import shutil

from config import (
    RSS_FEED_URL, PODCAST_AUDIO_FOLDER, PODCAST_HISTORY_FILE, WHISPER_MODEL_PATH,
    WHISPER_EXECUTABLE, TRANSCRIBED_FOLDER, AUTO_OVERWRITE, GITHUB_REPO_CHECK,
    GITHUB_REPO_NAME, ENABLE_GITHUB_COMMIT, UPLOAD_MP3_FILES, UPDATE_HTML_LINKS,
    GITHUB_USERNAME, GITHUB_TOKEN, GITHUB_REPO_PRIVATE, DEBUG_MODE_LIMIT, 
    AUTO_DELETE_MP3, AUTO_DELETE_AFTER_UPLOAD, REPO_ROOT, ENABLE_GITHUB_PAGES,
    WHISPER_SETUP, WHISPER_ROOT
)

# Constants
REPO_ROOT = os.path.expanduser(REPO_ROOT)
PODCAST_AUDIO_FOLDER = os.path.expanduser(PODCAST_AUDIO_FOLDER)
PODCAST_HISTORY_FILE = os.path.expanduser(PODCAST_HISTORY_FILE)
TRANSCRIBED_FOLDER = os.path.join(REPO_ROOT, "transcribed")
DB_PATH = os.path.join(REPO_ROOT, "podcasts.db")

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
    
    create_initial_commit(REPO_ROOT)  # Ensure the branch exists before enabling GitHub Pages

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
    if response.status_code in [201, 204]:  # 201 Created or 204 No Content
        # Extract the filename from PODCAST_HISTORY_FILE
        history_filename = os.path.basename(PODCAST_HISTORY_FILE)
        print(f"GitHub Pages enabled for repository {GITHUB_REPO_NAME}.")
        print(f"Visit your site at: https://{GITHUB_USERNAME}.github.io/{GITHUB_REPO_NAME}/{history_filename}")
    else:
        print(f"Failed to enable GitHub Pages: {response.status_code} - {response.text}")

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

def check_git_lfs_installed():
    """Check if Git LFS is installed, and install it using Homebrew if not."""
    try:
        subprocess.run(["git", "lfs", "install"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print("Git LFS is installed and initialized.")
    except subprocess.CalledProcessError:
        print("Git LFS is not installed. Installing with brew...")
        subprocess.run(["brew", "install", "git-lfs"], check=True)
        subprocess.run(["git", "lfs", "install"], check=True)
        print("Git LFS installed and initialized successfully.")

def create_initial_commit(repo_root):
    """Create an initial commit on the main branch if it doesn't exist."""
    try:
        subprocess.run(["git", "checkout", "main"], cwd=repo_root, check=True)
        print("Switched to existing main branch.")
    except subprocess.CalledProcessError:
        subprocess.run(["git", "checkout", "-b", "main"], cwd=repo_root, check=True)
        print("Created and switched to new main branch.")
    
    subprocess.run(["git", "add", "--all"], cwd=repo_root, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo_root, check=True)
    subprocess.run(["git", "push", "-u", "origin", "main"], cwd=repo_root, check=True)

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

def initialize_local_git_repo(repo_root):
    """Initialize the local Git repository with sparse checkout."""
    if not os.path.exists(repo_root):
        os.makedirs(repo_root)
    
    if not os.path.exists(os.path.join(repo_root, ".git")):
        print(f"Initializing local Git repository in {repo_root}...")
        subprocess.run(["git", "init"], cwd=repo_root, check=True)
        subprocess.run(["git", "remote", "add", "origin", f"git@github.com:{GITHUB_USERNAME}/{GITHUB_REPO_NAME}.git"], cwd=repo_root, check=True)
        subprocess.run(["git", "config", "core.sparseCheckout", "true"], cwd=repo_root, check=True)
        
        with open(os.path.join(repo_root, ".git", "info", "sparse-checkout"), "w") as f:
            f.write("/*\n")
            f.write("!/transcribed/\n")
            f.write("/transcribed/*/\n")
        
        # Check if the remote has any commits
        result = subprocess.run(["git", "ls-remote", "--exit-code", "origin", "main"], cwd=repo_root, capture_output=True, text=True)
        
        if result.returncode == 0:
            # Remote main branch exists, pull it
            subprocess.run(["git", "pull", "origin", "main"], cwd=repo_root, check=True)
            print("Pulled existing main branch from remote.")
        else:
            # Remote is empty, create initial commit and push
            with open(os.path.join(repo_root, "README.md"), "w") as f:
                f.write(f"# {GITHUB_REPO_NAME}\n\nThis repository contains podcast archives.")
            
            subprocess.run(["git", "add", "README.md"], cwd=repo_root, check=True)
            subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo_root, check=True)
            subprocess.run(["git", "branch", "-M", "main"], cwd=repo_root, check=True)
            subprocess.run(["git", "push", "-u", "origin", "main"], cwd=repo_root, check=True)
            print("Created and pushed initial commit to main branch.")
        
        print("Local Git repository initialized with sparse checkout.")
    else:
        print("Git repository already initialized.")

def commit_database_and_html(repo_root, db_path, history_file):
    """Commit changes to the database and HTML file."""
    subprocess.run(["git", "add", os.path.relpath(db_path, repo_root)], cwd=repo_root, check=True)
    subprocess.run(["git", "add", os.path.relpath(history_file, repo_root)], cwd=repo_root, check=True)
    
    status = subprocess.run(["git", "status", "--porcelain"], cwd=repo_root, capture_output=True, text=True).stdout
    if status.strip():
        subprocess.run(["git", "commit", "-m", "Update database and HTML"], cwd=repo_root, check=True)
        subprocess.run(["git", "push", "origin", "main"], cwd=repo_root, check=True)
        print("Database and HTML changes committed and pushed.")
    else:
        print("No changes to commit for database and HTML.")

def temporarily_include_transcribed(repo_root):
    """Temporarily include the transcribed directory in sparse checkout."""
    sparse_checkout_file = os.path.join(repo_root, ".git", "info", "sparse-checkout")
    
    # Backup current sparse-checkout configuration
    shutil.copy(sparse_checkout_file, f"{sparse_checkout_file}.bak")
    
    # Add transcribed/ to sparse-checkout
    with open(sparse_checkout_file, "a") as f:
        f.write("transcribed/\n")
    
    # Reapply sparse-checkout
    subprocess.run(["git", "sparse-checkout", "reapply"], cwd=repo_root, check=True)

def revert_sparse_checkout(repo_root):
    """Revert sparse checkout to original configuration."""
    sparse_checkout_file = os.path.join(repo_root, ".git", "info", "sparse-checkout")
    backup_file = f"{sparse_checkout_file}.bak"
    
    # Restore original sparse-checkout configuration
    shutil.move(backup_file, sparse_checkout_file)
    
    # Reapply sparse-checkout
    subprocess.run(["git", "sparse-checkout", "reapply"], cwd=repo_root, check=True)

def commit_new_podcast_files(repo_root, new_files):
    """Commit new podcast files to GitHub."""
    print("Starting to commit new podcast files...")
    try:
        temporarily_include_transcribed(repo_root)
        
        files_to_commit = []
        for file in new_files:
            relative_path = os.path.relpath(file, repo_root)
            full_path = os.path.join(repo_root, relative_path)
            print(f"Checking file: {full_path}")
            if os.path.exists(full_path):
                files_to_commit.append(relative_path)
                try:
                    subprocess.run(["git", "add", "--sparse", relative_path], cwd=repo_root, check=True)
                    print(f"Added file to staging: {relative_path}")
                except subprocess.CalledProcessError as e:
                    print(f"Error adding file {relative_path}: {e}")
            else:
                print(f"Warning: File {full_path} does not exist and will not be committed.")
        
        if files_to_commit:
            try:
                subprocess.run(["git", "commit", "-m", "Add new podcast files"], cwd=repo_root, check=True)
                print("Committed new podcast files.")
                subprocess.run(["git", "push", "origin", "main"], cwd=repo_root, check=True)
                print(f"New podcast files committed and pushed: {', '.join(files_to_commit)}")
                return True
            except subprocess.CalledProcessError as e:
                print(f"Error during commit or push: {e}")
                return False
        else:
            print("No new podcast files to commit.")
            return False
    except Exception as e:
        print(f"An unexpected error occurred while committing new podcast files: {e}")
        return False
    finally:
        revert_sparse_checkout(repo_root)
        print("Reverted sparse checkout configuration.")

def sync_with_github(repo_name, repo_root):
    """Sync the local repository with GitHub, excluding the transcribed folder."""
    if os.path.exists(os.path.join(repo_root, ".git")):
        print(f"Syncing local repository {repo_name} with GitHub...")
        subprocess.run(["git", "pull", "--sparse-checkout"], cwd=repo_root, check=True)
    else:
        print(f"Cloning {repo_name} from GitHub with sparse-checkout...")
        subprocess.run(["git", "clone", "--filter=blob:none", "--sparse", f"git@github.com:{GITHUB_USERNAME}/{repo_name}.git", repo_root], check=True)
        subprocess.run(["git", "sparse-checkout", "set", "!", "transcribed"], cwd=repo_root, check=True)

def cleanup_local_files(files_to_clean):
    for file in files_to_clean:
        try:
            os.remove(file)
            print(f"Removed local file: {file}")
        except OSError as e:
            print(f"Error removing file {file}: {e}")

def install_sqlite_with_brew():
    """Install SQLite using Homebrew if not installed."""
    try:
        subprocess.run(["sqlite3", "--version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print("SQLite is installed.")
    except subprocess.CalledProcessError:
        print("SQLite is not installed. Installing with brew...")
        subprocess.run(["brew", "install", "sqlite"], check=True)
        print("SQLite installed successfully.")

def setup_database(db_path):
    """Setup the SQLite database and tables."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS podcasts (
                        id INTEGER PRIMARY KEY,
                        title TEXT,
                        pubDate TEXT,
                        guid TEXT,
                        link TEXT,
                        file_name TEXT,
                        transcript_name TEXT
                    )''')
    conn.commit()
    conn.close()

def add_podcast_to_db(db_path, metadata, file_name, transcript_name):
    """Insert podcast data into the SQLite database."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Construct the GitHub URLs
    mp3_github_url = f"https://media.githubusercontent.com/media/{GITHUB_USERNAME}/{GITHUB_REPO_NAME}/main/transcribed/{normalize_folder_name(metadata['title'])}/{file_name}"
    transcript_github_url = f"https://raw.githubusercontent.com/{GITHUB_USERNAME}/{GITHUB_REPO_NAME}/main/transcribed/{normalize_folder_name(metadata['title'])}/{transcript_name}"
    
    cursor.execute('''INSERT INTO podcasts (title, pubDate, guid, link, file_name, transcript_name) 
                      VALUES (?, ?, ?, ?, ?, ?)''',
                   (metadata['title'], metadata['pubDate'], metadata['guid'], metadata['link'], mp3_github_url, transcript_github_url))
    conn.commit()
    conn.close()

def generate_html_from_db(db_path, history_file):
    """Generate HTML file from SQLite database."""
    print(f"Generating HTML from DB: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    start_html_log(history_file)

    cursor.execute('SELECT title, pubDate, file_name, transcript_name, guid, link FROM podcasts')
    rows = cursor.fetchall()
    print(f"Found {len(rows)} podcast entries in the database.")
    for row in rows:
        title, pubDate, file_name, transcript_name, guid, link = row
        print(f"Adding podcast entry to HTML: Title={title}, PubDate={pubDate}, FileName={file_name}, TranscriptName={transcript_name}, GUID={guid}, Link={link}")
        save_downloaded_url(history_file, {'title': title, 'pubDate': pubDate, 'guid': guid, 'link': link}, file_name, transcript_name)

    end_html_log(history_file)
    conn.close()
    print(f"HTML generation complete: {history_file}")

def normalize_folder_name(title):
    """Normalize folder names by replacing spaces with underscores."""
    return re.sub(r'[^\w\s-]', '', title).replace(" ", "_").strip("_")

def organize_podcast_files(title, mp3_file, transcript_file):
    """Organize podcast files into folders without committing."""
    normalized_title = normalize_folder_name(title)
    podcast_folder = os.path.join(TRANSCRIBED_FOLDER, normalized_title)
    
    if not os.path.exists(podcast_folder):
        os.makedirs(podcast_folder, exist_ok=True)
    
    if UPLOAD_MP3_FILES:
        mp3_dest = os.path.join(podcast_folder, os.path.basename(mp3_file))
        shutil.move(mp3_file, mp3_dest)
    else:
        if AUTO_DELETE_MP3:
            os.remove(mp3_file)
    
    transcript_dest = os.path.join(podcast_folder, os.path.basename(transcript_file))
    shutil.move(transcript_file, transcript_dest)

def download_file(url, folder, title):
    """Download the file from the URL and save it to the folder with a readable filename."""
    filename = re.sub(r'[^\w\s-]', '', title).replace(" ", "_").strip("_")
    
    # Ensure the filename ends with '.mp3'
    if not filename.endswith(".mp3"):
        filename += ".mp3"

    local_filename = os.path.join(folder, filename)
    
    print(f"Downloading {url} to {local_filename}")
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(local_filename, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    return local_filename, filename

def transcribe_with_whisper(file_path, metadata):
    """Transcribe audio using Whisper and save to a text file."""
    wav_file = file_path.replace('.mp3', '.wav')
    
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
    
    # Remove the wav file after transcription
    os.remove(wav_file)
    
    # Simplify the date format
    simplified_date = datetime.strptime(metadata['pubDate'], "%a, %d %b %Y %H:%M:%S %z").strftime("%B %d, %Y")
    
    # Add podcast metadata to the transcript file
    with open(txt_file, "r+") as f:
        original_content = f.read()
        f.seek(0)
        # Use the original title with spaces here
        original_title = metadata['title']
        f.write(f"{original_title}\n{metadata['link']}\n{simplified_date}\n\n")
        f.write(original_content)

    return txt_file

def start_html_log(history_file):
    """Initialize the PodcastHistory file with a header, if it does not exist."""
    if not os.path.exists(history_file):
        header = """
<html>
<head>
    <title>Podcasts I've Listened To</title>
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
        h2 {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            font-weight: 600;
            font-size: 24px;
            color: #000000;
            margin-bottom: 20px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            text-align: center;
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
    </style>
</head>
<body>
    <h2>Podcasts I've Listened To</h2>
    <table>
        <tr>
            <th>Title</th>
            <th>Pub Date</th>
            <th>Transcript</th>
            <th>Transcribed Audio</th>
            <th>Play via GitHub</th>
            <th>Pod Site</th>
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

def save_downloaded_url(history_file, metadata, file_name, transcript_name):
    """Save the downloaded URL and metadata to the PodcastHistory file."""
    print(f"Saving to HTML: {metadata['title']}")
    normalized_title = normalize_folder_name(metadata['title'])
    
    # Ensure file_name and transcript_name are just the filenames, not full URLs
    file_name = os.path.basename(file_name)
    transcript_name = os.path.basename(transcript_name)
    
    # Construct the GitHub URLs
    mp3_github_url = f"https://media.githubusercontent.com/media/{GITHUB_USERNAME}/{GITHUB_REPO_NAME}/main/transcribed/{normalized_title}/{file_name}"
    transcript_github_url = f"https://raw.githubusercontent.com/{GITHUB_USERNAME}/{GITHUB_REPO_NAME}/main/transcribed/{normalized_title}/{transcript_name}"
    
    entry = f"""
<tr>
    <td><a href="{html.escape(metadata['guid'])}" target="_blank">{html.escape(metadata['title'])}</a></td>
    <td>{html.escape(format_date(metadata['pubDate']))}</td>
    <td><a href="{transcript_github_url}" target="_blank">Download Transcript</a></td>
    <td><a href="{mp3_github_url}">Press <strong>Option</strong> (Mac) to d/l</a></td>
    <td><audio src="{mp3_github_url}" controls></audio></td>
    <td><a href="{html.escape(metadata['link'])}" target="_blank">Pod Site</a></td>
</tr>
    """
    with open(history_file, "a") as f:
        f.write(entry)

def update_html_links(history_file):
    """Update HTML file links to point to GitHub."""
    with open(history_file, 'r+') as f:
        content = f.read()
        content = re.sub(
            r'file://[^"]+\.mp3',
            lambda match: match.group(0).replace('file://', f"https://media.githubusercontent.com/media/{GITHUB_USERNAME}/{GITHUB_REPO_NAME}/main/transcribed/"),
            content
        )
        content = re.sub(
            r'file://[^"]+\.txt',
            lambda match: match.group(0).replace('file://', f"https://raw.githubusercontent.com/{GITHUB_USERNAME}/{GITHUB_REPO_NAME}/main/transcribed/"),
            content
        )
        f.seek(0)
        f.write(content)
        f.truncate()

def format_date(date_str):
    """Format the date to 'Month Day, Year'."""
    date_obj = datetime.strptime(date_str, "%a, %d %b %Y %H:%M:%S %z")
    return date_obj.strftime("%B %d, %Y")

def load_downloaded_urls(history_file):
    """Load the list of downloaded URLs from the PodcastHistory file."""
    downloaded_urls = set()
    if os.path.exists(history_file):
        with open(history_file, 'r') as f:
            for line in f:
                match = re.search(r'<a href="([^"]+)" target="_blank">Stream</a>', line)
                if match:
                    downloaded_urls.add(match.group(1))
    return downloaded_urls

def process_feed(feed_url, download_folder, history_file, db_path, debug=True):
    """Process the RSS feed, download new MP3 files, and store data in SQLite DB."""
    if debug:
        print(f"Fetching feed from {feed_url}")
    
    response = requests.get(feed_url)
    response.raise_for_status()

    root = ET.fromstring(response.content)

    # Connect to the database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    new_files = []

    for item in root.findall('./channel/item')[:DEBUG_MODE_LIMIT]:
        title = item.find('title').text
        pubDate = item.find('pubDate').text
        guid = item.find('guid').text
        link = item.find('link').text
        enclosure = item.find('enclosure')

        if enclosure is not None:
            mp3_url = enclosure.get('url')
            if mp3_url:
                if debug:
                    print(f"Enclosure URL found: {mp3_url}")
                
                # Check if this URL is already in the database
                cursor.execute("SELECT COUNT(1) FROM podcasts WHERE file_name = ?", (mp3_url,))
                already_processed = cursor.fetchone()[0] > 0
                
                if not already_processed:
                    if debug:
                        print(f"New file found: {mp3_url}")
                    
                    try:
                        metadata = {
                            "title": title,
                            "pubDate": pubDate,
                            "guid": guid,
                            "link": link
                        }
                        local_filename, filename = download_file(mp3_url, download_folder, title)
                        transcript_file = transcribe_with_whisper(local_filename, metadata)
                        add_podcast_to_db(db_path, metadata, filename, os.path.basename(transcript_file))
                        
                        if debug:
                            print(f"Downloaded, transcribed, and saved: {mp3_url} as {filename} with transcript {transcript_file}")
                        
                        new_files.extend([local_filename, transcript_file])
                        organize_podcast_files(title, local_filename, transcript_file)
                        
                    except Exception as e:
                        if debug:
                            print(f"Failed to process {mp3_url}: {e}")
                else:
                    if debug:
                        print(f"File already processed: {mp3_url}")
        else:
            if debug:
                print(f"No enclosure found for {title}")

    # Close the database connection
    conn.close()

    upload_successful = False
    if new_files:
        generate_html_from_db(db_path, history_file)
        if UPDATE_HTML_LINKS:
            update_html_links(history_file)
        if ENABLE_GITHUB_COMMIT:
            commit_database_and_html(REPO_ROOT, DB_PATH, PODCAST_HISTORY_FILE)
            upload_successful = commit_new_podcast_files(REPO_ROOT, new_files)
        if ENABLE_GITHUB_PAGES:
            enable_github_pages()

    if upload_successful:
        for file in new_files:
            if os.path.exists(file):
                os.remove(file)
        print("Local files deleted after successful upload.")
    else:
        print("Upload was not successful. Local files were not deleted.")

    # Cleanup any remaining files in the transcribed directory
    transcribed_dir = os.path.join(REPO_ROOT, "transcribed")
    if os.path.exists(transcribed_dir):
        for root, dirs, files in os.walk(transcribed_dir):
            for file in files:
                os.remove(os.path.join(root, file))
            for dir in dirs:
                shutil.rmtree(os.path.join(root, dir))
        print("Cleaned up remaining files in the transcribed directory.")
    else:
        print("Transcribed directory does not exist. No cleanup needed.")

    if debug:
        print("Feed processing completed.")

if __name__ == "__main__":
    check_git_installed()
    check_git_lfs_installed()  # Ensure Git LFS is installed

    if ENABLE_GITHUB_COMMIT and GITHUB_USERNAME != "your_github_username":
        check_github_ssh_connection()

    if GITHUB_REPO_CHECK:
        check_create_github_repo(GITHUB_REPO_NAME)
    
    install_sqlite_with_brew()

    initialize_local_git_repo(REPO_ROOT)
    setup_database(DB_PATH)
    
    try:
        process_feed(RSS_FEED_URL, PODCAST_AUDIO_FOLDER, PODCAST_HISTORY_FILE, DB_PATH, debug=True)
        print("Script completed successfully.")
    except Exception as e:
        print(f"An error occurred during processing: {e}")
        print("The script did not complete successfully. Local files may not have been uploaded or deleted.")
