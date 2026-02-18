"""Fixed migration script for discover_prospecting_clean.db"""

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
                    "Vertex", "Zenith", "Prime", "Core", "Peak", "Metro",
                    "Regional", "National", "International", "Digital", "Smart", "Quantum"]

COMPANY_SUFFIXES = ["Solutions", "Enterprises", "Industries", "Group", "Corporation",
                    "Systems", "Technologies", "Partners", "Associates", "Holdings",
                    "Ventures", "Capital", "Services", "Consulting", "Labs", "Works"]


def generate_company_name(industry, existing_names):
    """Generate a unique company name"""
    attempts = 0
    while attempts < 100:
        if industry == "Healthcare":
            base = random.choice(["Medical", "Health", "Care", "Wellness", "Clinical", "MediTech", "HealthCare"])
        elif industry == "Technology":
            base = random.choice(["Tech", "Digital", "Cyber", "Cloud", "Data", "AI", "Software"])
        elif industry == "Finance":
            base = random.choice(["Capital", "Financial", "Trust", "Wealth", "Asset", "Investment", "Banking"])
        elif industry == "Retail":
            base = random.choice(["Retail", "Commerce", "Market", "Store", "Shop", "Outlet", "Mart"])
        elif industry == "Manufacturing":
            base = random.choice(["Industrial", "Manufacturing", "Production", "Factory", "Assembly", "Fabrication"])
        else:
            base = industry
        
        prefix = random.choice(COMPANY_PREFIXES)
        suffix = random.choice(COMPANY_SUFFIXES)
        
        # Try different combinations
        name_options = [
            f"{prefix} {base} {suffix}",
            f"{prefix} {suffix}",
            f"{base} {suffix}",
            f"{prefix} {base}",
        ]
        
        name = random.choice(name_options)
        if name not in existing_names:
            return name
        attempts += 1
    
    # Fallback with number
    return f"{base} {suffix} {random.randint(100, 999)}"


