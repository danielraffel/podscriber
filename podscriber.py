import os
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
    GITHUB_REPO_NAME, ENABLE_GITHUB_COMMIT, UPDATE_HTML_LINKS,
    GITHUB_USERNAME, GITHUB_TOKEN, GITHUB_REPO_PRIVATE, DEBUG_MODE_LIMIT, 
    REPO_ROOT, ENABLE_GITHUB_PAGES,
    WHISPER_SETUP, WHISPER_ROOT
)

# Configuration and Constants
REPO_ROOT = os.path.expanduser(REPO_ROOT)
PODCAST_AUDIO_FOLDER = os.path.expanduser(PODCAST_AUDIO_FOLDER)
PODCAST_HISTORY_FILE = os.path.expanduser(PODCAST_HISTORY_FILE)
TRANSCRIBED_FOLDER = os.path.join(REPO_ROOT, "transcribed")
DB_PATH = os.path.join(REPO_ROOT, "podcasts.db")

# Git Operations
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

def initialize_local_git_repo(repo_root):
    """Initialize the local Git repository, check for existing database and pull it."""
    if not os.path.exists(repo_root):
        os.makedirs(repo_root)
    
    if not os.path.exists(os.path.join(repo_root, ".git")):
        print(f"Initializing local Git repository in {repo_root}...")
        subprocess.run(["git", "init"], cwd=repo_root, check=True)
        subprocess.run(["git", "remote", "add", "origin", f"git@github.com:{GITHUB_USERNAME}/{GITHUB_REPO_NAME}.git"], cwd=repo_root, check=True)

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
        
        print("Local Git repository initialized.")
    else:
        print("Git repository already initialized.")

    # Check if the database exists in the repository
    if ENABLE_GITHUB_COMMIT:
        check_and_pull_database(repo_root)

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
    if response.status_code in [201, 204]:  # 201 Created or 204 No Content
        # Construct the URL to the podcast archive
        history_filename = os.path.basename(PODCAST_HISTORY_FILE)
        archive_url = f"https://{GITHUB_USERNAME}.github.io/{GITHUB_REPO_NAME}/{history_filename}"
        print(f"GitHub Pages enabled for repository {GITHUB_REPO_NAME}.")
        print(f"Visit your site at: {archive_url}")
        
        # Update the README.md with the archive link
        update_readme_with_archive_link(REPO_ROOT, archive_url)
    else:
        print(f"Failed to enable GitHub Pages: {response.status_code} - {response.text}")

def check_and_pull_database(repo_root):
    """Check if the database exists in the remote repository and pull it if available."""
    db_path = os.path.join(repo_root, "podcasts.db")
    if os.path.exists(db_path):
        print("Local database exists. No need to pull from remote.")
    else:
        # Attempt to pull the latest database from GitHub
        try:
            subprocess.run(["git", "checkout", "main"], cwd=repo_root, check=True)
            subprocess.run(["git", "pull", "origin", "main"], cwd=repo_root, check=True)
            if os.path.exists(db_path):
                print("Database pulled successfully from GitHub.")
            else:
                print("No database found in the remote repository.")
        except subprocess.CalledProcessError as e:
            print(f"Failed to pull database from GitHub: {e}")

def commit_database_and_files(repo_root, db_path, history_file, new_files):
    """Commit changes to the database, HTML file, and new podcast files."""
    if not os.path.exists(history_file):
        print(f"Error: {history_file} does not exist.")
        return

    try:
        # Stage the database, HTML file, and transcribed folder
        subprocess.run(["git", "add", os.path.relpath(db_path, repo_root)], cwd=repo_root, check=True)
        subprocess.run(["git", "add", os.path.relpath(history_file, repo_root)], cwd=repo_root, check=True)
        
        # Add the entire transcribed folder to staging
        if os.path.exists(TRANSCRIBED_FOLDER):
            subprocess.run(["git", "add", os.path.relpath(TRANSCRIBED_FOLDER, repo_root)], cwd=repo_root, check=True)
        
        # Stage new podcast files (if any)
        for file in new_files:
            subprocess.run(["git", "add", os.path.relpath(file, repo_root)], cwd=repo_root, check=True)
        
        # Check if there are any changes to commit
        status = subprocess.run(["git", "status", "--porcelain"], cwd=repo_root, capture_output=True, text=True).stdout
        if status.strip():
            subprocess.run(["git", "commit", "-m", "Update database, HTML, and podcast files"], cwd=repo_root, check=True)
            subprocess.run(["git", "push", "origin", "main"], cwd=repo_root, check=True)
            print("Database, HTML, and podcast files committed and pushed.")
            return True
        else:
            print("No changes to commit for database, HTML, or podcast files.")
            return False

    except subprocess.CalledProcessError as e:
        print(f"Failed to commit changes: {e}")
        return False

