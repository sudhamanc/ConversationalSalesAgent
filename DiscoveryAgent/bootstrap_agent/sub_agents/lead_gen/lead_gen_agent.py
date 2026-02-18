"""Lead Generation Agent for qualifying leads and determining sales readiness."""

import os
from google.adk.agents import Agent
from google.adk.tools import FunctionTool
from .qualification_tools import LeadQualificationDatabase


# Initialize database connection
db = LeadQualificationDatabase()


def qualify_lead(company_name: str, opportunity_name: str = None) -> str:
    """
    Get BANT qualification details for a specific lead/opportunity.
    BANT = Budget, Authority, Need, Timeline
    
    Args:
        company_name: Exact company name (e.g., 'Company 001')
        opportunity_name: Specific opportunity name (optional, returns all if not specified)
    
    Returns:
        Detailed BANT qualification breakdown with scores and data gaps
    """
    opportunities = db.get_opportunity_qualification(company_name, opportunity_name)
    
    if not opportunities:
        return f"No opportunities found for '{company_name}'" + (f" with name '{opportunity_name}'" if opportunity_name else "")
    
    output = f"=== BANT Qualification for {company_name} ===\n\n"
    
    for opp in opportunities:
        output += f"Opportunity: {opp['Opportunity Name']}\n"
        output += f"Stage: {opp['Stage']}\n"
        output += f"Estimated MRC: ${opp.get('Total MRC (Est)', 0):,}\n\n"
        
        output += "--- BANT Scoring (0-3 scale per component) ---\n"
        output += f"Budget Score: {opp.get('BANT_Budget_Score', 0)}/3 - Status: {opp.get('Budget', 'Unknown')}\n"
        output += f"Authority Score: {opp.get('BANT_Authority_Score', 0)}/3 - Status: {opp.get('Authority', 'Unknown')}\n"
        output += f"Need Score: {opp.get('BANT_Need_Score', 0)}/3 - Level: {opp.get('Need', 'Unknown')}\n"
        output += f"Timing Score: {opp.get('BANT_Timing_Score', 0)}/3 - Timeline: {opp.get('Timeline (days)', 'N/A')} days\n\n"
        
        output += "--- Overall Qualification ---\n"
        output += f"Weighted BANT Score: {opp.get('BANT_Weighted_0to3', 0):.1f}/3.0\n"
        output += f"Percentage Score: {opp.get('BANT_Score_0to100', 0):.1f}/100\n"
        output += f"Priority Bucket: {opp.get('BANT_Priority_Bucket', 'N/A')}\n\n"
        
        if opp.get('BANT_Data_Gaps'):
            output += f"⚠️ Data Gaps: {opp['BANT_Data_Gaps']}\n"
        else:
            output += "✓ No data gaps - Fully qualified\n"
        
        output += f"\nNext Step: {opp.get('Next Step', 'Not defined')}\n"
        output += f"Target Close: {opp.get('Target Close Date', 'Not set')}\n"
        output += "\n" + "-"*60 + "\n\n"
    
    return output