def migrate_database():
    """Perform the database migration"""
    
    print("\n" + "="*70)
    print("DATABASE MIGRATION: Expanding to 100 companies")
    print("="*70)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check if we need to restore from backup
    cursor.execute("SELECT COUNT(*) FROM accounts")
    account_count = cursor.fetchone()[0]
    
    if account_count == 0:
        print("\n⚠️  Accounts table is empty. Restoring from backup...")
        cursor.execute("SELECT COUNT(*) FROM accounts_backup")
        backup_count = cursor.fetchone()[0]
        if backup_count > 0:
            cursor.execute("DROP TABLE accounts")
            cursor.execute("ALTER TABLE accounts_backup RENAME TO accounts")
            print(f"   ✅ Restored {backup_count} companies from backup")
    
    # Step 1: Read existing data
    print("\n1️⃣  Reading existing data...")
    cursor.execute("SELECT * FROM accounts")
    existing_accounts = cursor.fetchall()
    
    cursor.execute("PRAGMA table_info(accounts)")
    columns_info = cursor.fetchall()
    
    print(f"   ✅ Found {len(existing_accounts)} existing companies")
    
    # Step 2: Create new accounts table
    print("\n2️⃣  Creating new accounts table with updated schema...")
    
    cursor.execute("DROP TABLE IF EXISTS accounts_backup")
    cursor.execute("CREATE TABLE accounts_backup AS SELECT * FROM accounts")
    cursor.execute("DROP TABLE accounts")
    
    cursor.execute("""
        CREATE TABLE accounts (
            "Company Name" TEXT PRIMARY KEY,
            "Parent Company" TEXT,
            "Industry" TEXT,
            "Territory/Region" TEXT,
            "Street" TEXT,
            "City" TEXT,
            "State" TEXT,
            "Website" TEXT,
            "Existing Customer" TEXT
        )
    """)
    
    print("   ✅ Created new accounts table")
    
    # Step 3: Migrate existing 50 companies
    print("\n3️⃣  Migrating existing 50 companies with new addresses...")
    
    existing_names = set()
    for row in existing_accounts:
        company_name = row[0]
        parent_company = row[1] if len(row) > 1 else None
        industry = row[2] if len(row) > 2 else "Technology"
        region = row[3] if len(row) > 3 else "Northeast"
        website = row[5] if len(row) > 5 else f"www.{company_name.lower().replace(' ', '')}.com"
        
        existing_names.add(company_name)
        
        # Get address for region
        if region in ADDRESSES:
            street, city, state = random.choice(ADDRESSES[region])
        else:
            street, city, state = random.choice(ADDRESSES["West"])
        
        existing_customer = random.choice(["Y", "N"])
        
        cursor.execute("""
            INSERT INTO accounts VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (company_name, parent_company, industry, region, street, city, state, website, existing_customer))
    
    print(f"   ✅ Migrated {len(existing_accounts)} companies")
    
    # Step 4: Generate 50 new companies
    print("\n4️⃣  Generating 50 new companies...")
    
    regions = list(ADDRESSES.keys())
    new_companies = []
    
    for i in range(50):
        region = random.choice(regions)
        industry = random.choice(INDUSTRIES)
        company_name = generate_company_name(industry, existing_names)
        existing_names.add(company_name)
        
        street, city, state = random.choice(ADDRESSES[region])
        parent_company = None
        website = f"www.{company_name.lower().replace(' ', '')}.com"
        existing_customer = random.choice(["Y", "N"])
        
        cursor.execute("""
            INSERT INTO accounts VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (company_name, parent_company, industry, region, street, city, state, website, existing_customer))
        
        new_companies.append({
            "name": company_name,
            "industry": industry,
            "region": region
        })
    
    print(f"   ✅ Added 50 new companies")
    
    # Step 5: Generate contacts for new companies
    print("\n5️⃣  Generating contacts for new companies...")
    
    titles = ["CEO", "CTO", "CFO", "VP of Sales", "VP of Operations", "Director of IT",
              "Marketing Manager", "Operations Manager", "Product Manager", "CIO", "CMO"]
    roles = ["Economic Buyer", "Champion", "Influencer", "Gatekeeper"]
    
    first_names = ["John", "Jane", "Michael", "Sarah", "David", "Emily", "Robert", "Lisa",
                   "James", "Mary", "William", "Jennifer", "Richard", "Patricia", "Thomas",
                   "Elizabeth", "Christopher", "Linda", "Daniel", "Barbara"]
    last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller",
                  "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Wilson", "Anderson",
                  "Taylor", "Thomas", "Moore", "Jackson", "White", "Harris"]
    
    contacts_added = 0
    for company in new_companies:
        num_contacts = random.randint(2, 4)
        for _ in range(num_contacts):
            name = f"{random.choice(first_names)} {random.choice(last_names)}"
            title = random.choice(titles)
            role = random.choice(roles)
            email = f"{name.lower().replace(' ', '.')}@{company['name'].lower().replace(' ','')[:15]}.com"
            phone = f"{random.randint(200,999)}-{random.randint(200,999)}-{random.randint(1000,9999)}"
            notes = f"Key contact for {company['name']}"
            
            cursor.execute("""
                INSERT INTO contacts VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (company['name'], name, title, role, email, phone, notes))
            
            contacts_added += 1
    
    print(f"   ✅ Added {contacts_added} new contacts")
    
    # Step 6: Generate opportunities for new companies
    print("\n6️⃣  Generating opportunities for new companies...")
    
    stages = ["Discovery", "Qualification", "Proposal", "Negotiation", "Closed Won"]
    
    opps_added = 0
    for company in new_companies:
        num_opps = random.randint(1, 2)
        for _ in range(num_opps):
            opp_name = f"{company['name']} - {random.choice(['Platform', 'Service', 'Solution', 'System'])} Deal"
            stage = random.choice(stages)
            
            month = random.randint(3, 12)
            day = random.randint(1, 28)
            close_date = f"{month:02d}/{day:02d}/2026"
            
            total_mrc = random.randint(5000, 100000)
            budget_text = random.choice(["Confirmed", "Estimated", "Pending Approval"])
            authority_text = random.choice(["Decision Maker", "Influencer", "Champion"])
            need_text = random.choice(["High", "Medium", "Low"])
            timeline_days = random.randint(30, 365)
            next_step = random.choice([
                "Schedule discovery call",
                "Send proposal",
                "Follow up with decision maker",
                "Present demo",
                "Negotiate terms",
                "Request for references"
            ])
            
            # BANT Scoring
            budget_score = random.randint(1, 3)
            authority_score = random.randint(1, 3)
            need_score = random.randint(1, 3)
            
            if timeline_days < 90:
                timing_score = 3
            elif timeline_days < 180:
                timing_score = 2
            else:
                timing_score = 1
            
            weighted_score = (budget_score + authority_score + need_score + timing_score) / 4.0
            bant_100 = round((weighted_score / 3.0) * 100, 1)
            
            if bant_100 >= 75:
                priority = "A"
            elif bant_100 >= 50:
                priority = "B"
            else:
                priority = "C"
            
            gaps = []
            if budget_score < 2:
                gaps.append("Budget")
            if authority_score < 2:
                gaps.append("Authority")
            if need_score < 2:
                gaps.append("Need")
            if timing_score < 2:
                gaps.append("Timeline")
            gaps_text = ", ".join(gaps) if gaps else "None"
            
            cursor.execute("""
                INSERT INTO opportunities VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (company['name'], opp_name, stage, total_mrc, budget_text, authority_text, need_text,
                  timeline_days, close_date, next_step, budget_score, authority_score, need_score,
                  timing_score, weighted_score, bant_100, priority, gaps_text))
            
            opps_added += 1
    
    print(f"   ✅ Added {opps_added} new opportunities")
    
    # Step 7: Generate insights for new companies
    print("\n7️⃣  Generating insights for new companies...")
    
    buying_signals = [
        "Budget allocated for Q2 2026",
        "Recent leadership change - new CIO hired",
        "Competitor evaluation in progress",
        "Current system end-of-life approaching",
        "Expansion plans announced",
        "Digital transformation initiative launched",
        "Increased website activity",
        "Attending industry conferences"
    ]
    
    pain_points = [
        "Manual processes causing operational delays",
        "Lack of real-time visibility into operations",
        "Integration challenges with legacy systems",
        "Scalability concerns with current infrastructure",
        "Compliance requirements not being met",
        "High operational costs",
        "Data silos preventing insights",
        "Poor customer experience"
    ]
    
    positioning = [
        "Emphasize ROI and cost savings potential",
        "Highlight ease of integration capabilities",
        "Focus on scalability and growth support",
        "Demonstrate compliance features",
        "Showcase customer success stories",
        "Stress time-to-value and quick wins",
        "Present analytical capabilities",
        "Emphasize superior customer support"
    ]
    
    for company in new_companies:
        cursor.execute("""
            INSERT INTO insights VALUES (?, ?, ?, ?)
        """, (company['name'], random.choice(buying_signals),
              random.choice(pain_points), random.choice(positioning)))
    
    print(f"   ✅ Added {len(new_companies)} insight records")
    
    # Step 8: Generate spend data for new companies
    print("\n8️⃣  Generating ad spend data for new companies...")
    
    agencies = ["GroupM", "Publicis", "Omnicom", "IPG", "Dentsu", "Independent", "In-House"]
    
    for company in new_companies:
        estimated_annual = random.randint(50000, 5000000)
        digital = int(estimated_annual * random.uniform(0.3, 0.5))
        programmatic = int(digital * random.uniform(0.4, 0.6))
        tv = int(estimated_annual * random.uniform(0.1, 0.3))
        audio = int(estimated_annual * random.uniform(0.05, 0.15))
        ooh = int(estimated_annual * random.uniform(0.05, 0.15))
        search = int(digital * random.uniform(0.2, 0.4))
        social = int(digital * random.uniform(0.2, 0.4))
        agency = random.choice(agencies)
        
        cursor.execute("""
            INSERT INTO spend VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (company['name'], estimated_annual, digital, programmatic, tv, audio, ooh,
              search, social, agency))
    
    print(f"   ✅ Added {len(new_companies)} spend records")
    
    # Step 9: Generate action recommendations for new companies
    print("\n9️⃣  Generating action recommendations...")
    
    owners = ["Sales Rep 1", "Sales Rep 2", "Sales Rep 3", "Account Manager", "Business Development"]
    priorities = ["High", "Medium", "Low"]
    
    for company in new_companies:
        owner = random.choice(owners)
        priority = random.choice(priorities)
        
        # Random date in Feb-Mar 2026
        month = random.randint(2, 3)
        day = random.randint(1, 28)
        outreach_date = f"{month:02d}/{day:02d}/2026"
        
        cadence = random.choice(["Weekly", "Bi-weekly", "Monthly"])
        
        cursor.execute("""
            INSERT INTO actions VALUES (?, ?, ?, ?, ?)
        """, (company['name'], owner, priority, outreach_date, cadence))
    
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
    print("   • Added 'City' and 'State' columns with real addresses")
    print("   • Added 'Existing Customer' column (Y/N randomly assigned)")
    print("   • Removed 'USA' from addresses")
    print("   • Expanded from 50 to 100 companies")
    print("   • Generated matching records in all related tables:")
    print(f"      - {contacts_added} new contacts")
    print(f"      - {opps_added} new opportunities")
    print(f"      - 50 new insights")
    print(f"      - 50 new spend records")
    print(f"      - 50 new action items")
    print("\n🎯 Next steps:")
    print("   1. Restart your chat server: Get-Process python | Stop-Process")
    print("   2. cd C:\\Code\\ConversationalSalesAgent\\DiscoveryAgent")
    print("   3. .\\.\venv312\\Scripts\\python.exe main_server.py")
    print("   4. Test with: 'What companies do we have?'")
    print("="*70 + "\n")


if __name__ == "__main__":
    print("\n⚠️  WARNING: This will modify your database!")
    print("   A backup table 'accounts_backup' will be created.")
    response = input("\nProceed with migration? (yes/no): ").strip().lower()
    
    if response == "yes":
        migrate_database()
    else:
        print("Migration cancelled.")
