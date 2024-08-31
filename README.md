# Podscriber

`podscriber` is a Python-based tool, currently optimized for macOS, that downloads podcast episodes, transcribes them using Whisper, and generates an HTML archive of your listening history. This archive is hosted on GitHub pages, with each episode linked to its transcript, allowing you to revisit and search through both the audio and text of what you've listened to.

## Prerequisites

Before running `podscriber`, ensure you have the following installed:

- **uv**: [UV](https://astral.sh/blog/uv-unified-python-packaging) is a fast Python package and project manager.
- **Git**: Required for committing files to a GitHub repository.
- **Whisper**: A speech-to-text model that `podscriber` uses to transcribe podcast audio.
- **ffmpeg**: Needed for converting audio files during the transcription process.
- **Python**: Although `uv` can install and manage Python versions, having Python pre-installed can streamline the setup.

### Whisper Setup

[WhisperSetup](https://github.com/danielraffel/WhisperSetup) is a streamlined script designed to quickly set up and compile `whisper.cpp`, enabling high-performance speech-to-text transcription on macOS, optimized for Apple Silicon so you can run the transcription locally. `podscriber` will automatically use this script to guide you through setting up Whisper if it detects that it’s not already installed.

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

If you configure your `GITHUB_USERNAME` and `GITHUB_REPO_NAME` in `config.py`, the generated GitHub Pages site will be accessible at:

```
https://<GITHUB_USERNAME>.github.io/<GITHUB_REPO_NAME>/
```

## Suggested Usage: Automate with Cron

To keep your podcast downloads and transcriptions up to date, you might want to automate the process using a cron job. Here’s an example cron job that runs the script once a day:

```bash
0 2 * * * cd ~/podscriber && ~/.cargo/bin/uv run python3 podscriber.py
```

This cron job will execute `podscriber.py` every day at 2 AM.
