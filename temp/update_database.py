"""Database update utilities for discover_prospecting_clean.db"""

import sqlite3
import pandas as pd
from pathlib import Path
from datetime import datetime

DB_PATH = Path("data/discover_prospecting_clean.db")


def connect_db():
    """Connect to the database"""
    return sqlite3.connect(DB_PATH)


def view_all_tables():
    """Show all tables and their record counts"""
    conn = connect_db()
    cursor = conn.cursor()
    
    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = cursor.fetchall()
    
    print("\n" + "="*60)
    print("DATABASE TABLES")
    print("="*60)
    
    for table in tables:
        table_name = table[0]
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        print(f"  {table_name}: {count} records")
    
    conn.close()
    print("="*60 + "\n")


def view_table_structure(table_name: str):
    """Show the structure of a specific table"""
    conn = connect_db()
    cursor = conn.cursor()
    
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    
    print(f"\n{'='*60}")
    print(f"STRUCTURE OF TABLE: {table_name}")
    print(f"{'='*60}")
    print(f"{'Column Name':<30} {'Type':<15} {'Not Null'}")
    print("-"*60)
    
    for col in columns:
        col_name = col[1]
        col_type = col[2]
        not_null = "YES" if col[3] else "NO"
        print(f"{col_name:<30} {col_type:<15} {not_null}")
    
    conn.close()
    print("="*60 + "\n")


def view_table_data(table_name: str, limit: int = 10):
    """View sample data from a table"""
    conn = connect_db()
    
    query = f"SELECT * FROM {table_name} LIMIT {limit}"
    df = pd.read_sql_query(query, conn)
    
    print(f"\n{'='*60}")
    print(f"SAMPLE DATA FROM: {table_name} (first {limit} rows)")
    print(f"{'='*60}")
    print(df.to_string())
    print(f"{'='*60}\n")
    
    conn.close()


def add_company(company_data: dict):
    """Add a new company to the accounts table"""
    conn = connect_db()
    cursor = conn.cursor()
    
    # Get the next company ID
    cursor.execute("SELECT MAX(CAST(SUBSTR([Account/Company ID], 9) AS INTEGER)) FROM accounts")
    max_id = cursor.fetchone()[0] or 0
    new_id = f"Company {max_id + 1:03d}"
    
    # Required fields
    required_fields = {
        "Account/Company ID": new_id,
        "Company Name": company_data.get("Company Name", "New Company"),
        "Industry": company_data.get("Industry", "Technology"),
        "Territory/Region": company_data.get("Territory/Region", "Northeast"),
        "Company Size (employees)": company_data.get("Company Size (employees)", 100),
        "Annual Revenue (USD)": company_data.get("Annual Revenue (USD)", 1000000),
        "Estimated Annual Spend": company_data.get("Estimated Annual Spend", 50000)
    }
    
    # Insert into accounts
    columns = ", ".join([f'"{k}"' for k in required_fields.keys()])
    placeholders = ", ".join(["?" for _ in required_fields])
    query = f"INSERT INTO accounts ({columns}) VALUES ({placeholders})"
    
    cursor.execute(query, list(required_fields.values()))
    conn.commit()
    
    print(f"✅ Added company: {required_fields['Company Name']} (ID: {new_id})")
    
    conn.close()
    return new_id


def add_contact(contact_data: dict):
    """Add a new contact to the contacts table"""
    conn = connect_db()
    cursor = conn.cursor()
    
    # Get the next contact ID
    cursor.execute("SELECT MAX(CAST(SUBSTR([Contact ID], 9) AS INTEGER)) FROM contacts")
    max_id = cursor.fetchone()[0] or 0
    new_id = f"Contact {max_id + 1:03d}"
    
    # Required fields
    required_fields = {
        "Contact ID": new_id,
        "Account/Company ID": contact_data.get("Account/Company ID", "Company 001"),
        "Name": contact_data.get("Name", "John Doe"),
        "Title": contact_data.get("Title", "Manager"),
        "Email": contact_data.get("Email", "john.doe@example.com"),
        "Phone": contact_data.get("Phone", "555-0100"),
        "Role in Decision Making": contact_data.get("Role in Decision Making", "Influencer"),
        "Engagement Level": contact_data.get("Engagement Level", "Medium")
    }
    
    # Insert into contacts
    columns = ", ".join([f'"{k}"' for k in required_fields.keys()])
    placeholders = ", ".join(["?" for _ in required_fields])
    query = f"INSERT INTO contacts ({columns}) VALUES ({placeholders})"
    
    cursor.execute(query, list(required_fields.values()))
    conn.commit()
    
    print(f"✅ Added contact: {required_fields['Name']} (ID: {new_id})")
    
    conn.close()
    return new_id


