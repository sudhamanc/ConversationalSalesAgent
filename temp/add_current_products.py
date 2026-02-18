"""Add Current Products column to accounts table"""

import sqlite3
import random

DB_PATH = "data/discover_prospecting_clean.db"

PRODUCTS = ["Internet", "Voice", "Video", "SDWAN", "Business Mobile"]


def add_current_products_column():
    """Add Current Products column and populate for existing customers"""
    
    print("\n" + "="*70)
    print("ADDING CURRENT PRODUCTS COLUMN")
    print("="*70)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check if column already exists
    cursor.execute("PRAGMA table_info(accounts)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if "Current Products" in columns:
        print("\n⚠️  'Current Products' column already exists")
        response = input("Drop and recreate? (yes/no): ").strip().lower()
        if response == "yes":
            cursor.execute('ALTER TABLE accounts DROP COLUMN "Current Products"')
            print("✅ Dropped existing column")
        else:
            print("Update cancelled.")
            conn.close()
            return
    
    # Add the new column
    print("\n📝 Adding 'Current Products' column...")
    cursor.execute('ALTER TABLE accounts ADD COLUMN "Current Products" TEXT')
    print("✅ Column added successfully")
    
    # Get all existing customers
    cursor.execute('''
        SELECT "Company Name", "Existing Customer"
        FROM accounts
        WHERE "Existing Customer" = 'Y'
    ''')
    
    existing_customers = cursor.fetchall()
    print(f"\n✅ Found {len(existing_customers)} existing customers to update")
    
    # Populate Current Products for existing customers
    print("\n📝 Populating Current Products...")
    
    updates = []
    
    for company_name, _ in existing_customers:
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
            SET "Current Products" = ?
            WHERE "Company Name" = ?
        ''', (products_str, company_name))
        
        updates.append((company_name, products_str))
    
    conn.commit()
    
    print(f"✅ Updated {len(updates)} existing customers with product combinations")
    
    # Show statistics
    print("\n📊 Product Distribution Statistics:")
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
    
    print("\nIndividual Product Counts:")
    for product, count in sorted(product_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {product}: {count} customers")
    
    print("\nProduct Bundle Sizes:")
    for num, count in sorted(product_combo_counts.items()):
        print(f"  {num} product{'s' if num > 1 else ''}: {count} customers")
    
    # Show sample of updated records
    print("\n📋 Sample of Updated Records:")
    print("-" * 70)
    
    cursor.execute('''
        SELECT "Company Name", Industry, "Current Products"
        FROM accounts
        WHERE "Existing Customer" = 'Y'
        ORDER BY "Company Name"
        LIMIT 15
    ''')
    
    for company, industry, products in cursor.fetchall():
        print(f"\n  {company}")
        print(f"    Industry: {industry}")
        print(f"    Products: {products}")
    
    # Verify prospects don't have products
    cursor.execute('''
        SELECT COUNT(*)
        FROM accounts
        WHERE "Existing Customer" = 'N' 
        AND "Current Products" IS NOT NULL
        AND "Current Products" != ''
    ''')
    
    prospect_with_products = cursor.fetchone()[0]
    
    if prospect_with_products == 0:
        print("\n✅ Verified: No prospects have Current Products assigned")
    else:
        print(f"\n⚠️  Warning: {prospect_with_products} prospects have products assigned")
    
    # Show summary
    cursor.execute('''
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN "Existing Customer" = 'Y' THEN 1 ELSE 0 END) as customers,
            SUM(CASE WHEN "Current Products" IS NOT NULL AND "Current Products" != '' THEN 1 ELSE 0 END) as with_products
        FROM accounts
    ''')
    
    total, customers, with_products = cursor.fetchone()
    
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    print(f"Total Accounts: {total}")
    print(f"Existing Customers: {customers}")
    print(f"Accounts with Current Products: {with_products}")
    print("="*70)
    
    conn.close()
    
    print("\n✅ UPDATE COMPLETED SUCCESSFULLY!\n")


if __name__ == "__main__":
    print("\n⚠️  This will add 'Current Products' column to accounts table")
    print("    and populate it for existing customers (Y)")
    response = input("Proceed? (yes/no): ").strip().lower()
    
    if response == "yes":
        add_current_products_column()
    else:
        print("Update cancelled.")
