"""Update remaining Company 043-050 with realistic names"""

import sqlite3
import random

DB_PATH = "data/discover_prospecting_clean.db"

# Additional realistic company names by industry
COMPANY_NAMES = {
    "Technology": [
        "TechForge Solutions", "DigitalCore Systems", "ByteWise Technologies", "CloudVision Group",
        "IntelliCode Systems", "DataWave Solutions", "SoftwarePlus Group", "TechSphere Innovations"
    ],
    "Healthcare": [
        "CareConnect Health", "MedPro Solutions", "HealthBridge Partners", "VitalCare Systems",
        "WellnessTech Group", "MediVision Health", "CuraTech Solutions", "HealthCore Partners"
    ],
    "Finance": [
        "WealthBridge Advisors", "FinanceFirst Group", "Capital Dynamics", "TrustPoint Financial",
        "Premier Wealth Partners", "InvestSmart Advisors", "Sterling Financial Group", "Pinnacle Capital"
    ],
    "Retail": [
        "ShopHub Retail", "RetailPro Solutions", "StoreSmart Group", "Commerce Innovations",
        "MegaStore Enterprises", "ShopStream Retail", "ValueVision Stores", "RetailCore Group"
    ],
    "Manufacturing": [
        "IndustrialPro Systems", "FabriCore Manufacturing", "PrecisionWork Industries", "BuildTech Solutions",
        "ManufacturePlus Group", "ProductionWorks LLC", "QualityBuild Industries", "TechFab Manufacturing"
    ],
    "Telecom": [
        "DataBridge Telecom", "SignalPro Networks", "TeleCore Solutions", "ConnectStream Communications",
        "NetWorks Plus", "VoiceBridge Systems", "TeleVision Networks", "CommCore Solutions"
    ],
    "Energy": [
        "EnergyCore Solutions", "PowerBridge Systems", "RenewTech Energy", "VoltStream Corporation",
        "GreenPower Solutions", "EcoVolt Systems", "PowerFlow Energy", "SustainEnergy Group"
    ],
    "Media": [
        "ContentCore Studios", "MediaStream Productions", "BroadVision Media", "StudioPro Network",
        "MediaBridge Group", "CreativeWorks Studios", "VisionStream Media", "ContentPlus Productions"
    ],
    "Transportation": [
        "TransCore Logistics", "FleetBridge Services", "LogiStream Solutions", "CargoMasters Group",
        "TransportPlus Systems", "RouteCore Logistics", "ShipBridge Services", "MoveSmart Logistics"
    ],
    "Real Estate": [
        "EstateCore Realty", "PropertyBridge Group", "RealtyPlus Solutions", "LandVision Properties",
        "UrbanCore Realty", "EstateStream Group", "PropertyWorks Realty", "PrimeSpace Properties"
    ],
    "Education": [
        "EduStream Solutions", "LearnBridge Systems", "AcademyCore Group", "ScholarPlus Technologies",
        "KnowledgeStream Group", "EduWorks Solutions", "BrightPath Education", "LearnCore Systems"
    ],
    "Hospitality": [
        "GuestStream Services", "HospitalityCore Group", "StayBridge Hotels", "ServicePlus Hospitality",
        "WelcomeWorks Group", "ComfortStream Resorts", "GuestBridge Services", "HospitalityPro Group"
    ],
    "Construction": [
        "BuildCore Construction", "StructureWorks Builders", "ConstructStream LLC", "SiteCore Builders",
        "BuildBridge Solutions", "FoundationWorks Group", "ConstructPlus Builders", "StructurePro LLC"
    ],
    "Automotive": [
        "AutoCore Solutions", "DriveBridge Automotive", "VehicleStream Systems", "MotorPlus Group",
        "CarCore Technologies", "AutoStream Solutions", "DriveTech Automotive", "VehicleBridge Group"
    ],
    "Aerospace": [
        "AeroBridge Systems", "SkyCore Aerospace", "FlightStream Group", "SpaceWorks Solutions",
        "AeroStream Technologies", "FlightCore Systems", "SkyBridge Aerospace", "AeroPro Group"
    ]
}


def generate_website(company_name):
    """Generate website URL from company name"""
    name = company_name.lower()
    for suffix in [' group', ' solutions', ' technologies', ' systems', ' services', 
                   ' partners', ' corp', ' corporation', ' inc', ' llc', ' enterprises',
                   ' industries', ' associates', ' holdings', ' ventures', ' capital',
                   ' consulting', ' labs', ' works', ' network', ' studio', ' studios',
                   ' productions', ' media', ' realty', ' properties', ' builders',
                   ' construction', ' automotive', ' aerospace']:
        name = name.replace(suffix, '')
    
    name = name.strip().replace(' ', '')
    return f"www.{name}.com"


