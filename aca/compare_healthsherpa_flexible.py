#!/usr/bin/env python3
"""
Flexible HealthSherpa vs Database Comparison Tool
Easily test different ZIP codes, ages, and tobacco statuses
"""

import re
import json
import html
import psycopg2
import sys
from bs4 import BeautifulSoup

# =============================================================================
# CONFIGURATION - Modify these to test different scenarios
# =============================================================================

ZIP_CODE = '77447'
TEST_AGE = 62
TOBACCO_USER = True  # Set to False for non-tobacco comparison
SAMPLE_SIZE = 10  # Number of plans to show in comparison table (0 = all plans)

# =============================================================================

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
        print(f"❌ HTML file not found for ZIP {zip_code}")
        print(f"   Expected: {html_file}")
        return None
    
    # Extract data-react-opts attribute
    soup = BeautifulSoup(html_content, 'html.parser')
    elements = soup.find_all(attrs={'data-react-opts': True})
    
    if not elements:
        print(f"❌ Could not find data-react-opts in HTML for ZIP {zip_code}")
        return None
    
    react_data_raw = elements[0].get('data-react-opts')
    decoded = html.unescape(react_data_raw)
    
    try:
        react_data = json.loads(decoded)
    except json.JSONDecodeError as e:
        print(f"❌ Failed to parse JSON: {e}")
        return None
    
    # Navigate to plan data
    try:
        plans = react_data['state']['entities']['insurance_full_plans']
    except KeyError:
        print(f"❌ Could not find plan data in expected structure")
        return None
    
    # Extract plan details
    healthsherpa_plans = {}
    
    for plan in plans:
        if not isinstance(plan, dict):
            continue
        
        hios_id = plan.get('hios_id', '')
        base_id = hios_id[:14] if len(hios_id) >= 14 else hios_id
        
        if not base_id:
            continue
        
        # Get gross premium (pre-subsidy)
        gross_premium = plan.get('gross_premium')
        premium_dollars = gross_premium if isinstance(gross_premium, (int, float)) else None
        
        # Get subsidized premium for reference
        subsidized_premium = plan.get('premium')
        subsidized_dollars = subsidized_premium if isinstance(subsidized_premium, (int, float)) else None
        
        name = plan.get('name', '')
        issuer_data = plan.get('issuer', {})
        issuer_name = issuer_data.get('name', '') if isinstance(issuer_data, dict) else ''
        metal_level = plan.get('metal_level', '')
        plan_type = plan.get('plan_type', '')
        
        cost_sharing = plan.get('cost_sharing', {})
        deductible = cost_sharing.get('medical_ded_ind', '') if isinstance(cost_sharing, dict) else ''
        
        healthsherpa_plans[base_id] = {
            'hios_id': hios_id,
            'name': name,
            'issuer': issuer_name,
            'metal_level': metal_level,
            'plan_type': plan_type,
            'gross_premium': premium_dollars,
            'subsidized_premium': subsidized_dollars,
            'deductible': deductible,
        }
    
    return healthsherpa_plans

