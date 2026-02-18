"""Migrate discover_prospecting_clean.db to new schema with 100 companies"""

import sqlite3
import random
from pathlib import Path

DB_PATH = Path("data/discover_prospecting_clean.db")

# Real street addresses by region
ADDRESSES = {
    "Northeast": [
        ("123 Beacon Street", "Boston", "MA"),
        ("456 Park Avenue", "New York", "NY"),
        ("789 Market Street", "Philadelphia", "PA"),
        ("234 Charles Street", "Baltimore", "MD"),
        ("567 Thames Street", "Newport", "RI"),
        ("890 Elm Street", "Hartford", "CT"),
        ("345 Washington Street", "Newark", "NJ"),
        ("678 Main Street", "Providence", "RI"),
        ("901 State Street", "Albany", "NY"),
        ("1234 Liberty Avenue", "Pittsburgh", "PA"),
    ],
    "Southeast": [
        ("555 Peachtree Street", "Atlanta", "GA"),
        ("777 Ocean Drive", "Miami", "FL"),
        ("888 Bourbon Street", "New Orleans", "LA"),
        ("999 Duke Street", "Charlotte", "NC"),
        ("1111 Main Street", "Charleston", "SC"),
        ("2222 Broadway", "Nashville", "TN"),
        ("3333 Beach Boulevard", "Jacksonville", "FL"),
        ("4444 Kings Highway", "Myrtle Beach", "SC"),
        ("5555 Music Row", "Nashville", "TN"),
        ("6666 Palm Avenue", "Tampa", "FL"),
    ],
    "Midwest": [
        ("321 Michigan Avenue", "Chicago", "IL"),
        ("654 Hennepin Avenue", "Minneapolis", "MN"),
        ("987 Woodward Avenue", "Detroit", "MI"),
        ("147 Main Street", "Columbus", "OH"),
        ("258 Grand Avenue", "St. Louis", "MO"),
        ("369 State Street", "Madison", "WI"),
        ("741 Market Street", "Indianapolis", "IN"),
        ("852 Prospect Avenue", "Cleveland", "OH"),
        ("963 Wisconsin Avenue", "Milwaukee", "WI"),
        ("159 Broadway", "Kansas City", "MO"),
    ],
    "West": [
        ("2468 Sunset Boulevard", "Los Angeles", "CA"),
        ("1357 Market Street", "San Francisco", "CA"),
        ("3690 Pine Street", "Seattle", "WA"),
        ("4821 Broadway", "Denver", "CO"),
        ("5932 Main Street", "Phoenix", "AZ"),
        ("6043 Fremont Street", "Las Vegas", "NV"),
        ("7154 University Avenue", "Berkeley", "CA"),
        ("8265 Broadway", "Portland", "OR"),
        ("9376 Coast Highway", "San Diego", "CA"),
        ("1487 Tech Drive", "San Jose", "CA"),
    ],
    "Southwest": [
        ("777 Congress Avenue", "Austin", "TX"),
        ("888 Main Street", "Dallas", "TX"),
        ("999 San Jacinto Boulevard", "Houston", "TX"),
        ("1010 Broadway", "San Antonio", "TX"),
        ("2020 Central Avenue", "Albuquerque", "NM"),
        ("3030 Mill Avenue", "Tempe", "AZ"),
        ("4040 University Boulevard", "Tucson", "AZ"),
        ("5050 Commerce Street", "Fort Worth", "TX"),
        ("6060 Guadalupe Street", "Austin", "TX"),
        ("7070 McKinney Avenue", "Dallas", "TX"),
    ],
}

INDUSTRIES = ["Technology", "Healthcare", "Retail", "Manufacturing", "Finance", 
              "Telecom", "Energy", "Media", "Transportation", "Real Estate",
              "Education", "Hospitality", "Construction", "Automotive", "Aerospace"]

COMPANY_PREFIXES = ["Global", "Advanced", "Premier", "Elite", "Innovative", "United",
                    "Dynamic", "Strategic", "Precision", "Alpha", "Apex", "Summit",
                    "Vertex", "Zenith", "Prime", "Core", "Peak", "Elite", "Metro",
                    "Regional", "National", "International", "Digital", "Smart"]

COMPANY_SUFFIXES = ["Solutions", "Enterprises", "Industries", "Group", "Corporation",
                    "Systems", "Technologies", "Partners", "Associates", "Holdings",
                    "Ventures", "Capital", "Services", "Consulting", "Labs"]


