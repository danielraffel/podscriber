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
import random
import string
import filecmp

# Import configuration
from config import (
    RSS_FEED_URL, PODCAST_AUDIO_FOLDER, PODCAST_HISTORY_FILE, WHISPER_MODEL_PATH,
    WHISPER_EXECUTABLE, TRANSCRIBED_FOLDER, AUTO_OVERWRITE, GITHUB_REPO_CHECK,
    GITHUB_REPO_NAME, ENABLE_GITHUB_COMMIT, UPDATE_HTML_LINKS,
    GITHUB_USERNAME, GITHUB_TOKEN, GITHUB_REPO_PRIVATE, DEBUG_MODE_LIMIT, 
    REPO_ROOT, ENABLE_GITHUB_PAGES,
    WHISPER_SETUP, WHISPER_ROOT,CHROMADB_DB_PATH, TOKENIZERS_PARALLELISM,
    USE_EXISTING_DATA, APP_ENTRY, JINJA_TEMPLATES, PUBLIC_SSH_KEY, PRIVATE_SSH_KEY,
    USE_GITHUB_DEPLOY_KEY, GITHUB_PRO_ACCOUNT
)

# Set Hugging Face Tokenizers environment variable
os.environ["TOKENIZERS_PARALLELISM"] = TOKENIZERS_PARALLELISM

