#!/usr/bin/env python3
"""
Analyze what unique capabilities our database provides vs HealthSherpa
What can we answer that HealthSherpa cannot?
"""

import psycopg2
import json
from collections import defaultdict

def analyze_database_capabilities():
    """Identify unique database capabilities"""
    
    with open('/Users/andy/aca_overview_test/.db_password', 'r') as f:
        password = f.read().strip()
    
    conn = psycopg2.connect(
        f"host=aca-plans-db.cc98ea006lul.us-east-1.rds.amazonaws.com "
        f"dbname=aca_plans user=aca_admin password={password}"
    )
    cur = conn.cursor()
    
    print(f"\n{'='*120}")
    print(f"DATABASE UNIQUE VALUE ANALYSIS")
    print(f"What can our database answer that HealthSherpa cannot?")
    print(f"{'='*120}\n")
    
    # 1. Age-based premium curves
    print("="*120)
    print("1. AGE-BASED PREMIUM CURVES")
    print("="*120)
    print("\nHealthSherpa: Shows premium for ONE age at a time (requires page reload)")
    print("Our Database: Has premiums for ALL ages (0-120) for every plan\n")
    
    # Get sample plan with all ages
    cur.execute("""
        SELECT p.plan_id, p.plan_marketing_name, r.age, r.individual_rate
        FROM plans p
        JOIN rates r ON p.plan_id = r.plan_id
        WHERE p.plan_id LIKE '11718TX0140016%'
        ORDER BY r.age
        LIMIT 20
    """)
    
    print("Sample: Plan 11718TX0140016 - Community Ultra Select Bronze")
    print(f"{'Age':>5s} | {'Premium':>10s}")
    print("-" * 20)
    for row in cur.fetchall():
        age = row[2]
        rate = row[3]
        print(f"{age:>5d} | ${rate:>9.2f}")
    
    # Show age curve impact
    cur.execute("""
        SELECT 
            MIN(individual_rate) as min_rate,
            MAX(individual_rate) as max_rate,
            MAX(individual_rate) / MIN(individual_rate) as age_ratio
        FROM rates
        WHERE plan_id LIKE '11718TX0140016%'
    """)
    
    row = cur.fetchone()
    print(f"\nAge Curve Impact:")
    print(f"  Youngest premium: ${row[0]:.2f}")
    print(f"  Oldest premium:   ${row[1]:.2f}")
    print(f"  Ratio:            {row[2]:.2f}x (oldest pays {row[2]:.1f}x more)")
    
    print(f"\n🎯 USE CASE: Family with mixed ages can calculate total household premium")
    print(f"             without making multiple HealthSherpa requests\n")
    
    # 2. Geographic coverage analysis
    print("="*120)
    print("2. GEOGRAPHIC COVERAGE & SERVICE AREAS")
    print("="*120)
    print("\nHealthSherpa: Shows plans for ONE ZIP at a time")
    print("Our Database: Can query which ZIPs a plan covers, or all plans in a county/state\n")
    
    # Plans per county
    cur.execute("""
        SELECT 
            c.county_name,
            c.state_code,
            COUNT(DISTINCT p.plan_id) as plan_count
        FROM plans p
        JOIN plan_service_areas psa ON p.service_area_id = psa.service_area_id
        JOIN counties c ON psa.county_fips = c.county_fips
        WHERE c.state_code = 'TX'
        GROUP BY c.county_name, c.state_code
        ORDER BY plan_count DESC
        LIMIT 10
    """)
    
    print("Sample: Texas Counties - Plan Availability")
    print(f"{'County':30s} | {'Plans Available':>15s}")
    print("-" * 50)
    for row in cur.fetchall():
        print(f"{row[0]:30s} | {row[2]:>15d}")
    
    print(f"\n🎯 USE CASE: 'Show me all plans available in Harris County'")
    print(f"             'Which counties does this plan cover?'")
    print(f"             'Compare plan availability between counties'\n")
    
    # 3. Cross-ZIP comparisons
    print("="*120)
    print("3. CROSS-ZIP & RATING AREA ANALYSIS")
    print("="*120)
    print("\nHealthSherpa: One ZIP at a time, no comparison capability")
    print("Our Database: Compare premiums across ZIPs for same plan\n")
    
    # Same plan, different ZIPs
    cur.execute("""
        SELECT DISTINCT
            zc.zip_code,
            c.county_name,
            r.individual_rate
        FROM rates r
        JOIN plans p ON r.plan_id = p.plan_id
        JOIN plan_service_areas psa ON p.service_area_id = psa.service_area_id
        JOIN zip_counties zc ON psa.county_fips = zc.county_fips
        JOIN counties c ON zc.county_fips = c.county_fips
        WHERE p.plan_id LIKE '11718TX0140016%'
          AND r.age = 40
          AND zc.zip_code IN ('77002', '77447', '77459', '77494')
        ORDER BY zc.zip_code
    """)
    
    print("Sample: Same Plan (Community Bronze), Age 40, Different Houston-area ZIPs")
    print(f"{'ZIP':>10s} | {'County':25s} | {'Premium':>10s}")
    print("-" * 50)
    rates_by_zip = {}
    for row in cur.fetchall():
        rates_by_zip[row[0]] = row[2]
        print(f"{row[0]:>10s} | {row[1]:25s} | ${row[2]:>9.2f}")
    
    if len(set(rates_by_zip.values())) > 1:
        print(f"\n⚠️  SAME PLAN, DIFFERENT PRICES by ZIP/rating area")
    else:
        print(f"\n✅ Same price across all ZIPs (same rating area)")
    
    print(f"\n🎯 USE CASE: 'Is this plan cheaper in the next ZIP code?'")
    print(f"             'Rating area analysis'\n")
    
    # 4. Issuer analysis
    print("="*120)
    print("4. ISSUER & MARKET ANALYSIS")
    print("="*120)
    print("\nHealthSherpa: Shows issuers for displayed plans only")
    print("Our Database: Complete issuer market presence, plan counts, pricing strategies\n")
    
    cur.execute("""
        SELECT 
            issuer_name,
            COUNT(DISTINCT plan_id) as plan_count,
            COUNT(DISTINCT metal_level) as metal_levels,
            COUNT(DISTINCT plan_type) as plan_types
        FROM plans
        WHERE state_code = 'TX'
        GROUP BY issuer_name
        ORDER BY plan_count DESC
    """)
    
    print("Sample: Texas Issuer Market Presence")
    print(f"{'Issuer':40s} | {'Plans':>8s} | {'Metals':>8s} | {'Types':>8s}")
    print("-" * 75)
    for row in cur.fetchall()[:10]:
        print(f"{row[0]:40s} | {row[1]:>8d} | {row[2]:>8d} | {row[3]:>8d}")
    
    print(f"\n🎯 USE CASE: 'Which insurers have the most options?'")
    print(f"             'Show me all Blue Cross plans in Texas'\n")
    
    # 5. Plan attribute queries
    print("="*120)
    print("5. STRUCTURED PLAN ATTRIBUTES")
    print("="*120)
    print("\nHealthSherpa: Attributes embedded in display, not queryable")
    print("Our Database: Structured JSONB attributes for complex queries\n")
    
    cur.execute("""
        SELECT 
            plan_id,
            plan_marketing_name,
            REPLACE(REPLACE(TRIM(plan_attributes->>'deductible_individual'), '$', ''), ',', '')::numeric as deductible,
            REPLACE(REPLACE(TRIM(plan_attributes->>'moop_individual'), '$', ''), ',', '')::numeric as oop_max,
            (plan_attributes->>'is_hsa_eligible') as hsa
        FROM plans
        WHERE state_code = 'TX'
          AND (plan_attributes->>'is_hsa_eligible') = 'Yes'
          AND plan_attributes->>'deductible_individual' IS NOT NULL
          AND TRIM(plan_attributes->>'deductible_individual') != ''
          AND REPLACE(REPLACE(TRIM(plan_attributes->>'deductible_individual'), '$', ''), ',', '')::numeric < 5000
        ORDER BY REPLACE(REPLACE(TRIM(plan_attributes->>'deductible_individual'), '$', ''), ',', '')::numeric
        LIMIT 10
    """)
    
    print("Sample Query: 'HSA-eligible plans with deductible < $5,000'")
    print(f"{'Plan ID':16s} | {'Deductible':>12s} | {'OOP Max':>12s}")
    print("-" * 45)
    for row in cur.fetchall():
        ded = row[2] if row[2] else 0
        oop = row[3] if row[3] else 0
        print(f"{row[0][:14]:16s} | ${ded:>11,.0f} | ${oop:>11,.0f}")
    
    print(f"\n🎯 USE CASE: 'Show HSA plans under $5k deductible'")
    print(f"             'Plans with zero deductible for primary care'")
    print(f"             'Low OOP max plans for chronic conditions'\n")
    
    # 6. Bulk analysis capabilities
    print("="*120)
    print("6. BULK ANALYSIS & STATISTICS")
    print("="*120)
    print("\nHealthSherpa: Manual comparison, one page at a time")
    print("Our Database: Statistical analysis across thousands of plans\n")
    
    cur.execute("""
        SELECT 
            state_code,
            metal_level,
            COUNT(*) as plans,
            AVG((SELECT individual_rate FROM rates WHERE rates.plan_id = plans.plan_id AND age = 40)) as avg_premium_40,
            AVG(
                CASE 
                    WHEN plan_attributes->>'deductible_individual' IS NOT NULL 
                     AND TRIM(plan_attributes->>'deductible_individual') != ''
                    THEN REPLACE(REPLACE(TRIM(plan_attributes->>'deductible_individual'), '$', ''), ',', '')::numeric
                    ELSE NULL
                END
            ) as avg_deductible
        FROM plans
        WHERE metal_level IN ('Bronze', 'Silver', 'Gold', 'Platinum')
        GROUP BY state_code, metal_level
        ORDER BY state_code, 
                 CASE metal_level 
                    WHEN 'Bronze' THEN 1 
                    WHEN 'Silver' THEN 2 
                    WHEN 'Gold' THEN 3 
                    WHEN 'Platinum' THEN 4 
                 END
    """)
    
    print("Sample: Average Premiums & Deductibles by State & Metal Level (Age 40)")
    print(f"{'State':>6s} | {'Metal':12s} | {'Plans':>6s} | {'Avg Premium':>13s} | {'Avg Deductible':>15s}")
    print("-" * 70)
    for row in cur.fetchall()[:15]:
        avg_prem = row[3] if row[3] else 0
        avg_ded = row[4] if row[4] else 0
        print(f"{row[0]:>6s} | {row[1]:12s} | {row[2]:>6d} | ${avg_prem:>12.2f} | ${avg_ded:>14,.0f}")
    
    print(f"\n🎯 USE CASE: 'What's the average Silver plan premium in Texas?'")
    print(f"             'How do Bronze deductibles compare across states?'")
    print(f"             'Market trend analysis'\n")
    
    # 7. Service area & network mapping
    print("="*120)
    print("7. SERVICE AREA MAPPING")
    print("="*120)
    print("\nHealthSherpa: No visibility into service area structure")
    print("Our Database: Complete service area to county mappings\n")
    
    cur.execute("""
        SELECT 
            sa.service_area_id,
            sa.service_area_name,
            COUNT(DISTINCT psa.county_fips) as counties_covered,
            COUNT(DISTINCT p.plan_id) as plans_in_area
        FROM service_areas sa
        LEFT JOIN plan_service_areas psa ON sa.service_area_id = psa.service_area_id
        LEFT JOIN plans p ON sa.service_area_id = p.service_area_id
        WHERE sa.state_code = 'TX'
        GROUP BY sa.service_area_id, sa.service_area_name
        ORDER BY counties_covered DESC
        LIMIT 10
    """)
    
    print("Sample: Texas Service Areas")
    print(f"{'Service Area ID':20s} | {'Counties':>10s} | {'Plans':>8s}")
    print("-" * 45)
    for row in cur.fetchall():
        print(f"{row[0]:20s} | {row[2]:>10d} | {row[3]:>8d}")
    
    print(f"\n🎯 USE CASE: 'Which service area has most plans?'")
    print(f"             'Geographic coverage optimization'\n")
    
    # Summary
    print("="*120)
    print("SUMMARY: DATABASE UNIQUE CAPABILITIES")
    print("="*120)
    
    capabilities = [
        ("Age Curves", "All ages for any plan instantly", "Single age per request"),
        ("Geographic Analysis", "All ZIPs/counties at once", "One ZIP at a time"),
        ("Cross-ZIP Comparison", "Compare same plan across areas", "Not possible"),
        ("Issuer Analysis", "Full market presence data", "Limited to current view"),
        ("Complex Queries", "Filter by any attribute combination", "Basic filtering only"),
        ("Bulk Statistics", "Analyze thousands of plans", "Manual comparison"),
        ("Service Areas", "Complete coverage mapping", "No visibility"),
        ("Historical/Bulk Export", "Can export all data", "Manual screen scraping"),
        ("API Integration", "Programmatic access", "Web UI only"),
        ("Rating Area Analysis", "Premium variation by area", "Not visible"),
    ]
    
    print(f"\n{'Capability':25s} | {'Our Database':35s} | {'HealthSherpa':30s}")
    print("-" * 95)
    for cap, db_val, hs_val in capabilities:
        print(f"{cap:25s} | {db_val:35s} | {hs_val:30s}")
    
    print("\n" + "="*120)
    print("CONCLUSION")
    print("="*120)
    print("""
HealthSherpa: Great for individual plan shopping (user-friendly UI)
Our Database: Great for:
  • API/programmatic access
  • Bulk analysis and statistics
  • Geographic/demographic comparisons
  • Market research
  • Rating area analysis
  • Building custom plan comparison tools
  • Integration with other systems
  • Multi-age household calculations

VALUE PROPOSITION: We enable questions HealthSherpa cannot answer.
    """)
    
    conn.close()

if __name__ == "__main__":
    analyze_database_capabilities()