def add_opportunity(opp_data: dict):
    """Add a new opportunity to the opportunities table"""
    conn = connect_db()
    cursor = conn.cursor()
    
    # Get the next opportunity ID
    cursor.execute("SELECT MAX(CAST(SUBSTR([Opportunity ID], 13) AS INTEGER)) FROM opportunities")
    max_id = cursor.fetchone()[0] or 0
    new_id = f"Opportunity {max_id + 1:03d}"
    
    # Required fields with BANT scoring
    required_fields = {
        "Opportunity ID": new_id,
        "Account/Company ID": opp_data.get("Account/Company ID", "Company 001"),
        "Opportunity Name": opp_data.get("Opportunity Name", "New Opportunity"),
        "Stage": opp_data.get("Stage", "Discovery"),
        "Expected Close Date": opp_data.get("Expected Close Date", "2026-12-31"),
        "Estimated Deal Value (USD)": opp_data.get("Estimated Deal Value (USD)", 50000),
        "Budget": opp_data.get("Budget", 2),  # 0-3
        "Authority": opp_data.get("Authority", 2),  # 0-3
        "Need": opp_data.get("Need", 2),  # 0-3
        "Timeline (days)": opp_data.get("Timeline (days)", 180),
        "Priority Bucket": opp_data.get("Priority Bucket", "B"),
        "Next Action": opp_data.get("Next Action", "Schedule discovery call")
    }
    
    # Calculate BANT score
    budget = required_fields["Budget"]
    authority = required_fields["Authority"]
    need = required_fields["Need"]
    timeline_days = required_fields["Timeline (days)"]
    
    # Timeline score (0-3): <90 days=3, 90-180=2, 180-360=1, >360=0
    if timeline_days < 90:
        timeline_score = 3
    elif timeline_days < 180:
        timeline_score = 2
    elif timeline_days < 360:
        timeline_score = 1
    else:
        timeline_score = 0
    
    # Convert to 0-100 scale
    bant_score = ((budget + authority + need + timeline_score) / 12.0) * 100
    required_fields["BANT_Score_0to100"] = round(bant_score, 1)
    
    # Insert into opportunities
    columns = ", ".join([f'"{k}"' for k in required_fields.keys()])
    placeholders = ", ".join(["?" for _ in required_fields])
    query = f"INSERT INTO opportunities ({columns}) VALUES ({placeholders})"
    
    cursor.execute(query, list(required_fields.values()))
    conn.commit()
    
    print(f"✅ Added opportunity: {required_fields['Opportunity Name']} (ID: {new_id}, BANT: {bant_score:.1f})")
    
    conn.close()
    return new_id


def update_record(table: str, record_id_column: str, record_id: str, updates: dict):
    """Update a record in any table"""
    conn = connect_db()
    cursor = conn.cursor()
    
    # Build update query
    set_clause = ", ".join([f'"{k}" = ?' for k in updates.keys()])
    query = f'UPDATE {table} SET {set_clause} WHERE "{record_id_column}" = ?'
    
    values = list(updates.values()) + [record_id]
    cursor.execute(query, values)
    conn.commit()
    
    rows_affected = cursor.rowcount
    
    if rows_affected > 0:
        print(f"✅ Updated {rows_affected} record(s) in {table}")
    else:
        print(f"⚠️  No records updated. ID '{record_id}' not found in {table}")
    
    conn.close()


def delete_record(table: str, record_id_column: str, record_id: str):
    """Delete a record from any table"""
    conn = connect_db()
    cursor = conn.cursor()
    
    query = f'DELETE FROM {table} WHERE "{record_id_column}" = ?'
    cursor.execute(query, [record_id])
    conn.commit()
    
    rows_affected = cursor.rowcount
    
    if rows_affected > 0:
        print(f"✅ Deleted {rows_affected} record(s) from {table}")
    else:
        print(f"⚠️  No records deleted. ID '{record_id}' not found in {table}")
    
    conn.close()


def run_query(sql: str):
    """Run a custom SQL query"""
    conn = connect_db()
    
    try:
        if sql.strip().upper().startswith("SELECT"):
            df = pd.read_sql_query(sql, conn)
            print("\n" + "="*60)
            print("QUERY RESULTS")
            print("="*60)
            print(df.to_string())
            print("="*60 + "\n")
        else:
            cursor = conn.cursor()
            cursor.execute(sql)
            conn.commit()
            print(f"✅ Query executed successfully. Rows affected: {cursor.rowcount}")
    except Exception as e:
        print(f"❌ Error: {str(e)}")
    finally:
        conn.close()