def get_database_rates(zip_code, age, tobacco):
    """Get rates from database for given ZIP, age, and tobacco status"""
    with open('/Users/andy/aca_overview_test/.db_password', 'r') as f:
        password = f.read().strip()
    
    conn = psycopg2.connect(
        f"host=aca-plans-db.cc98ea006lul.us-east-1.rds.amazonaws.com "
        f"dbname=aca_plans user=aca_admin password={password}"
    )
    cur = conn.cursor()
    
    # Get all plans for this ZIP with rates
    cur.execute("""
        SELECT DISTINCT
            LEFT(p.plan_id, 14) as base_id,
            p.plan_id,
            p.plan_marketing_name,
            p.issuer_name,
            p.metal_level,
            p.plan_type,
            r.individual_rate,
            r.individual_tobacco_rate
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
        plan_id = row[1]
        name = row[2]
        issuer = row[3]
        metal_level = row[4]
        plan_type = row[5]
        non_tob_rate = float(row[6]) if row[6] else None
        tob_rate = float(row[7]) if row[7] else None
        
        deductible = ''  # Can add deductible query if needed
        
        db_plans[base_id] = {
            'plan_id': plan_id,
            'name': name,
            'issuer': issuer,
            'metal_level': metal_level,
            'plan_type': plan_type,
            'non_tobacco_rate': non_tob_rate,
            'tobacco_rate': tob_rate,
            'deductible': deductible,
        }
    
    conn.close()
    return db_plans

def compare_plans(healthsherpa_plans, db_plans, tobacco_user):
    """Compare HealthSherpa and database plans"""
    # Find plans in both sources
    common_ids = set(healthsherpa_plans.keys()) & set(db_plans.keys())
    
    if not common_ids:
        print("❌ No common plans found between HealthSherpa and database")
        return
    
    # Create comparison data
    comparisons = []
    
    for base_id in common_ids:
        hs_plan = healthsherpa_plans[base_id]
        db_plan = db_plans[base_id]
        
        hs_premium = hs_plan['gross_premium']
        db_non_tob = db_plan['non_tobacco_rate']
        db_tob = db_plan['tobacco_rate']
        
        # Determine expected rate based on tobacco status
        expected_rate = db_tob if tobacco_user and db_tob else db_non_tob
        
        # Calculate match
        if hs_premium and expected_rate:
            diff = abs(hs_premium - expected_rate)
            match = diff < 0.50
            pct_diff = (diff / expected_rate) * 100 if expected_rate > 0 else 0
        else:
            diff = None
            match = False
            pct_diff = None
        
        comparisons.append({
            'base_id': base_id,
            'issuer': hs_plan['issuer'],
            'name': hs_plan['name'],
            'metal_level': hs_plan['metal_level'],
            'hs_premium': hs_premium,
            'db_non_tob': db_non_tob,
            'db_tob': db_tob,
            'expected_rate': expected_rate,
            'diff': diff,
            'pct_diff': pct_diff,
            'match': match,
        })
    
    # Sort by match status (matches first) then by difference
    comparisons.sort(key=lambda x: (not x['match'], x['diff'] if x['diff'] else 999999))
    
    return comparisons

def print_comparison_table(comparisons, tobacco_user, sample_size=0):
    """Print formatted comparison table"""
    if sample_size > 0:
        comparisons = comparisons[:sample_size]
    
    print("\n" + "=" * 140)
    print(f"COMPARISON TABLE ({len(comparisons)} plans)")
    print("=" * 140)
    print(f"\n{'Plan ID':<16} {'Issuer':<25} {'Metal':<10} {'HS Premium':<12} {'DB Rate':<12} {'Diff':<12} {'Status':<15}")
    print("-" * 140)
    
    match_count = 0
    
    for comp in comparisons:
        base_id = comp['base_id']
        issuer = comp['issuer'][:24]
        metal = comp['metal_level'][:9]
        hs_premium = comp['hs_premium']
        expected = comp['expected_rate']
        diff = comp['diff']
        match = comp['match']
        pct_diff = comp['pct_diff']
        
        hs_str = f"${hs_premium:.2f}" if hs_premium else "N/A"
        exp_str = f"${expected:.2f}" if expected else "N/A"
        
        if match:
            diff_str = "$0.00"
            status = "✅ MATCH"
            match_count += 1
        elif diff is not None:
            diff_str = f"${diff:.2f}"
            status = f"❌ {pct_diff:.1f}% off"
        else:
            diff_str = "N/A"
            status = "⚠️  Missing data"
        
        print(f"{base_id:<16} {issuer:<25} {metal:<10} {hs_str:<12} {exp_str:<12} {diff_str:<12} {status:<15}")
    
    print("\n" + "=" * 140)
    print(f"SUMMARY: {match_count}/{len(comparisons)} plans match ({match_count/len(comparisons)*100:.1f}%)")
    print("=" * 140)
    
    # Calculate statistics
    diffs = [c['diff'] for c in comparisons if c['diff'] is not None]
    if diffs:
        avg_diff = sum(diffs) / len(diffs)
        max_diff = max(diffs)
        print(f"\nAverage difference: ${avg_diff:.2f}")
        print(f"Maximum difference: ${max_diff:.2f}")
    
    # Show by issuer
    issuer_stats = {}
    for comp in comparisons:
        issuer = comp['issuer']
        if issuer not in issuer_stats:
            issuer_stats[issuer] = {'total': 0, 'matches': 0}
        issuer_stats[issuer]['total'] += 1
        if comp['match']:
            issuer_stats[issuer]['matches'] += 1
    
    print("\n" + "-" * 80)
    print("ACCURACY BY ISSUER")
    print("-" * 80)
    for issuer, stats in sorted(issuer_stats.items()):
        pct = (stats['matches'] / stats['total']) * 100
        print(f"{issuer[:40]:<42} {stats['matches']}/{stats['total']} ({pct:.0f}%)")

# =============================================================================
# MAIN EXECUTION
# =============================================================================

if __name__ == "__main__":
    # Allow command line overrides
    if len(sys.argv) > 1:
        ZIP_CODE = sys.argv[1]
    if len(sys.argv) > 2:
        TEST_AGE = int(sys.argv[2])
    if len(sys.argv) > 3:
        TOBACCO_USER = sys.argv[3].lower() in ('true', 'yes', '1', 'tobacco')
    
    print("=" * 140)
    print("HEALTHSHERPA vs DATABASE COMPARISON")
    print("=" * 140)
    print(f"\n📍 ZIP Code:       {ZIP_CODE}")
    print(f"👤 Age:            {TEST_AGE}")
    print(f"🚬 Tobacco User:   {'Yes' if TOBACCO_USER else 'No'}")
    print(f"📊 Sample Size:    {'All plans' if SAMPLE_SIZE == 0 else f'{SAMPLE_SIZE} plans'}")
    print("\n" + "-" * 140)
    
    # Extract HealthSherpa data
    print("\n1️⃣  Extracting data from HealthSherpa HTML...")
    hs_plans = extract_healthsherpa_data(ZIP_CODE)
    
    if not hs_plans:
        print("❌ Failed to extract HealthSherpa data")
        sys.exit(1)
    
    print(f"   ✓ Extracted {len(hs_plans)} plans from HealthSherpa")
    
    # Get database rates
    print("\n2️⃣  Querying database for comparison rates...")
    db_plans = get_database_rates(ZIP_CODE, TEST_AGE, TOBACCO_USER)
    print(f"   ✓ Retrieved {len(db_plans)} plans from database")
    
    # Compare
    print("\n3️⃣  Comparing plan data...")
    comparisons = compare_plans(hs_plans, db_plans, TOBACCO_USER)
    
    if not comparisons:
        print("❌ No plans to compare")
        sys.exit(1)
    
    print(f"   ✓ Found {len(comparisons)} common plans")
    
    # Display results
    print_comparison_table(comparisons, TOBACCO_USER, SAMPLE_SIZE)
    
    print("\n✅ Comparison complete")
    print(f"\n💡 To test different parameters, edit the configuration at the top of this script")
    print(f"   Or run: python3 compare_healthsherpa_flexible.py <ZIP> <AGE> <tobacco|non-tobacco>")
