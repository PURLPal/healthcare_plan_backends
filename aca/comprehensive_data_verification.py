#!/usr/bin/env python3
"""
Comprehensive Data Verification - ALL HealthSherpa fields vs Database
Verifies: Premiums, Deductibles, OOP Max, and ALL 32 benefit categories
"""

import re
import json
import html
import psycopg2
import sys
from bs4 import BeautifulSoup
from collections import defaultdict
from decimal import Decimal

def parse_dollar_value(value):
    """Parse dollar value from string"""
    if not value or value == 'Not Applicable':
        return None
    
    # Remove commas and dollar signs
    cleaned = re.sub(r'[$,]', '', str(value))
    
    try:
        return float(cleaned)
    except (ValueError, AttributeError):
        return None

def extract_complete_healthsherpa_data(zip_code):
    """Extract ALL available data from HealthSherpa"""
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
    
    # Get applicant info
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
        
        # Extract ALL data
        benefits = plan.get('benefits', {}) if isinstance(plan.get('benefits'), dict) else {}
        cost_sharing = plan.get('cost_sharing', {}) if isinstance(plan.get('cost_sharing'), dict) else {}
        
        hs_plans[base_id] = {
            'hios_id': hios_id,
            'name': plan.get('name', ''),
            'issuer': plan.get('issuer', {}).get('name', '') if isinstance(plan.get('issuer'), dict) else '',
            'metal_level': plan.get('metal_level', ''),
            'plan_type': plan.get('plan_type', ''),
            'hsa_eligible': plan.get('hsa_eligible', False),
            'referral_required': plan.get('referral_required_for_specialist', False),
            
            # Financial
            'premium': plan.get('gross_premium'),
            'subsidy': plan.get('premium'),
            
            # Cost Sharing
            'deductible_individual': parse_dollar_value(cost_sharing.get('medical_ded_ind')),
            'deductible_family': parse_dollar_value(cost_sharing.get('medical_ded_fam')),
            'oop_max_individual': parse_dollar_value(cost_sharing.get('medical_moop_ind')),
            'oop_max_family': parse_dollar_value(cost_sharing.get('medical_moop_fam')),
            'drug_ded_individual': cost_sharing.get('drug_ded_ind'),
            'drug_ded_family': cost_sharing.get('drug_ded_fam'),
            'drug_oop_individual': cost_sharing.get('drug_moop_ind'),
            'drug_oop_family': cost_sharing.get('drug_moop_fam'),
            'medical_coinsurance': cost_sharing.get('medical_coins'),
            
            # ALL Benefits (32 categories)
            'benefits': {
                'primary_care': benefits.get('primary_care'),
                'specialist': benefits.get('specialist'),
                'emergency_room': benefits.get('emergency'),
                'urgent_care': benefits.get('urgent_care'),
                'preventative': benefits.get('preventative'),
                'imaging_advanced': benefits.get('imaging_advanced'),
                'imaging_xray': benefits.get('imaging_xray'),
                'lab_services': benefits.get('lab_services'),
                'generic_rx': benefits.get('generic_rx'),
                'preferred_rx': benefits.get('preferred_rx'),
                'non_preferred_rx': benefits.get('non_preferred_rx'),
                'specialty_rx': benefits.get('specialty_rx'),
                'inpatient_facility': benefits.get('inpatient_facility'),
                'inpatient_physician': benefits.get('inpatient_physician'),
                'outpatient_facility': benefits.get('outpatient_facility'),
                'outpatient_physician': benefits.get('outpatient_physician'),
                'outpatient_rehab': benefits.get('outpatient_rehabilitation_services'),
                'mental_health_inpatient': benefits.get('mental_health_inpatient'),
                'mental_health_outpatient': benefits.get('mental_health_outpatient'),
                'substance_abuse_inpatient': benefits.get('substance_abuse_disorder_inpatient'),
                'substance_abuse_outpatient': benefits.get('substance_abuse_disorder_outpatient'),
                'maternity': benefits.get('maternity'),
                'prenatal_postnatal': benefits.get('prenatal_and_postnatal_care'),
                'well_baby': benefits.get('well_baby'),
                'chiropractic': benefits.get('chiropractic'),
                'physical_therapy': benefits.get('phys_occ_therapy'),
                'home_health': benefits.get('home_health_care_services'),
                'hospice': benefits.get('hospice_services'),
                'skilled_nursing': benefits.get('skilled_nursing_facility'),
                'ambulance': benefits.get('ambulance'),
                'other_practitioner': benefits.get('other_practitioner_office_visit'),
            }
        }
    
    return {
        'age': age,
        'tobacco': tobacco,
        'plans': hs_plans,
    }