# System Checks and Setup
def install_sqlite_with_brew():
    """Install SQLite using Homebrew if not installed."""
    try:
        subprocess.run(["sqlite3", "--version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print("SQLite is installed.")
    except subprocess.CalledProcessError:
        print("SQLite is not installed. Installing with brew...")
        subprocess.run(["brew", "install", "sqlite"], check=True)
        print("SQLite installed successfully.")

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

def install_whisper():
    """Attempt to install Whisper if it's not found."""
    try:
        whisper_setup_path = os.path.expanduser(WHISPER_SETUP)
        os.makedirs(whisper_setup_path, exist_ok=True)
        print("Attempting to install Whisper...")
        os.system(f"git clone https://github.com/danielraffel/WhisperSetup.git {whisper_setup_path}")
        os.system(f"cd {whisper_setup_path} && ./whisper_setup.sh")
        print("Whisper installation complete.")
    except Exception as e:
        print(f"Failed to install Whisper: {e}")
        exit(1)

# Database Operations
def setup_database(db_path):
    """Setup the SQLite database and tables."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Define the SQL query to create the podcasts table
    cursor.execute('''CREATE TABLE IF NOT EXISTS podcasts (
                        id INTEGER PRIMARY KEY,
                        title TEXT,                  -- Podcast episode title
                        listenDate TEXT,             -- Date you listened to the episode
                        guid TEXT,                   -- Unique identifier for the episode
                        link TEXT,                   -- Link to the episode's webpage
                        file_name TEXT,              -- URL of the original MP3 file from the RSS feed enclosure
                        transcript_name TEXT,        -- URL of the transcription file stored on GitHub
                        transcript_text TEXT         -- Content of the transcription text
                    )''')
    conn.commit()
    conn.close()

def add_podcast_to_db(db_path, metadata, mp3_url, transcript_name, transcript_text):
    """Insert podcast data into the SQLite database, including transcription content."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute('''INSERT INTO podcasts (title, listenDate, guid, link, file_name, transcript_name, transcript_text) 
                      VALUES (?, ?, ?, ?, ?, ?, ?)''',
                   (metadata['title'], metadata['listenDate'], metadata['guid'], metadata['link'], mp3_url, transcript_name, transcript_text))
    conn.commit()
    conn.close()

def generate_html_from_db(db_path, history_file):
    """Generate HTML file from SQLite database."""
    print(f"Generating HTML from DB: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Start the HTML log (this will overwrite any existing content)
    start_html_log(history_file)

    cursor.execute('SELECT title, listenDate, file_name, transcript_name, guid, link FROM podcasts')
    rows = cursor.fetchall()
    print(f"Found {len(rows)} podcast entries in the database.")
    for row in rows:
        title, listenDate, file_name, transcript_name, guid, link = row
        print(f"Adding podcast entry to HTML: Title={title}, ListenDate={listenDate}, FileName={file_name}, TranscriptName={transcript_name}, GUID={guid}, Link={link}")
        save_downloaded_url(history_file, {'title': title, 'listenDate': listenDate, 'guid': guid, 'link': link}, file_name, transcript_name)

    # End the HTML log properly
    end_html_log(history_file)
    conn.close()
    print(f"HTML generation complete: {history_file}")

# Feed Processing
def process_feed(feed_url, download_folder, history_file, db_path, debug=True):
    """Process the RSS feed, download new MP3 files, transcribe them, and store data in SQLite DB."""
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
                            "title": title if title is not None else "Untitled",
                            "listenDate": pubDate if pubDate is not None else datetime.now().strftime("%a, %d %b %Y %H:%M:%S %z"),
                            "guid": guid if guid is not None else mp3_url,
                            "link": link if link is not None else ""
                        }
                        local_filename, filename = download_file(mp3_url, download_folder, title)
                        transcript_file, transcript_text = transcribe_with_whisper(local_filename, metadata)
                        
                        # Organize files and get new paths
                        new_mp3_path, new_transcript_path = organize_podcast_files(title, local_filename, transcript_file)
                        
                        # Update new_files list with correct paths
                        new_files.extend([path for path in [new_mp3_path, new_transcript_path] if path])

                        if debug:
                            print(f"Organized files: MP3={new_mp3_path}, Transcript={new_transcript_path}")
                        
                        # Save podcast metadata into the database, including transcript text
                        add_podcast_to_db(db_path, metadata, mp3_url, os.path.basename(new_transcript_path), transcript_text)

                        if debug:
                            print(f"Downloaded, transcribed, and saved: {mp3_url} as {filename} with transcript {new_transcript_path}")
                        
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

    # Ensure HTML is generated
    if new_files or debug:
        print("Generating HTML file...")
        generate_html_from_db(db_path, history_file)
    else:
        print("No new podcasts found, skipping HTML generation.")

# File Operations
def normalize_folder_name(title):
    """Normalize folder names by replacing spaces with underscores and removing non-alphanumeric characters."""
    return re.sub(r'[^\w\s-]', '', title).replace(" ", "_").strip("_")

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
    
    # Read the transcription content
    with open(txt_file, "r") as f:
        transcript_text = f.read()
    
    # Simplify the date format
    simplified_date = datetime.strptime(metadata['listenDate'], "%a, %d %b %Y %H:%M:%S %z").strftime("%B %d, %Y")
    
    # Add podcast metadata to the transcript file
    with open(txt_file, "r+") as f:
        original_content = f.read()
        f.seek(0)
        # Use the original title with spaces here
        original_title = metadata['title']
        f.write(f"{original_title}\n{metadata['link']}\n{simplified_date}\n\n")
        f.write(original_content)

    # After transcription, delete the MP3 and WAV files
    os.remove(file_path)
    os.remove(wav_file)
    
    return txt_file, transcript_text

def organize_podcast_files(title, mp3_file, transcript_file):
    """Organize podcast files into folders and return new file paths."""
    normalized_title = normalize_folder_name(title)
    podcast_folder = os.path.join(TRANSCRIBED_FOLDER, normalized_title)
    
    if not os.path.exists(podcast_folder):
        os.makedirs(podcast_folder, exist_ok=True)
    
    new_transcript_path = os.path.join(podcast_folder, os.path.basename(transcript_file))
    shutil.move(transcript_file, new_transcript_path)
    
    return None, new_transcript_path

# Utilities
def format_date(date_str):
    """Format the date to 'Month Day, Year'."""
    date_obj = datetime.strptime(date_str, "%a, %d %b %Y %H:%M:%S %z")
    return date_obj.strftime("%B %d, %Y")

# HTML Operations
def start_html_log(history_file):
    """Initialize the PodcastHistory file with a header, if it does not exist."""
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
            border-bottom: none.
        }
        tr:nth-child(even) {
            background-color: #f9f9f9;
        }
        tr:hover {
            background-color: #f0f0f0;
            transition: background-color 0.3s ease.
        }
        a {
            color: #2c3e50;
            text-decoration: none.
            border-bottom: 1px solid #3498db;
            transition: color 0.3s ease, border-bottom-color 0.3s ease.
        }
        a:hover {
            color: #3498db;
            border-bottom-color: #2c3e50.
        }
    </style>
</head>
<body>
    <h2>Podcasts I've Listened To</h2>
    <table>
        <tr>
            <th>Title</th>
            <th>Listen Date</th>
            <th>Transcript</th>
            <th>Stream</th>
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

    transcript_github_url = f"https://raw.githubusercontent.com/{GITHUB_USERNAME}/{GITHUB_REPO_NAME}/main/transcribed/{normalize_folder_name(metadata['title'])}/{transcript_name}"
    
    # Handle case where link might be None
    pod_site_link = f"<a href=\"{html.escape(metadata['link'])}\" target=\"_blank\">Pod Site</a>" if metadata['link'] else "N/A"
    
    entry = f"""
<tr>
    <td><a href="{html.escape(metadata['guid'])}" target="_blank">{html.escape(metadata['title'])}</a></td>
    <td>{html.escape(format_date(metadata['listenDate']))}</td>
    <td><a href="{transcript_github_url}" target="_blank">Download Transcript</a></td>
    <td><audio src="{file_name}" controls></audio></td>
    <td>{pod_site_link}</td>
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

# Main Script Execution
if __name__ == "__main__":
    check_git_installed()

    if ENABLE_GITHUB_COMMIT and GITHUB_USERNAME != "your_github_username":
        check_github_ssh_connection()

    if GITHUB_REPO_CHECK:
        check_create_github_repo(GITHUB_REPO_NAME)
    
    install_sqlite_with_brew()

    if not check_whisper_installed():
        print("Whisper is not installed. Attempting to install Whisper...")
        install_whisper()

    initialize_local_git_repo(REPO_ROOT)
    setup_database(DB_PATH)

    try:
        new_files = []
        process_feed(RSS_FEED_URL, PODCAST_AUDIO_FOLDER, PODCAST_HISTORY_FILE, DB_PATH, debug=True)
        
        if ENABLE_GITHUB_COMMIT:
            upload_successful = commit_database_and_files(REPO_ROOT, DB_PATH, PODCAST_HISTORY_FILE, new_files)
            if upload_successful:
                print("Upload was successful.")
            else:
                print("Upload was not successful.")

        # Final fetch and reset to ensure local repo is in sync
        subprocess.run(["git", "fetch", "origin"], cwd=REPO_ROOT, check=True)
        subprocess.run(["git", "reset", "--hard", "origin/main"], cwd=REPO_ROOT, check=True)

        # Enable GitHub Pages if requested and update README with the archive link
        if ENABLE_GITHUB_PAGES:
            enable_github_pages()

        print("Script completed successfully.")
    except Exception as e:
        print(f"An error occurred during processing: {e}")
        print("The script did not complete successfully. Local files may not have been uploaded or deleted.")
