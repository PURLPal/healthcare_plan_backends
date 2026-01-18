#!/usr/bin/env python3
"""
Comprehensive HealthSherpa vs Database Comparison
Compares premiums, deductibles, OOP max, and benefits
"""

import re
import json
import html
import psycopg2
import sys
from bs4 import BeautifulSoup
from collections import defaultdict

def parse_dollar_amount(value):
    """Parse dollar amount from string"""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = re.sub(r'[$,\s]', '', value)
        try:
            return float(cleaned)
        except ValueError:
            return None
    return None

def extract_healthsherpa_data(zip_code):
    """Extract plan data from HealthSherpa HTML using React props"""
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
    
    try:
        react_data = json.loads(decoded)
    except json.JSONDecodeError:
        return None
    
    # Extract age and tobacco status
    age_from_html = None
    tobacco_from_html = None
    try:
        household = react_data['state']['household']
        if 'applicants' in household and len(household['applicants']) > 0:
            applicant = household['applicants'][0]
            age_from_html = applicant.get('age')
            tobacco_from_html = applicant.get('smoker', False)
    except (KeyError, TypeError):
        pass
    
    # Get plan data
    try:
        plans = react_data['state']['entities']['insurance_full_plans']
    except KeyError:
        return None
    
    healthsherpa_plans = {}
    
    for plan in plans:
        if not isinstance(plan, dict):
            continue
        
        hios_id = plan.get('hios_id', '')
        base_id = hios_id[:14] if len(hios_id) >= 14 else hios_id
        
        if not base_id:
            continue
        
        # Premium data
        gross_premium = plan.get('gross_premium')
        premium_dollars = gross_premium if isinstance(gross_premium, (int, float)) else None
        
        # Basic info
        name = plan.get('name', '')
        issuer_data = plan.get('issuer', {})
        issuer_name = issuer_data.get('name', '') if isinstance(issuer_data, dict) else ''
        metal_level = plan.get('metal_level', '')
        plan_type = plan.get('plan_type', '')
        
        # Cost sharing
        cost_sharing = plan.get('cost_sharing', {})
        if isinstance(cost_sharing, dict):
            deductible_ind = parse_dollar_amount(cost_sharing.get('medical_ded_ind'))
            deductible_fam = parse_dollar_amount(cost_sharing.get('medical_ded_fam'))
            oop_max_ind = parse_dollar_amount(cost_sharing.get('medical_moop_ind'))
            oop_max_fam = parse_dollar_amount(cost_sharing.get('medical_moop_fam'))
        else:
            deductible_ind = deductible_fam = oop_max_ind = oop_max_fam = None
        
        # Benefits
        benefits = plan.get('benefits', {})
        pcp_visit = benefits.get('primary_care', '') if isinstance(benefits, dict) else ''
        specialist = benefits.get('specialist', '') if isinstance(benefits, dict) else ''
        generic_rx = benefits.get('generic_rx', '') if isinstance(benefits, dict) else ''
        emergency = benefits.get('emergency', '') if isinstance(benefits, dict) else ''
        
        healthsherpa_plans[base_id] = {
            'hios_id': hios_id,
            'name': name,
            'issuer': issuer_name,
            'metal_level': metal_level,
            'plan_type': plan_type,
            'premium': premium_dollars,
            'deductible_individual': deductible_ind,
            'deductible_family': deductible_fam,
            'oop_max_individual': oop_max_ind,
            'oop_max_family': oop_max_fam,
            'pcp_visit': pcp_visit,
            'specialist': specialist,
            'generic_rx': generic_rx,
            'emergency': emergency,
        }
    
    return {
        'plans': healthsherpa_plans,
        'age': age_from_html,
        'tobacco': tobacco_from_html,
    }

