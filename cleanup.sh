#!/bin/bash

# Function to display help message
show_help() {
    echo "Usage: $(basename "$0") [options]"
    echo
    echo "Options:"
    echo "  --no-delete-chromadb    Skip deleting the Chromadb directory"
    echo "  --no-delete-git         Skip deleting the .git directory"
    echo "  --no-delete-history     Skip deleting the podcast history file"
    echo "  --no-delete-audio       Skip deleting files in the podcast audio folder"
    echo "  --no-delete-transcribed Skip deleting files in the transcribed folder"
    echo "  --no-delete-repo        Skip deleting the GitHub repository"
    echo "  -h, --help              Show this help message"
    echo
    exit 0
}

# Default flags (all operations enabled)
DELETE_GIT=true
DELETE_CHROMADB=true
DELETE_HISTORY=true
DELETE_AUDIO=true
DELETE_TRANSCRIBED=true
DELETE_REPO=true

# Parse command-line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --no-delete-chromadb)
            DELETE_CHROMADB=false
            ;;
        --no-delete-git)
            DELETE_GIT=false
            ;;
        --no-delete-history)
            DELETE_HISTORY=false
            ;;
        --no-delete-audio)
            DELETE_AUDIO=false
            ;;
        --no-delete-transcribed)
            DELETE_TRANSCRIBED=false
            ;;
        --no-delete-repo)
            DELETE_REPO=false
            ;;
        -h|--help)
            show_help
            ;;
        *)
            echo "Unknown option: $1"
            show_help
            ;;
    esac
    shift
done

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

# Delete specific files and directories based on flags
if [ "$DELETE_GIT" = true ]; then
    echo "Deleting ${REPO_ROOT}.git"
    rm -rf "${REPO_ROOT}.git"
fi

if [ "$DELETE_CHROMADB" = true ]; then
    echo "Deleting all files and directories within ${CHROMADB_DB_PATH}"
    rm -rf "${CHROMADB_DB_PATH:?}/"*
fi

if [ "$DELETE_HISTORY" = true ]; then
    echo "Deleting $PODCAST_HISTORY_FILE"
    rm -f "$PODCAST_HISTORY_FILE"
fi

if [ "$DELETE_AUDIO" = true ]; then
    echo "Deleting all files and directories within ${PODCAST_AUDIO_FOLDER}"
    rm -rf "${PODCAST_AUDIO_FOLDER:?}/"*
fi

if [ "$DELETE_TRANSCRIBED" = true ]; then
    echo "Deleting all files and directories within ${TRANSCRIBED_FOLDER}"
    rm -rf "${TRANSCRIBED_FOLDER:?}/"*
fi

if [ "$DELETE_REPO" = true ]; then
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
fi
