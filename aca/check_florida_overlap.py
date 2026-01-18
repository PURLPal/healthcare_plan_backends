#!/usr/bin/env python3
"""
Check what plans are actually shared between HealthSherpa and Database for Florida
"""

import re
import json
import html
import psycopg2
from bs4 import BeautifulSoup

# Extract ALL HealthSherpa Florida plans
html_file = '/Users/andy/DEMOS_FINAL_SPRINT/sample_sites/healthsherpa/33433/all_plans.html'

with open(html_file, 'r', encoding='utf-8') as f:
    html_content = f.read()

soup = BeautifulSoup(html_content, 'html.parser')
elements = soup.find_all(attrs={'data-react-opts': True})
react_data_raw = elements[0].get('data-react-opts')
decoded = html.unescape(react_data_raw)
react_data = json.loads(decoded)

household = react_data['state']['household']
age = household['applicants'][0]['age']

plans = react_data['state']['entities']['insurance_full_plans']
hs_plan_ids = set()
hs_issuers = set()

for plan in plans:
    if isinstance(plan, dict):
        hios_id = plan.get('hios_id', '')
        base_id = hios_id[:14] if len(hios_id) >= 14 else hios_id
        if base_id:
            hs_plan_ids.add(base_id)
        issuer = plan.get('issuer', {})
        if isinstance(issuer, dict):
            hs_issuers.add(issuer.get('name', ''))

print(f"HealthSherpa for ZIP 33433:")
print(f"  Total Plans: {len(hs_plan_ids)}")
print(f"  Issuers: {sorted(hs_issuers)}\n")

# Get ALL database plans
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
        p.issuer_name
    FROM plans p
    JOIN plan_service_areas psa ON p.service_area_id = psa.service_area_id
    JOIN zip_counties zc ON psa.county_fips = zc.county_fips
    WHERE zc.zip_code = '33433'
      AND p.plan_id LIKE '%%01'
""")

db_plan_ids = set()
db_issuers = set()

for row in cur.fetchall():
    db_plan_ids.add(row[0])
    db_issuers.add(row[1])

conn.close()

print(f"Database for ZIP 33433:")
print(f"  Total Plans: {len(db_plan_ids)}")
print(f"  Issuers: {sorted(db_issuers)}\n")

# Find overlap
overlap = hs_plan_ids & db_plan_ids
only_hs = hs_plan_ids - db_plan_ids
only_db = db_plan_ids - hs_plan_ids

print("="*80)
print(f"OVERLAP ANALYSIS:")
print("="*80)
print(f"Plans in BOTH:        {len(overlap)}")
print(f"Only in HealthSherpa: {len(only_hs)}")
print(f"Only in Database:     {len(only_db)}\n")

if overlap:
    print("Overlapping Plan IDs (first 10):")
    for plan_id in sorted(list(overlap))[:10]:
        print(f"  {plan_id}")
else:
    print("❌ NO OVERLAPPING PLANS!")

print("\n" + "="*80)
print("ISSUER COMPARISON:")
print("="*80)
print(f"\nIssuers in HealthSherpa only:")
for issuer in sorted(hs_issuers - db_issuers):
    print(f"  - {issuer}")

print(f"\nIssuers in Database only:")
for issuer in sorted(db_issuers - hs_issuers):
    print(f"  - {issuer}")

print(f"\nIssuers in BOTH:")
for issuer in sorted(hs_issuers & db_issuers):
    print(f"  - {issuer}")
