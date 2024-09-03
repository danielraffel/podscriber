#!/bin/bash

# Get values from config.py using the Python helper script
CONFIG_VALUES=$(python3 get_config.py)
IFS=',' read -r REPO_ROOT GITHUB_USERNAME GITHUB_TOKEN GITHUB_REPO_NAME PODCAST_AUDIO_FOLDER TRANSCRIBED_FOLDER PODCAST_HISTORY_FILE <<< "$CONFIG_VALUES"

# Replace ~ with $HOME
REPO_ROOT="${REPO_ROOT/#\~/$HOME}"
PODCAST_AUDIO_FOLDER="${PODCAST_AUDIO_FOLDER/#\~/$HOME}"
TRANSCRIBED_FOLDER="${TRANSCRIBED_FOLDER/#\~/$HOME}"
PODCAST_HISTORY_FILE="${PODCAST_HISTORY_FILE/#\~/$HOME}"

# Debug output: Print the resolved paths
echo "Resolved REPO_ROOT: $REPO_ROOT"
echo "Resolved PODCAST_AUDIO_FOLDER: $PODCAST_AUDIO_FOLDER"
echo "Resolved TRANSCRIBED_FOLDER: $TRANSCRIBED_FOLDER"
echo "Resolved PODCAST_HISTORY_FILE: $PODCAST_HISTORY_FILE"

# Delete specific files and directories
echo "Deleting ${REPO_ROOT}.git"
rm -rf "${REPO_ROOT}.git"

# echo "Deleting ${REPO_ROOT}podcasts.db"
# rm -f "${REPO_ROOT}podcasts.db"

echo "Deleting all files and directories within ${CHROMADB_DB_PATH}"
rm -rf "${CHROMADB_DB_PATH:?}/"*

echo "Deleting $PODCAST_HISTORY_FILE"
rm -f "$PODCAST_HISTORY_FILE"

echo "Deleting all files and directories within ${PODCAST_AUDIO_FOLDER}"
rm -rf "${PODCAST_AUDIO_FOLDER:?}/"*

echo "Deleting all files and directories within ${TRANSCRIBED_FOLDER}"
rm -rf "${TRANSCRIBED_FOLDER:?}/"*

# Delete the GitHub repository if it exists
REPO_URL="https://github.com/$GITHUB_USERNAME/$GITHUB_REPO_NAME"
echo "Checking if repository exists at $REPO_URL"

# Check if the repository exists
REPO_EXISTS=$(curl -s -o /dev/null -w "%{http_code}" -u "$GITHUB_USERNAME:$GITHUB_TOKEN" "$REPO_URL")

if [ "$REPO_EXISTS" -eq 200 ]; then
    echo "Repository $GITHUB_REPO_NAME exists. Deleting..."
    curl -X DELETE -u "$GITHUB_USERNAME:$GITHUB_TOKEN" "https://api.github.com/repos/$GITHUB_USERNAME/$GITHUB_REPO_NAME"
    echo "Repository $GITHUB_REPO_NAME deleted."
else
    echo "Repository $GITHUB_REPO_NAME does not exist."
fi