def copy_files_to_repo_root():
    """Ensure the APP_ENTRY, JINJA_TEMPLATES, pyproject.toml, config.py, Dockerfile, docker-compose.yaml, podscriber.py, and private SSH key are copied into the Git repository."""
    app_entry_copy = os.path.join(REPO_ROOT, "main.py")
    jinja_templates_copy = os.path.join(REPO_ROOT, "templates")
    config_copy = os.path.join(REPO_ROOT, "config.py")
    pyproject_copy = os.path.join(REPO_ROOT, "pyproject.toml")
    dockerfile_copy = os.path.join(REPO_ROOT, "Dockerfile")
    docker_compose_copy = os.path.join(REPO_ROOT, "docker-compose.yaml")
    podscriber_copy = os.path.join(REPO_ROOT, "podscriber.py")
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_source = os.path.join(script_dir, "repo_root_config.py")
    pyproject_source = os.path.join(script_dir, "pyproject.toml")
    dockerfile_source = os.path.join(script_dir, "Dockerfile")
    docker_compose_source = os.path.join(script_dir, "docker-compose.yaml")

    # Check and copy APP_ENTRY file
    if os.path.exists(APP_ENTRY):
        print(f"Found APP_ENTRY: {APP_ENTRY}")
        if not os.path.exists(app_entry_copy) or os.path.getmtime(app_entry_copy) < os.path.getmtime(APP_ENTRY):
            print(f"Copying {APP_ENTRY} to {app_entry_copy}")
            shutil.copy(APP_ENTRY, app_entry_copy)
            run_git_command(["git", "add", app_entry_copy], REPO_ROOT)
            run_git_command(["git", "commit", "-m", "Update main.py"], REPO_ROOT)
        else:
            print(f"{app_entry_copy} already exists and is up-to-date.")
    else:
        print(f"APP_ENTRY not found: {APP_ENTRY}")

    # Check and copy JINJA_TEMPLATES directory
    if os.path.exists(JINJA_TEMPLATES):
        print(f"Found JINJA_TEMPLATES: {JINJA_TEMPLATES}")
        if not os.path.exists(jinja_templates_copy):
            print(f"Copying {JINJA_TEMPLATES} to {jinja_templates_copy}")
            shutil.copytree(JINJA_TEMPLATES, jinja_templates_copy)
            run_git_command(["git", "add", jinja_templates_copy], REPO_ROOT)
            run_git_command(["git", "commit", "-m", "Update templates"], REPO_ROOT)
        else:
            print(f"{jinja_templates_copy} already exists.")
    else:
        print(f"JINJA_TEMPLATES not found: {JINJA_TEMPLATES}")

    # Check and copy config.py or repo_root_config.py based on repo visibility
    if GITHUB_REPO_PRIVATE:
        # If the repo is private, copy the actual config.py
        if os.path.exists("config.py"):
            print(f"Copying config.py to {config_copy}")
            shutil.copy("config.py", config_copy)
            run_git_command(["git", "add", config_copy], REPO_ROOT)
            run_git_command(["git", "commit", "-m", "Update config.py"], REPO_ROOT)
        else:
            print(f"config.py not found.")
    else:
        # If the repo is public, copy repo_root_config.py and rename it to config.py
        if os.path.exists(config_source):
            print(f"Found config source: {config_source}")
            if not os.path.exists(config_copy) or os.path.getmtime(config_copy) < os.path.getmtime(config_source):
                print(f"Copying {config_source} to {config_copy}")
                shutil.copy(config_source, config_copy)
                run_git_command(["git", "add", config_copy], REPO_ROOT)
                run_git_command(["git", "commit", "-m", "Update config.py"], REPO_ROOT)
            else:
                print(f"{config_copy} already exists and is up-to-date.")
        else:
            print(f"Config source not found: {config_source}")

    # Check and copy pyproject.toml
    if os.path.exists(pyproject_source):
        print(f"Found pyproject.toml source: {pyproject_source}")
        if not os.path.exists(pyproject_copy) or os.path.getmtime(pyproject_copy) < os.path.getmtime(pyproject_source):
            print(f"Copying {pyproject_source} to {pyproject_copy}")
            shutil.copy(pyproject_source, pyproject_copy)
            run_git_command(["git", "add", pyproject_copy], REPO_ROOT)
            run_git_command(["git", "commit", "-m", "Update pyproject.toml"], REPO_ROOT)
        else:
            print(f"{pyproject_copy} already exists and is up-to-date.")
    else:
        print(f"pyproject.toml source not found: {pyproject_source}")

    # Check and copy Dockerfile
    if os.path.exists(dockerfile_source):
        print(f"Found Dockerfile source: {dockerfile_source}")
        if not os.path.exists(dockerfile_copy) or os.path.getmtime(dockerfile_copy) < os.path.getmtime(dockerfile_source):
            print(f"Copying {dockerfile_source} to {dockerfile_copy}")
            shutil.copy(dockerfile_source, dockerfile_copy)
            run_git_command(["git", "add", dockerfile_copy], REPO_ROOT)
            run_git_command(["git", "commit", "-m", "Update Dockerfile"], REPO_ROOT)
        else:
            print(f"{dockerfile_copy} already exists and is up-to-date.")
    else:
        print(f"Dockerfile source not found: {dockerfile_source}")

    # Check and copy docker-compose.yaml
    if os.path.exists(docker_compose_source):
        print(f"Found docker-compose.yaml source: {docker_compose_source}")
        if not os.path.exists(docker_compose_copy) or os.path.getmtime(docker_compose_copy) < os.path.getmtime(docker_compose_source):
            print(f"Copying {docker_compose_source} to {docker_compose_copy}")
            shutil.copy(docker_compose_source, docker_compose_copy)
            run_git_command(["git", "add", docker_compose_copy], REPO_ROOT)
            run_git_command(["git", "commit", "-m", "Update docker-compose.yaml"], REPO_ROOT)
        else:
            print(f"{docker_compose_copy} already exists and is up-to-date.")
    else:
        print(f"docker-compose.yaml source not found: {docker_compose_source}")

    # Check and copy podscriber.py
    if os.path.exists(os.path.join(script_dir, "podscriber.py")):
        print(f"Found podscriber.py: {os.path.join(script_dir, 'podscriber.py')}")
        if not os.path.exists(podscriber_copy) or os.path.getmtime(podscriber_copy) < os.path.getmtime(os.path.join(script_dir, "podscriber.py")):
            print(f"Copying podscriber.py to {podscriber_copy}")
            shutil.copy(os.path.join(script_dir, "podscriber.py"), podscriber_copy)
            run_git_command(["git", "add", podscriber_copy], REPO_ROOT)
            run_git_command(["git", "commit", "-m", "Update podscriber.py"], REPO_ROOT)
        else:
            print(f"{podscriber_copy} already exists and is up-to-date.")
    else:
        print(f"podscriber.py not found: {os.path.join(script_dir, 'podscriber.py')}")

    # Check and copy private SSH key
    private_ssh_key_source = os.path.expanduser(PRIVATE_SSH_KEY)  # Changed to PRIVATE_SSH_KEY
    if os.path.exists(private_ssh_key_source):
        print(f"Found private SSH key: {private_ssh_key_source}")
        private_ssh_key_copy = os.path.join(REPO_ROOT, os.path.basename(private_ssh_key_source))
        if not os.path.exists(private_ssh_key_copy) or not filecmp.cmp(private_ssh_key_source, private_ssh_key_copy):
            print(f"Copying {private_ssh_key_source} to {private_ssh_key_copy}")
            shutil.copy(private_ssh_key_source, private_ssh_key_copy)
            run_git_command(["git", "add", private_ssh_key_copy], REPO_ROOT)
            run_git_command(["git", "commit", "-m", "Update private SSH key"], REPO_ROOT)
        else:
            print(f"{private_ssh_key_copy} already exists and is up-to-date.")
    else:
        print(f"Private SSH key not found: {private_ssh_key_source}")

