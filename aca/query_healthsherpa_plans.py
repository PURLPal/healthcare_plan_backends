#!/usr/bin/env python3
"""
Query ACA plans using HealthSherpa base IDs (without variant suffixes)
Handles the -00, -01 variant matching automatically
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import json
import sys

# Database connection
DB_HOST = "aca-plans-db.cc98ea006lul.us-east-1.rds.amazonaws.com"
DB_PORT = 5432
DB_NAME = "aca_plans"
DB_USER = "aca_admin"
DB_PASSWORD = "AvRePOWBfVFZyPsKPPG2tV3r"

def get_connection():
    """Get database connection"""
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        cursor_factory=RealDictCursor
    )

def query_plans_by_base_ids(base_plan_ids, one_variant_per_base=True):
    """
    Query plans matching HealthSherpa base IDs
    
    Args:
        base_plan_ids: List of 14-character base plan IDs (without -00, -01 suffix)
        one_variant_per_base: If True, return only first variant per base plan
    
    Returns:
        List of plan dictionaries
    """
    conn = get_connection()
    cur = conn.cursor()
    
    # Create LIKE conditions for each base ID
    like_conditions = ' OR '.join([f"p.plan_id LIKE %s" for _ in base_plan_ids])
    like_params = [f"{base_id}%" for base_id in base_plan_ids]
    
    # Build query with variant handling
    if one_variant_per_base:
        query = f"""
        WITH matched_plans AS (
            SELECT 
                p.*,
                SUBSTRING(p.plan_id, 1, 14) as base_plan_id,
                ROW_NUMBER() OVER (PARTITION BY SUBSTRING(p.plan_id, 1, 14) ORDER BY p.plan_id) as rn
            FROM plans p
            WHERE {like_conditions}
        )
        SELECT 
            plan_id,
            plan_marketing_name,
            metal_level,
            plan_type,
            issuer_name,
            issuer_id,
            service_area_id,
            is_new_plan,
            plan_attributes
        FROM matched_plans
        WHERE rn = 1
        ORDER BY plan_id
        """
    else:
        query = f"""
        SELECT 
            p.plan_id,
            p.plan_marketing_name,
            p.metal_level,
            p.plan_type,
            p.issuer_name,
            p.issuer_id,
            p.service_area_id,
            p.is_new_plan,
            p.plan_attributes
        FROM plans p
        WHERE {like_conditions}
        ORDER BY p.plan_id
        """
    
    cur.execute(query, like_params)
    results = cur.fetchall()
    
    conn.close()
    return [dict(row) for row in results]

def extract_numeric(value):
    """Extract numeric value from string like '$5,000' or '5000'"""
    if not value or value == 'Not Applicable':
        return None
    import re
    cleaned = re.sub(r'[^0-9.]', '', str(value))
    try:
        return float(cleaned) if cleaned else None
    except:
        return None

def find_lowest_moop(base_plan_ids):
    """Find plans with lowest maximum out-of-pocket costs"""
    plans = query_plans_by_base_ids(base_plan_ids)
    
    # Extract MOOP values
    for plan in plans:
        attrs = plan['plan_attributes']
        plan['moop_individual_num'] = extract_numeric(attrs.get('moop_individual'))
        plan['moop_family_num'] = extract_numeric(attrs.get('moop_family'))
    
    # Filter to plans with MOOP data
    valid_plans = [p for p in plans if p['moop_individual_num'] is not None]
    
    # Sort by MOOP
    valid_plans.sort(key=lambda x: x['moop_individual_num'])
    
    return valid_plans

def find_lowest_deductible(base_plan_ids):
    """Find plans with lowest deductibles"""
    plans = query_plans_by_base_ids(base_plan_ids)
    
    # Extract deductible values
    for plan in plans:
        attrs = plan['plan_attributes']
        plan['deductible_individual_num'] = extract_numeric(attrs.get('deductible_individual'))
        plan['deductible_family_num'] = extract_numeric(attrs.get('deductible_family'))
    
    # Filter to plans with deductible data
    valid_plans = [p for p in plans if p['deductible_individual_num'] is not None]
    
    # Sort by deductible
    valid_plans.sort(key=lambda x: x['deductible_individual_num'])
    
    return valid_plans

def summarize_by_metal_level(base_plan_ids):
    """Summarize cost-sharing by metal level"""
    plans = query_plans_by_base_ids(base_plan_ids)
    
    # Extract numeric values
    for plan in plans:
        attrs = plan['plan_attributes']
        plan['deductible_num'] = extract_numeric(attrs.get('deductible_individual'))
        plan['moop_num'] = extract_numeric(attrs.get('moop_individual'))
        plan['hsa_eligible'] = attrs.get('is_hsa_eligible') == 'Yes'
    
    # Group by metal level
    from collections import defaultdict
    by_metal = defaultdict(list)
    
    for plan in plans:
        by_metal[plan['metal_level']].append(plan)
    
    # Calculate statistics
    summary = {}
    for metal_level, metal_plans in by_metal.items():
        deductibles = [p['deductible_num'] for p in metal_plans if p['deductible_num']]
        moops = [p['moop_num'] for p in metal_plans if p['moop_num']]
        hsa_count = sum(1 for p in metal_plans if p['hsa_eligible'])
        
        summary[metal_level] = {
            'plan_count': len(metal_plans),
            'avg_deductible': sum(deductibles) / len(deductibles) if deductibles else None,
            'min_deductible': min(deductibles) if deductibles else None,
            'max_deductible': max(deductibles) if deductibles else None,
            'avg_moop': sum(moops) / len(moops) if moops else None,
            'min_moop': min(moops) if moops else None,
            'max_moop': max(moops) if moops else None,
            'hsa_eligible_count': hsa_count
        }
    
    return summary

def print_plan_summary(plan):
    """Pretty print a plan"""
    attrs = plan['plan_attributes']
    print(f"\n{plan['plan_id']}")
    print(f"  Name: {plan['plan_marketing_name']}")
    print(f"  Issuer: {plan['issuer_name']}")
    print(f"  Metal: {plan['metal_level']} | Type: {plan['plan_type']}")
    print(f"  Deductible: {attrs.get('deductible_individual', 'N/A')}")
    print(f"  Max OOP: {attrs.get('moop_individual', 'N/A')}")
    print(f"  HSA Eligible: {attrs.get('is_hsa_eligible', 'N/A')}")

def main():
    # Example: HealthSherpa plans for ZIP 33433 (subset for demo)
    healthsherpa_plans = [
        "21525FL0020002", "48121FL0070122", "44228FL0040008", "21525FL0020006",
        "44228FL0040005", "48121FL0070051", "48121FL0070107", "21525FL0020001",
        "21525FL0020004", "44228FL0040001", "21525FL0020005", "44228FL0040007",
        "19898FL0340092", "30252FL0070065", "19898FL0340017", "68398FL0090001",
        "68398FL0030058", "19898FL0340016", "21525FL0020003", "54172FL0010010"
    ]
    
    print("=" * 80)
    print("HEALTHSHERPA PLAN ANALYSIS")
    print("=" * 80)
    
    # Query 1: Lowest MOOP
    print("\n" + "=" * 80)
    print("QUERY 1: Plans with Lowest Maximum Out-of-Pocket Costs")
    print("=" * 80)
    
    lowest_moop = find_lowest_moop(healthsherpa_plans)
    print(f"\nTop 10 plans by lowest individual MOOP (from {len(lowest_moop)} with data):")
    
    for i, plan in enumerate(lowest_moop[:10], 1):
        attrs = plan['plan_attributes']
        print(f"\n{i}. {plan['plan_id']}")
        print(f"   Max OOP: {attrs.get('moop_individual')} ({plan['metal_level']})")
        print(f"   Name: {plan['plan_marketing_name'][:60]}")
        print(f"   Issuer: {plan['issuer_name']}")
    
    # Query 2: Lowest Deductible
    print("\n" + "=" * 80)
    print("QUERY 2: Plans with Lowest Deductibles")
    print("=" * 80)
    
    lowest_ded = find_lowest_deductible(healthsherpa_plans)
    print(f"\nTop 10 plans by lowest individual deductible (from {len(lowest_ded)} with data):")
    
    for i, plan in enumerate(lowest_ded[:10], 1):
        attrs = plan['plan_attributes']
        print(f"\n{i}. {plan['plan_id']}")
        print(f"   Deductible: {attrs.get('deductible_individual')} ({plan['metal_level']})")
        print(f"   Max OOP: {attrs.get('moop_individual')}")
        print(f"   Name: {plan['plan_marketing_name'][:60]}")
    
    # Query 3: Summary by Metal Level
    print("\n" + "=" * 80)
    print("QUERY 3: Cost Summary by Metal Level")
    print("=" * 80)
    
    summary = summarize_by_metal_level(healthsherpa_plans)
    
    metal_order = ['Platinum', 'Gold', 'Silver', 'Expanded Bronze', 'Bronze', 'Catastrophic']
    
    for metal in metal_order:
        if metal in summary:
            s = summary[metal]
            print(f"\n{metal}:")
            print(f"  Plans: {s['plan_count']}")
            if s['avg_deductible']:
                print(f"  Deductible Range: ${s['min_deductible']:,.0f} - ${s['max_deductible']:,.0f} (avg: ${s['avg_deductible']:,.0f})")
            if s['avg_moop']:
                print(f"  Max OOP Range: ${s['min_moop']:,.0f} - ${s['max_moop']:,.0f} (avg: ${s['avg_moop']:,.0f})")
            print(f"  HSA Eligible: {s['hsa_eligible_count']}")
    
    print("\n" + "=" * 80)
    print("LIMITATIONS & NEXT STEPS")
    print("=" * 80)
    print("""
✅ Currently Available Queries:
   - Lowest deductibles (in-network tier 1 only)
   - Lowest MOOP (in-network tier 1 only)
   - HSA eligibility
   - Plans by metal level, type, issuer

❌ NOT Yet Available (Need Benefits Table):
   - Out-of-network specialist costs
   - Drug costs (generic, brand, specialty)
   - Primary care copays
   - ER copays
   - Tier 2 cost-sharing

To enable full queries:
1. Download benefits-and-cost-sharing-puf.csv from CMS
2. Update database/load_data.py to load benefits table
3. Reload database with benefits data
4. Use benefits JOIN queries (see QUERY_HEALTHSHERPA_PLANS.sql)
    """)

if __name__ == '__main__':
    main()
