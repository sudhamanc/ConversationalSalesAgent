"""Database query tools for the discovery agent."""

import sqlite3
import os
from typing import List, Dict, Any
import pandas as pd


class ProspectingDatabase:
    """Interface to the prospecting database."""
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            # Default to data folder relative to project root
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            db_path = os.path.join(project_root, "data", "discover_prospecting_clean.db")
        self.db_path = db_path
    
    def _execute_query(self, query: str, params: tuple = None) -> List[Dict[str, Any]]:
        """Execute a query and return results as list of dictionaries."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            results = [dict(row) for row in cursor.fetchall()]
            return results
        finally:
            conn.close()
    
    def _execute_write(self, query: str, params: tuple = None) -> int:
        """Execute a write query (INSERT, UPDATE, DELETE) and return rows affected."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            conn.commit()
            return cursor.rowcount
        finally:
            conn.close()
    
    def search_companies(self, company_name: str = None, industry: str = None, region: str = None, customer_status: str = None) -> List[Dict[str, Any]]:
        """Search for companies by name, industry, region, or customer status.
        
        Args:
            company_name: Company name to search for
            industry: Industry to filter by
            region: Territory/Region to filter by
            customer_status: 'Y' for existing customers, 'N' for prospects, None for all
        """
        query = """SELECT "Company Name", "Parent Company", Industry, "Territory/Region",
                   Street, City, State, zip_code, Website, "Existing Customer",
                   "Current Products", "Products of Interest" FROM accounts WHERE 1=1"""
        conditions = []
        params = []
        
        if company_name:
            conditions.append("\"Company Name\" LIKE ?")
            params.append(f"%{company_name}%")
        if industry:
            conditions.append("Industry LIKE ?")
            params.append(f"%{industry}%")
        if region:
            conditions.append("\"Territory/Region\" LIKE ?")
            params.append(f"%{region}%")
        if customer_status:
            conditions.append("\"Existing Customer\" = ?")
            params.append(customer_status)
        
        if conditions:
            query += " AND " + " AND ".join(conditions)
        
        return self._execute_query(query, tuple(params) if params else None)
    
    def get_company_details(self, company_name: str) -> Dict[str, Any]:
        """Get detailed information about a specific company including location, customer status, and products."""
        query = """
        SELECT a."Company Name", a."Parent Company", a.Industry, a."Territory/Region",
               a.Street, a.City, a.State, a.Website,
               a."Existing Customer", a."Current Products", a."Products of Interest",
               s."Estimated Annual Spend", s.Digital, s.Programmatic, 
               s.TV, s.Audio, s.OOH, s.Search, s.Social, s."Primary Agency"
        FROM accounts a
        LEFT JOIN spend s ON a."Company Name" = s."Company Name"
        WHERE a."Company Name" = ?
        """
        results = self._execute_query(query, (company_name,))
        return results[0] if results else None
    
    def get_contacts_for_company(self, company_name: str) -> List[Dict[str, Any]]:
        """Get all contacts for a specific company."""
        query = """
        SELECT "Name", Title, "Role in Decision Making", Email, Phone, Notes
        FROM contacts
        WHERE "Company Name" = ?
        """
        return self._execute_query(query, (company_name,))
    
    def get_decision_makers(self, company_name: str) -> List[Dict[str, Any]]:
        """Get economic buyers and key decision makers for a company."""
        query = """
        SELECT "Name", Title, "Role in Decision Making", Email, Phone
        FROM contacts
        WHERE "Company Name" = ? 
        AND "Role in Decision Making" IN ('Economic Buyer', 'Technical Buyer', 'Champion')
        """
        return self._execute_query(query, (company_name,))
    
    def get_opportunities_for_company(self, company_name: str) -> List[Dict[str, Any]]:
        """Get all opportunities for a specific company."""
        query = """
        SELECT "Opportunity Name", Stage, "Total MRC (Est)", Budget, Authority, Need,
               "Timeline (days)", "Target Close Date", "Next Step",
               "BANT_Score_0to100", "BANT_Priority_Bucket", "BANT_Data_Gaps"
        FROM opportunities
        WHERE "Company Name" = ?
        ORDER BY "BANT_Score_0to100" DESC
        """
        return self._execute_query(query, (company_name,))
    
    def get_insights_for_company(self, company_name: str) -> Dict[str, Any]:
        """Get buying signals, pain points, and positioning for a company."""
        query = """
        SELECT "Buying Signals", "Pain Points", "Recommended Positioning"
        FROM insights
        WHERE "Company Name" = ?
        """
        results = self._execute_query(query, (company_name,))
        return results[0] if results else None
    
    def get_actions_for_company(self, company_name: str) -> Dict[str, Any]:
        """Get recommended actions for a company."""
        query = """
        SELECT Owner, Priority, "Initial Outreach Date", "Follow-Up Cadence"
        FROM actions
        WHERE "Company Name" = ?
        """
        results = self._execute_query(query, (company_name,))
        return results[0] if results else None
    
    def get_high_priority_opportunities(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get high-priority opportunities across all companies."""
        query = """
        SELECT o."Company Name", o."Opportunity Name", o.Stage, o."Total MRC (Est)",
               o."BANT_Score_0to100", o."BANT_Priority_Bucket", o."Target Close Date"
        FROM opportunities o
        WHERE o."BANT_Priority_Bucket" IN ('A (High)', 'B (Medium)')
        ORDER BY o."BANT_Score_0to100" DESC
        LIMIT ?
        """
        return self._execute_query(query, (limit,))
    
    def search_by_intent_signals(self, signal_keyword: str) -> List[Dict[str, Any]]:
        """Search companies by buying signals or pain points."""
        query = """
        SELECT a."Company Name", a.Industry, a."Territory/Region",
               a.Street, a.City, a.State,
               a."Existing Customer", a."Current Products", a."Products of Interest",
               i."Buying Signals", i."Pain Points", i."Recommended Positioning"
        FROM accounts a
        JOIN insights i ON a."Company Name" = i."Company Name"
        WHERE i."Buying Signals" LIKE ? OR i."Pain Points" LIKE ?
        """
        keyword = f"%{signal_keyword}%"
        return self._execute_query(query, (keyword, keyword))    
    # ==================== WRITE OPERATIONS ====================
    
    def add_company(self, company_name: str, industry: str, region: str,
                   street: str, city: str, state: str, website: str,
                   parent_company: str = None, existing_customer: str = 'N',
                   current_products: str = None, products_of_interest: str = None,
                   zip_code: str = None) -> bool:
        """Add a new company to accounts table.

        Args:
            company_name: Company name (must be unique)
            industry: Industry classification
            region: Territory/Region
            street: Street address
            city: City
            state: State abbreviation
            website: Company website
            parent_company: Parent company name (optional)
            existing_customer: 'Y' or 'N'
            current_products: Comma-separated products (for existing customers)
            products_of_interest: Comma-separated products (for prospects)
            zip_code: ZIP code (optional)

        Returns:
            True if successful, False otherwise
        """
        query = """
        INSERT INTO accounts (
            "Company Name", "Parent Company", Industry, "Territory/Region",
            Street, City, State, zip_code, Website, "Existing Customer",
            "Current Products", "Products of Interest"
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        try:
            rows = self._execute_write(query, (
                company_name, parent_company, industry, region,
                street, city, state, zip_code, website, existing_customer,
                current_products, products_of_interest
            ))
            return rows > 0
        except sqlite3.IntegrityError:
            return False  # Company already exists
    
    def update_company(self, company_name: str, **kwargs) -> bool:
        """Update company information.
        
        Args:
            company_name: Company name to update
            **kwargs: Fields to update (industry, region, street, city, state, website,
                     parent_company, existing_customer, current_products, products_of_interest)
        
        Returns:
            True if successful, False otherwise
        """
        # Map Python-style names to database column names
        field_mapping = {
            'industry': 'Industry',
            'region': '"Territory/Region"',
            'street': 'Street',
            'city': 'City',
            'state': 'State',
            'zip_code': 'zip_code',
            'website': 'Website',
            'parent_company': '"Parent Company"',
            'existing_customer': '"Existing Customer"',
            'current_products': '"Current Products"',
            'products_of_interest': '"Products of Interest"'
        }
        
        updates = []
        values = []
        
        for key, value in kwargs.items():
            if key in field_mapping:
                updates.append(f"{field_mapping[key]} = ?")
                values.append(value)
        
        if not updates:
            return False
        
        values.append(company_name)
        query = f'UPDATE accounts SET {", ".join(updates)} WHERE "Company Name" = ?'
        
        rows = self._execute_write(query, tuple(values))
        return rows > 0
    
    def add_contact(self, company_name: str, contact_name: str, title: str,
                   role_in_decision_making: str, email: str = None, phone: str = None,
                   notes: str = None) -> bool:
        """Add a new contact to contacts table.
        
        Args:
            company_name: Company name (must exist in accounts)
            contact_name: Contact full name
            title: Job title
            role_in_decision_making: Decision-making role
            email: Email address (optional)
            phone: Phone number (optional)
            notes: Additional notes (optional)
        
        Returns:
            True if successful, False otherwise
        """
        query = """
        INSERT INTO contacts (
            "Company Name", "Name", Title, "Role in Decision Making",
            Email, Phone, Notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        try:
            rows = self._execute_write(query, (
                company_name, contact_name, title, role_in_decision_making,
                email, phone, notes
            ))
            return rows > 0
        except sqlite3.IntegrityError:
            return False
    
    def update_contact(self, company_name: str, contact_name: str, **kwargs) -> bool:
        """Update contact information.
        
        Args:
            company_name: Company name
            contact_name: Contact name to update
            **kwargs: Fields to update (title, role_in_decision_making, email, phone, notes)
        
        Returns:
            True if successful, False otherwise
        """
        field_mapping = {
            'title': 'Title',
            'role_in_decision_making': '"Role in Decision Making"',
            'email': 'Email',
            'phone': 'Phone',
            'notes': 'Notes'
        }
        
        updates = []
        values = []
        
        for key, value in kwargs.items():
            if key in field_mapping:
                updates.append(f"{field_mapping[key]} = ?")
                values.append(value)
        
        if not updates:
            return False
        
        values.extend([company_name, contact_name])
        query = f'UPDATE contacts SET {", ".join(updates)} WHERE "Company Name" = ? AND "Name" = ?'
        
        rows = self._execute_write(query, tuple(values))
        return rows > 0
    
    def add_insight(self, company_name: str, buying_signals: str = None,
                   pain_points: str = None, recommended_positioning: str = None) -> bool:
        """Add or update insights for a company.
        
        Args:
            company_name: Company name
            buying_signals: Buying signals text
            pain_points: Pain points text
            recommended_positioning: Positioning recommendations
        
        Returns:
            True if successful, False otherwise
        """
        # Try insert first, then update if it exists
        query = """
        INSERT OR REPLACE INTO insights (
            "Company Name", "Buying Signals", "Pain Points", "Recommended Positioning"
        ) VALUES (?, ?, ?, ?)
        """
        rows = self._execute_write(query, (
            company_name, buying_signals, pain_points, recommended_positioning
        ))
        return rows > 0
    
    def update_insight(self, company_name: str, **kwargs) -> bool:
        """Update insights for a company.
        
        Args:
            company_name: Company name
            **kwargs: Fields to update (buying_signals, pain_points, recommended_positioning)
        
        Returns:
            True if successful, False otherwise
        """
        field_mapping = {
            'buying_signals': '"Buying Signals"',
            'pain_points': '"Pain Points"',
            'recommended_positioning': '"Recommended Positioning"'
        }
        
        updates = []
        values = []
        
        for key, value in kwargs.items():
            if key in field_mapping:
                updates.append(f"{field_mapping[key]} = ?")
                values.append(value)
        
        if not updates:
            return False
        
        values.append(company_name)
        query = f'UPDATE insights SET {", ".join(updates)} WHERE "Company Name" = ?'
        
        rows = self._execute_write(query, tuple(values))
        return rows > 0