# Configuration and Constants
REPO_ROOT = os.path.expanduser(REPO_ROOT)
PODCAST_AUDIO_FOLDER = os.path.expanduser(PODCAST_AUDIO_FOLDER)
PODCAST_HISTORY_FILE = os.path.expanduser(PODCAST_HISTORY_FILE)
TRANSCRIBED_FOLDER = os.path.join(REPO_ROOT, "transcribed")
CHROMADB_DB_PATH = os.path.expanduser(CHROMADB_DB_PATH)

# Get podcast entries from ChromaDB
def get_podcast_entries(podcast_collection):
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
            mp3_url = metadata.get("mp3_url", "#")  
            link = metadata.get("link", "#")  

            # Construct the transcript URL
            transcript_github_url = f"https://raw.githubusercontent.com/{GITHUB_USERNAME}/{GITHUB_REPO_NAME}/main/transcribed/{normalize_folder_name(podcast_name)}/{normalize_folder_name(episode_title)}.txt"

            # Update metadata with mp3_url and transcript_url
            metadata['mp3_url'] = mp3_url
            metadata['transcript_url'] = transcript_github_url  # Now this is defined

            # Append each entry as a dictionary
            entries.append({
                "podcast_name": podcast_name,
                "episode_title": episode_title,
                "listen_date": listen_date,
                "transcript_url": transcript_github_url,  # Ensure this is included
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

def generate_random_string(length=8):
    """Generate a random string of fixed length."""
    letters = string.ascii_letters + string.digits
    return ''.join(random.choice(letters) for i in range(length))

def generate_ssh_keys(repo_name):
    """Generate SSH keys for the specified repository."""
    random_suffix = generate_random_string()
    public_key_name = f"{repo_name}_{random_suffix}.pub"
    private_key_name = f"{repo_name}_{random_suffix}"
    public_key_path = os.path.expanduser(f"~/.ssh/{public_key_name}")
    private_key_path = os.path.expanduser(f"~/.ssh/{private_key_name}")

    # Generate SSH key pair
    subprocess.run(["ssh-keygen", "-t", "rsa", "-b", "4096", "-f", private_key_path, "-N", ""], check=True)

    # Update config.py with the new key names
    update_config_with_keys(public_key_name, private_key_name)

    return public_key_path, private_key_path

def update_config_with_keys(public_key_name, private_key_name):
    """Update the config.py file with the new SSH key names."""
    config_path = "config.py"

    with open(config_path, 'r') as file:
        config_content = file.read()

    # Replace the placeholders with the actual filenames
    config_content = re.sub(
        r'PUBLIC_SSH_KEY\s*=\s*".*"',
        f'PUBLIC_SSH_KEY = "~/.ssh/{public_key_name}"',
        config_content
    )
    config_content = re.sub(
        r'PRIVATE_SSH_KEY\s*=\s*".*"',
        f'PRIVATE_SSH_KEY = "~/.ssh/{private_key_name}"',
        config_content
    )

    with open(config_path, 'w') as file:
        file.write(config_content)

    # Reload the config module to get the updated values
    import importlib
    import config
    importlib.reload(config)
    global PUBLIC_SSH_KEY, PRIVATE_SSH_KEY
    PUBLIC_SSH_KEY = config.PUBLIC_SSH_KEY
    PRIVATE_SSH_KEY = config.PRIVATE_SSH_KEY

def add_deploy_key_to_repo(repo_name, public_key):
    """Add the public SSH key as a deploy key to the GitHub repository."""
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    url = f"https://api.github.com/repos/{GITHUB_USERNAME}/{repo_name}/keys"
    data = {
        "title": f"Deploy Key for {repo_name}",
        "key": open(public_key).read(),
        "read_only": True
    }
    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()
    print(f"Deploy key added to {repo_name}.")

def check_create_github_repo(repo_name):
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
            "private": GITHUB_REPO_PRIVATE
        }
        create_response = requests.post(create_repo_url, headers=headers, json=data)
        create_response.raise_for_status()
        print(f"Repository {repo_name} created successfully.")

        # Check if we need to generate SSH keys
        if GITHUB_REPO_PRIVATE and USE_GITHUB_DEPLOY_KEY:
            public_key_path, private_key_path = generate_ssh_keys(repo_name)
            add_deploy_key_to_repo(repo_name, public_key_path)
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
        run_git_command(["git", "clone", f"git@github.com:{GITHUB_USERNAME}/{GITHUB_REPO_NAME}.git", repo_root], cwd=".")
    else:
        if is_git_repo(repo_root):
            print(f"Git repository already initialized in {repo_root}.")
            # Check if 'main' branch exists
            result = subprocess.run(["git", "show-ref", "--verify", "--quiet", "refs/heads/main"], cwd=repo_root)
            if result.returncode != 0:
                print("Creating 'main' branch...")
                run_git_command(["git", "checkout", "-b", "main"], repo_root)
            else:
                print("'main' branch already exists.")
        else:
            print(f"Directory {repo_root} exists but is not a git repository. Initializing as git repository.")
            run_git_command(["git", "init"], repo_root)
            run_git_command(["git", "remote", "add", "origin", f"git@github.com:{GITHUB_USERNAME}/{GITHUB_REPO_NAME}.git"], repo_root)
            run_git_command(["git", "checkout", "-b", "main"], repo_root)

# Ensure there's an initial commit in the repository
def ensure_initial_commit(repo_root):
    """Ensure there's an initial commit in the repository."""
    # Check if there are any commits
    result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo_root, capture_output=True, text=True)
    if result.returncode != 0:
        print("No commits found. Creating initial commit...")
        # Create a README.md file
        with open(os.path.join(repo_root, "README.md"), "w") as f:
            f.write(f"# {GITHUB_REPO_NAME}\n\nThis repository contains podcast archives.")
        
        # Add and commit README.md
        run_git_command(["git", "add", "README.md"], repo_root)
        run_git_command(["git", "commit", "-m", "Initial commit"], repo_root)
        
        # Push to the remote repository
        run_git_command(["git", "push", "-u", "origin", "main"], repo_root)
        print("Initial commit created and pushed.")
    else:
        print("Repository already has commits.")

