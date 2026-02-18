"""Check database schema"""
import sqlite3

conn = sqlite3.connect('data/discover_prospecting_clean.db')
cursor = conn.cursor()

cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [t[0] for t in cursor.fetchall()]

print("\nDatabase Tables and Structures:")
print("="*60)

for table in tables:
    cursor.execute(f"PRAGMA table_info({table})")
    columns = cursor.fetchall()
    cursor.execute(f"SELECT COUNT(*) FROM {table}")
    count = cursor.fetchone()[0]
    
    print(f"\n{table} ({count} records):")
    for col in columns:
        print(f"  - {col[1]} ({col[2]})")

conn.close()
