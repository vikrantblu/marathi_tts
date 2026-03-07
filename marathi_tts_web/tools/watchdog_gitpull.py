#!/usr/bin/env python3
import time
import logging
import subprocess
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from threading import Lock

class GitPullEventHandler(FileSystemEventHandler):
    def __init__(self, directory):
        self.directory = directory
        self.lock = Lock()

    def on_any_event(self, event):
        logging.info(f"Detected change: {event.src_path}")
        self.run_git_pull()

    def run_git_pull(self):
        with self.lock:
            try:
                result = subprocess.run(["git", "fetch"], cwd=self.directory, check=True, capture_output=True, text=True)
                if "up to date" not in result.stdout:
                    subprocess.run(["git", "pull"], cwd=self.directory, check=True)
                    logging.info("Git pull executed successfully")
                else:
                    logging.info("No changes detected")
            except subprocess.CalledProcessError as e:
                logging.error(f"An error occurred while running git pull: {e}")

def main(directory):
    logging.basicConfig(level=logging.INFO)
    event_handler = GitPullEventHandler(directory)
    observer = Observer()
    observer.schedule(event_handler, directory, recursive=True)
    observer.start()
    logging.info(f"Started monitoring {directory} for changes")

    try:
        while True:
            event_handler.run_git_pull()
            time.sleep(5)  # Sleep for 5 seconds between each git pull attempt
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == "__main__":
    directory_to_watch = "/mnt/d/vedic_research/"
    main(directory_to_watch)
    