# Create the initial commit in the local Git repository
def create_initial_commit(repo_root):
    """Create the initial commit in the local Git repository."""
    readme_path = os.path.join(repo_root, "README.md")
    try:
        with open(readme_path, "w") as f:
            f.write(f"# {GITHUB_REPO_NAME}\n\nThis repository contains podcast archives.")
        
        # Add README to Git
        if not run_git_command(["git", "add", "README.md"], repo_root):
            print("Failed to add README.md to Git.")
            return

        # Commit the README file
        if not run_git_command(["git", "commit", "-m", "Initial commit"], repo_root):
            print("Failed to commit README.md.")
            return

        # Rename the branch to 'main'
        if not run_git_command(["git", "branch", "-M", "main"], repo_root):
            print("Failed to rename branch to main.")
            return

        # Push the initial commit to the remote repository on the 'main' branch
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

# Enable GitHub Pages for the repository and update the README.md with the PODCAST_HISTORY_FILE link
def enable_github_pages():
    """Enable GitHub Pages for the repository."""
    # Check if the repository is private and the account is not Pro
    if GITHUB_REPO_PRIVATE and not GITHUB_PRO_ACCOUNT:
        print("Skipping GitHub Pages setup: Private repositories require a Pro account.")
        return

    # Construct the URL to the podcast archive
    history_filename = os.path.basename(PODCAST_HISTORY_FILE)
    archive_url = f"https://{GITHUB_USERNAME}.github.io/{GITHUB_REPO_NAME}/{history_filename}"

    if check_github_pages_enabled():
        print(f"GitHub Pages is already enabled for {GITHUB_REPO_NAME}.")
        print(f"Visit your site at: {archive_url}")
        return

    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    url = f"https://api.github.com/repos/{GITHUB_USERNAME}/{GITHUB_REPO_NAME}/pages"

    # Ensure the `main` branch exists before enabling GitHub Pages
    result = subprocess.run(["git", "rev-parse", "--verify", "origin/main"], cwd=REPO_ROOT, capture_output=True, text=True)
    if result.returncode != 0:
        print("The 'main' branch does not exist yet. Skipping GitHub Pages setup.")
        return

    # Proceed to enable GitHub Pages after verifying the branch
    data = {
        "source": {
            "branch": "main",
            "path": "/"
        }
    }
    
    response = requests.post(url, headers=headers, json=data)
    if response.status_code in [201, 204]:
        print(f"GitHub Pages enabled for repository {GITHUB_REPO_NAME}.")
        print(f"Visit your site at: {archive_url}")
        
        # Update the README.md with the archive link
        update_readme_with_archive_link(REPO_ROOT, archive_url)
    else:
        print(f"Failed to enable GitHub Pages: {response.status_code} - {response.text}")

