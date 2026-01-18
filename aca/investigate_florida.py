#!/usr/bin/env python3
"""
Deep dive into Florida premium variance
Check plan ID matching and explore benefits data
"""

import re
import json
import html
import psycopg2
from bs4 import BeautifulSoup

def extract_florida_data():
    """Extract Florida HealthSherpa data"""
    html_file = '/Users/andy/DEMOS_FINAL_SPRINT/sample_sites/healthsherpa/33433/all_plans.html'
    
    with open(html_file, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    soup = BeautifulSoup(html_content, 'html.parser')
    elements = soup.find_all(attrs={'data-react-opts': True})
    
    if not elements:
        return None
    
    react_data_raw = elements[0].get('data-react-opts')
    decoded = html.unescape(react_data_raw)
    react_data = json.loads(decoded)
    
    # Get household info
    household = react_data['state']['household']
    age = household['applicants'][0]['age']
    tobacco = household['applicants'][0]['smoker']
    
    plans = react_data['state']['entities']['insurance_full_plans']
    
    # Extract first 10 plans with full details
    sample_plans = []
    for i, plan in enumerate(plans[:10]):
        if not isinstance(plan, dict):
            continue
        
        hios_id = plan.get('hios_id', '')
        base_id = hios_id[:14]
        
        # Get benefits
        benefits = plan.get('benefits', {})
        
        sample_plans.append({
            'hios_id': hios_id,
            'base_id': base_id,
            'name': plan.get('name'),
            'issuer': plan.get('issuer', {}).get('name') if isinstance(plan.get('issuer'), dict) else '',
            'gross_premium': plan.get('gross_premium'),
            'premium_cents': plan.get('premium'),
            'metal_level': plan.get('metal_level'),
            'plan_type': plan.get('plan_type'),
            'benefits': {
                'primary_care': benefits.get('primary_care') if isinstance(benefits, dict) else None,
                'specialist': benefits.get('specialist') if isinstance(benefits, dict) else None,
                'emergency': benefits.get('emergency') if isinstance(benefits, dict) else None,
                'urgent_care': benefits.get('urgent_care') if isinstance(benefits, dict) else None,
                'generic_rx': benefits.get('generic_rx') if isinstance(benefits, dict) else None,
                'preferred_brand_rx': benefits.get('preferred_brand_rx') if isinstance(benefits, dict) else None,
                'out_of_network_primary': benefits.get('out_of_network_primary') if isinstance(benefits, dict) else None,
                'out_of_network_specialist': benefits.get('out_of_network_specialist') if isinstance(benefits, dict) else None,
            },
            'cost_sharing': plan.get('cost_sharing', {}),
        })
    
    return {
        'age': age,
        'tobacco': tobacco,
        'plans': sample_plans,
    }

def get_database_florida_data():
    """Get Florida database data with benefits"""
    with open('/Users/andy/aca_overview_test/.db_password', 'r') as f:
        password = f.read().strip()
    
    conn = psycopg2.connect(
        f"host=aca-plans-db.cc98ea006lul.us-east-1.rds.amazonaws.com "
        f"dbname=aca_plans user=aca_admin password={password}"
    )
    cur = conn.cursor()
    
    # Get age from HealthSherpa first
    hs_data = extract_florida_data()
    age = hs_data['age']
    
    cur.execute("""
        SELECT DISTINCT
            LEFT(p.plan_id, 14) as base_id,
            p.plan_id,
            p.plan_marketing_name,
            p.issuer_name,
            p.metal_level,
            p.plan_type,
            r.individual_rate,
            r.individual_tobacco_rate,
            p.plan_attributes
        FROM plans p
        JOIN rates r ON p.plan_id = r.plan_id
        JOIN plan_service_areas psa ON p.service_area_id = psa.service_area_id
        JOIN zip_counties zc ON psa.county_fips = zc.county_fips
        WHERE zc.zip_code = '33433'
          AND r.age = %s
          AND p.plan_id LIKE '%%01'
        ORDER BY p.issuer_name, p.plan_marketing_name
        LIMIT 10
    """, (age,))
    
    db_plans = []
    for row in cur.fetchall():
        plan_attrs = row[8] or {}
        
        db_plans.append({
            'base_id': row[0],
            'plan_id': row[1],
            'name': row[2],
            'issuer': row[3],
            'metal_level': row[4],
            'plan_type': row[5],
            'non_tobacco_rate': float(row[6]) if row[6] else None,
            'tobacco_rate': float(row[7]) if row[7] else None,
            'attributes': plan_attrs,
        })
    
    conn.close()
    return db_plans

print("="*120)
print("FLORIDA DEEP DIVE - Plan ID Matching & Benefits Analysis")
print("="*120)

# Extract HealthSherpa data
print("\n📥 Extracting HealthSherpa data...")
hs_data = extract_florida_data()
print(f"   Age: {hs_data['age']}, Tobacco: {hs_data['tobacco']}")
print(f"   Sample plans: {len(hs_data['plans'])}")

# Get database data
print("\n📊 Querying database...")
db_plans = get_database_florida_data()
print(f"   Sample plans: {len(db_plans)}")

# Create lookup
db_lookup = {p['base_id']: p for p in db_plans}

# Compare
print("\n" + "="*120)
print("PLAN ID MATCHING VERIFICATION")
print("="*120)

matched = 0
for hs_plan in hs_data['plans']:
    base_id = hs_plan['base_id']
    if base_id in db_lookup:
        matched += 1
        db_plan = db_lookup[base_id]
        
        print(f"\n✅ Plan ID Match: {base_id}")
        print(f"   HealthSherpa: {hs_plan['name'][:60]}")
        print(f"   Database:     {db_plan['name'][:60]}")
        print(f"   Issuer Match: {hs_plan['issuer'] == db_plan['issuer']} ({hs_plan['issuer']})")
        
        # Premium comparison
        hs_premium = hs_plan['gross_premium']
        db_rate = db_plan['tobacco_rate'] if hs_data['tobacco'] else db_plan['non_tobacco_rate']
        
        if hs_premium and db_rate:
            diff = hs_premium - db_rate
            pct = (diff / db_rate * 100) if db_rate else 0
            print(f"   PREMIUM COMPARISON:")
            print(f"     HealthSherpa: ${hs_premium:.2f}")
            print(f"     Database:     ${db_rate:.2f}")
            print(f"     Difference:   ${diff:.2f} ({pct:+.2f}%)")
        
        # Benefits comparison
        print(f"   BENEFITS FROM HEALTHSHERPA:")
        benefits = hs_plan['benefits']
        for key, value in benefits.items():
            if value:
                print(f"     {key:30s}: {value}")
    else:
        print(f"\n❌ Plan NOT in database: {base_id} - {hs_plan['name'][:60]}")

print(f"\n{'='*120}")
print(f"SUMMARY: {matched}/{len(hs_data['plans'])} plans matched by Plan ID")
print("="*120)

# Show database benefits structure
print("\n" + "="*120)
print("DATABASE BENEFITS STRUCTURE")
print("="*120)

for db_plan in db_plans[:3]:
    print(f"\nPlan: {db_plan['base_id']}")
    print(f"Attributes available: {list(db_plan['attributes'].keys())}")
    
    # Print all attributes
    for key, value in db_plan['attributes'].items():
        if value is not None:
            print(f"  {key}: {value}")
