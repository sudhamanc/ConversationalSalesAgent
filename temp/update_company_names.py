"""Update first 50 companies with realistic names and websites"""

import sqlite3
import random

DB_PATH = "data/discover_prospecting_clean.db"

# Realistic company names by industry
COMPANY_NAMES = {
    "Technology": [
        "DataSync Technologies", "CloudCore Systems", "NexGen Software", "TechVision Solutions",
        "InnovateTech Group", "ByteStream Analytics", "CyberShield Security", "QuantumLeap AI",
        "DevOps Masters", "CodeCraft Studios", "NetLogic Systems", "InfoBridge Tech"
    ],
    "Healthcare": [
        "WellCare Medical Group", "HealthFirst Partners", "CarePoint Systems", "MediTech Solutions",
        "Vitality Health Services", "CuraBridge Healthcare", "PrimeCare Medical", "HealthStream Network",
        "MediCore Solutions", "WellSpring Health", "PulseMed Technologies", "LifeCare Systems"
    ],
    "Finance": [
        "Capital Trust Partners", "Premier Financial Group", "SecureWealth Advisors", "Summit Capital Management",
        "Prosperity Financial Services", "Heritage Trust Company", "Vanguard Asset Management", "Alliance Capital Partners",
        "Cornerstone Financial Group", "Beacon Wealth Advisors", "Prestige Banking Solutions", "Fortress Capital"
    ],
    "Retail": [
        "MarketPlace Retail Group", "ShopSmart Enterprises", "RetailEdge Solutions", "Commerce Central",
        "StoreFront Innovations", "MegaMart Retail", "ValuePlus Stores", "TrendSetters Retail",
        "ConsumerFirst Markets", "OptiRetail Solutions", "PrimeMart Group", "ShopWise Stores"
    ],
    "Manufacturing": [
        "PrecisionBuild Industries", "ManuTech Solutions", "Industrial Dynamics Corp", "ProFab Manufacturing",
        "AssemblyLine Systems", "MasterCraft Industries", "Production Plus LLC", "BuildRight Manufacturing",
        "QualityFirst Fabrication", "SteelWorks Industries", "TechForge Manufacturing", "AutoMate Production"
    ],
    "Telecom": [
        "ConnectPlus Communications", "SignalWave Networks", "TeleLink Solutions", "DataFlow Telecom",
        "NetSpan Communications", "VoiceStream Networks", "WirelessEdge Solutions", "BroadBand Connect",
        "TeleBridge Systems", "CommUnity Networks", "Digital Telecom Group", "FiberLink Communications"
    ],
    "Energy": [
        "PowerStream Energy", "GreenTech Energy Solutions", "SolarVolt Systems", "EnergyPlus Corporation",
        "CleanPower Innovations", "Renewable Energy Partners", "GridMaster Solutions", "EcoEnergy Group",
        "PowerGen Systems", "BrightFuture Energy", "VoltCore Technologies", "Sustainable Power Corp"
    ],
    "Media": [
        "MediaVision Productions", "ContentStream Studios", "BroadCast Pro Media", "Digital Media Works",
        "StoryLine Productions", "MediaMasters Group", "CreativeEdge Studios", "StreamWorks Media",
        "VisionCraft Productions", "MediaHub Network", "ContentPro Studios", "BroadCast Central"
    ],
    "Transportation": [
        "LogiTrans Solutions", "FleetMaster Logistics", "TransportStream Systems", "CargoLink Services",
        "RouteMaster Logistics", "FastTrack Transport", "MoveIt Logistics", "ShipSmart Solutions",
        "FreightPro Systems", "LogistiCore Services", "TransitEdge Solutions", "DeliveryFirst Logistics"
    ],
    "Real Estate": [
        "PropertyPro Realty", "PrimeLocation Group", "RealtyEdge Solutions", "EstateHub Realty",
        "UrbanSpace Properties", "LandMark Realty", "PropertyFirst Group", "RealtyMasters Inc",
        "EstateVision Properties", "HomeBase Realty", "PrimeEstate Group", "Realty Innovations"
    ],
    "Education": [
        "LearnTech Solutions", "EduVision Systems", "Knowledge Hub", "ScholarStream Technologies",
        "BrightMinds Education", "LearnFirst Group", "EduCore Solutions", "AcademyPro Systems",
        "SmartLearn Technologies", "EduBridge Solutions", "ScholarTech Group", "Knowledge Works"
    ],
    "Hospitality": [
        "HospitalityPlus Group", "GuestFirst Services", "StayWell Hotels", "ServiceMasters Hospitality",
        "ComfortZone Resorts", "WelcomeInn Group", "HospitalityEdge Solutions", "GuestCare Services",
        "LodgeMasters Group", "StaySmart Hospitality", "ResortPro Systems", "HospitalityHub"
    ],
    "Construction": [
        "BuildMasters Construction", "StructurePro Builders", "ConstructEdge Solutions", "FoundationFirst Builders",
        "ProBuild Construction", "SiteMasters Group", "BuildRight Solutions", "ConstructionPlus LLC",
        "StructureWorks Builders", "BuildSmart Construction", "Foundation Builders", "ConstructPro Group"
    ],
    "Automotive": [
        "AutoTech Solutions", "DriveWorks Automotive", "VehiclePro Systems", "MotorMasters Group",
        "AutoEdge Solutions", "CarCraft Technologies", "DriveFirst Automotive", "VehicleTech Group",
        "AutoPro Solutions", "MotorWorks Systems", "CarTech Innovations", "DriveMasters Group"
    ],
    "Aerospace": [
        "AeroTech Solutions", "SkyWorks Aerospace", "FlightMasters Group", "AeroEdge Systems",
        "SpaceTech Solutions", "AirStream Technologies", "AeroVision Group", "FlightPro Systems",
        "SkyTech Innovations", "AeroDynamics Corp", "SpaceWorks Group", "AeroMasters Solutions"
    ]
}


