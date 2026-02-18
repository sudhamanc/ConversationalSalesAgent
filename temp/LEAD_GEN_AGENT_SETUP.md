# Lead Generation Sub-Agent Documentation

This document describes the Lead Gen Sub-Agent created for qualifying leads using BANT methodology and determining sales readiness using the prospecting database.

## Overview

The Lead Gen Agent specializes in lead qualification, BANT scoring, and sales readiness assessment. It evaluates leads based on Budget, Authority, Need, and Timeline (BANT) criteria to help sales teams prioritize opportunities with the highest conversion probability.

## BANT Methodology

### Scoring System
- **Budget (0-3)**: Financial capability and budget approval status
  - 0 = Unknown/No budget
  - 1 = Budget exists but not approved
  - 2 = Budget approved but limited
  - 3 = Budget approved and confirmed

- **Authority (0-3)**: Access to decision makers
  - 0 = Unknown stakeholders
  - 1 = Single party contact
  - 2 = Multi-party engagement
  - 3 = Confirmed economic buyer access

- **Need (0-3)**: Business need intensity
  - 0 = No clear need
  - 1 = Low priority need
  - 2 = Medium priority need
  - 3 = High priority/critical need

- **Timeline (0-3)**: Decision urgency
  - 0 = No timeline (>90 days)
  - 1 = Long timeline (60-90 days)
  - 2 = Medium timeline (30-59 days)
  - 3 = Urgent (<30 days)

### Overall Scoring
- **Weighted Score**: 0-3.0 (average of components)
- **Percentage Score**: 0-100 (weighted score × 33.33)
- **Priority Buckets**:
  - A (High): 66.7-100
  - B (Medium): 50.0-66.6
  - C (Low): 0-49.9

## Files Created

### 1. Sub-Agent Module: `bootstrap_agent/sub_agents/lead_gen/`

#### `__init__.py`
Package initialization file that exports the lead_gen_agent.

#### `qualification_tools.py`
Database interface layer containing the `LeadQualificationDatabase` class with the following methods:

- **`get_opportunity_qualification()`** - Get BANT scores for specific opportunities
- **`get_qualified_leads()`** - Get leads above a score threshold
- **`get_leads_by_stage()`** - Filter leads by sales stage
- **`get_leads_with_gaps()`** - Find leads with incomplete qualification data
- **`get_sales_ready_leads()`** - Get fully qualified, high-priority leads
- **`get_lead_qualification_summary()`** - Pipeline qualification statistics
- **`get_bant_component_analysis()`** - Detailed BANT breakdown for an opportunity
- **`get_urgency_leads()`** - Get leads with urgent timelines

#### `lead_gen_agent.py`
Main agent definition with 7 agent tools:

1. **`qualify_lead`** - Get BANT qualification for a specific lead
   ```python
   qualify_lead("Company 001", "Opp 1-1")
   ```

2. **`assess_sales_readiness`** - Determine if a lead is ready for sales engagement
   ```python
   assess_sales_readiness("Company 001", "Opp 1-1")
   ```
   Returns readiness status:
   - 🟢 SALES READY - HIGH PRIORITY (80-100)
   - 🟢 SALES READY - STANDARD (66.7-79.9)
   - 🟡 MARGINALLY QUALIFIED (50-66.6)
   - 🟠 UNDER-QUALIFIED (33-49.9)
   - 🔴 NOT SALES READY (<33)

3. **`get_qualified_leads`** - Get all qualified leads above a threshold
   ```python
   get_qualified_leads(min_score=60.0, priority="A (High)")
   ```

4. **`identify_qualification_gaps`** - Find leads with incomplete BANT data
   ```python
   identify_qualification_gaps(company_name="Company 002")
   ```

5. **`prioritize_leads`** - Rank leads by qualification and urgency
   ```python
   prioritize_leads(limit=10)
   ```

6. **`get_lead_qualification_summary`** - Pipeline health metrics
   ```python
   get_lead_qualification_summary()
   ```

7. **`get_urgent_leads`** - Leads with critical timelines
   ```python
   get_urgent_leads(max_days=30)
   ```

### 2. Root Agent Integration: `bootstrap_agent/agent.py`

The lead gen agent has been registered with the root orchestrator agent:
- Imported `lead_gen_agent` from the sub_agents module
- Added to the `sub_agents` list
- Updated orchestrator instructions to route qualification/scoring queries to the lead gen agent

### 3. Test Script: `test_lead_gen_agent.py`

Comprehensive test script that verifies:
- Database qualification tools functionality
- Agent tools functionality
- Example queries for each tool

## Agent Capabilities

### 1. Lead Qualification (BANT)
- Complete BANT scoring (0-100 scale)
- Component-level breakdown (Budget, Authority, Need, Timeline)
- Priority bucket classification (A/B/C)
- Data gap identification

