#!/usr/bin/env python3
"""
Extract HealthSherpa plan data using React props method
Following methodology from HEALTHSHERPA_EXTRACTION_METHOD.md
"""

import re
import json
import html
import psycopg2

ZIP_CODE = '77447'
AGE = 62

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

# Read HTML file
html_file = f'/Users/andy/DEMOS_FINAL_SPRINT/sample_sites/healthsherpa/{ZIP_CODE}/all_plans.html'

print("=" * 100)
print(f"EXTRACTING HEALTHSHERPA DATA - ZIP {ZIP_CODE}")
print("Using React Props Method from data-react-opts attribute")
print("=" * 100)

with open(html_file, 'r', encoding='utf-8') as f:
    html_content = f.read()

print(f"\nHTML file size: {len(html_content):,} bytes")

# Find the data-react-opts attribute
# Pattern: data-react-opts="...JSON..."
print("\nSearching for data-react-opts attribute...")

# Try different patterns
patterns = [
    r'data-react-opts=["\']([^"\']+)["\']',  # Single line
    r'data-react-opts=["\']((?:[^"\'\\]|\\.)*)["\']',  # With escaping
]

react_data_raw = None

for pattern in patterns:
    matches = re.findall(pattern, html_content, re.DOTALL)
    if matches:
        print(f"✓ Found {len(matches)} data-react-opts attributes")
        # Take the largest one (likely the main data)
        react_data_raw = max(matches, key=len)
        break

if not react_data_raw:
    print("❌ Could not find data-react-opts attribute")
    print("\nSearching for alternative data attributes...")
    
    # Try other possible attributes
    alt_patterns = [
        r'data-props=["\']([^"\']+)["\']',
        r'data-initial-state=["\']([^"\']+)["\']',
        r'data-state=["\']([^"\']+)["\']',
    ]
    
    for pattern in alt_patterns:
        matches = re.findall(pattern, html_content, re.DOTALL)
        if matches:
            print(f"✓ Found alternative: {pattern}")
            react_data_raw = max(matches, key=len)
            break

if not react_data_raw:
    # Try finding it with BeautifulSoup
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Look for elements with data-react-opts
    elements = soup.find_all(attrs={'data-react-opts': True})
    if elements:
        print(f"✓ Found {len(elements)} elements with data-react-opts via BeautifulSoup")
        react_data_raw = elements[0].get('data-react-opts')

if not react_data_raw:
    print("❌ FAILED: Could not find React data in HTML")
    print("\nDebugging: Searching for common React patterns...")
    
    # Check if there's any React data at all
    if 'react' in html_content.lower():
        print("✓ File contains 'react' references")
    if 'data-' in html_content:
        print("✓ File contains data- attributes")
        # Show first few data attributes
        data_attrs = re.findall(r'data-[\w-]+', html_content)[:10]
        print(f"  Found: {set(data_attrs)}")
    
    exit(1)

print(f"\n✓ Extracted data-react-opts (length: {len(react_data_raw):,} characters)")

# Decode HTML entities
print("\nDecoding HTML entities...")
decoded = html.unescape(react_data_raw)
print(f"✓ Decoded (length: {len(decoded):,} characters)")

# Parse JSON
print("\nParsing JSON...")
try:
    react_data = json.loads(decoded)
    print("✓ Successfully parsed JSON")
except json.JSONDecodeError as e:
    print(f"❌ JSON parsing failed: {e}")
    print(f"\nFirst 500 chars of decoded data:")
    print(decoded[:500])
    exit(1)

# Navigate to plan data
print("\nNavigating to plan data structure...")

# Try different possible paths
possible_paths = [
    ['state', 'entities', 'insurance_full_plans'],
    ['state', 'plans'],
    ['entities', 'insurance_full_plans'],
    ['plans'],
    ['insurance_full_plans'],
    ['components', 'state', 'entities', 'insurance_full_plans'],
]

plan_data = None
used_path = None

for path in possible_paths:
    try:
        current = react_data
        for key in path:
            current = current[key]
        if current and isinstance(current, dict):
            plan_data = current
            used_path = ' -> '.join(path)
            break
    except (KeyError, TypeError):
        continue

if not plan_data:
    print("⚠️  Could not find plan data in expected structure")
    print("\nExploring JSON structure...")
    
    if isinstance(react_data, dict):
        print(f"\nTop-level keys: {list(react_data.keys())}")
        
        # Check state key
        if 'state' in react_data:
            state = react_data['state']
            print(f"\nKeys in 'state': {list(state.keys()) if isinstance(state, dict) else 'not a dict'}")
            
            # Check entities
            if isinstance(state, dict) and 'entities' in state:
                entities = state['entities']
                print(f"\nKeys in 'state.entities': {list(entities.keys()) if isinstance(entities, dict) else 'not a dict'}")
                
                # Try to find plans
                if isinstance(entities, dict):
                    for key in entities.keys():
                        if 'plan' in key.lower():
                            print(f"\n✓ Found plan-related key: '{key}'")
                            print(f"   Type: {type(entities[key])}")
                            if isinstance(entities[key], (dict, list)):
                                print(f"   Length/Size: {len(entities[key])}")
                                plan_data = entities[key]
                                used_path = f"state -> entities -> {key}"
                                break
        
        # Check components
        if not plan_data and 'components' in react_data:
            components = react_data['components']
            print(f"\nKeys in 'components': {list(components.keys()) if isinstance(components, dict) else type(components)}")
    
    if not plan_data:
        print("\n❌ Still could not locate plan data")
        exit(1)

