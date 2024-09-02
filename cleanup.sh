#!/bin/bash

# Get values from config.py using the Python helper script
CONFIG_VALUES=$(python3 get_config.py)
IFS=',' read -r REPO_ROOT GITHUB_USERNAME GITHUB_TOKEN GITHUB_REPO_NAME TRANSCRIBED_FOLDER PODCAST_HISTORY_FILE <<< "$CONFIG_VALUES"

# Delete specific files and directories
rm -rf "${REPO_ROOT}.git"
rm -f "${REPO_ROOT}podcasts.db"
rm -f "$PODCAST_HISTORY_FILE"
rm -rf "${PODCAST_AUDIO_FOLDER}/*"
rm -rf "${TRANSCRIBED_FOLDER}/*"

# Delete the GitHub repository if it exists
REPO_URL="https://github.com/$GITHUB_USERNAME/$GITHUB_REPO_NAME"

# Check if the repository exists
REPO_EXISTS=$(curl -s -o /dev/null -w "%{http_code}" -u "$GITHUB_USERNAME:$GITHUB_TOKEN" "$REPO_URL")

if [ "$REPO_EXISTS" -eq 200 ]; then
    echo "Repository $GITHUB_REPO_NAME exists. Deleting..."
    curl -X DELETE -u "$GITHUB_USERNAME:$GITHUB_TOKEN" "https://api.github.com/repos/$GITHUB_USERNAME/$GITHUB_REPO_NAME"
    echo "Repository $GITHUB_REPO_NAME deleted."
else
    echo "Repository $GITHUB_REPO_NAME does not exist."
fi
