#!/bin/bash

# Configuration variables
LOCAL_DIR="."  # Path to your local app directory
REMOTE_USER="quadra"            # Your SSH username
REMOTE_HOST="inovato"     # Your server hostname or IP
REMOTE_DIR="/home/quadra/kidsweather" # Destination path on remote server

# Display the commit hash that would be written to commit.txt
echo "Would create commit.txt with commit hash: $(git rev-parse HEAD)"

# Deploy using rsync
# --delete: Remove files on destination that don't exist in source
# --exclude: Skip .git directory and any other files you don't want to transfer
# -avz: Archive mode, verbose output, compress during transfer
# -e ssh: Use SSH for remote connection

rsync -avz --delete --dry-run \
      --exclude='.git' \
      --exclude='.gitignore' \
      --exclude='node_modules' \
      --exclude='.env' \
      --exclude='*.sqlite3' \
      --filter=':- .gitignore' \
      -e "ssh -o RemoteCommand=none" \
      $LOCAL_DIR/ $REMOTE_USER@$REMOTE_HOST:$REMOTE_DIR/

# Set executable permissions for all shell scripts on the remote server
# ssh -o RemoteCommand=none $REMOTE_USER@$REMOTE_HOST "chmod +x $REMOTE_DIR/*.sh"

echo "Dry Run completed successfully!"
