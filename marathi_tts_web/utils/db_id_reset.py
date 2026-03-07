#!/usr/bin/env python3
import sqlite3
import re
import os

# Path to the SQLite3 database file
db_path = 'db.sqlite3'

# Connect to the database
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Table to reset IDs for
table = 'tts_userinput'

# Validate table name (alphanumeric + underscore only)
if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', table):
    raise ValueError(f"Invalid table name: {table}")

# Verify table exists in the database
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
if not cursor.fetchone():
    raise ValueError(f"Table does not exist: {table}")

# Get the table schema
cursor.execute(f"PRAGMA table_info({table})")
schema = cursor.fetchall()

# Create a new table with the same structure but without the auto-increment on the id column
new_table = f"{table}_new"
columns = ", ".join([f"{col[1]} {col[2]}" for col in schema if col[1] != 'id'])
cursor.execute(f"CREATE TABLE {new_table} (id INTEGER PRIMARY KEY, {columns})")

# Copy data from the old table to the new table with new IDs
cursor.execute(f"""
    INSERT INTO {new_table} (id, {', '.join([col[1] for col in schema if col[1] != 'id'])})
    SELECT row_number() OVER () AS id, {', '.join([col[1] for col in schema if col[1] != 'id'])}
    FROM {table}
""")

# Drop the old table
cursor.execute(f"DROP TABLE {table}")

# Rename the new table to the original table name
cursor.execute(f"ALTER TABLE {new_table} RENAME TO {table}")

# Reset the auto-increment sequence
cursor.execute(f"UPDATE sqlite_sequence SET seq = (SELECT MAX(id) FROM {table}) WHERE name = '{table}'")

# Commit the changes and close the connection
conn.commit()
conn.close()

print(f"Primary key IDs have been reset for table: {table}")