# Update the README.md by replacing the existing description with the archive link
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
    if not run_git_command(["git", "add", "README.md"], cwd=repo_root):
        print("Failed to add README.md to Git.")
        return
    if not run_git_command(["git", "commit", "-m", "Update README.md with podcast archive link"], cwd=repo_root):
        print("Failed to commit README.md.")
        return
    if not run_git_command(["git", "push", "origin", "main"], cwd=repo_root):
        print("Failed to push changes to remote.")
        return

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
def commit_database_and_files(repo_root, db_path, history_file, new_files):
    """Commit changes to the database directory, HTML file, and new transcribed files."""
    if not os.path.exists(history_file):
        print(f"Error: {history_file} does not exist.")
        return False

    if db_path and not os.path.exists(db_path):
        print(f"Error: Database path {db_path} does not exist.")
        return False

    try:
        # Check if there is an initial commit
        has_commit = has_initial_commit(repo_root)

        if not has_commit:
            print("No initial commit found. Creating initial commit.")
            create_initial_commit(repo_root)
            # After creating the initial commit, proceed with adding and pushing new files

        # Check for uncommitted changes before stashing
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repo_root,
            capture_output=True,
            text=True
        ).stdout
        if status.strip():
            # Uncommitted changes exist, stash them
            if not run_git_command(["git", "stash"], cwd=repo_root):
                print("Failed to stash changes.")
                return False
        else:
            print("No changes to stash.")

        # Pull latest changes
        if not run_git_command(["git", "pull", "--rebase", "origin", "main"], cwd=repo_root):
            print("Failed to pull latest changes.")
            return False

        # Try to pop the stash, but continue even if there's nothing to pop
        result = subprocess.run(
            ["git", "stash", "pop"],
            cwd=repo_root,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            if "No stash entries found" in result.stderr or "No stash entries found" in result.stdout:
                print("No stash entries to pop.")
            else:
                print(f"Error during git stash pop: {result.stderr}")
                return False

        # Stage the entire ChromaDB database directory
        if db_path:
            print(f"Adding to Git: {os.path.relpath(db_path, repo_root)}")
            if not run_git_command(
                ["git", "add", os.path.relpath(db_path, repo_root)],
                cwd=repo_root
            ):
                print("Failed to add database directory to Git.")
                return False

        # Stage the HTML file
        print(f"Adding to Git: {os.path.relpath(history_file, repo_root)}")
        if not run_git_command(
            ["git", "add", os.path.relpath(history_file, repo_root)],
            cwd=repo_root
        ):
            print("Failed to add history file to Git.")
            return False

        # Stage the transcribed folder if it exists
        if os.path.exists(TRANSCRIBED_FOLDER):
            print(f"Adding to Git: {os.path.relpath(TRANSCRIBED_FOLDER, repo_root)}")
            if not run_git_command(
                ["git", "add", os.path.relpath(TRANSCRIBED_FOLDER, repo_root)],
                cwd=repo_root
            ):
                print("Failed to add transcribed folder to Git.")
                return False

        # Stage the updated chroma_hashes.txt file
        hash_file = os.path.join(repo_root, 'chroma_hashes.txt')
        if os.path.exists(hash_file):
            print(f"Adding to Git: {os.path.relpath(hash_file, repo_root)}")
            if not run_git_command(
                ["git", "add", os.path.relpath(hash_file, repo_root)],
                cwd=repo_root
            ):
                print("Failed to add chroma_hashes.txt to Git.")
                return False

        # Debugging: Print git status
        status_result = subprocess.run(
            ["git", "status"],
            cwd=repo_root,
            capture_output=True,
            text=True
        )
        print(f"Git status output:\n{status_result.stdout}")

        # Check if there are any changes to commit
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repo_root,
            capture_output=True,
            text=True
        ).stdout
        if status.strip():
            if not run_git_command(
                ["git", "commit", "-m", "Update database, HTML, and podcast files"],
                cwd=repo_root
            ):
                print("Failed to commit changes.")
                return False

            # Check if 'main' branch exists on remote
            result = subprocess.run(["git", "ls-remote", "--exit-code", "--heads", "origin", "main"], cwd=repo_root, capture_output=True)
            if result.returncode != 0:
                print("'main' branch doesn't exist on remote. Pushing current branch.")
                current_branch = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=repo_root, capture_output=True, text=True).stdout.strip()
                if not run_git_command(["git", "push", "-u", "origin", current_branch], cwd=repo_root):
                    print(f"Failed to push {current_branch} to remote.")
                    return False
            else:
                if not run_git_command(["git", "push", "origin", "main"], cwd=repo_root):
                    print("Failed to push changes to remote.")
                    return False

            print("Database, HTML, and podcast files committed and pushed.")
            return True
        else:
            print("No changes to commit for the database, HTML, or podcast files.")
            return False

    except Exception as e:
        print(f"Failed to commit changes: {e}")
        return False

