#!/usr/bin/env python3
import sqlite3
import os
#old_app_name = 'tts'
#new_app_name = 'ss_app'
# Path to the SQLite3 database file
db_path = 'db.sqlite3'

# Path to the models.py file
models_path = '{app_new_name}/models.py'  # Update this path

# Old table name and new table name
old_table_name = 'old_app_name_userinput'  # Replace with the current table name
new_table_name = '{app_new_name}_userinput'  # Replace with the new table name

# Connect to the database
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Rename the table
cursor.execute(f"ALTER TABLE {old_table_name} RENAME TO {new_table_name}")

# Commit the changes and close the connection
conn.commit()
conn.close()

print(f"Table renamed from {old_table_name} to {new_table_name}")

# Update the models.py file
with open(models_path, 'r') as file:
    models_content = file.read()

# Replace the old table name with the new table name in the models.py file
models_content = models_content.replace(f"db_table = '{old_table_name}'", f"db_table = '{new_table_name}'")

with open(models_path, 'w') as file:
    file.write(models_content)

print(f"Updated models.py to use the new table name: {new_table_name}")