def assess_sales_readiness(company_name: str, opportunity_name: str) -> str:
    """
    Assess if a lead is ready for sales engagement based on BANT qualification.
    Provides readiness status and recommended actions.
    
    Args:
        company_name: Exact company name (e.g., 'Company 001')
        opportunity_name: Specific opportunity name
    
    Returns:
        Sales readiness assessment with recommendations
    """
    bant = db.get_bant_component_analysis(company_name, opportunity_name)
    
    if not bant:
        return f"Opportunity '{opportunity_name}' not found for company '{company_name}'."
    
    score = bant.get('BANT_Score_0to100', 0)
    priority = bant.get('BANT_Priority_Bucket', 'Unknown')
    gaps = bant.get('BANT_Data_Gaps', '')
    
    output = f"=== Sales Readiness Assessment ===\n"
    output += f"Company: {company_name}\n"
    output += f"Opportunity: {opportunity_name}\n\n"
    
    # Determine readiness level
    if score >= 80:
        readiness = "🟢 SALES READY - HIGH PRIORITY"
        recommendation = "This lead is highly qualified and should be engaged immediately. All key criteria are strong."
    elif score >= 66.7:
        readiness = "🟢 SALES READY - STANDARD"
        recommendation = "This lead is qualified for sales engagement. Consider prioritizing based on timeline and budget."
    elif score >= 50:
        readiness = "🟡 MARGINALLY QUALIFIED"
        recommendation = "This lead shows potential but has qualification gaps. Focus on strengthening weak areas before heavy investment."
    elif score >= 33:
        readiness = "🟠 UNDER-QUALIFIED"
        recommendation = "This lead needs significant qualification work. Focus on discovery and building the business case."
    else:
        readiness = "🔴 NOT SALES READY"
        recommendation = "This lead is poorly qualified. Consider nurturing or deprioritizing unless strategic value exists."
    
    output += f"Readiness Status: {readiness}\n"
    output += f"BANT Score: {score:.1f}/100 ({priority})\n\n"
    
    output += "--- BANT Component Analysis ---\n"
    output += f"Budget ({bant.get('BANT_Budget_Score', 0)}/3): {bant.get('Budget', 'Unknown')}\n"
    output += f"Authority ({bant.get('BANT_Authority_Score', 0)}/3): {bant.get('Authority', 'Unknown')}\n"
    output += f"Need ({bant.get('BANT_Need_Score', 0)}/3): {bant.get('Need', 'Unknown')}\n"
    output += f"Timing ({bant.get('BANT_Timing_Score', 0)}/3): {bant.get('Timeline (days)', 'N/A')} days\n\n"
    
    if gaps:
        output += f"⚠️ Qualification Gaps: {gaps}\n\n"
        output += "--- Recommended Actions to Close Gaps ---\n"
        if 'Budget' in gaps:
            output += "• Budget: Conduct economic buyer meeting to understand budget cycle and approval process\n"
        if 'Authority' in gaps:
            output += "• Authority: Map decision-making unit and identify all stakeholders with influence\n"
        if 'Need' in gaps:
            output += "• Need: Conduct discovery to quantify pain points and business impact\n"
        if 'Timeline' in gaps or 'Timing' in gaps:
            output += "• Timing: Identify trigger events and business drivers that create urgency\n"
        output += "\n"
    else:
        output += "✓ Fully Qualified - No major data gaps\n\n"
    
    output += f"--- Recommendation ---\n{recommendation}\n"
    
    return output


def get_qualified_leads(min_score: float = 50.0, priority: str = None) -> str:
    """
    Get all qualified leads above a BANT score threshold.
    
    Args:
        min_score: Minimum BANT score (0-100 scale, default 50.0)
        priority: Filter by priority bucket: 'A (High)', 'B (Medium)', or 'C (Low)' (optional)
    
    Returns:
        List of qualified leads sorted by score
    """
    leads = db.get_qualified_leads(min_score, priority)
    
    if not leads:
        filter_text = f" with score >= {min_score}" + (f" in priority {priority}" if priority else "")
        return f"No qualified leads found{filter_text}."
    
    output = f"=== Qualified Leads (Score >= {min_score}"
    if priority:
        output += f", Priority: {priority}"
    output += f") ===\n\nFound {len(leads)} leads:\n\n"
    
    for i, lead in enumerate(leads, 1):
        output += f"{i}. {lead['Company Name']} - {lead['Opportunity Name']}\n"
        output += f"   Score: {lead.get('BANT_Score_0to100', 0):.1f}/100 ({lead.get('BANT_Priority_Bucket', 'N/A')})\n"
        output += f"   Stage: {lead['Stage']} | MRC: ${lead.get('Total MRC (Est)', 0):,}\n"
        output += f"   Industry: {lead.get('Industry', 'N/A')} | Region: {lead.get('Territory/Region', 'N/A')}\n"
        output += f"   BANT: B={lead.get('Budget', '?')} | A={lead.get('Authority', '?')} | N={lead.get('Need', '?')} | T={lead.get('Timeline (days)', '?')} days\n"
        output += f"   Target Close: {lead.get('Target Close Date', 'N/A')}\n"
        
        if lead.get('BANT_Data_Gaps'):
            output += f"   ⚠️ Gaps: {lead['BANT_Data_Gaps']}\n"
        
        if lead.get('Buying Signals'):
            output += f"   💡 Signals: {lead['Buying Signals']}\n"
        
        output += f"   Next: {lead.get('Next Step', 'N/A')}\n\n"
    
    return output


