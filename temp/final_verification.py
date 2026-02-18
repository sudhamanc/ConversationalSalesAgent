"""Final verification - check all company names are realistic"""

import sqlite3

DB_PATH = "data/discover_prospecting_clean.db"

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

print("\n" + "="*80)
print("FINAL VERIFICATION - ALL COMPANY NAMES")
print("="*80)

# Check for any remaining generic names
cursor.execute('''
    SELECT COUNT(*) 
    FROM accounts 
    WHERE "Company Name" LIKE 'Company %'
''')

generic_count = cursor.fetchone()[0]

if generic_count == 0:
    print("\n✅ SUCCESS: No generic 'Company XXX' names found!")
else:
    print(f"\n⚠️  WARNING: {generic_count} generic names still exist!")

# Get total unique company names
cursor.execute('SELECT COUNT(DISTINCT "Company Name") FROM accounts')
unique_names = cursor.fetchone()[0]

cursor.execute('SELECT COUNT(*) FROM accounts')
total_records = cursor.fetchone()[0]

print(f"✅ Total records: {total_records}")
print(f"✅ Unique company names: {unique_names}")

if unique_names == total_records:
    print("✅ All company names are unique!")

# Show first 15 companies
print("\n📊 First 15 Companies (Alphabetically):")
print("-" * 80)

cursor.execute('''
    SELECT "Company Name", Industry, Website, "Existing Customer"
    FROM accounts 
    ORDER BY "Company Name" 
    LIMIT 15
''')

for i, (name, industry, website, customer) in enumerate(cursor.fetchall(), 1):
    status = "Customer" if customer == "Y" else "Prospect"
    print(f"{i:2}. {name}")
    print(f"    {industry} | {website} | {status}")

print("\n" + "="*80)

conn.close()