# Add the podcast metadata and transcript to the ChromaDB collection
def add_podcast_to_db_chroma(metadata, mp3_url, transcript_name, transcript_text):
    global podcast_collection
    metadata['mp3_url'] = mp3_url  # Store the mp3_url in the metadata

    # Construct the transcript GitHub URL and add it to metadata
    transcript_github_url = f"https://raw.githubusercontent.com/{GITHUB_USERNAME}/{GITHUB_REPO_NAME}/main/transcribed/{normalize_folder_name(metadata['podcast_name'])}/{transcript_name}"
    metadata['transcript_url'] = transcript_github_url  # Add transcript URL to metadata

    document = f"{metadata['podcast_name']} - {metadata['episode_title']}\nTranscript: {transcript_text}"

    podcast_collection.upsert(
        documents=[document],  # Add the text of the transcript with additional metadata as a document
        ids=[metadata['guid']],  # Use the GUID as the document ID
        metadatas=[metadata]  # Store the entire metadata dictionary
    )

    print(f"Data committed to ChromaDB with transcript URL: {transcript_github_url}")

# Generate the HTML file from the ChromaDB collection
def generate_html_from_chroma_db(history_file):
    global podcast_collection
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
def process_feed(feed_url, download_folder, history_file, debug=True):
    global podcast_collection
    """Process the RSS feed, download new MP3 files, transcribe them, and store data in ChromaDB."""
    
    if USE_EXISTING_DATA and os.path.exists(CHROMADB_DB_PATH) and os.path.exists(TRANSCRIBED_FOLDER):
        print("Using existing ChromaDB and transcript data.")
        # Skip fetching RSS feed and directly generate HTML
        generate_html_from_chroma_db(history_file)
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

                    # Save podcast metadata into the ChromaDB, including transcript text
                    add_podcast_to_db_chroma(metadata, mp3_url, os.path.basename(new_transcript_path), transcript_text)

                    # Add both the MP3 and WAV file paths to new_files for deletion later
                    wav_file = mp3_file_path.replace('.mp3', '.wav')
                    new_files.append((mp3_file_path, wav_file))  # Append tuple with MP3 and WAV paths
                    print(f"Added to new_files: {mp3_file_path}, {wav_file}")

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