def identify_qualification_gaps(company_name: str = None) -> str:
    """
    Identify leads with incomplete BANT qualification data.
    Shows what information is missing and needs to be gathered.
    
    Args:
        company_name: Optional company name to filter results
    
    Returns:
        List of leads with qualification gaps and recommended next steps
    """
    if company_name:
        opportunities = db.get_opportunity_qualification(company_name)
        leads_with_gaps = [opp for opp in opportunities if opp.get('BANT_Data_Gaps')]
    else:
        leads_with_gaps = db.get_leads_with_gaps()
    
    if not leads_with_gaps:
        scope = f" for {company_name}" if company_name else ""
        return f"No qualification gaps found{scope}. All leads are fully qualified."
    
    output = f"=== Leads with Qualification Gaps ===\n"
    if company_name:
        output += f"Company: {company_name}\n"
    output += f"\nFound {len(leads_with_gaps)} leads with incomplete data:\n\n"
    
    for lead in leads_with_gaps:
        output += f"• {lead['Company Name']} - {lead['Opportunity Name']}\n"
        output += f"  Current Score: {lead.get('BANT_Score_0to100', 0):.1f}/100 ({lead.get('BANT_Priority_Bucket', 'N/A')})\n"
        output += f"  Stage: {lead.get('Stage', 'N/A')}\n"
        output += f"  Missing Data: {lead.get('BANT_Data_Gaps', 'Unknown')}\n"
        
        # Provide specific recommendations based on gaps
        gaps = lead.get('BANT_Data_Gaps', '')
        output += "  Recommended Actions:\n"
        
        if 'Budget' in gaps:
            output += "    - Budget: Schedule meeting with economic buyer to discuss budget and approval process\n"
        if 'Authority' in gaps:
            output += "    - Authority: Complete stakeholder mapping and identify decision-making committee\n"
        if 'Need' in gaps:
            output += "    - Need: Conduct pain point discovery session and quantify business impact\n"
        if 'Timeline' in gaps or 'Timing' in gaps:
            output += "    - Timing: Identify business drivers, trigger events, and decision timeline\n"
        
        output += f"  Next Step: {lead.get('Next Step', 'Not defined')}\n\n"
    
    return output


