#!/usr/bin/env python3
"""
Comprehensive Benefits Comparison: ER, Out-of-Network, Specialist, etc.
Compares HealthSherpa vs Database for all benefit fields
"""

import re
import json
import html
import psycopg2
import sys
from bs4 import BeautifulSoup
from collections import defaultdict

def parse_cost_value(value):
    """Parse cost values like '$30 copay after deductible' or 'No Charge'"""
    if not value or value == 'Not Applicable':
        return None
    
    # Check for "No Charge" or "$0"
    if 'no charge' in str(value).lower() or value == '$0':
        return {'type': 'no_charge', 'display': 'No Charge'}
    
    # Extract copay
    copay_match = re.search(r'\$(\d+(?:,\d{3})*)', str(value))
    if copay_match:
        amount = float(copay_match.group(1).replace(',', ''))
        return {'type': 'copay', 'amount': amount, 'display': value}
    
    # Coinsurance
    if '%' in str(value):
        pct_match = re.search(r'(\d+)%', str(value))
        if pct_match:
            pct = int(pct_match.group(1))
            return {'type': 'coinsurance', 'percent': pct, 'display': value}
    
    return {'type': 'other', 'display': str(value)}

def extract_healthsherpa_benefits(zip_code):
    """Extract comprehensive benefits data from HealthSherpa"""
    html_file = f'/Users/andy/DEMOS_FINAL_SPRINT/sample_sites/healthsherpa/{zip_code}/all_plans.html'
    
    try:
        with open(html_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
    except FileNotFoundError:
        return None
    
    soup = BeautifulSoup(html_content, 'html.parser')
    elements = soup.find_all(attrs={'data-react-opts': True})
    
    if not elements:
        return None
    
    react_data_raw = elements[0].get('data-react-opts')
    decoded = html.unescape(react_data_raw)
    react_data = json.loads(decoded)
    
    # Get age/tobacco
    household = react_data['state']['household']
    age = household['applicants'][0]['age']
    tobacco = household['applicants'][0]['smoker']
    
    plans = react_data['state']['entities']['insurance_full_plans']
    
    hs_plans = {}
    
    for plan in plans:
        if not isinstance(plan, dict):
            continue
        
        hios_id = plan.get('hios_id', '')
        base_id = hios_id[:14]
        
        if not base_id:
            continue
        
        benefits = plan.get('benefits', {}) if isinstance(plan.get('benefits'), dict) else {}
        
        hs_plans[base_id] = {
            'name': plan.get('name', ''),
            'issuer': plan.get('issuer', {}).get('name', '') if isinstance(plan.get('issuer'), dict) else '',
            'metal_level': plan.get('metal_level', ''),
            'premium': plan.get('gross_premium'),
            'benefits': {
                'primary_care': benefits.get('primary_care'),
                'specialist': benefits.get('specialist'),
                'emergency_room': benefits.get('emergency'),
                'urgent_care': benefits.get('urgent_care'),
                'generic_rx': benefits.get('generic_rx'),
                'preferred_brand_rx': benefits.get('preferred_brand_rx'),
                'specialist_rx': benefits.get('specialist_rx'),
                'inpatient_hospital': benefits.get('inpatient_hospital'),
                'outpatient_surgery': benefits.get('outpatient_surgery'),
                'mental_health_outpatient': benefits.get('mental_health_outpatient'),
                'out_of_network_primary': benefits.get('out_of_network_primary'),
                'out_of_network_specialist': benefits.get('out_of_network_specialist'),
                'out_of_network_emergency': benefits.get('out_of_network_emergency'),
            }
        }
    
    return {
        'age': age,
        'tobacco': tobacco,
        'plans': hs_plans,
    }

def get_database_benefits(zip_code, age):
    """Get benefits data from database"""
    with open('/Users/andy/aca_overview_test/.db_password', 'r') as f:
        password = f.read().strip()
    
    conn = psycopg2.connect(
        f"host=aca-plans-db.cc98ea006lul.us-east-1.rds.amazonaws.com "
        f"dbname=aca_plans user=aca_admin password={password}"
    )
    cur = conn.cursor()
    
    # Get plans with benefits
    cur.execute("""
        SELECT DISTINCT
            LEFT(p.plan_id, 14) as base_id,
            p.plan_id,
            p.plan_marketing_name,
            p.issuer_name,
            r.individual_rate,
            r.individual_tobacco_rate
        FROM plans p
        JOIN rates r ON p.plan_id = r.plan_id
        JOIN plan_service_areas psa ON p.service_area_id = psa.service_area_id
        JOIN zip_counties zc ON psa.county_fips = zc.county_fips
        WHERE zc.zip_code = %s
          AND r.age = %s
          AND p.plan_id LIKE '%%01'
    """, (zip_code, age))
    
    plan_rows = cur.fetchall()
    
    # Now get benefits for these plans
    db_plans = {}
    
    for row in plan_rows:
        base_id = row[0]
        plan_id = row[1]
        
        # Get benefits from benefits table
        cur.execute("""
            SELECT
                benefit_name,
                is_covered,
                cost_sharing_details
            FROM benefits
            WHERE plan_id = %s
        """, (plan_id,))
        
        benefits_data = {}
        for benefit_row in cur.fetchall():
            benefit_name = benefit_row[0]
            is_covered = benefit_row[1]
            cost_details = benefit_row[2] or {}
            
            if not is_covered:
                benefits_data[benefit_name] = 'Not Covered'
            elif isinstance(cost_details, dict):
                # Extract cost sharing from JSONB
                copay = cost_details.get('copay_amount')
                coinsurance = cost_details.get('coinsurance_rate')
                display = cost_details.get('display_string')
                
                if display:
                    benefits_data[benefit_name] = display
                elif copay:
                    benefits_data[benefit_name] = f"${copay} copay"
                elif coinsurance:
                    benefits_data[benefit_name] = f"{coinsurance}% coinsurance"
                else:
                    benefits_data[benefit_name] = 'Covered'
            else:
                benefits_data[benefit_name] = 'Covered'
        
        db_plans[base_id] = {
            'plan_id': plan_id,
            'name': row[2],
            'issuer': row[3],
            'non_tobacco_rate': float(row[4]) if row[4] else None,
            'tobacco_rate': float(row[5]) if row[5] else None,
            'benefits': benefits_data,
        }
    
    conn.close()
    return db_plans

def compare_benefits(zip_code):
    """Compare benefits between HealthSherpa and Database"""
    
    print(f"\n{'='*120}")
    print(f"BENEFITS COMPARISON - ZIP {zip_code}")
    print(f"{'='*120}\n")
    
    # Extract HealthSherpa
    print("📥 Extracting HealthSherpa benefits...")
    hs_data = extract_healthsherpa_benefits(zip_code)
    
    if not hs_data:
        print(f"❌ Could not extract HealthSherpa data for ZIP {zip_code}")
        return
    
    age = hs_data['age']
    tobacco = hs_data['tobacco']
    hs_plans = hs_data['plans']
    
    print(f"   ✓ Extracted {len(hs_plans)} plans")
    print(f"   ✓ Applicant: Age {age}, {'Tobacco' if tobacco else 'Non-Tobacco'}")
    
    # Get database
    print(f"\n📊 Querying database benefits...")
    db_plans = get_database_benefits(zip_code, age)
    print(f"   ✓ Retrieved {len(db_plans)} plans with benefits data")
    
    # Compare
    common_ids = set(hs_plans.keys()) & set(db_plans.keys())
    print(f"\n🔍 Comparing {len(common_ids)} common plans...")
    
    # Stats
    benefit_types = [
        'primary_care',
        'specialist',
        'emergency_room',
        'urgent_care',
        'generic_rx',
        'out_of_network_primary',
        'out_of_network_specialist',
    ]
    
    stats = defaultdict(lambda: {'total': 0, 'has_hs': 0, 'has_db': 0, 'both': 0})
    
    # Sample comparisons
    print(f"\n{'='*120}")
    print(f"SAMPLE BENEFIT COMPARISONS (First 5 Plans)")
    print(f"{'='*120}\n")
    
    for i, base_id in enumerate(sorted(list(common_ids))[:5]):
        hs = hs_plans[base_id]
        db = db_plans[base_id]
        
        print(f"Plan {i+1}: {base_id}")
        print(f"  Name: {hs['name'][:70]}")
        print(f"  Issuer: {hs['issuer'][:50]}")
        print(f"  Metal: {hs['metal_level']}")
        
        print(f"\n  {'Benefit':<30} {'HealthSherpa':<35} {'Database':<35}")
        print(f"  {'-'*100}")
        
        for benefit_type in benefit_types:
            hs_value = hs['benefits'].get(benefit_type)
            
            # Map to database benefit names
            db_key_map = {
                'primary_care': 'Primary Care Visit to Treat an Injury or Illness',
                'specialist': 'Specialist Visit',
                'emergency_room': 'Emergency Room Care',
                'urgent_care': 'Urgent Care',
                'generic_rx': 'Generic Drugs',
                'out_of_network_primary': 'Out-of-Network Primary Care',
                'out_of_network_specialist': 'Out-of-Network Specialist',
            }
            
            db_key = db_key_map.get(benefit_type, benefit_type)
            db_value = db['benefits'].get(db_key)
            
            hs_display = str(hs_value) if hs_value else 'N/A'
            db_display = str(db_value) if db_value else 'N/A'
            
            print(f"  {benefit_type:<30} {hs_display[:34]:<35} {db_display[:34]:<35}")
            
            # Track stats
            stats[benefit_type]['total'] += 1
            if hs_value:
                stats[benefit_type]['has_hs'] += 1
            if db_value:
                stats[benefit_type]['has_db'] += 1
            if hs_value and db_value:
                stats[benefit_type]['both'] += 1
        
        print()
    
    # Overall statistics
    print(f"\n{'='*120}")
    print(f"BENEFIT DATA AVAILABILITY STATISTICS")
    print(f"{'='*120}\n")
    
    print(f"{'Benefit Type':<35} {'HS Has Data':<15} {'DB Has Data':<15} {'Both Have':<15}")
    print(f"{'-'*120}")
    
    for benefit_type in benefit_types:
        s = stats[benefit_type]
        hs_pct = (s['has_hs'] / s['total'] * 100) if s['total'] > 0 else 0
        db_pct = (s['has_db'] / s['total'] * 100) if s['total'] > 0 else 0
        both_pct = (s['both'] / s['total'] * 100) if s['total'] > 0 else 0
        
        print(f"{benefit_type:<35} {s['has_hs']:4d}/{s['total']:4d} ({hs_pct:5.1f}%)  "
              f"{s['has_db']:4d}/{s['total']:4d} ({db_pct:5.1f}%)  "
              f"{s['both']:4d}/{s['total']:4d} ({both_pct:5.1f}%)")
    
    return {
        'zip_code': zip_code,
        'total_common': len(common_ids),
        'stats': dict(stats),
    }

if __name__ == "__main__":
    zip_codes = ['77447', '03031', '33433', '43003', '54414']
    
    if len(sys.argv) > 1:
        zip_codes = sys.argv[1:]
    
    for zip_code in zip_codes:
        compare_benefits(zip_code)