# Initialize the PodcastHistory file with a header, if it does not exist
def start_html_log(history_file):
    """Initialize the PodcastHistory file with a header, if it does not exist."""
    header = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Podcast &#x1F442; Archive</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        /* Optional: Custom styles can go here */
    </style>
</head>
<body class="bg-gray-100">
    <div class="container mx-auto p-4">
        <h2 class="text-3xl font-bold mb-4">Podcast &#x1F442; Archive</h2>
        <table id="podcastTable" class="min-w-full bg-white shadow-md rounded-lg overflow-hidden">
            <thead>
                <tr class="bg-blue-500 text-white uppercase text-sm leading-normal">
                    <th class="py-3 px-6 text-left">Podcast</th>
                    <th class="py-3 px-6 text-left">Episode</th>
                    <th class="py-3 px-6 text-left">Listen Date</th>
                    <th class="py-3 px-6 text-left">Transcript</th>
                    <th class="py-3 px-6 text-left">Stream</th>
                </tr>
            </thead>
            <tbody class="text-gray-600 text-sm font-light">
                """
    with open(history_file, "w") as f:
        f.write(header)

# Add a footer to the PodcastHistory file
def end_html_log(history_file):
    """Finalize the PodcastHistory file with a footer."""
    footer = """
            </tbody>
        </table>
    </div>
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
</body>
</html>
    """
    with open(history_file, "a") as f:
        f.write(footer)

# Save the downloaded URL and metadata to the PodcastHistory file
def save_downloaded_url(history_file, metadata, transcript_name):
    """Save the downloaded URL and metadata to the PodcastHistory file."""
    print(f"Saving to HTML: {metadata['episode_title']}")

    # Construct the transcript URL on GitHub
    transcript_github_url = f"https://raw.githubusercontent.com/{GITHUB_USERNAME}/{GITHUB_REPO_NAME}/main/transcribed/{normalize_folder_name(metadata['podcast_name'])}/{transcript_name}"
    
    # Add transcript_url to metadata
    metadata['transcript_url'] = transcript_github_url

    # Handle case where link might be None or empty
    pod_site_link = f"<a href=\"{html.escape(metadata.get('link', ''))}\" target=\"_blank\">Pod Site</a>" if metadata.get('link') else "N/A"
    
    entry = f"""
