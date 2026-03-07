#!/usr/bin/env python3
import shutil
import os
from datetime import datetime

# Path to the SQLite3 database file
db_path = 'db.sqlite3'

# Directory where backups will be stored
backup_dir = './db_backup/'

# Ensure the backup directory exists
os.makedirs(backup_dir, exist_ok=True)

# Generate a backup file name with a timestamp
backup_file = os.path.join(backup_dir, f'db.sqlite3_{datetime.now().strftime("%Y%m%d%H%M%S")}')

# Copy the database file to the backup location
shutil.copy2(db_path, backup_file)

print(f'Backup created: {backup_file}')