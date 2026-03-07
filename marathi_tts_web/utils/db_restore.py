#!/usr/bin/env python3
import shutil
import os
from datetime import datetime

# Directory where backups are stored
backup_dir = './db_backup/'

# Path to the SQLite3 database file
db_path = 'db.sqlite3'

# Ensure the backup directory exists
if not os.path.exists(backup_dir):
    print(f"Backup directory {backup_dir} does not exist.")
    exit(1)

# Find the latest backup file
backup_files = [os.path.join(backup_dir, f) for f in os.listdir(backup_dir) if os.path.isfile(os.path.join(backup_dir, f))]
if not backup_files:
    print("No backup files found.")
    exit(1)

latest_backup_file = max(backup_files, key=os.path.getctime)

# Print paths for debugging
print(f'Latest backup file path: {latest_backup_file}')
print(f'Database path: {db_path}')

# Copy the latest backup file to the original database location
shutil.copy2(latest_backup_file, db_path)

print(f'Database restored from {latest_backup_file} to {db_path}')