def generate_website(company_name):
    """Generate website URL from company name"""
    # Remove common suffixes
    name = company_name.lower()
    for suffix in [' group', ' solutions', ' technologies', ' systems', ' services', 
                   ' partners', ' corp', ' corporation', ' inc', ' llc', ' enterprises',
                   ' industries', ' associates', ' holdings', ' ventures', ' capital',
                   ' consulting', ' labs', ' works', ' network', ' studio', ' studios',
                   ' productions', ' media', ' realty', ' properties', ' builders',
                   ' construction', ' automotive', ' aerospace']:
        name = name.replace(suffix, '')
    
    # Clean up
    name = name.strip().replace(' ', '')
    
    return f"www.{name}.com"


def update_company_names():
    """Update first 50 companies with realistic names"""
    
    print("\n" + "="*70)
    print("UPDATING FIRST 50 COMPANIES WITH REALISTIC NAMES")
    print("="*70)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get first 50 companies with their industries
    cursor.execute('''
        SELECT "Company Name", Industry 
        FROM accounts 
        ORDER BY "Company Name" 
        LIMIT 50
    ''')
    
    companies = cursor.fetchall()
    print(f"\n✅ Found {len(companies)} companies to update")
    
    # Track used names to avoid duplicates
    used_names = set()
    
    # Get all existing company names to avoid conflicts
    cursor.execute('SELECT "Company Name" FROM accounts')
    all_existing = {row[0] for row in cursor.fetchall()}
    
    updates = []
    
    for old_name, industry in companies:
        # Get potential names for this industry
        if industry in COMPANY_NAMES:
            potential_names = COMPANY_NAMES[industry].copy()
        else:
            # Use generic names if industry not in our list
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
    
    # Update accounts table
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
    
    # Verify updates
    print("\n🔍 Verifying updates...")
    
    cursor.execute('SELECT COUNT(*) FROM accounts')
    total = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(DISTINCT "Company Name") FROM accounts')
    unique = cursor.fetchone()[0]
    
    print(f"   Total companies: {total}")
    print(f"   Unique names: {unique}")
    
    # Show sample of updated companies
    print("\n📊 Sample of updated companies:")
    cursor.execute('''
        SELECT "Company Name", Industry, Website 
        FROM accounts 
        ORDER BY "Company Name" 
        LIMIT 10
    ''')
    
    for name, industry, website in cursor.fetchall():
        print(f"\n  {name}")
        print(f"    Industry: {industry}")
        print(f"    Website: {website}")
    
    conn.close()
    
    print("\n" + "="*70)
    print("✅ UPDATE COMPLETED SUCCESSFULLY!")
    print("="*70)
    print("\n🎯 Next steps:")
    print("   1. Restart your chat server")
    print("   2. Test with queries about specific companies")
    print("="*70 + "\n")


if __name__ == "__main__":
    print("\n⚠️  This will update the first 50 company names and websites")
    response = input("Proceed? (yes/no): ").strip().lower()
    
    if response == "yes":
        update_company_names()
    else:
        print("Update cancelled.")
