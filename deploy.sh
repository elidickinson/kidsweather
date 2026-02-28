#!/bin/bash

# Configuration variables
LOCAL_DIR="."  # Path to your local app directory
REMOTE_USER="quadra"            # Your SSH username
REMOTE_HOST="inovatoraw"     # Your server hostname or IP
REMOTE_DIR="/home/quadra/kidsweather" # Destination path on remote server

# Create commit.txt file with current commit hash
git rev-parse HEAD > commit.txt
echo "Created commit.txt with commit hash: $(cat commit.txt)"

# Deploy using rsync
# --delete: Remove files on destination that don't exist in source
# --exclude: Skip .git directory and any other files you don't want to transfer
# -avz: Archive mode, verbose output, compress during transfer
# -e ssh: Use SSH for remote connection

rsync -avz --delete \
      --include='commit.txt' \
      --exclude='.git' \
      --exclude='.gitignore' \
      --exclude='node_modules' \
      --exclude='.env' \
      --exclude='__pycache__' \
      --exclude='api_cache' \
      --exclude='.venv' \
      --exclude='*.sqlite3' \
      --filter=':- .gitignore' \
      -e "ssh -o RemoteCommand=none" \
      $LOCAL_DIR/ $REMOTE_USER@$REMOTE_HOST:$REMOTE_DIR/

# Set executable permissions for all shell scripts on the remote server
ssh -o RemoteCommand=none $REMOTE_USER@$REMOTE_HOST "chmod +x $REMOTE_DIR/*.sh"

echo "Deployment completed successfully!"
