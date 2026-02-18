import sqlite3
import pandas as pd

# Connect to database
conn = sqlite3.connect('data/discover_prospecting_clean.db')
cursor = conn.cursor()

# Get all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()
print("Tables in database:")
for table in tables:
    print(f"  - {table[0]}")

print("\n" + "="*80 + "\n")

# For each table, show structure and sample data
for table in tables:
    table_name = table[0]
    print(f"Table: {table_name}")
    print("-" * 80)
    
    # Get schema
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    print("Columns:")
    for col in columns:
        print(f"  {col[1]} ({col[2]})")
    
    # Get sample data
    print("\nSample data (first 3 rows):")
    df = pd.read_sql_query(f"SELECT * FROM {table_name} LIMIT 3", conn)
    print(df.to_string())
    
    # Get row count
    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    count = cursor.fetchone()[0]
    print(f"\nTotal rows: {count}")
    print("\n" + "="*80 + "\n")

conn.close()