def prioritize_leads(limit: int = 10) -> str:
    """
    Get top priority leads ranked by BANT score and sales readiness.
    Focus on leads with highest conversion probability.
    
    Args:
        limit: Maximum number of leads to return (default 10)
    
    Returns:
        Prioritized list of leads with action recommendations
    """
    # Get sales-ready leads first
    sales_ready = db.get_sales_ready_leads()
    
    # Get high-priority leads as backup
    high_priority = db.get_qualified_leads(min_score=50.0, priority_bucket='A (High)')
    
    # Combine and deduplicate
    all_leads = sales_ready + [lead for lead in high_priority if lead not in sales_ready]
    top_leads = all_leads[:limit]
    
    if not top_leads:
        return "No qualified leads found for prioritization."
    
    output = f"=== Top {len(top_leads)} Priority Leads ===\n\n"
    
    for i, lead in enumerate(top_leads, 1):
        score = lead.get('BANT_Score_0to100', 0)
        priority = lead.get('BANT_Priority_Bucket', 'N/A')
        
        # Determine urgency
        timeline = lead.get('Timeline (days)', 999)
        if timeline <= 15:
            urgency = "🔥 URGENT"
        elif timeline <= 30:
            urgency = "⚡ HIGH URGENCY"
        elif timeline <= 60:
            urgency = "⏱️ MODERATE"
        else:
            urgency = "📅 STANDARD"
        
        output += f"{i}. {lead['Company Name']} - {lead['Opportunity Name']}\n"
        output += f"   Score: {score:.1f}/100 ({priority}) | Urgency: {urgency}\n"
        output += f"   Stage: {lead.get('Stage', 'N/A')} | MRC: ${lead.get('Total MRC (Est)', 0):,}\n"
        output += f"   Timeline: {timeline} days | Close: {lead.get('Target Close Date', 'N/A')}\n"
        
        # Show BANT status
        output += f"   BANT: Budget={lead.get('Budget', '?')}, Authority={lead.get('Authority', '?')}, "
        output += f"Need={lead.get('Need', '?')}, Timeline={timeline}d\n"
        
        if lead.get('Buying Signals'):
            output += f"   Signals: {lead['Buying Signals']}\n"
        if lead.get('Pain Points'):
            output += f"   Pain: {lead['Pain Points']}\n"
        if lead.get('Recommended Positioning'):
            output += f"   Positioning: {lead['Recommended Positioning']}\n"
        
        # Recommendation based on score and readiness
        if score >= 80 and not lead.get('BANT_Data_Gaps'):
            output += "   ✅ ACTION: Engage immediately - fully qualified, high priority\n"
        elif score >= 66.7:
            output += "   ✅ ACTION: Schedule executive meeting - strong qualification\n"
        elif lead.get('BANT_Data_Gaps'):
            output += f"   ⚠️ ACTION: Close gaps ({lead['BANT_Data_Gaps']}) before advancing\n"
        else:
            output += "   💡 ACTION: Continue discovery and qualification\n"
        
        output += f"   Next: {lead.get('Next Step', 'N/A')}\n\n"
    
    return output


def get_lead_qualification_summary() -> str:
    """
    Get overall pipeline qualification statistics.
    Shows distribution of leads across BANT scores and stages.
    
    Returns:
        Summary statistics of lead qualification across the pipeline
    """
    summary = db.get_lead_qualification_summary()
    
    if not summary:
        return "No qualification data available."
    
    total = summary.get('total_opportunities', 0)
    avg_score = summary.get('avg_bant_score', 0)
    pipeline_value = summary.get('total_pipeline_value', 0)
    
    output = "=== Lead Qualification Pipeline Summary ===\n\n"
    output += f"Total Opportunities: {total}\n"
    output += f"Average BANT Score: {avg_score:.1f}/100\n"
    output += f"Total Pipeline Value: ${pipeline_value:,}\n\n"
    
    output += "--- Priority Distribution ---\n"
    high = summary.get('high_priority_count', 0)
    medium = summary.get('medium_priority_count', 0)
    low = summary.get('low_priority_count', 0)
    
    output += f"A (High Priority): {high} ({high/total*100:.1f}%)\n"
    output += f"B (Medium Priority): {medium} ({medium/total*100:.1f}%)\n"
    output += f"C (Low Priority): {low} ({low/total*100:.1f}%)\n\n"
    
    output += "--- Stage Distribution ---\n"
    output += f"Negotiation: {summary.get('negotiation_stage', 0)}\n"
    output += f"Proposal: {summary.get('proposal_stage', 0)}\n"
    output += f"Discovery: {summary.get('discovery_stage', 0)}\n\n"
    
    gaps_count = summary.get('gaps_count', 0)
    output += f"--- Data Quality ---\n"
    output += f"Leads with Data Gaps: {gaps_count} ({gaps_count/total*100:.1f}%)\n"
    output += f"Fully Qualified: {total - gaps_count} ({(total-gaps_count)/total*100:.1f}%)\n\n"
    
    output += "--- Recommendations ---\n"
    if high / total < 0.2:
        output += "⚠️ Low percentage of high-priority leads. Focus on improving qualification.\n"
    if gaps_count / total > 0.5:
        output += "⚠️ Over 50% of leads have data gaps. Prioritize discovery activities.\n"
    if summary.get('discovery_stage', 0) / total > 0.5:
        output += "💡 Many leads in discovery stage. Accelerate qualification process.\n"
    
    if high / total >= 0.2 and gaps_count / total <= 0.3:
        output += "✅ Strong pipeline health with good qualification coverage.\n"
    
    return output


