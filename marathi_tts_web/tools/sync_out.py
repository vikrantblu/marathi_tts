#!/usr/bin/env python3
import logging
import os
import subprocess
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import sys

logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')

EXCLUDE_PATTERNS = [
    '.git', 
    '.git/*', 
    '.gitignore', 
    '__pycache__', 
    '__pycache__/*', 
    '*Zone.Identifier',
    'staticfiles/',
    'staticfiles/*',
    'db.sqlite3',
    '.venv',
    'media/*',
    'logs/*',
    'media/',
    'logs/',
]
def sync_directories(dir_a, dir_b, exclude_patterns):
    if not os.path.exists(dir_a):
        logging.error(f"Source directory {dir_a} does not exist.")
        return
    if not os.path.exists(dir_b):
        logging.error(f"Destination directory {dir_b} does not exist.")
        return

    exclude_args = []
    for pattern in exclude_patterns:
        exclude_args.extend(['--exclude', pattern])
    
    rsync_command = [
        'rsync',
        '-avz',  # archive mode, verbose, compress file data during the transfer
        '--delete',  # delete extraneous files from destination dirs
    ] + exclude_args + [dir_a, dir_b]
    
    logging.info(f"Running command: {' '.join(rsync_command)}")
    try:
        subprocess.run(rsync_command, check=True)
        logging.info(f"Synchronization from {dir_a} to {dir_b} completed successfully")
        delete_zone_identifier_files(dir_b)
    except subprocess.CalledProcessError as e:
        logging.error(f"An error occurred while synchronizing: {e}")

def delete_zone_identifier_files(directory):
    logging.info(f"Checking for Zone.Identifier files in {directory}")
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('Zone.Identifier'):
                file_path = os.path.join(root, file)
                try:
                    os.remove(file_path)
                    logging.info(f"Deleted {file_path}")
                except Exception as e:
                    logging.error(f"Failed to delete {file_path}: {e}")

class SyncEventHandler(FileSystemEventHandler):
    def __init__(self, dir_a, dir_b, exclude_patterns):
        self.dir_a = dir_a
        self.dir_b = dir_b
        self.exclude_patterns = exclude_patterns

    def on_any_event(self, event):
        if any(pattern in event.src_path for pattern in EXCLUDE_PATTERNS):
            return
        logging.info(f"Detected change: {event.src_path}")
        sync_directories(self.dir_a, self.dir_b, self.exclude_patterns)

def run_git_commands(directory):
    try:
        subprocess.run(["git", "add", "."], cwd=directory, check=True)
        subprocess.run(["git", "commit", "-m", "updated the code"], cwd=directory, check=True)
        subprocess.run(["git", "push"], cwd=directory, check=True)
        logging.info("Git commands executed successfully")
        sys.exit(0)  # Exit the program after successful git commands
    except subprocess.CalledProcessError as e:
        logging.error(f"An error occurred while running git commands: {e}")

def main(dir_a, dir_b, exclude_patterns):
    logging.info("Starting synchronization service")
    
    # Perform initial synchronization
    logging.info("Performing initial synchronization")
    sync_directories(dir_a, dir_b, exclude_patterns)
    
    logging.info("Synchronization completed")

    # Run git commands in dir_b
    run_git_commands(dir_b)

    # Set up watchdog observers
    event_handler = SyncEventHandler(dir_a, dir_b, exclude_patterns)
    observer_a = Observer()
    observer_b = Observer()
    observer_a.schedule(event_handler, dir_a, recursive=True)
    observer_b.schedule(event_handler, dir_b, recursive=True)
    
    observer_a.start()
    observer_b.start()

    try:
        while True:
            pass
    except KeyboardInterrupt:
        observer_a.stop()
        observer_b.stop()
    
    observer_a.join()
    observer_b.join()

if __name__ == "__main__":
    dir_a = "/mnt/c/mytools/github/marathi_tts/"
    dir_b = "/home/vicky/marathi_tts/"

    exclude_patterns = EXCLUDE_PATTERNS
    main(dir_a, dir_b, exclude_patterns)