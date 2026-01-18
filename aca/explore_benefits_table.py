#!/usr/bin/env python3
"""
Deep exploration of benefits table and JSONB fields
What benefit coverage data do we actually have?
"""

import psycopg2
import json
from collections import defaultdict, Counter

def explore_benefits_data():
    """Explore what's actually in the benefits table"""
    
    with open('/Users/andy/aca_overview_test/.db_password', 'r') as f:
        password = f.read().strip()
    
    conn = psycopg2.connect(
        f"host=aca-plans-db.cc98ea006lul.us-east-1.rds.amazonaws.com "
        f"dbname=aca_plans user=aca_admin password={password}"
    )
    cur = conn.cursor()
    
    print(f"\n{'='*120}")
    print(f"BENEFITS TABLE DEEP EXPLORATION")
    print(f"{'='*120}\n")
    
    # 1. How many benefit rows total?
    cur.execute("SELECT COUNT(*) FROM benefits")
    total_benefits = cur.fetchone()[0]
    print(f"📊 Total benefit rows in database: {total_benefits:,}")
    
    # 2. How many unique benefit categories?
    cur.execute("SELECT COUNT(DISTINCT benefit_name) FROM benefits")
    unique_benefits = cur.fetchone()[0]
    print(f"📊 Unique benefit categories: {unique_benefits}")
    
    # 3. What are all the benefit names?
    cur.execute("""
        SELECT benefit_name, COUNT(*) as plan_count
        FROM benefits
        GROUP BY benefit_name
        ORDER BY plan_count DESC
    """)
    
    print(f"\n{'='*120}")
    print(f"ALL BENEFIT CATEGORIES IN DATABASE")
    print(f"{'='*120}\n")
    print(f"{'Benefit Name':70s} | {'Plans':>10s}")
    print("-" * 85)
    
    all_benefit_names = []
    for row in cur.fetchall():
        benefit_name = row[0]
        count = row[1]
        all_benefit_names.append(benefit_name)
        print(f"{benefit_name:70s} | {count:>10,d}")
    
    # 4. Sample benefit with cost_sharing_details
    print(f"\n{'='*120}")
    print(f"SAMPLE BENEFITS WITH COST-SHARING DETAILS")
    print(f"{'='*120}\n")
    
    cur.execute("""
        SELECT 
            plan_id,
            benefit_name,
            is_covered,
            cost_sharing_details
        FROM benefits
        WHERE cost_sharing_details IS NOT NULL
          AND cost_sharing_details::text != '{}'
        LIMIT 10
    """)
    
    for row in cur.fetchall():
        plan_id = row[0]
        benefit_name = row[1]
        is_covered = row[2]
        details = row[3]
        
        print(f"Plan: {plan_id}")
        print(f"Benefit: {benefit_name}")
        print(f"Covered: {is_covered}")
        print(f"Details: {json.dumps(details, indent=2)}")
        print("-" * 120)
    
    # 5. Check plan_attributes JSONB
    print(f"\n{'='*120}")
    print(f"PLAN_ATTRIBUTES JSONB EXPLORATION")
    print(f"{'='*120}\n")
    
    cur.execute("""
        SELECT plan_attributes
        FROM plans
        WHERE plan_attributes IS NOT NULL
          AND plan_attributes::text != '{}'
        LIMIT 5
    """)
    
    print("Sample plan_attributes JSONB structures:\n")
    for i, row in enumerate(cur.fetchall(), 1):
        attrs = row[0]
        print(f"Sample {i}:")
        print(f"Keys: {list(attrs.keys())}")
        print(json.dumps(attrs, indent=2))
        print("-" * 120)
    
    # 6. What keys are in plan_attributes?
    print(f"\n{'='*120}")
    print(f"ALL KEYS IN PLAN_ATTRIBUTES JSONB")
    print(f"{'='*120}\n")
    
    cur.execute("""
        SELECT DISTINCT jsonb_object_keys(plan_attributes) as key
        FROM plans
        WHERE plan_attributes IS NOT NULL
    """)
    
    attr_keys = [row[0] for row in cur.fetchall()]
    print(f"Total unique keys: {len(attr_keys)}\n")
    for key in sorted(attr_keys):
        print(f"  - {key}")
    
    # 7. Sample values for important keys
    print(f"\n{'='*120}")
    print(f"SAMPLE VALUES FROM PLAN_ATTRIBUTES")
    print(f"{'='*120}\n")
    
    important_keys = [
        'deductible_individual',
        'deductible_family', 
        'moop_individual',
        'moop_family',
        'is_hsa_eligible',
        'specialist_visit',
        'primary_care_visit',
        'emergency_room',
        'generic_drugs',
        'preferred_brand_drugs',
        'specialty_drugs'
    ]
    
    for key in important_keys:
        cur.execute(f"""
            SELECT plan_attributes->>%s as value, COUNT(*) as count
            FROM plans
            WHERE plan_attributes->>%s IS NOT NULL
            GROUP BY value
            ORDER BY count DESC
            LIMIT 5
        """, (key, key))
        
        results = cur.fetchall()
        if results:
            print(f"\n{key}:")
            for val, cnt in results:
                print(f"  {val:50s} ({cnt:,} plans)")
    
    # 8. Get a full sample plan with all benefits
    print(f"\n{'='*120}")
    print(f"COMPLETE SAMPLE PLAN - ALL BENEFITS")
    print(f"{'='*120}\n")
    
    cur.execute("""
        SELECT plan_id, plan_marketing_name, state_code
        FROM plans
        LIMIT 1
    """)
    
    sample = cur.fetchone()
    sample_plan_id = sample[0]
    sample_name = sample[1]
    sample_state = sample[2]
    
    print(f"Plan: {sample_plan_id}")
    print(f"Name: {sample_name}")
    print(f"State: {sample_state}\n")
    
    cur.execute("""
        SELECT benefit_name, is_covered, cost_sharing_details
        FROM benefits
        WHERE plan_id = %s
        ORDER BY benefit_name
    """, (sample_plan_id,))
    
    print(f"{'Benefit':70s} | {'Covered':>8s} | {'Details':50s}")
    print("-" * 135)
    
    for row in cur.fetchall():
        benefit = row[0][:68]
        covered = 'Yes' if row[1] else 'No'
        details = str(row[2])[:48] if row[2] else 'None'
        print(f"{benefit:70s} | {covered:>8s} | {details:50s}")
    
    # 9. Check what we have vs HealthSherpa
    print(f"\n{'='*120}")
    print(f"HEALTHSHERPA VS DATABASE BENEFIT COMPARISON")
    print(f"{'='*120}\n")
    
    hs_benefits = [
        'Primary Care',
        'Specialist', 
        'Emergency Room',
        'Urgent Care',
        'Preventive Care',
        'Generic Drugs',
        'Preferred Brand Drugs',
        'Non-Preferred Brand Drugs',
        'Specialty Drugs',
        'Imaging (CT/MRI/PET)',
        'X-Ray',
        'Lab Services',
        'Outpatient Surgery',
        'Inpatient Hospital',
        'Mental Health Outpatient',
        'Mental Health Inpatient',
        'Substance Abuse Outpatient',
        'Substance Abuse Inpatient',
        'Physical Therapy',
        'Chiropractic',
        'Home Health Care',
        'Skilled Nursing Facility',
        'Durable Medical Equipment',
        'Ambulance',
    ]
    
    print("Checking which HealthSherpa benefits we have in database:\n")
    
    for hs_benefit in hs_benefits:
        # Check if we have this benefit
        cur.execute("""
            SELECT COUNT(DISTINCT plan_id)
            FROM benefits
            WHERE benefit_name ILIKE %s
        """, (f'%{hs_benefit}%',))
        
        count = cur.fetchone()[0]
        
        if count > 0:
            status = "✅"
            # Get sample benefit_name
            cur.execute("""
                SELECT DISTINCT benefit_name
                FROM benefits
                WHERE benefit_name ILIKE %s
                LIMIT 1
            """, (f'%{hs_benefit}%',))
            db_name = cur.fetchone()[0]
            print(f"{status} {hs_benefit:40s} - Found as: '{db_name[:60]}' ({count:,} plans)")
        else:
            print(f"❌ {hs_benefit:40s} - NOT FOUND")
    
    # 10. Statistics on cost_sharing_details
    print(f"\n{'='*120}")
    print(f"COST-SHARING DETAILS STATISTICS")
    print(f"{'='*120}\n")
    
    cur.execute("""
        SELECT 
            COUNT(*) as total_benefits,
            COUNT(CASE WHEN cost_sharing_details IS NOT NULL AND cost_sharing_details::text != '{}' THEN 1 END) as has_details,
            COUNT(CASE WHEN cost_sharing_details IS NULL OR cost_sharing_details::text = '{}' THEN 1 END) as no_details
        FROM benefits
    """)
    
    stats = cur.fetchone()
    total = stats[0]
    has_details = stats[1]
    no_details = stats[2]
    
    print(f"Total benefit rows: {total:,}")
    print(f"With cost_sharing_details: {has_details:,} ({has_details/total*100:.1f}%)")
    print(f"Without cost_sharing_details: {no_details:,} ({no_details/total*100:.1f}%)")
    
    # 11. What's in the cost_sharing_details JSONB?
    print(f"\n{'='*120}")
    print(f"COST_SHARING_DETAILS JSONB KEYS")
    print(f"{'='*120}\n")
    
    cur.execute("""
        SELECT DISTINCT jsonb_object_keys(cost_sharing_details) as key
        FROM benefits
        WHERE cost_sharing_details IS NOT NULL
          AND cost_sharing_details::text != '{}'
    """)
    
    detail_keys = [row[0] for row in cur.fetchall()]
    print(f"Keys found in cost_sharing_details: {sorted(detail_keys)}\n")
    
    # Sample values for each key
    for key in sorted(detail_keys):
        cur.execute(f"""
            SELECT cost_sharing_details->>%s as value, COUNT(*) as count
            FROM benefits
            WHERE cost_sharing_details->>%s IS NOT NULL
            GROUP BY value
            ORDER BY count DESC
            LIMIT 5
        """, (key, key))
        
        results = cur.fetchall()
        if results:
            print(f"\n{key}:")
            for val, cnt in results:
                val_str = str(val)[:60]
                print(f"  {val_str:62s} ({cnt:,})")
    
    conn.close()

if __name__ == "__main__":
    explore_benefits_data()