def export_to_csv(table: str, output_file: str):
    """Export a table to CSV"""
    conn = connect_db()
    df = pd.read_sql_query(f"SELECT * FROM {table}", conn)
    df.to_csv(output_file, index=False)
    print(f"✅ Exported {len(df)} rows from {table} to {output_file}")
    conn.close()


def import_from_csv(table: str, csv_file: str, if_exists: str = "append"):
    """Import data from CSV into a table"""
    conn = connect_db()
    df = pd.read_csv(csv_file)
    df.to_sql(table, conn, if_exists=if_exists, index=False)
    print(f"✅ Imported {len(df)} rows into {table}")
    conn.close()


def interactive_menu():
    """Interactive menu for database operations"""
    while True:
        print("\n" + "="*60)
        print("DATABASE UPDATE MENU")
        print("="*60)
        print("1. View all tables")
        print("2. View table structure")
        print("3. View table data")
        print("4. Add new company")
        print("5. Add new contact")
        print("6. Add new opportunity")
        print("7. Update a record")
        print("8. Delete a record")
        print("9. Run custom SQL query")
        print("10. Export table to CSV")
        print("11. Import from CSV")
        print("0. Exit")
        print("="*60)
        
        choice = input("\nEnter your choice: ").strip()
        
        if choice == "0":
            print("Goodbye!")
            break
        elif choice == "1":
            view_all_tables()
        elif choice == "2":
            table = input("Enter table name: ").strip()
            view_table_structure(table)
        elif choice == "3":
            table = input("Enter table name: ").strip()
            limit = int(input("Number of rows to show (default 10): ").strip() or "10")
            view_table_data(table, limit)
        elif choice == "4":
            print("\n--- Add New Company ---")
            company_data = {
                "Company Name": input("Company Name: ").strip(),
                "Industry": input("Industry: ").strip(),
                "Territory/Region": input("Region: ").strip(),
                "Company Size (employees)": int(input("Company Size (employees): ").strip() or "100"),
                "Annual Revenue (USD)": int(input("Annual Revenue (USD): ").strip() or "1000000"),
                "Estimated Annual Spend": int(input("Estimated Annual Spend: ").strip() or "50000")
            }
            add_company(company_data)
        elif choice == "5":
            print("\n--- Add New Contact ---")
            contact_data = {
                "Account/Company ID": input("Company ID (e.g., Company 001): ").strip(),
                "Name": input("Contact Name: ").strip(),
                "Title": input("Title: ").strip(),
                "Email": input("Email: ").strip(),
                "Phone": input("Phone: ").strip(),
                "Role in Decision Making": input("Role (Economic Buyer/Champion/Influencer): ").strip(),
                "Engagement Level": input("Engagement Level (High/Medium/Low): ").strip()
            }
            add_contact(contact_data)
        elif choice == "6":
            print("\n--- Add New Opportunity ---")
            opp_data = {
                "Account/Company ID": input("Company ID (e.g., Company 001): ").strip(),
                "Opportunity Name": input("Opportunity Name: ").strip(),
                "Stage": input("Stage (Discovery/Proposal/Negotiation/Closed Won): ").strip(),
                "Expected Close Date": input("Expected Close Date (YYYY-MM-DD): ").strip(),
                "Estimated Deal Value (USD)": int(input("Deal Value (USD): ").strip() or "50000"),
                "Budget": int(input("Budget Score (0-3): ").strip() or "2"),
                "Authority": int(input("Authority Score (0-3): ").strip() or "2"),
                "Need": int(input("Need Score (0-3): ").strip() or "2"),
                "Timeline (days)": int(input("Timeline (days): ").strip() or "180"),
                "Priority Bucket": input("Priority Bucket (A/B/C): ").strip() or "B"
            }
            add_opportunity(opp_data)
        elif choice == "9":
            print("\n--- Run Custom SQL ---")
            sql = input("Enter SQL query: ").strip()
            run_query(sql)
        elif choice == "10":
            table = input("Enter table name: ").strip()
            output = input("Output CSV file: ").strip()
            export_to_csv(table, output)
        else:
            print("Invalid choice. Please try again.")


if __name__ == "__main__":
    print("\n🗄️  Database Update Utility")
    print(f"Database: {DB_PATH}")
    interactive_menu()