def update_remaining_companies():
    """Update Company 043-050 with realistic names"""
    
    print("\n" + "="*70)
    print("UPDATING REMAINING GENERIC COMPANY NAMES")
    print("="*70)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get all remaining generic "Company XXX" records
    cursor.execute('''
        SELECT "Company Name", Industry 
        FROM accounts 
        WHERE "Company Name" LIKE 'Company 0%'
        ORDER BY "Company Name"
    ''')
    
    companies = cursor.fetchall()
    print(f"\n✅ Found {len(companies)} generic company names to update")
    
    if not companies:
        print("   No generic names found - all companies already updated!")
        conn.close()
        return
    
    # Get all existing company names to avoid conflicts
    cursor.execute('SELECT "Company Name" FROM accounts')
    all_existing = {row[0] for row in cursor.fetchall()}
    
    used_names = set()
    updates = []
    
    for old_name, industry in companies:
        # Get potential names for this industry
        if industry in COMPANY_NAMES:
            potential_names = COMPANY_NAMES[industry].copy()
        else:
            potential_names = [
                f"Premier {industry} Group",
                f"Advanced {industry} Solutions",
                f"Elite {industry} Systems",
                f"{industry} Innovations",
                f"Global {industry} Partners"
            ]
        
        # Find an unused name
        new_name = None
        random.shuffle(potential_names)
        
        for name in potential_names:
            if name not in used_names and name not in all_existing:
                new_name = name
                break
        
        # If no unused name found, add a number
        if not new_name:
            base_name = potential_names[0]
            counter = 1
            while f"{base_name} {counter}" in used_names or f"{base_name} {counter}" in all_existing:
                counter += 1
            new_name = f"{base_name} {counter}"
        
        used_names.add(new_name)
        website = generate_website(new_name)
        
        updates.append((old_name, new_name, website))
    
    print("\n📝 Updating company names and websites...")
    
    # Update all tables
    for old_name, new_name, website in updates:
        # Update accounts
        cursor.execute('''
            UPDATE accounts 
            SET "Company Name" = ?, Website = ?
            WHERE "Company Name" = ?
        ''', (new_name, website, old_name))
        
        # Update contacts
        cursor.execute('''
            UPDATE contacts 
            SET "Company Name" = ?
            WHERE "Company Name" = ?
        ''', (new_name, old_name))
        
        # Update opportunities
        cursor.execute('''
            UPDATE opportunities 
            SET "Company Name" = ?
            WHERE "Company Name" = ?
        ''', (new_name, old_name))
        
        # Update insights
        cursor.execute('''
            UPDATE insights 
            SET "Company Name" = ?
            WHERE "Company Name" = ?
        ''', (new_name, old_name))
        
        # Update spend
        cursor.execute('''
            UPDATE spend 
            SET "Company Name" = ?
            WHERE "Company Name" = ?
        ''', (new_name, old_name))
        
        # Update actions
        cursor.execute('''
            UPDATE actions 
            SET "Company Name" = ?
            WHERE "Company Name" = ?
        ''', (new_name, old_name))
        
        print(f"  ✓ {old_name} → {new_name}")
        print(f"    Website: {website}")
    
    conn.commit()
    
    print(f"\n✅ Updated {len(updates)} companies across all tables")
    
    # Verify no generic names remain
    print("\n🔍 Verifying no generic names remain...")
    
    cursor.execute('''
        SELECT COUNT(*) 
        FROM accounts 
        WHERE "Company Name" LIKE 'Company 0%'
    ''')
    
    remaining = cursor.fetchone()[0]
    
    if remaining == 0:
        print("   ✅ SUCCESS: All generic company names have been updated!")
    else:
        print(f"   ⚠️  Warning: {remaining} generic names still remain")
    
    # Show all updated companies
    print("\n📊 Updated companies:")
    for old_name, new_name, website in updates:
        cursor.execute('''
            SELECT Industry, Street, City, State, "Existing Customer"
            FROM accounts 
            WHERE "Company Name" = ?
        ''', (new_name,))
        
        row = cursor.fetchone()
        if row:
            industry, street, city, state, customer = row
            print(f"\n  {new_name}")
            print(f"    Industry: {industry}")
            print(f"    Location: {street}, {city}, {state}")
            print(f"    Website: {website}")
            print(f"    Status: {'Existing Customer' if customer == 'Y' else 'Prospect'}")
    
    conn.close()
    
    print("\n" + "="*70)
    print("✅ UPDATE COMPLETED SUCCESSFULLY!")
    print("="*70 + "\n")


if __name__ == "__main__":
    print("\n⚠️  This will update all remaining generic 'Company XXX' names")
    response = input("Proceed? (yes/no): ").strip().lower()
    
    if response == "yes":
        update_remaining_companies()
    else:
        print("Update cancelled.")
