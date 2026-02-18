"""Simple direct database test"""
import sqlite3

conn = sqlite3.connect('data/discover_prospecting_clean.db')
cursor = conn.cursor()

print("\n📊 DIRECT DATABASE TEST")
print("="*70)

cursor.execute('SELECT COUNT(*) FROM accounts')
count = cursor.fetchone()[0]
print(f"\n✅ Total Companies: {count}")

cursor.execute('SELECT "Company Name", Industry, Street, City, State, "Existing Customer" FROM accounts LIMIT 5')
print("\n✅ Sample Companies:")
for row in cursor.fetchall():
    print(f"\n  {row[0]}")
    print(f"    Industry: {row[1]}")
    print(f"    Address: {row[2]}, {row[3]}, {row[4]}")
    print(f"    Existing Customer: {row[5]}")

cursor.execute('SELECT COUNT(*) FROM accounts WHERE "Existing Customer" = "Y"')
existing = cursor.fetchone()[0]
print(f"\n✅ Existing Customers: {existing} of {count}")

conn.close()
print("\n" + "="*70)