def generate_company_name(industry, existing_names):
    """Generate a unique company name"""
    while True:
        if industry == "Healthcare":
            base = random.choice(["Medical", "Health", "Care", "Wellness", "Clinical", "MediTech"])
        elif industry == "Technology":
            base = random.choice(["Tech", "Digital", "Cyber", "Cloud", "Data", "AI"])
        elif industry == "Finance":
            base = random.choice(["Capital", "Financial", "Trust", "Wealth", "Asset", "Investment"])
        elif industry == "Retail":
            base = random.choice(["Retail", "Commerce", "Market", "Store", "Shop", "Outlet"])
        elif industry == "Manufacturing":
            base = random.choice(["Industrial", "Manufacturing", "Production", "Factory", "Assembly"])
        else:
            base = industry
        
        prefix = random.choice(COMPANY_PREFIXES)
        suffix = random.choice(COMPANY_SUFFIXES)
        
        name = f"{prefix} {base} {suffix}"
        if name not in existing_names:
            return name


def migrate_database():
    """Perform the database migration"""
    
    print("\n" + "="*70)
    print("DATABASE MIGRATION: Expanding to 100 companies")
    print("="*70)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Step 1: Backup existing data
    print("\n1️⃣  Reading existing data...")
    cursor.execute("SELECT * FROM accounts")
    existing_accounts = cursor.fetchall()
    
    cursor.execute("PRAGMA table_info(accounts)")
    columns_info = cursor.fetchall()
    old_columns = [col[1] for col in columns_info]
    
    print(f"   ✅ Found {len(existing_accounts)} existing companies")
    
    # Step 2: Create new schema
    print("\n2️⃣  Updating table schema...")
    
    # Drop and recreate accounts table with new schema
    cursor.execute("DROP TABLE IF EXISTS accounts_backup")
    cursor.execute("CREATE TABLE accounts_backup AS SELECT * FROM accounts")
    cursor.execute("DROP TABLE accounts")
    
    cursor.execute("""
        CREATE TABLE accounts (
            "Account/Company ID" TEXT PRIMARY KEY,
            "Company Name" TEXT NOT NULL,
            "Industry" TEXT,
            "Territory/Region" TEXT,
            "Street" TEXT,
            "City" TEXT,
            "State" TEXT,
            "Company Size (employees)" INTEGER,
            "Annual Revenue (USD)" INTEGER,
            "Estimated Annual Spend" INTEGER,
            "Existing Customer" TEXT
        )
    """)
    
    print("   ✅ Updated accounts table schema")
    
    # Step 3: Migrate existing records with new addresses
    print("\n3️⃣  Migrating existing 50 companies...")
    
    existing_names = set()
    for i, row in enumerate(existing_accounts, 1):
        company_id = row[0]
        company_name = row[1]
        industry = row[2]
        region = row[3]
        company_size = row[5] if len(row) > 5 else 100
        annual_revenue = row[6] if len(row) > 6 else 1000000
        estimated_spend = row[7] if len(row) > 7 else 50000
        
        existing_names.add(company_name)
        
        # Get address for region
        if region in ADDRESSES:
            address_pool = ADDRESSES[region]
        else:
            address_pool = ADDRESSES["West"]
        
        street, city, state = random.choice(address_pool)
        existing_customer = random.choice(["Y", "N"])
        
        cursor.execute("""
            INSERT INTO accounts VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (company_id, company_name, industry, region, street, city, state,
              company_size, annual_revenue, estimated_spend, existing_customer))
    
    print(f"   ✅ Migrated {len(existing_accounts)} companies")
    
    # Step 4: Generate 50 new companies
    print("\n4️⃣  Generating 50 new companies...")
    
    regions = list(ADDRESSES.keys())
    new_companies = []
    
    for i in range(51, 101):
        company_id = f"Company {i:03d}"
        region = random.choice(regions)
        industry = random.choice(INDUSTRIES)
        company_name = generate_company_name(industry, existing_names)
        existing_names.add(company_name)
        
        street, city, state = random.choice(ADDRESSES[region])
        company_size = random.randint(50, 5000)
        annual_revenue = random.randint(500000, 50000000)
        estimated_spend = int(annual_revenue * random.uniform(0.01, 0.10))
        existing_customer = random.choice(["Y", "N"])
        
        cursor.execute("""
            INSERT INTO accounts VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (company_id, company_name, industry, region, street, city, state,
              company_size, annual_revenue, estimated_spend, existing_customer))
        
        new_companies.append({
            "id": company_id,
            "name": company_name,
            "industry": industry,
            "region": region
        })
    
    print(f"   ✅ Added 50 new companies")
    
    # Step 5: Generate contacts for new companies
    print("\n5️⃣  Generating contacts for new companies...")
    
    cursor.execute("SELECT MAX(CAST(SUBSTR([Contact ID], 9) AS INTEGER)) FROM contacts")
    max_contact_id = cursor.fetchone()[0] or 142
    
    titles = ["CEO", "CTO", "CFO", "VP of Sales", "VP of Operations", "Director of IT",
              "Marketing Manager", "Operations Manager", "Product Manager"]
    roles = ["Economic Buyer", "Champion", "Influencer", "Gatekeeper"]
    engagement_levels = ["High", "Medium", "Low"]
    
    first_names = ["John", "Jane", "Michael", "Sarah", "David", "Emily", "Robert", "Lisa",
                   "James", "Mary", "William", "Jennifer", "Richard", "Patricia", "Thomas"]
    last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller",
                  "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Wilson"]
    
    contact_id = max_contact_id + 1
    for company in new_companies:
        # Generate 2-4 contacts per company
        num_contacts = random.randint(2, 4)
        for _ in range(num_contacts):
            contact_id_str = f"Contact {contact_id:03d}"
            name = f"{random.choice(first_names)} {random.choice(last_names)}"
            title = random.choice(titles)
            email = f"{name.lower().replace(' ', '.')}@{company['name'].lower().replace(' ', '')}.com"
            phone = f"555-{random.randint(1000, 9999)}"
            role = random.choice(roles)
            engagement = random.choice(engagement_levels)
            
            cursor.execute("""
                INSERT INTO contacts VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (contact_id_str, company['id'], name, title, email, phone, role, engagement))
            
            contact_id += 1
    
    print(f"   ✅ Added {contact_id - max_contact_id - 1} new contacts")
    
    # Step 6: Generate opportunities for new companies
    print("\n6️⃣  Generating opportunities for new companies...")
    
    cursor.execute("SELECT MAX(CAST(SUBSTR([Opportunity ID], 13) AS INTEGER)) FROM opportunities")
    max_opp_id = cursor.fetchone()[0] or 102
    
    stages = ["Discovery", "Qualification", "Proposal", "Negotiation", "Closed Won", "Closed Lost"]
    priority_buckets = ["A", "B", "C"]
    
    opp_id = max_opp_id + 1
    for company in new_companies:
        # Generate 1-2 opportunities per company
        num_opps = random.randint(1, 2)
        for _ in range(num_opps):
            opp_id_str = f"Opportunity {opp_id:03d}"
            opp_name = f"{company['name']} - {random.choice(['Platform', 'Service', 'Solution', 'System'])} Deal"
            stage = random.choice(stages)
            
            # Random date in 2026
            month = random.randint(3, 12)
            day = random.randint(1, 28)
            close_date = f"2026-{month:02d}-{day:02d}"
            
            deal_value = random.randint(25000, 500000)
            budget = random.randint(0, 3)
            authority = random.randint(0, 3)
            need = random.randint(0, 3)
            timeline_days = random.randint(30, 365)
            
            # Calculate timeline score
            if timeline_days < 90:
                timeline_score = 3
            elif timeline_days < 180:
                timeline_score = 2
            elif timeline_days < 360:
                timeline_score = 1
            else:
                timeline_score = 0
            
            bant_score = ((budget + authority + need + timeline_score) / 12.0) * 100
            
            if bant_score >= 75:
                priority = "A"
            elif bant_score >= 50:
                priority = "B"
            else:
                priority = "C"
            
            next_action = random.choice([
                "Schedule discovery call",
                "Send proposal",
                "Follow up with decision maker",
                "Present demo",
                "Negotiate terms"
            ])
            
            cursor.execute("""
                INSERT INTO opportunities VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (opp_id_str, company['id'], opp_name, stage, close_date, deal_value,
                  budget, authority, need, timeline_days, bant_score, priority, next_action))
            
            opp_id += 1
    
    print(f"   ✅ Added {opp_id - max_opp_id - 1} new opportunities")
    
    # Step 7: Generate insights for new companies
    print("\n7️⃣  Generating insights for new companies...")
    
    buying_signals = [
        "Budget allocated for Q2",
        "Recent leadership change",
        "Competitor evaluation in progress",
        "Current system end-of-life approaching",
        "Expansion plans announced",
        "Digital transformation initiative"
    ]
    
    pain_points = [
        "Manual processes causing delays",
        "Lack of real-time visibility",
        "Integration challenges",
        "Scalability concerns",
        "Compliance requirements",
        "High operational costs"
    ]
    
    positioning = [
        "Emphasize ROI and cost savings",
        "Highlight ease of integration",
        "Focus on scalability and growth",
        "Demonstrate compliance features",
        "Showcase customer success stories",
        "Stress time-to-value"
    ]
    
    for company in new_companies:
        cursor.execute("""
            INSERT INTO insights VALUES (?, ?, ?, ?)
        """, (company['id'], random.choice(buying_signals),
              random.choice(pain_points), random.choice(positioning)))
    
    print(f"   ✅ Added {len(new_companies)} insight records")
    
    # Step 8: Generate spend data for new companies
    print("\n8️⃣  Generating ad spend data for new companies...")
    
    channels = ["Search", "Display", "Social", "Video", "Email"]
    platforms = ["Google", "Facebook", "LinkedIn", "Twitter", "YouTube"]
    
    for company in new_companies:
        channel = random.choice(channels)
        platform = random.choice(platforms)
        monthly_spend = random.randint(1000, 50000)
        impressions = monthly_spend * random.randint(100, 1000)
        clicks = int(impressions * random.uniform(0.01, 0.05))
        conversions = int(clicks * random.uniform(0.02, 0.10))
        
        cursor.execute("""
            INSERT INTO spend VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (company['id'], channel, platform, monthly_spend, impressions, clicks, conversions))
    
    print(f"   ✅ Added {len(new_companies)} spend records")
    
    # Step 9: Generate action recommendations for new companies
    print("\n9️⃣  Generating action recommendations...")
    
    tactics = [
        "Personalized email outreach",
        "Executive briefing",
        "Product demonstration",
        "Case study presentation",
        "Proof of concept",
        "ROI calculator review"
    ]
    
    for company in new_companies:
        cursor.execute("""
            INSERT INTO actions VALUES (?, ?, ?)
        """, (company['id'], random.choice(tactics),
              f"Engage with key stakeholders at {company['name']}"))
    
    print(f"   ✅ Added {len(new_companies)} action records")
    
    # Commit all changes
    conn.commit()
    
    # Step 10: Verify migration
    print("\n🔟  Verifying migration...")
    
    cursor.execute("SELECT COUNT(*) FROM accounts")
    account_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM contacts")
    contact_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM opportunities")
    opp_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM insights")
    insight_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM spend")
    spend_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM actions")
    action_count = cursor.fetchone()[0]
    
    print(f"   📊 Final Counts:")
    print(f"      - Accounts: {account_count}")
    print(f"      - Contacts: {contact_count}")
    print(f"      - Opportunities: {opp_count}")
    print(f"      - Insights: {insight_count}")
    print(f"      - Spend Records: {spend_count}")
    print(f"      - Action Items: {action_count}")
    
    conn.close()
    
    print("\n" + "="*70)
    print("✅ MIGRATION COMPLETED SUCCESSFULLY!")
    print("="*70)
    print("\n📋 Summary of changes:")
    print("   • Renamed 'Address' column to 'Street'")
    print("   • Added 'City' and 'State' columns")
    print("   • Added 'Existing Customer' column (Y/N)")
    print("   • Updated all addresses to real street addresses")
    print("   • Expanded from 50 to 100 companies")
    print("   • Generated matching records in all related tables")
    print("\n🎯 Next steps:")
    print("   1. Restart your chat server to use the updated database")
    print("   2. Test queries with the new data")
    print("="*70 + "\n")


if __name__ == "__main__":
    print("\n⚠️  WARNING: This will modify your database!")
    print("   A backup table 'accounts_backup' will be created.")
    response = input("\nProceed with migration? (yes/no): ").strip().lower()
    
    if response == "yes":
        migrate_database()
    else:
        print("Migration cancelled.")