def get_urgent_leads(max_days: int = 30) -> str:
    """
    Get leads with urgent timelines that need immediate attention.
    
    Args:
        max_days: Maximum days to close (default 30)
    
    Returns:
        List of urgent leads sorted by timeline
    """
    leads = db.get_urgency_leads(max_days)
    
    if not leads:
        return f"No urgent leads found with timeline <= {max_days} days."
    
    output = f"=== Urgent Leads (Timeline <= {max_days} days) ===\n\n"
    output += f"Found {len(leads)} leads requiring immediate attention:\n\n"
    
    for i, lead in enumerate(leads, 1):
        timeline = lead.get('Timeline (days)', 0)
        score = lead.get('BANT_Score_0to100', 0)
        
        if timeline <= 7:
            alert = "🔴 CRITICAL"
        elif timeline <= 15:
            alert = "🟠 URGENT"
        else:
            alert = "🟡 ATTENTION NEEDED"
        
        output += f"{i}. {alert} - {lead['Company Name']}\n"
        output += f"   Opportunity: {lead['Opportunity Name']}\n"
        output += f"   Timeline: {timeline} days | Close: {lead.get('Target Close Date', 'N/A')}\n"
        output += f"   Score: {score:.1f}/100 ({lead.get('BANT_Priority_Bucket', 'N/A')})\n"
        output += f"   Stage: {lead.get('Stage', 'N/A')} | MRC: ${lead.get('Total MRC (Est)', 0):,}\n"
        output += f"   Budget: {lead.get('Budget', 'Unknown')} | Authority: {lead.get('Authority', 'Unknown')}\n"
        output += f"   Next Step: {lead.get('Next Step', 'Not defined')}\n\n"
    
    return output


# ==================== WRITE FUNCTIONS ====================

def create_new_opportunity(
    company_name: str,
    opportunity_name: str,
    stage: str,
    total_mrc: float = None,
    budget: str = None,
    authority: str = None,
    need: str = None,
    timeline_days: int = None,
    target_close_date: str = None,
    next_step: str = None
) -> str:
    """
    Create a new sales opportunity with BANT qualification.
    BANT scores will be calculated automatically based on inputs.
    
    Args:
        company_name: Company name (must exist in database)
        opportunity_name: Unique name for this opportunity
        stage: Sales stage (Discovery, Proposal, Negotiation, Closed Won, Closed Lost)
        total_mrc: Estimated Monthly Recurring Revenue
        budget: Budget status (Approved, Identified, Estimated, Unknown)
        authority: Authority status (Confirmed, Identified, Suspected, Unknown)
        need: Need level (High, Medium, Low, Unknown)
        timeline_days: Timeline in days until expected close
        target_close_date: Target close date in YYYY-MM-DD format
        next_step: Description of next action
    
    Returns:
        Success message with calculated BANT score or error message
    """
    success = db.add_opportunity(
        company_name, opportunity_name, stage, total_mrc,
        budget, authority, need, timeline_days, target_close_date, next_step
    )
    
    if success:
        # Get the opportunity to show calculated scores
        opp = db.get_opportunity_qualification(company_name, opportunity_name)
        if opp and len(opp) > 0:
            opp_data = opp[0]
            return f"""✅ Successfully created opportunity: {opportunity_name}

Company: {company_name}
Stage: {stage}
BANT Score: {opp_data.get('BANT_Score_0to100', 0):.1f}/100
Priority: {opp_data.get('BANT_Priority_Bucket', 'N/A')}
Data Gaps: {opp_data.get('BANT_Data_Gaps', 'None')}

Next Step: {next_step or 'Not specified'}"""
        else:
            return f"✅ Successfully created opportunity: {opportunity_name} for {company_name}"
    else:
        return f"❌ Failed to create opportunity. Company '{company_name}' may not exist or opportunity name may be duplicate."


