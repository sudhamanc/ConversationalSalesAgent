"""Add Products of Interest column to accounts table"""

import sqlite3
import random

DB_PATH = "data/discover_prospecting_clean.db"

PRODUCTS = ["Internet", "Voice", "Video", "SDWAN", "Business Mobile"]


def add_products_of_interest_column():
    """Add Products of Interest column and populate for prospects"""
    
    print("\n" + "="*70)
    print("ADDING PRODUCTS OF INTEREST COLUMN")
    print("="*70)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check if column already exists
    cursor.execute("PRAGMA table_info(accounts)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if "Products of Interest" in columns:
        print("\n⚠️  'Products of Interest' column already exists")
        response = input("Drop and recreate? (yes/no): ").strip().lower()
        if response == "yes":
            cursor.execute('ALTER TABLE accounts DROP COLUMN "Products of Interest"')
            print("✅ Dropped existing column")
        else:
            print("Update cancelled.")
            conn.close()
            return
    
    # Add the new column
    print("\n📝 Adding 'Products of Interest' column...")
    cursor.execute('ALTER TABLE accounts ADD COLUMN "Products of Interest" TEXT')
    print("✅ Column added successfully")
    
    # Get all prospects (Existing Customer = N)
    cursor.execute('''
        SELECT "Company Name", "Existing Customer"
        FROM accounts
        WHERE "Existing Customer" = 'N'
    ''')
    
    prospects = cursor.fetchall()
    print(f"\n✅ Found {len(prospects)} prospects to update")
    
    # Populate Products of Interest for prospects
    print("\n📝 Populating Products of Interest...")
    
    updates = []
    
    for company_name, _ in prospects:
        # Randomly select 1-5 products
        num_products = random.randint(1, 5)
        selected_products = random.sample(PRODUCTS, num_products)
        
        # Sort for consistency
        selected_products.sort()
        
        # Create comma-separated string
        products_str = ", ".join(selected_products)
        
        # Update the record
        cursor.execute('''
            UPDATE accounts 
            SET "Products of Interest" = ?
            WHERE "Company Name" = ?
        ''', (products_str, company_name))
        
        updates.append((company_name, products_str))
    
    conn.commit()
    
    print(f"✅ Updated {len(updates)} prospects with product interests")
    
    # Show statistics
    print("\n📊 Product Interest Distribution Statistics:")
    print("-" * 70)
    
    # Count products
    product_counts = {product: 0 for product in PRODUCTS}
    product_combo_counts = {}
    
    for _, products_str in updates:
        products_list = [p.strip() for p in products_str.split(",")]
        
        # Count individual products
        for product in products_list:
            if product in product_counts:
                product_counts[product] += 1
        
        # Count combinations by number
        num_products = len(products_list)
        product_combo_counts[num_products] = product_combo_counts.get(num_products, 0) + 1
    
    print("\nIndividual Product Interest Counts:")
    for product, count in sorted(product_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {product}: {count} prospects")
    
    print("\nProduct Interest Bundle Sizes:")
    for num, count in sorted(product_combo_counts.items()):
        print(f"  {num} product{'s' if num > 1 else ''}: {count} prospects")
    
    # Show sample of updated records
    print("\n📋 Sample of Updated Prospects:")
    print("-" * 70)
    
    cursor.execute('''
        SELECT "Company Name", Industry, "Products of Interest"
        FROM accounts
        WHERE "Existing Customer" = 'N'
        ORDER BY "Company Name"
        LIMIT 15
    ''')
    
    for company, industry, products in cursor.fetchall():
        print(f"\n  {company}")
        print(f"    Industry: {industry}")
        print(f"    Products of Interest: {products}")
    
    # Verify existing customers don't have products of interest
    cursor.execute('''
        SELECT COUNT(*)
        FROM accounts
        WHERE "Existing Customer" = 'Y' 
        AND "Products of Interest" IS NOT NULL
        AND "Products of Interest" != ''
    ''')
    
    customers_with_interest = cursor.fetchone()[0]
    
    if customers_with_interest == 0:
        print("\n✅ Verified: No existing customers have Products of Interest assigned")
    else:
        print(f"\n⚠️  Warning: {customers_with_interest} existing customers have Products of Interest")
    
    # Show summary
    cursor.execute('''
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN "Existing Customer" = 'Y' THEN 1 ELSE 0 END) as customers,
            SUM(CASE WHEN "Existing Customer" = 'N' THEN 1 ELSE 0 END) as prospects,
            SUM(CASE WHEN "Current Products" IS NOT NULL AND "Current Products" != '' THEN 1 ELSE 0 END) as with_current,
            SUM(CASE WHEN "Products of Interest" IS NOT NULL AND "Products of Interest" != '' THEN 1 ELSE 0 END) as with_interest
        FROM accounts
    ''')
    
    total, customers, prospects, with_current, with_interest = cursor.fetchone()
    
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    print(f"Total Accounts: {total}")
    print(f"Existing Customers: {customers} (with Current Products: {with_current})")
    print(f"Prospects: {prospects} (with Products of Interest: {with_interest})")
    print("="*70)
    
    conn.close()
    
    print("\n✅ UPDATE COMPLETED SUCCESSFULLY!\n")


if __name__ == "__main__":
    print("\n⚠️  This will add 'Products of Interest' column to accounts table")
    print("    and populate it for prospects (Existing Customer = N)")
    response = input("Proceed? (yes/no): ").strip().lower()
    
    if response == "yes":
        add_products_of_interest_column()
    else:
        print("Update cancelled.")