def get_complete_database_data(zip_code, age):
    """Get complete plan data from database"""
    with open('/Users/andy/aca_overview_test/.db_password', 'r') as f:
        password = f.read().strip()
    
    conn = psycopg2.connect(
        f"host=aca-plans-db.cc98ea006lul.us-east-1.rds.amazonaws.com "
        f"dbname=aca_plans user=aca_admin password={password}"
    )
    cur = conn.cursor()
    
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
        WHERE zc.zip_code = %s
          AND r.age = %s
          AND p.plan_id LIKE '%%01'
    """, (zip_code, age))
    
    db_plans = {}
    
    for row in cur.fetchall():
        base_id = row[0]
        plan_id = row[1]
        plan_attrs = row[8] or {}
        
        # Get benefits
        cur.execute("""
            SELECT benefit_name, is_covered, cost_sharing_details
            FROM benefits
            WHERE plan_id = %s
        """, (plan_id,))
        
        benefits = {}
        for b_row in cur.fetchall():
            benefits[b_row[0]] = {
                'covered': b_row[1],
                'details': b_row[2] if b_row[2] else {}
            }
        
        db_plans[base_id] = {
            'plan_id': plan_id,
            'name': row[2],
            'issuer': row[3],
            'metal_level': row[4],
            'plan_type': row[5],
            'non_tobacco_rate': float(row[6]) if row[6] else None,
            'tobacco_rate': float(row[7]) if row[7] else None,
            'deductible_individual': parse_dollar_value(plan_attrs.get('deductible_individual')),
            'deductible_family': parse_dollar_value(plan_attrs.get('deductible_family')),
            'oop_max_individual': parse_dollar_value(plan_attrs.get('moop_individual')),
            'oop_max_family': parse_dollar_value(plan_attrs.get('moop_family')),
            'hsa_eligible': plan_attrs.get('is_hsa_eligible') == 'Yes',
            'benefits': benefits,
            'attributes': plan_attrs,
        }
    
    conn.close()
    return db_plans

def comprehensive_verification(zip_code):
    """Comprehensive verification of all data points"""
    
    print(f"\n{'='*120}")
    print(f"COMPREHENSIVE DATA VERIFICATION - ZIP {zip_code}")
    print(f"{'='*120}\n")
    
    # Extract HealthSherpa
    print("📥 Extracting HealthSherpa data...")
    hs_data = extract_complete_healthsherpa_data(zip_code)
    
    if not hs_data:
        print(f"❌ Could not extract HealthSherpa data")
        return None
    
    age = hs_data['age']
    tobacco = hs_data['tobacco']
    hs_plans = hs_data['plans']
    
    print(f"   ✓ Extracted {len(hs_plans)} plans")
    print(f"   ✓ Applicant: Age {age}, {'Tobacco' if tobacco else 'Non-Tobacco'}")
    
    # Get database
    print(f"\n📊 Querying database...")
    db_plans = get_complete_database_data(zip_code, age)
    print(f"   ✓ Retrieved {len(db_plans)} plans")
    
    # Compare
    common_ids = set(hs_plans.keys()) & set(db_plans.keys())
    print(f"\n🔍 Comparing {len(common_ids)} common plans...")
    
    # Statistics
    stats = {
        'premium': {'total': 0, 'match': 0, 'diffs': []},
        'deductible_individual': {'total': 0, 'match': 0, 'diffs': []},
        'deductible_family': {'total': 0, 'match': 0, 'diffs': []},
        'oop_max_individual': {'total': 0, 'match': 0, 'diffs': []},
        'oop_max_family': {'total': 0, 'match': 0, 'diffs': []},
        'hsa_eligible': {'total': 0, 'match': 0},
    }
    
    benefit_stats = defaultdict(lambda: {'total': 0, 'hs_has': 0, 'db_has': 0, 'both': 0})
    
    # Detailed sample comparison
    print(f"\n{'='*120}")
    print(f"SAMPLE DETAILED COMPARISON (First 3 Plans)")
    print(f"{'='*120}\n")
    
    for i, base_id in enumerate(sorted(list(common_ids))[:3]):
        hs = hs_plans[base_id]
        db = db_plans[base_id]
        
        print(f"{'─'*120}")
        print(f"Plan {i+1}: {base_id}")
        print(f"Name: {hs['name'][:80]}")
        print(f"Issuer: {hs['issuer'][:50]}")
        print(f"Metal: {hs['metal_level']}, Type: {hs['plan_type']}")
        print(f"{'─'*120}")
        
        # Premium
        hs_prem = hs['premium']
        db_rate = db['tobacco_rate'] if tobacco else db['non_tobacco_rate']
        
        prem_match = abs(hs_prem - db_rate) < 0.50 if (hs_prem and db_rate) else False
        prem_diff = abs(hs_prem - db_rate) if (hs_prem and db_rate) else None
        
        stats['premium']['total'] += 1
        if prem_match:
            stats['premium']['match'] += 1
        if prem_diff is not None:
            stats['premium']['diffs'].append(prem_diff)
        
        status = "✅" if prem_match else "❌"
        print(f"\n💰 PREMIUM: {status}")
        print(f"   HealthSherpa: ${hs_prem:.2f}" if hs_prem else "   HealthSherpa: N/A")
        print(f"   Database:     ${db_rate:.2f}" if db_rate else "   Database:     N/A")
        if prem_diff is not None:
            print(f"   Difference:   ${prem_diff:.2f}")
        
        # Deductibles & OOP Max
        print(f"\n💵 COST SHARING:")
        
        for field, label in [
            ('deductible_individual', 'Deductible (Ind)'),
            ('deductible_family', 'Deductible (Fam)'),
            ('oop_max_individual', 'OOP Max (Ind)'),
            ('oop_max_family', 'OOP Max (Fam)'),
        ]:
            hs_val = hs.get(field)
            db_val = db.get(field)
            
            match = abs(hs_val - db_val) < 1.0 if (hs_val and db_val) else (hs_val is None and db_val is None)
            diff = abs(hs_val - db_val) if (hs_val and db_val) else None
            
            stats[field]['total'] += 1
            if match:
                stats[field]['match'] += 1
            if diff is not None:
                stats[field]['diffs'].append(diff)
            
            status = "✅" if match else "❌"
            hs_str = f"${hs_val:,.0f}" if hs_val else "N/A"
            db_str = f"${db_val:,.0f}" if db_val else "N/A"
            diff_str = f" (diff: ${diff:.0f})" if diff else ""
            
            print(f"   {label:20s}: HS={hs_str:>10s} | DB={db_str:>10s}{diff_str:15s} {status}")
        
        # HSA Eligible
        hs_hsa = hs.get('hsa_eligible', False)
        db_hsa = db.get('hsa_eligible', False)
        hsa_match = hs_hsa == db_hsa
        
        stats['hsa_eligible']['total'] += 1
        if hsa_match:
            stats['hsa_eligible']['match'] += 1
        
        status = "✅" if hsa_match else "❌"
        print(f"   {'HSA Eligible':20s}: HS={str(hs_hsa):>10s} | DB={str(db_hsa):>10s}                {status}")
        
        # Benefits sample (first 10)
        print(f"\n🏥 BENEFITS SAMPLE (10 categories):")
        benefit_sample = [
            'primary_care', 'specialist', 'emergency_room', 'urgent_care', 'preventative',
            'generic_rx', 'inpatient_facility', 'mental_health_outpatient', 'lab_services', 'imaging_advanced'
        ]
        
        for benefit in benefit_sample:
            hs_val = hs['benefits'].get(benefit)
            
            # Try to find in database
            db_val = None
            for db_benefit_name, db_benefit_data in db['benefits'].items():
                if benefit.lower().replace('_', ' ') in db_benefit_name.lower():
                    db_val = "Covered" if db_benefit_data['covered'] else "Not Covered"
                    break
            
            hs_has = hs_val is not None
            db_has = db_val is not None
            
            benefit_stats[benefit]['total'] += 1
            if hs_has:
                benefit_stats[benefit]['hs_has'] += 1
            if db_has:
                benefit_stats[benefit]['db_has'] += 1
            if hs_has and db_has:
                benefit_stats[benefit]['both'] += 1
            
            status = "✅" if (hs_has and db_has) else ("⚠️" if hs_has else "❌")
            hs_str = str(hs_val)[:30] if hs_val else "N/A"
            db_str = str(db_val)[:30] if db_val else "N/A"
            
            print(f"   {benefit:25s}: HS={hs_str:32s} | DB={db_str:32s} {status}")
        
        print()
    
    # Overall Statistics
    print(f"\n{'='*120}")
    print(f"OVERALL VERIFICATION STATISTICS ({len(common_ids)} plans)")
    print(f"{'='*120}\n")
    
    print(f"📊 FINANCIAL DATA:")
    print(f"   {'Field':30s} {'Match Rate':20s} {'Avg Difference':20s}")
    print(f"   {'-'*70}")
    
    for field in ['premium', 'deductible_individual', 'deductible_family', 'oop_max_individual', 'oop_max_family']:
        s = stats[field]
        match_rate = (s['match'] / s['total'] * 100) if s['total'] > 0 else 0
        avg_diff = sum(s['diffs']) / len(s['diffs']) if s['diffs'] else 0
        
        print(f"   {field:30s} {s['match']:4d}/{s['total']:4d} ({match_rate:5.1f}%)  ${avg_diff:>10.2f}")
    
    # HSA
    s = stats['hsa_eligible']
    match_rate = (s['match'] / s['total'] * 100) if s['total'] > 0 else 0
    print(f"   {'hsa_eligible':30s} {s['match']:4d}/{s['total']:4d} ({match_rate:5.1f}%)")
    
    print(f"\n🏥 BENEFITS DATA AVAILABILITY:")
    print(f"   {'Benefit':30s} {'HS Has':15s} {'DB Has':15s} {'Both':15s}")
    print(f"   {'-'*75}")
    
    for benefit in sorted(benefit_stats.keys()):
        s = benefit_stats[benefit]
        hs_pct = (s['hs_has'] / s['total'] * 100) if s['total'] > 0 else 0
        db_pct = (s['db_has'] / s['total'] * 100) if s['total'] > 0 else 0
        both_pct = (s['both'] / s['total'] * 100) if s['total'] > 0 else 0
        
        print(f"   {benefit:30s} {s['hs_has']:3d}/{s['total']:3d} ({hs_pct:5.1f}%)  {s['db_has']:3d}/{s['total']:3d} ({db_pct:5.1f}%)  {s['both']:3d}/{s['total']:3d} ({both_pct:5.1f}%)")
    
    return {
        'zip_code': zip_code,
        'total_plans': len(common_ids),
        'stats': stats,
        'benefit_stats': dict(benefit_stats),
    }

if __name__ == "__main__":
    zip_codes = ['77447', '03031', '43003']
    
    if len(sys.argv) > 1:
        zip_codes = sys.argv[1:]
    
    all_results = []
    
    for zip_code in zip_codes:
        result = comprehensive_verification(zip_code)
        if result:
            all_results.append(result)
            print(f"\n{'#'*120}\n")