print(f"✓ Found plan data at: {used_path}")
print(f"✓ Number of plans: {len(plan_data)}")

# Extract premium data
print("\n" + "=" * 100)
print("EXTRACTED PLAN DATA FROM HEALTHSHERPA")
print("=" * 100)

healthsherpa_plans = {}

# Handle both list and dict formats
if isinstance(plan_data, list):
    plans_list = plan_data
elif isinstance(plan_data, dict):
    plans_list = list(plan_data.values())
else:
    plans_list = []

for plan in plans_list:
    if not isinstance(plan, dict):
        continue
    
    # Extract base plan ID (14 chars)
    hios_id = plan.get('hios_id', '')
    base_id = hios_id[:14] if len(hios_id) >= 14 else hios_id
    
    # Premium (subsidized - what user pays)
    premium_cents = plan.get('premium')
    premium_dollars = premium_cents / 100.0 if premium_cents else None
    
    # Gross premium (full price before subsidy - THIS is what we compare with DB)
    gross_premium = plan.get('gross_premium')
    gross_premium_dollars = gross_premium if isinstance(gross_premium, (int, float)) else None
    
    # Other details
    name = plan.get('name', '')
    issuer_data = plan.get('issuer', {})
    issuer_name = issuer_data.get('name', '') if isinstance(issuer_data, dict) else ''
    
    # Cost sharing
    cost_sharing = plan.get('cost_sharing', {})
    deductible = cost_sharing.get('medical_ded_ind', '') if isinstance(cost_sharing, dict) else ''
    
    healthsherpa_plans[base_id] = {
        'hios_id': hios_id,
        'name': name,
        'issuer': issuer_name,
        'premium': premium_dollars,
        'gross_premium': gross_premium_dollars,
        'deductible': deductible,
    }

print(f"\nExtracted {len(healthsherpa_plans)} plans with premium data")

# Now compare with database
with open('/Users/andy/aca_overview_test/.db_password', 'r') as f:
    password = f.read().strip()

conn = psycopg2.connect(
    f"host=aca-plans-db.cc98ea006lul.us-east-1.rds.amazonaws.com "
    f"dbname=aca_plans user=aca_admin password={password}"
)
cur = conn.cursor()

# Sample plans to compare
SAMPLE_PLANS = [
    '34826TX0030001',
    '27248TX0010016',
    '47501TX0040004',
    '34826TX0020001',
    '11718TX0140016',
]

print("\n" + "=" * 120)
print(f"COMPARISON: HEALTHSHERPA vs DATABASE (Age {AGE}, Tobacco User)")
print("=" * 120)
print(f"\n{'Plan ID':<18} {'Issuer':<25} {'HS Premium':<13} {'DB Non-Tob':<13} {'DB Tobacco':<13} {'Match':<20}")
print("-" * 120)

for base_id in SAMPLE_PLANS:
    plan_id_01 = base_id + '-01'
    
    # Get database values
    cur.execute("""
        SELECT issuer_name FROM plans WHERE plan_id = %s
    """, (plan_id_01,))
    
    plan_row = cur.fetchone()
    if not plan_row:
        continue
    
    issuer = plan_row[0][:24] if plan_row[0] else "Unknown"
    
    cur.execute("""
        SELECT individual_rate, individual_tobacco_rate
        FROM rates
        WHERE plan_id = %s AND age = %s
    """, (plan_id_01, AGE))
    
    rate_row = cur.fetchone()
    
    if rate_row:
        db_non_tob = float(rate_row[0])
        db_tob = float(rate_row[1]) if rate_row[1] else None
        
        # Get HealthSherpa value (gross_premium is pre-subsidy)
        hs_data = healthsherpa_plans.get(base_id, {})
        hs_premium = hs_data.get('gross_premium')
        
        hs_str = f"${hs_premium:.2f}" if hs_premium else "Not found"
        non_tob_str = f"${db_non_tob:.2f}"
        tob_str = f"${db_tob:.2f}" if db_tob else "N/A"
        
        match = "?"
        if hs_premium:
            diff_non_tob = abs(hs_premium - db_non_tob)
            diff_tob = abs(hs_premium - db_tob) if db_tob else 999999
            
            if diff_non_tob < 0.50:
                match = "✅ Non-Tobacco"
            elif diff_tob < 0.50:
                match = "✅ Tobacco"
            else:
                match = f"❌ Off by ${min(diff_non_tob, diff_tob):.2f}"
        
        print(f"{base_id:<18} {issuer:<25} {hs_str:<13} {non_tob_str:<13} {tob_str:<13} {match:<20}")

conn.close()

print("\n" + "=" * 120)
print("✅ EXTRACTION COMPLETE")
print("=" * 120)
