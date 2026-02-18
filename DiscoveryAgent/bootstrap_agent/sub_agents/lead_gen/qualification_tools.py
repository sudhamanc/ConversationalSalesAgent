"""Database query tools for lead qualification and BANT scoring."""

import sqlite3
import os
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta


class LeadQualificationDatabase:
    """Interface to the prospecting database for lead qualification."""
    
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
    
    def get_opportunity_qualification(self, company_name: str, opportunity_name: str = None) -> List[Dict[str, Any]]:
        """Get BANT qualification details for opportunities."""
        query = """
        SELECT 
            o."Company Name",
            o."Opportunity Name",
            o.Stage,
            o."Total MRC (Est)",
            o.Budget,
            o.Authority,
            o.Need,
            o."Timeline (days)",
            o."Target Close Date",
            o."Next Step",
            o.BANT_Budget_Score,
            o.BANT_Authority_Score,
            o.BANT_Need_Score,
            o.BANT_Timing_Score,
            o.BANT_Weighted_0to3,
            o.BANT_Score_0to100,
            o.BANT_Priority_Bucket,
            o.BANT_Data_Gaps
        FROM opportunities o
        WHERE o."Company Name" = ?
        """
        params = [company_name]
        
        if opportunity_name:
            query += ' AND o."Opportunity Name" = ?'
            params.append(opportunity_name)
        
        query += ' ORDER BY o.BANT_Score_0to100 DESC'
        
        return self._execute_query(query, tuple(params))
    
    def get_qualified_leads(self, min_score: float = 50.0, priority_bucket: str = None) -> List[Dict[str, Any]]:
        """Get all qualified leads above a threshold score."""
        query = """
        SELECT 
            o."Company Name",
            o."Opportunity Name",
            o.Stage,
            o."Total MRC (Est)",
            o.BANT_Score_0to100,
            o.BANT_Priority_Bucket,
            o.Budget,
            o.Authority,
            o.Need,
            o."Timeline (days)",
            o."Target Close Date",
            o."Next Step",
            o.BANT_Data_Gaps,
            a.Industry,
            a."Territory/Region",
            a.Street,
            a.City,
            a.State,
            a."Existing Customer",
            a."Current Products",
            a."Products of Interest",
            i."Buying Signals",
            i."Pain Points"
        FROM opportunities o
        JOIN accounts a ON o."Company Name" = a."Company Name"
        LEFT JOIN insights i ON o."Company Name" = i."Company Name"
        WHERE o.BANT_Score_0to100 >= ?
        """
        params = [min_score]
        
        if priority_bucket:
            query += ' AND o.BANT_Priority_Bucket = ?'
            params.append(priority_bucket)
        
        query += ' ORDER BY o.BANT_Score_0to100 DESC, o."Target Close Date" ASC'
        
        return self._execute_query(query, tuple(params) if params else None)
    
    def get_leads_by_stage(self, stage: str) -> List[Dict[str, Any]]:
        """Get leads filtered by sales stage."""
        query = """
        SELECT 
            o."Company Name",
            o."Opportunity Name",
            o.Stage,
            o."Total MRC (Est)",
            o.BANT_Score_0to100,
            o.BANT_Priority_Bucket,
            o."Target Close Date",
            o."Next Step",
            o.BANT_Data_Gaps
        FROM opportunities o
        WHERE o.Stage = ?
        ORDER BY o.BANT_Score_0to100 DESC
        """
        return self._execute_query(query, (stage,))
    
    def get_leads_with_gaps(self, gap_type: str = None) -> List[Dict[str, Any]]:
        """Get leads with qualification data gaps."""
        query = """
        SELECT 
            o."Company Name",
            o."Opportunity Name",
            o.Stage,
            o.BANT_Score_0to100,
            o.BANT_Priority_Bucket,
            o.BANT_Data_Gaps,
            o.Budget,
            o.Authority,
            o.Need,
            o."Timeline (days)",
            o."Next Step"
        FROM opportunities o
        WHERE o.BANT_Data_Gaps IS NOT NULL AND o.BANT_Data_Gaps != ''
        """
        
        if gap_type:
            query += f" AND o.BANT_Data_Gaps LIKE ?"
            return self._execute_query(query, (f'%{gap_type}%',))
        
        query += ' ORDER BY o.BANT_Score_0to100 DESC'
        return self._execute_query(query)
    
    def get_sales_ready_leads(self) -> List[Dict[str, Any]]:
        """Get leads that are sales-ready (high BANT score, minimal gaps)."""
        query = """
        SELECT 
            o."Company Name",
            o."Opportunity Name",
            o.Stage,
            o."Total MRC (Est)",
            o.BANT_Score_0to100,
            o.BANT_Priority_Bucket,
            o.Budget,
            o.Authority,
            o.Need,
            o."Timeline (days)",
            o."Target Close Date",
            o."Next Step",
            o.BANT_Data_Gaps,
            a.Industry,
            a."Territory/Region",
            a.Street,
            a.City,
            a.State,
            a."Existing Customer",
            a."Current Products",
            a."Products of Interest",
            i."Buying Signals",
            i."Pain Points",
            i."Recommended Positioning",
            s."Estimated Annual Spend"
        FROM opportunities o
        JOIN accounts a ON o."Company Name" = a."Company Name"
        LEFT JOIN insights i ON o."Company Name" = i."Company Name"
        LEFT JOIN spend s ON o."Company Name" = s."Company Name"
        WHERE o.BANT_Score_0to100 >= 66.7
        AND o.BANT_Priority_Bucket IN ('A (High)', 'B (Medium)')
        AND (o.BANT_Data_Gaps IS NULL OR o.BANT_Data_Gaps = '')
        ORDER BY o.BANT_Score_0to100 DESC, o."Timeline (days)" ASC
        """
        return self._execute_query(query)
    
    def get_lead_qualification_summary(self) -> Dict[str, Any]:
        """Get overall lead qualification statistics."""
        query = """
        SELECT 
            COUNT(*) as total_opportunities,
            AVG(BANT_Score_0to100) as avg_bant_score,
            SUM(CASE WHEN BANT_Priority_Bucket = 'A (High)' THEN 1 ELSE 0 END) as high_priority_count,
            SUM(CASE WHEN BANT_Priority_Bucket = 'B (Medium)' THEN 1 ELSE 0 END) as medium_priority_count,
            SUM(CASE WHEN BANT_Priority_Bucket = 'C (Low)' THEN 1 ELSE 0 END) as low_priority_count,
            SUM(CASE WHEN BANT_Data_Gaps IS NOT NULL AND BANT_Data_Gaps != '' THEN 1 ELSE 0 END) as gaps_count,
            SUM(CASE WHEN Stage = 'Negotiation' THEN 1 ELSE 0 END) as negotiation_stage,
            SUM(CASE WHEN Stage = 'Proposal' THEN 1 ELSE 0 END) as proposal_stage,
            SUM(CASE WHEN Stage = 'Discovery' THEN 1 ELSE 0 END) as discovery_stage,
            SUM("Total MRC (Est)") as total_pipeline_value
        FROM opportunities
        """
        results = self._execute_query(query)
        return results[0] if results else {}
    
    def get_bant_component_analysis(self, company_name: str, opportunity_name: str) -> Dict[str, Any]:
        """Get detailed BANT component breakdown for an opportunity."""
        query = """
        SELECT 
            "Company Name",
            "Opportunity Name",
            Budget,
            BANT_Budget_Score,
            Authority,
            BANT_Authority_Score,
            Need,
            BANT_Need_Score,
            "Timeline (days)",
            BANT_Timing_Score,
            BANT_Weighted_0to3,
            BANT_Score_0to100,
            BANT_Priority_Bucket,
            BANT_Data_Gaps
        FROM opportunities
        WHERE "Company Name" = ? AND "Opportunity Name" = ?
        """
        results = self._execute_query(query, (company_name, opportunity_name))
        return results[0] if results else None
    
    def get_urgency_leads(self, max_days: int = 30) -> List[Dict[str, Any]]:
        """Get leads with urgent timelines."""
        query = """
        SELECT 
            o."Company Name",
            o."Opportunity Name",
            o.Stage,
            o."Total MRC (Est)",
            o.BANT_Score_0to100,
            o.BANT_Priority_Bucket,
            o."Timeline (days)",
            o."Target Close Date",
            o."Next Step",
            o.Budget,
            o.Authority,
            o.Need
        FROM opportunities o
        WHERE o."Timeline (days)" <= ?
        AND o.BANT_Score_0to100 >= 40
        ORDER BY o."Timeline (days)" ASC, o.BANT_Score_0to100 DESC
        """
        return self._execute_query(query, (max_days,))    
    # ==================== WRITE OPERATIONS ====================
    
    def add_opportunity(self, company_name: str, opportunity_name: str, stage: str,
                       total_mrc: float = None, budget: str = None, authority: str = None,
                       need: str = None, timeline_days: int = None, target_close_date: str = None,
                       next_step: str = None) -> bool:
        """Add a new opportunity to opportunities table.
        
        Args:
            company_name: Company name (must exist in accounts)
            opportunity_name: Unique opportunity name
            stage: Sales stage (e.g., 'Discovery', 'Proposal', 'Negotiation')
            total_mrc: Total Monthly Recurring Revenue estimate
            budget: Budget status (e.g., 'Identified', 'Approved')
            authority: Authority status (e.g., 'Confirmed', 'Unknown')
            need: Need level (e.g., 'High', 'Medium', 'Low')
            timeline_days: Timeline in days
            target_close_date: Target close date (YYYY-MM-DD format)
            next_step: Next step description
        
        Returns:
            True if successful, False otherwise
        """
        # Calculate BANT scores
        bant_budget = self._calculate_budget_score(budget)
        bant_authority = self._calculate_authority_score(authority)
        bant_need = self._calculate_need_score(need)
        bant_timing = self._calculate_timing_score(timeline_days)
        
        bant_weighted = (bant_budget + bant_authority + bant_need + bant_timing) / 4
        bant_score_100 = (bant_weighted / 3) * 100
        bant_priority = self._get_priority_bucket(bant_score_100)
        bant_gaps = self._identify_data_gaps(budget, authority, need, timeline_days)
        
        query = """
        INSERT INTO opportunities (
            "Company Name", "Opportunity Name", Stage, "Total MRC (Est)",
            Budget, Authority, Need, "Timeline (days)", "Target Close Date", "Next Step",
            BANT_Budget_Score, BANT_Authority_Score, BANT_Need_Score, BANT_Timing_Score,
            BANT_Weighted_0to3, BANT_Score_0to100, BANT_Priority_Bucket, BANT_Data_Gaps
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        try:
            rows = self._execute_write(query, (
                company_name, opportunity_name, stage, total_mrc,
                budget, authority, need, timeline_days, target_close_date, next_step,
                bant_budget, bant_authority, bant_need, bant_timing,
                bant_weighted, bant_score_100, bant_priority, bant_gaps
            ))
            return rows > 0
        except sqlite3.IntegrityError:
            return False  # Opportunity already exists
    
    def update_opportunity(self, company_name: str, opportunity_name: str, **kwargs) -> bool:
        """Update opportunity information and recalculate BANT scores.
        
        Args:
            company_name: Company name
            opportunity_name: Opportunity name
            **kwargs: Fields to update (stage, total_mrc, budget, authority, need, 
                     timeline_days, target_close_date, next_step)
        
        Returns:
            True if successful, False otherwise
        """
        # Get current values
        current_list = self.get_opportunity_qualification(company_name, opportunity_name)
        if not current_list or len(current_list) == 0:
            return False
        
        current = current_list[0]  # Get first item from list
        
        # Update with new values
        for key, value in kwargs.items():
            if key in current:
                current[key] = value
        
        # Recalculate BANT scores if relevant fields changed
        if any(k in kwargs for k in ['budget', 'authority', 'need', 'timeline_days']):
            bant_budget = self._calculate_budget_score(kwargs.get('budget', current.get('Budget')))
            bant_authority = self._calculate_authority_score(kwargs.get('authority', current.get('Authority')))
            bant_need = self._calculate_need_score(kwargs.get('need', current.get('Need')))
            bant_timing = self._calculate_timing_score(kwargs.get('timeline_days', current.get('Timeline (days)')))
            
            bant_weighted = (bant_budget + bant_authority + bant_need + bant_timing) / 4
            bant_score_100 = (bant_weighted / 3) * 100
            bant_priority = self._get_priority_bucket(bant_score_100)
            bant_gaps = self._identify_data_gaps(
                kwargs.get('budget', current.get('Budget')),
                kwargs.get('authority', current.get('Authority')),
                kwargs.get('need', current.get('Need')),
                kwargs.get('timeline_days', current.get('Timeline (days)'))
            )
            
            kwargs.update({
                'bant_budget_score': bant_budget,
                'bant_authority_score': bant_authority,
                'bant_need_score': bant_need,
                'bant_timing_score': bant_timing,
                'bant_weighted_0to3': bant_weighted,
                'bant_score_0to100': bant_score_100,
                'bant_priority_bucket': bant_priority,
                'bant_data_gaps': bant_gaps
            })
        
        field_mapping = {
            'stage': 'Stage',
            'total_mrc': '"Total MRC (Est)"',
            'budget': 'Budget',
            'authority': 'Authority',
            'need': 'Need',
            'timeline_days': '"Timeline (days)"',
            'target_close_date': '"Target Close Date"',
            'next_step': '"Next Step"',
            'bant_budget_score': 'BANT_Budget_Score',
            'bant_authority_score': 'BANT_Authority_Score',
            'bant_need_score': 'BANT_Need_Score',
            'bant_timing_score': 'BANT_Timing_Score',
            'bant_weighted_0to3': 'BANT_Weighted_0to3',
            'bant_score_0to100': 'BANT_Score_0to100',
            'bant_priority_bucket': 'BANT_Priority_Bucket',
            'bant_data_gaps': 'BANT_Data_Gaps'
        }
        
        updates = []
        values = []
        
        for key, value in kwargs.items():
            if key in field_mapping:
                updates.append(f"{field_mapping[key]} = ?")
                values.append(value)
        
        if not updates:
            return False
        
        values.extend([company_name, opportunity_name])
        query = f'UPDATE opportunities SET {", ".join(updates)} WHERE "Company Name" = ? AND "Opportunity Name" = ?'
        
        rows = self._execute_write(query, tuple(values))
        return rows > 0
    
    # Helper methods for BANT scoring
    def _calculate_budget_score(self, budget: str) -> float:
        """Calculate budget score (0-3)."""
        if not budget:
            return 0
        budget = budget.lower()
        if 'approved' in budget:
            return 3
        elif 'identified' in budget:
            return 2
        elif 'estimated' in budget:
            return 1
        return 0
    
    def _calculate_authority_score(self, authority: str) -> float:
        """Calculate authority score (0-3)."""
        if not authority:
            return 0
        authority = authority.lower()
        if 'confirmed' in authority:
            return 3
        elif 'identified' in authority:
            return 2
        elif 'suspected' in authority:
            return 1
        return 0
    
    def _calculate_need_score(self, need: str) -> float:
        """Calculate need score (0-3)."""
        if not need:
            return 0
        need = need.lower()
        if 'high' in need or 'critical' in need:
            return 3
        elif 'medium' in need or 'moderate' in need:
            return 2
        elif 'low' in need:
            return 1
        return 0
    
    def _calculate_timing_score(self, timeline_days: int) -> float:
        """Calculate timing score (0-3)."""
        if not timeline_days:
            return 0
        if timeline_days <= 30:
            return 3
        elif timeline_days <= 90:
            return 2
        elif timeline_days <= 180:
            return 1
        return 0
    
    def _get_priority_bucket(self, score: float) -> str:
        """Get priority bucket from BANT score."""
        if score >= 66.7:
            return 'A (High)'
        elif score >= 33.3:
            return 'B (Medium)'
        else:
            return 'C (Low)'
    
    def _identify_data_gaps(self, budget: str, authority: str, need: str, timeline: int) -> str:
        """Identify what BANT data is missing."""
        gaps = []
        if not budget or budget.lower() == 'unknown':
            gaps.append('Budget')
        if not authority or authority.lower() == 'unknown':
            gaps.append('Authority')
        if not need or need.lower() == 'unknown':
            gaps.append('Need')
        if not timeline:
            gaps.append('Timeline')
        return ', '.join(gaps) if gaps else ''