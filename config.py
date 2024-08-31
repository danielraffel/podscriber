# Configuration for Podcast Downloader and Transcriber
RSS_FEED_URL = "https://example.com/rss_feed.xml" # RSS Feed URL from which to download podcast episodes
REPO_ROOT = "~/podscriber/"  # Update this to the root of your Git repository

# Folder paths to store downloaded podcast files and transcriptions
PODCAST_AUDIO_FOLDER = "~/podscriber/podcast_mp3s" # Path to the folder where podcast audio files will be initially downloaded
PODCAST_HISTORY_FILE = "~/podscriber/podcast_history.html" # Path to the HTML file where your podcast archive will be stored
TRANSCRIBED_FOLDER = "~/podscriber/transcribed"  # Path where transcribed text files are stored

# Configuration for Whisper transcription
WHISPER_SETUP = "~/WhisperSetup" # Path to the WhisperSetup folder
WHISPER_ROOT = "~/whisper.cpp" # Path to the Whisper root folder
WHISPER_MODEL_PATH = "~/whisper.cpp/models/ggml-base.en.bin" # Path to the Whisper model file
WHISPER_EXECUTABLE = "~/whisper.cpp/main" # Path to the Whisper executable
AUTO_OVERWRITE = True  # Set to True to enable FFMPEG tp automatically overwrite files without asking, else False
AUTO_DELETE_MP3 = True  # Set to True to automatically delete MP3 files in PODCAST_AUDIO_FOLDER after transcription

# GitHub Integration Settings
GITHUB_USERNAME = "YOUR_GITHUB_USERNAME" # GitHub username for the repository where files will be committed
GITHUB_TOKEN = "YOUR_GITHUB_TOKEN" # GitHub token for authentication; generate it from your GitHub account
GITHUB_REPO_CHECK = True # Set to True to check and create the GitHub repository if it doesn't exist
GITHUB_REPO_NAME = "podcast-archives" # The name of the GitHub repository where podcast files will be stored
AUTO_DELETE_AFTER_UPLOAD = True  # Set to True to automatically delete files in TRANSCRIBED_FOLDER after uploading to GitHub
GITHUB_REPO_PRIVATE = False  # Set to True to create a private repository, False to create a public one
ENABLE_GITHUB_COMMIT = True # Set to True to enable committing transcribed text files to GITHUB_REPO_NAME
UPLOAD_MP3_FILES = True # Set to True to upload MP3 files to GITHUB_REPO_NAME (in addition to the transcripts)
UPDATE_HTML_LINKS = True # Set to True to update HTML links in the PODCAST_HISTORY_FILE to point to GitHub URLs
ENABLE_GITHUB_PAGES = True # Set to True to enable GitHub Pages automatically after processing

# Debugging and Testing
# DEBUG_MODE_LIMIT = 2  # Set this to limit the number of files to download during debugging for example 2. Set to None or remove to disable.

# Instructions for setting up GitHub Token
# 1. Go to https://github.com/settings/tokens and create a new Personal Access Token with just the `repo` scope.
# 2. Copy the generated token.
# 3. Replace the placeholder `your_github_token` in the `GITHUB_TOKEN` variable with the token you generated in this file `config.py`.
# 4. Save the `config.py` file.
