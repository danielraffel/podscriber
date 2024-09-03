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

## Development and Debugging with `cleanup.sh`

For development or debugging purposes, `podscriber` includes a script named `cleanup.sh` that allows you to reset your environment by removing all generated files and directories, as well as deleting the associated GitHub repository. This can be particularly useful if you want to run the script from scratch, ensuring a clean slate each time.

### What `cleanup.sh` Does

The `cleanup.sh` script performs the following actions:

1. **Removes Local Git Repository**: Deletes the `.git` directory within your local `podscriber` repository, effectively removing all version control history.

2. **Deletes Podcast Database**: Removes the `podcasts.db` file, which stores the metadata and other information related to your podcast episodes.

3. **Clears Audio and Transcript Files**: Deletes all downloaded podcast audio files and their corresponding transcriptions from the designated folders.

4. **Deletes HTML Archive**: Removes the HTML file that serves as the archive for your podcast transcriptions.

5. **Deletes the GitHub Repository**: If the GitHub repository associated with `podscriber` exists, the script will delete it. This requires your GitHub token to have the necessary permissions to delete repositories.

### How to Run `cleanup.sh`

Running the `cleanup.sh` script is straightforward:

1. Navigate to the `podscriber` directory:

   ```bash
   cd ~/podscriber
   ```

2. Execute the script manually:

   ```bash
   ./cleanup.sh
   ```

### Important Notes

- **Manual Execution**: This script is designed to be run manually, giving you full control over when you want to reset your environment.
- **GitHub Token Permissions**: Ensure that your GitHub token has the appropriate permissions to delete repositories. Without this, the script will not be able to remove the repository from GitHub.

This script is a powerful tool for developers working on `podscriber`, as it allows you to start fresh with each test run or debugging session, ensuring that no residual data or configurations affect your results.

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