<tr class="hover:bg-gray-100">
    <td class="py-4 px-6 border-b text-lg"><a href="{html.escape(metadata['link'])}" target="_blank" class="text-blue-600 hover:underline">{html.escape(metadata['podcast_name'])}</a></td>
    <td class="py-4 px-6 border-b text-lg"><a href="{html.escape(metadata['guid'])}" target="_blank" class="text-blue-600 hover:underline">{html.escape(metadata['episode_title'])}</a></td>
    <td class="py-4 px-6 border-b text-lg">{html.escape(format_date_short(metadata['listenDate']))}</td>
    <td class="py-4 px-6 border-b text-lg"><a href="{transcript_github_url}" target="_blank" class="text-blue-500 text-lg">&#x1F4C4;</a></td>
    <td class="py-4 px-6 border-b text-lg"><audio src="{metadata['mp3_url']}" controls class="w-8 h-8"></audio></td>
</tr>
    """
    with open(history_file, "a") as f:
        f.write(entry)

# Update the HTML file links to point to the appropriate locations, if necessary
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

    # Ensure there's an initial commit
    ensure_initial_commit(REPO_ROOT)

    # Ensure APP_ENTRY and JINJA_TEMPLATES are copied to the Git repository
    copy_files_to_repo_root()
    
    # Initialize ChromaDB after Git repository is synchronized
    global client, podcast_collection
    client = chromadb.PersistentClient(path=CHROMADB_DB_PATH)
    podcast_collection = client.get_or_create_collection(name="podcasts")
    client.heartbeat()

    # Generate and compare hashes before syncing
    hash_file = os.path.join(REPO_ROOT, 'chroma_hashes.txt')
    generate_chroma_hashes(CHROMADB_DB_PATH, REPO_ROOT, hash_file)

    pull_and_sync_chromadb_if_necessary(GITHUB_REPO_NAME, CHROMADB_DB_PATH, hash_file, os.path.relpath(CHROMADB_DB_PATH, REPO_ROOT))

    try:
        new_files = process_feed(RSS_FEED_URL, PODCAST_AUDIO_FOLDER, PODCAST_HISTORY_FILE, debug=True)
        print("RSS feed processing completed.")
        
        # Debugging statement to print whether new_files is empty or not
        # print(f"New files to be deleted: {new_files}")

        # Regenerate the chroma hashes after updating the database
        generate_chroma_hashes(CHROMADB_DB_PATH, REPO_ROOT, hash_file)

        if ENABLE_GITHUB_COMMIT:
            upload_successful = commit_database_and_files(REPO_ROOT, CHROMADB_DB_PATH, PODCAST_HISTORY_FILE, new_files)
            if upload_successful:
                print("Files successfully uploaded to GitHub.")
            else:
                print("No changes to upload to GitHub.")
   
    finally:
        print(f"Attempting to delete {len(new_files)} files")
        # Always attempt to delete MP3 and WAV files after processing
        for mp3_file, wav_file in new_files:
            if os.path.exists(mp3_file):
                try:
                    os.remove(mp3_file)
                    print(f"Deleted MP3 file: {mp3_file}")
                except Exception as e:
                    print(f"Failed to delete MP3 file: {mp3_file}. Error: {e}")
            else:
                print(f"MP3 file not found: {mp3_file}")

            if os.path.exists(wav_file):
                try:
                    os.remove(wav_file)
                    print(f"Deleted WAV file: {wav_file}")
                except Exception as e:
                    print(f"Failed to delete WAV file: {wav_file}. Error: {e}")
            else:
                print(f"WAV file not found: {wav_file}")

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