def get_database_data(zip_code, age):
    """Get comprehensive plan data from database"""
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
        ORDER BY p.issuer_name, p.plan_marketing_name
    """, (zip_code, age))
    
    db_plans = {}
    for row in cur.fetchall():
        base_id = row[0]
        plan_attrs = row[8] or {}
        
        # Extract cost sharing from JSONB
        deductible_ind = parse_dollar_amount(plan_attrs.get('deductible_individual'))
        deductible_fam = parse_dollar_amount(plan_attrs.get('deductible_family'))
        oop_max_ind = parse_dollar_amount(plan_attrs.get('oop_max_individual'))
        oop_max_fam = parse_dollar_amount(plan_attrs.get('oop_max_family'))
        
        db_plans[base_id] = {
            'plan_id': row[1],
            'name': row[2],
            'issuer': row[3],
            'metal_level': row[4],
            'plan_type': row[5],
            'non_tobacco_rate': float(row[6]) if row[6] else None,
            'tobacco_rate': float(row[7]) if row[7] else None,
            'deductible_individual': deductible_ind,
            'deductible_family': deductible_fam,
            'oop_max_individual': oop_max_ind,
            'oop_max_family': oop_max_fam,
        }
    
    conn.close()
    return db_plans

def compare_comprehensive(hs_plans, db_plans, tobacco_user):
    """Comprehensive comparison of all data points"""
    common_ids = set(hs_plans.keys()) & set(db_plans.keys())
    
    comparisons = []
    
    for base_id in common_ids:
        hs = hs_plans[base_id]
        db = db_plans[base_id]
        
        # Premium comparison
        hs_premium = hs['premium']
        db_rate = db['tobacco_rate'] if tobacco_user and db['tobacco_rate'] else db['non_tobacco_rate']
        
        premium_match = False
        premium_diff = None
        if hs_premium and db_rate:
            premium_diff = abs(hs_premium - db_rate)
            premium_match = premium_diff < 0.50
        
        # Deductible individual comparison
        hs_ded_ind = hs['deductible_individual']
        db_ded_ind = db['deductible_individual']
        ded_ind_match = False
        ded_ind_diff = None
        if hs_ded_ind and db_ded_ind:
            ded_ind_diff = abs(hs_ded_ind - db_ded_ind)
            ded_ind_match = ded_ind_diff < 1.0
        
        # OOP Max individual comparison
        hs_oop_ind = hs['oop_max_individual']
        db_oop_ind = db['oop_max_individual']
        oop_ind_match = False
        oop_ind_diff = None
        if hs_oop_ind and db_oop_ind:
            oop_ind_diff = abs(hs_oop_ind - db_oop_ind)
            oop_ind_match = oop_ind_diff < 1.0
        
        comparisons.append({
            'base_id': base_id,
            'issuer': hs['issuer'],
            'name': hs['name'],
            'metal_level': hs['metal_level'],
            # Premium
            'hs_premium': hs_premium,
            'db_rate': db_rate,
            'premium_match': premium_match,
            'premium_diff': premium_diff,
            # Deductible
            'hs_ded_ind': hs_ded_ind,
            'db_ded_ind': db_ded_ind,
            'ded_ind_match': ded_ind_match,
            'ded_ind_diff': ded_ind_diff,
            # OOP Max
            'hs_oop_ind': hs_oop_ind,
            'db_oop_ind': db_oop_ind,
            'oop_ind_match': oop_ind_match,
            'oop_ind_diff': oop_ind_diff,
        })
    
    return comparisons

def generate_report(zip_code):
    """Generate comprehensive comparison report for a ZIP code"""
    print(f"\n{'='*120}")
    print(f"COMPREHENSIVE COMPARISON REPORT - ZIP {zip_code}")
    print(f"{'='*120}\n")
    
    # Extract data
    print("📥 Extracting HealthSherpa data...")
    hs_data = extract_healthsherpa_data(zip_code)
    if not hs_data:
        print(f"❌ Could not extract data for ZIP {zip_code}")
        return None
    
    age = hs_data['age']
    tobacco = hs_data['tobacco']
    hs_plans = hs_data['plans']
    
    print(f"   ✓ Extracted {len(hs_plans)} plans")
    print(f"   ✓ Applicant: Age {age}, {'Tobacco User' if tobacco else 'Non-Tobacco'}")
    
    # Get database data
    print(f"\n📊 Querying database...")
    db_plans = get_database_data(zip_code, age)
    print(f"   ✓ Retrieved {len(db_plans)} plans from database")
    
    # Compare
    print(f"\n🔍 Comparing data points...")
    comparisons = compare_comprehensive(hs_plans, db_plans, tobacco)
    print(f"   ✓ Comparing {len(comparisons)} common plans")
    
    # Calculate statistics
    premium_matches = sum(1 for c in comparisons if c['premium_match'])
    ded_matches = sum(1 for c in comparisons if c['ded_ind_match'])
    oop_matches = sum(1 for c in comparisons if c['oop_ind_match'])
    
    premium_diffs = [c['premium_diff'] for c in comparisons if c['premium_diff'] is not None]
    ded_diffs = [c['ded_ind_diff'] for c in comparisons if c['ded_ind_diff'] is not None]
    oop_diffs = [c['oop_ind_diff'] for c in comparisons if c['oop_ind_diff'] is not None]
    
    # Summary stats
    print(f"\n{'='*120}")
    print(f"SUMMARY STATISTICS")
    print(f"{'='*120}\n")
    
    print(f"📊 Total Plans Compared: {len(comparisons)}")
    print(f"👤 Applicant Profile: Age {age}, {'Tobacco User' if tobacco else 'Non-Tobacco'}\n")
    
    print(f"💰 PREMIUM COMPARISON:")
    print(f"   Matches: {premium_matches}/{len(comparisons)} ({premium_matches/len(comparisons)*100:.1f}%)")
    if premium_diffs:
        print(f"   Avg Difference: ${sum(premium_diffs)/len(premium_diffs):.2f}")
        print(f"   Max Difference: ${max(premium_diffs):.2f}")
        print(f"   Min Difference: ${min(premium_diffs):.2f}")
    
    print(f"\n💵 DEDUCTIBLE (Individual) COMPARISON:")
    print(f"   Matches: {ded_matches}/{len([c for c in comparisons if c['ded_ind_diff'] is not None])} ({ded_matches/len([c for c in comparisons if c['ded_ind_diff'] is not None])*100:.1f}%)" if ded_diffs else "   No data")
    if ded_diffs:
        print(f"   Avg Difference: ${sum(ded_diffs)/len(ded_diffs):.2f}")
        print(f"   Max Difference: ${max(ded_diffs):.2f}")
    
    print(f"\n🏥 OUT-OF-POCKET MAX (Individual) COMPARISON:")
    print(f"   Matches: {oop_matches}/{len([c for c in comparisons if c['oop_ind_diff'] is not None])} ({oop_matches/len([c for c in comparisons if c['oop_ind_diff'] is not None])*100:.1f}%)" if oop_diffs else "   No data")
    if oop_diffs:
        print(f"   Avg Difference: ${sum(oop_diffs)/len(oop_diffs):.2f}")
        print(f"   Max Difference: ${max(oop_diffs):.2f}")
    
    # By issuer breakdown
    print(f"\n{'='*120}")
    print(f"ACCURACY BY ISSUER")
    print(f"{'='*120}\n")
    
    issuer_stats = defaultdict(lambda: {'total': 0, 'premium_match': 0, 'ded_match': 0, 'oop_match': 0})
    
    for c in comparisons:
        issuer = c['issuer']
        issuer_stats[issuer]['total'] += 1
        if c['premium_match']:
            issuer_stats[issuer]['premium_match'] += 1
        if c['ded_ind_match']:
            issuer_stats[issuer]['ded_match'] += 1
        if c['oop_ind_match']:
            issuer_stats[issuer]['oop_match'] += 1
    
    for issuer, stats in sorted(issuer_stats.items()):
        print(f"{issuer[:50]:<52} Plans: {stats['total']:3d}  |  Premium: {stats['premium_match']:3d}/{stats['total']:3d} ({stats['premium_match']/stats['total']*100:5.1f}%)")
    
    # Detailed comparison table
    print(f"\n{'='*120}")
    print(f"DETAILED COMPARISON (First 20 Plans)")
    print(f"{'='*120}\n")
    
    print(f"{'Plan ID':<16} {'Issuer':<25} {'HS Prem':<11} {'DB Prem':<11} {'Diff':<10} {'Status':<10}")
    print(f"{'-'*120}")
    
    for i, c in enumerate(comparisons[:20]):
        hs_prem = f"${c['hs_premium']:.2f}" if c['hs_premium'] else "N/A"
        db_prem = f"${c['db_rate']:.2f}" if c['db_rate'] else "N/A"
        diff = f"${c['premium_diff']:.2f}" if c['premium_diff'] is not None else "N/A"
        status = "✅ Match" if c['premium_match'] else f"❌ Off"
        
        print(f"{c['base_id']:<16} {c['issuer'][:24]:<25} {hs_prem:<11} {db_prem:<11} {diff:<10} {status:<10}")
    
    if len(comparisons) > 20:
        print(f"\n... and {len(comparisons) - 20} more plans")
    
    return {
        'zip_code': zip_code,
        'age': age,
        'tobacco': tobacco,
        'total_plans': len(comparisons),
        'premium_matches': premium_matches,
        'premium_match_rate': premium_matches/len(comparisons)*100 if comparisons else 0,
        'avg_premium_diff': sum(premium_diffs)/len(premium_diffs) if premium_diffs else 0,
        'max_premium_diff': max(premium_diffs) if premium_diffs else 0,
        'ded_matches': ded_matches,
        'ded_match_rate': ded_matches/len(ded_diffs)*100 if ded_diffs else 0,
        'oop_matches': oop_matches,
        'oop_match_rate': oop_matches/len(oop_diffs)*100 if oop_diffs else 0,
        'issuer_stats': dict(issuer_stats),
    }

if __name__ == "__main__":
    zip_codes = ['77447', '03031', '33433', '43003', '54414']
    
    if len(sys.argv) > 1:
        zip_codes = sys.argv[1:]
    
    all_results = []
    
    for zip_code in zip_codes:
        result = generate_report(zip_code)
        if result:
            all_results.append(result)
    
    # Overall summary
    if all_results:
        print(f"\n\n{'='*120}")
        print(f"OVERALL SUMMARY ACROSS ALL ZIP CODES")
        print(f"{'='*120}\n")
        
        for r in all_results:
            print(f"ZIP {r['zip_code']} ({r['total_plans']} plans):")
            print(f"  Premium Match Rate: {r['premium_match_rate']:.1f}% ({r['premium_matches']}/{r['total_plans']})")
            print(f"  Avg Difference: ${r['avg_premium_diff']:.2f}")
            print(f"  Max Difference: ${r['max_premium_diff']:.2f}\n")