### 2. Sales Readiness Assessment
- Readiness status determination
- Conversion probability analysis
- Specific recommendations based on gaps
- Action plans to improve qualification

### 3. Gap Analysis
- Identifies missing qualification data
- Recommends specific discovery activities
- Prioritizes gap-filling actions
- Tracks data quality across pipeline

### 4. Lead Prioritization
- Ranks by BANT score and urgency
- Surfaces sales-ready leads
- Combines multiple factors (score, timeline, stage)
- Provides clear action recommendations

### 5. Pipeline Health Monitoring
- Overall qualification statistics
- Distribution analysis (priority, stage)
- Data quality metrics
- Trend identification

## Usage Examples

### Example 1: Qualify a Specific Lead
```
User: "What is the BANT score for Company 001?"
Agent: Uses qualify_lead("Company 001")
Returns: Complete BANT breakdown with scores and gaps
```

### Example 2: Assess Sales Readiness
```
User: "Is Opp 1-1 at Company 001 ready for sales?"
Agent: Uses assess_sales_readiness("Company 001", "Opp 1-1")
Returns: Readiness status with recommendations
```

### Example 3: Get High-Quality Leads
```
User: "Show me all leads with BANT score above 70"
Agent: Uses get_qualified_leads(min_score=70.0)
Returns: List of qualified leads sorted by score
```

### Example 4: Find Data Gaps
```
User: "Which leads have incomplete qualification?"
Agent: Uses identify_qualification_gaps()
Returns: Leads with missing data and recommended actions
```

### Example 5: Prioritize Pipeline
```
User: "What are my top 10 priority opportunities?"
Agent: Uses prioritize_leads(limit=10)
Returns: Ranked list with urgency indicators and action items
```

### Example 6: Check Urgent Leads
```
User: "Show me urgent deals closing in the next 30 days"
Agent: Uses get_urgent_leads(max_days=30)
Returns: Time-sensitive opportunities requiring immediate attention
```

### Example 7: Pipeline Health Check
```
User: "Give me a summary of our pipeline qualification"
Agent: Uses get_lead_qualification_summary()
Returns: Overall metrics, distribution, and recommendations
```

## Qualification Workflow

### Stage 1: Discovery
- Initial contact established
- Basic need identified
- Timeline unknown or >90 days
- Expected Score: 0-33 (C - Low)

### Stage 2: Qualification
- Budget range confirmed
- Stakeholders mapped
- Need quantified
- Timeline defined (30-90 days)
- Expected Score: 33-66 (B-C)

### Stage 3: Sales Ready
- Budget approved
- Economic buyer engaged
- Clear business case
- Urgent timeline (<30 days)
- Expected Score: 66-100 (A-B - High)

## Data Quality Indicators

### Complete Qualification (No Gaps)
- All BANT components scored 2-3
- Decision-making unit mapped
- Budget and approval process understood
- Timeline tied to business events

### Incomplete Qualification (Has Gaps)
Focus on closing gaps:
- **Budget Gap**: Schedule economic buyer meeting
- **Authority Gap**: Complete stakeholder mapping
- **Need Gap**: Conduct pain point discovery
- **Timeline Gap**: Identify trigger events

## Integration with Discovery Agent

The Lead Gen Agent complements the Discovery Agent:

**Discovery Agent** → Identifies prospects and intent  
**Lead Gen Agent** → Qualifies and prioritizes

Typical workflow:
1. Discovery Agent finds companies with buying signals
2. Discovery Agent identifies decision makers
3. Lead Gen Agent assesses BANT qualification
4. Lead Gen Agent prioritizes by readiness
5. Sales team engages with qualified, prioritized leads

## Known Issues

**ADK 1.20.0 Import Error**: Same compatibility issue as Discovery Agent with the `agent_tool` decorator. Requires fix before agent can run.

## Key Metrics

The agent tracks these critical KPIs:
- **Average BANT Score**: Overall pipeline quality
- **Priority Distribution**: % in A/B/C buckets
- **Data Gap Rate**: % of leads with incomplete qualification
- **Sales Ready Count**: Leads meeting qualification threshold
- **Pipeline Value**: Total $ value by qualification tier

## Best Practices

1. **Qualify Early**: Start BANT discovery in first meetings
2. **Update Continuously**: Refresh scores as new data emerges
3. **Focus on Gaps**: Prioritize closing qualification gaps
4. **Use Urgency**: Combine score with timeline for prioritization
5. **Track Trends**: Monitor average scores over time
6. **Validate Assumptions**: Verify BANT data with multiple stakeholders

## Future Enhancements

Potential additions:
1. Predictive scoring using machine learning
2. Win probability calculations
3. Automated gap-filling recommendations
4. Integration with calendar for timeline tracking
5. Competitive displacement scoring
6. Account-level rollup scoring
7. Historical conversion rate analysis
