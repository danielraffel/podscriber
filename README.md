# Podscriber

`podscriber` is a Python-based tool, currently optimized for macOS, that downloads podcast episodes, transcribes them using Whisper, stores metadata in ChromaDB, and generates an HTML archive of your listening history. This archive is hosted on GitHub Pages, with each episode linked to its transcript, allowing you to revisit and search through both the audio and text of what you've listened to.

## Prerequisites

Before running `podscriber`, ensure you have the following installed:

- **uv**: [UV](https://astral.sh/blog/uv-unified-python-packaging) is a fast Python package and project manager.
- **Git**: Required for committing files to a GitHub repository.
- **Python**: Although `uv` can install and manage Python versions, having Python pre-installed can streamline the setup.

Be aware that if you do not have these installed `podscriber` **will** install them at run-time **without asking**:
- **Brew**: Needed for installing SQLite and Git LFS.
- **Whisper**: A speech-to-text model that `podscriber` uses to transcribe podcast audio (if missing will use [WhisperSetup](https://github.com/danielraffel/WhisperSetup))
- **ffmpeg**: Needed for converting audio files during the transcription process.
- **ChromaDB**: Used to store and manage podcast metadata and transcripts.

## Installation

### Step 1: Install `uv`

You need to install `uv` manually to run the script:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Step 2: Clone the Repository

Clone the `podscriber` repository to your local machine:

```bash
git clone https://github.com/danielraffel/podscriber.git
cd podscriber
```

### Step 3: Modify the `config.py` File

Before running the script, you must modify the `config.py` file:

1. **RSS Feed URL**: 
   - Set `RSS_FEED_URL` to the feed you want to monitor for new podcast episodes.

2. **GitHub Username**: 
   - Update `GITHUB_USERNAME` with your GitHub username where the repository will be hosted.

3. **GitHub Token**: 
   - Set `GITHUB_TOKEN` with a Personal Access Token from GitHub. This token is required for authentication to commit files and create the repository.
   - To generate a token:
     1. Go to [GitHub Personal Access Tokens](https://github.com/settings/tokens).
     2. Click "Generate new token" and select the `repo` scope.
     3. Replace the placeholder in `config.py` with your token:
        ```python
        GITHUB_TOKEN = "YOUR_GITHUB_TOKEN"
        ```

4. **Debug Mode Limit (Optional)**:
   - `DEBUG_MODE_LIMIT` controls the number of podcast episodes to process:
     - To process all episodes, set `DEBUG_MODE_LIMIT = None`.
     - To limit the number of episodes, set it to a specific number, e.g., `DEBUG_MODE_LIMIT = 2`.
     - **Do not comment out this line**; if you don't want to limit processing, set it to `None`.

Save your changes to `config.py`.

### Step 4: Run the Script

Execute the `podscriber.py` script using `uv`:

```bash
uv run python podscriber.py
```

`uv` will handle installing any additional dependencies specified in the `pyproject.toml` file.

## GitHub Integration

When the script runs, it can optionally create a GitHub Pages site where your transcriptions and podcast files will be accessible via a URL. This feature also serves as an archive of all the podcasts you've listened to, with direct links to the transcriptions.

### Example GitHub Pages URL

If you configure your `GITHUB_USERNAME`, `GITHUB_REPO_NAME` and `PODCAST_HISTORY_FILE` in `config.py`, the generated GitHub Pages site will be accessible at:

```
https://<GITHUB_USERNAME>.github.io/<GITHUB_REPO_NAME>/<PODCAST_HISTORY_FILE>
```

## Suggested Usage: Automate with Cron

To keep your podcast downloads and transcriptions up to date, you might want to automate the process using a cron job. Here’s an example cron job that runs the script once a day:

```bash
0 2 * * * PATH=/usr/local/bin:$PATH && cd ~/podscriber && screen -dmS podscriber_session ~/Users/plex/.cargo/bin/uv run python3 podscriber.py
```

This cron job will execute `podscriber.py` every day at 2 AM.

Given your preference, I'll convert the `cleanup.sh` script to a Python script so that it can directly import the configuration from `config.py`. This way, you won’t need to manage paths and other settings in multiple places.

### Converted `cleanup.py` Script

```python
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
```

## Development and Debugging with `cleanup.py`

For development or debugging, `podscriber` includes a `cleanup.py` script that resets your environment by removing generated files, directories, and the associated GitHub repository. This ensures a clean slate each time you run the script.

### What `cleanup.py` Does

The `cleanup.py` script performs the following actions:

1. **Removes Local Git Repository**: Deletes the `.git` directory, removing all version control history.
2. **Deletes ChromaDB Database**: Clears all files and directories within your ChromaDB path.
3. **Deletes Chroma Hash File**: Removes the `chroma_hashes.txt` file used by ChromaDB.
4. **Clears Audio and Transcript Files**: Deletes all podcast audio files and transcriptions.
5. **Deletes Podcast History File**: Removes the history file tracking processed podcasts.
6. **Deletes GitHub Repository**: If it exists, deletes the associated GitHub repository (requires appropriate token permissions).

### Running `cleanup.py`

To execute the script:

1. Navigate to the `podscriber` directory:

   ```bash
   cd ~/podscriber
   ```

2. Run the script:

   ```bash
   python3 cleanup.py
   ```

### Flags and Options

You can customize the cleanup by using flags to skip specific actions:

- `--no-delete-chromadb` : Skip deleting the ChromaDB database.
- `--no-delete-chromahash` : Skip deleting the Chroma hash file.
- `--no-delete-git` : Skip deleting the `.git` directory.
- `--no-delete-history` : Skip deleting the podcast history file.
- `--no-delete-audio` : Skip deleting audio files.
- `--no-delete-transcribed` : Skip deleting transcription files.
- `--no-delete-repo` : Skip deleting the GitHub repository.
- `-h, --help` : Display help information.

### Important Notes

- **Manual Execution**: This script is designed to be run manually, giving you full control over when you want to reset your environment.
- **GitHub Token Permissions**: Ensure that your GitHub token has the appropriate permissions to delete repositories. Without this, the script will not be able to remove the repository from GitHub.

## To-Do: Explain overcast-podcast-activity-feed integration
Perhaps I'll get around to explaining how I’m integrating this with [overcast-podcast-activity-feed](https://github.com/dblume/overcast-podcast-activity-feed). In the interim, I’ve made some modifications to [overcast.py](https://github.com/dblume/overcast-podcast-activity-feed/blob/main/overcast.py) to expose MP3 files using the `enclosure_url`. You can view the updated sections in this [gist](https://gist.github.com/danielraffel/5b981fdb72bbf96b28dc3f87fab1c81f). This allows me to access the podcast audio files I've listened to in Overcast and process them with Whisper. Here are the specific changes:

```python
class Episode:
    def __init__(self, podcast, title, url, guid, date, partial, enclosure_url):
        self.podcast = podcast
        self.title = title
        self.url = url
        self.guid = guid
        self.date = date
        self.partial = partial
        self.enclosure_url = enclosure_url
```

```python
def rss(self) -> str:
    date = self.std_date()
    t = time.strptime(date, "%Y-%m-%dT%H:%M:%S%z")
    date = time.strftime("%a, %d %b %Y %H:%M:%S " + date[-5:], t)
    return (f"<item>"
            f"<title>{escape(self.podcast)}: {escape(self.title)}</title>"
            f"<pubDate>{date}</pubDate>"
            f"<link>{escape(self.url)}</link>"
            f"<guid isPermaLink=\"true\">{self.guid}</guid>"
            f"<description><![CDATA[{self.podcast}: {self.title} on {date}]]></description>"
            f"<enclosure url=\"{escape(self.enclosure_url)}\" length=\"0\" type=\"audio/mpeg\" />"
            f"</item>\n")
```

```python
episodes: List[Episode] = list()
for rss in root.findall('.//outline[@type="rss"]'):
    rss_title = rss.attrib['title']
    for ep in rss.findall('outline[@type="podcast-episode"]'):
        if add_episode(ep):
            enclosure_url = ep.attrib.get('enclosureUrl', '')
            episodes.append(Episode(rss_title, ep.attrib['title'], ep.attrib['url'],
                ep.attrib['overcastUrl'], ep.attrib['userUpdatedDate'],
                'progress' in ep.attrib, enclosure_url))
episodes.sort(reverse=True)
```