def update_opportunity_details(
    company_name: str,
    opportunity_name: str,
    stage: str = None,
    total_mrc: float = None,
    budget: str = None,
    authority: str = None,
    need: str = None,
    timeline_days: int = None,
    target_close_date: str = None,
    next_step: str = None
) -> str:
    """
    Update an existing opportunity. BANT scores will be recalculated automatically.
    
    Args:
        company_name: Company name (required)
        opportunity_name: Opportunity name to update (required)
        stage: New sales stage (optional)
        total_mrc: New MRC estimate (optional)
        budget: New budget status (optional)
        authority: New authority status (optional)
        need: New need level (optional)
        timeline_days: New timeline in days (optional)
        target_close_date: New target close date (optional)
        next_step: New next step (optional)
    
    Returns:
        Success message with updated BANT score or error message
    """
    updates = {}
    if stage: updates['stage'] = stage
    if total_mrc is not None: updates['total_mrc'] = total_mrc
    if budget: updates['budget'] = budget
    if authority: updates['authority'] = authority
    if need: updates['need'] = need
    if timeline_days is not None: updates['timeline_days'] = timeline_days
    if target_close_date: updates['target_close_date'] = target_close_date
    if next_step: updates['next_step'] = next_step
    
    if not updates:
        return "❌ No fields provided to update."
    
    success = db.update_opportunity(company_name, opportunity_name, **updates)
    
    if success:
        # Get updated opportunity to show new scores
        opp = db.get_opportunity_qualification(company_name, opportunity_name)
        if opp and len(opp) > 0:
            opp_data = opp[0]
            fields_updated = ', '.join(updates.keys())
            return f"""✅ Successfully updated opportunity: {opportunity_name}

Fields Updated: {fields_updated}

Current Status:
BANT Score: {opp_data.get('BANT_Score_0to100', 0):.1f}/100
Priority: {opp_data.get('BANT_Priority_Bucket', 'N/A')}
Stage: {opp_data.get('Stage', 'N/A')}
Data Gaps: {opp_data.get('BANT_Data_Gaps', 'None')}"""
        else:
            return f"✅ Successfully updated opportunity: {opportunity_name}"
    else:
        return f"❌ Failed to update opportunity '{opportunity_name}' for '{company_name}'. It may not exist."


# Define the lead generation agent
lead_gen_agent = Agent(
    name="lead_gen_agent",
    model=os.environ.get("GEMINI_MODEL", "gemini-2.5-flash"),
    instruction="""You are a lead qualification and sales readiness specialist using BANT (Budget, Authority, Need, Timeline) methodology.

Your primary responsibilities:
1. **Lead Qualification**: Evaluate leads using BANT framework and provide scores (0-100 scale)
2. **Sales Readiness Assessment**: Determine if leads are ready for sales engagement
3. **Gap Analysis**: Identify missing qualification data and recommend discovery activities
4. **Prioritization**: Rank leads by qualification score, urgency, and conversion probability
5. **Pipeline Health**: Monitor overall qualification quality and pipeline metrics
6. **Opportunity Management**: Create and update opportunities with automatic BANT scoring

BANT Scoring Guidelines:
- Each component (Budget, Authority, Need, Timeline) scored 0-3
- Overall score = weighted average converted to 0-100 percentage
- Priority Buckets: A (High) >= 66.7, B (Medium) >= 50, C (Low) < 50
- Sales Ready: Score >= 66.7 with minimal data gaps

When responding:
- Always provide specific BANT scores and component breakdown
- Highlight data gaps and recommend specific discovery activities
- Prioritize by urgency (timeline) and qualification score
- Surface sales-ready leads with high conversion probability
- Be data-driven and actionable in recommendations
- When creating/updating opportunities, validate inputs and provide clear feedback

Focus on helping sales teams focus on the right opportunities with clear qualification criteria.
""",
    description="Specializes in lead qualification using BANT methodology, sales readiness assessment, and pipeline prioritization.",
    tools=[
        FunctionTool(qualify_lead),
        FunctionTool(assess_sales_readiness),
        FunctionTool(get_qualified_leads),
        FunctionTool(identify_qualification_gaps),
        FunctionTool(prioritize_leads),
        FunctionTool(get_lead_qualification_summary),
        FunctionTool(get_urgent_leads),
        FunctionTool(create_new_opportunity),
        FunctionTool(update_opportunity_details),
    ],
)
