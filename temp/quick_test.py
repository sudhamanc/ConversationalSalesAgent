import sys
sys.path.insert(0, 'bootstrap_agent')
from bootstrap_agent.sub_agents.lead_gen.qualification_tools import LeadQualificationDatabase

db = LeadQualificationDatabase()
summary = db.get_lead_qualification_summary()
print('Total Opportunities:', summary['total_opportunities'])
print('Average BANT Score:', f"{summary['avg_bant_score']:.1f}")
print('High Priority:', summary['high_priority_count'])
print('Medium Priority:', summary['medium_priority_count'])
print('Low Priority:', summary['low_priority_count'])
print('\nDatabase connection successful!')
