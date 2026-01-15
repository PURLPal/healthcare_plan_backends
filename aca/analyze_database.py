#!/usr/bin/env python3
"""
ACA Database Analysis Script
Analyzes plan coverage, ZIP code distribution, and data structure
"""

import os
import json
import pg8000.native

DB_HOST = "aca-plans-db.cc98ea006lul.us-east-1.rds.amazonaws.com"
DB_NAME = "aca_plans"
DB_USER = "aca_admin"
DB_PASSWORD = os.environ.get('ACA_DB_PASSWORD', '')

if not DB_PASSWORD:
    print("Error: Set ACA_DB_PASSWORD environment variable")
    print("Usage: ACA_DB_PASSWORD='your_password' python3 analyze_database.py")
    exit(1)

def connect_db():
    """Connect to PostgreSQL database"""
    return pg8000.native.Connection(
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        database=DB_NAME,
        timeout=10
    )

def analyze_zip_coverage(conn):
    """Analyze ZIP code coverage"""
    print("\n" + "="*80)
    print("ZIP CODE COVERAGE ANALYSIS")
    print("="*80)
    
    # ZIPs with no plans
    query_no_plans = """
    SELECT DISTINCT zc.zip_code, zc.state_code, c.county_name
    FROM zip_counties zc
    JOIN counties c ON zc.county_fips = c.county_fips
    WHERE NOT EXISTS (
        SELECT 1 
        FROM plan_service_areas psa
        WHERE psa.county_fips = zc.county_fips
    )
    ORDER BY zc.state_code, zc.zip_code
    LIMIT 20;
    """
    
    no_plans = conn.run(query_no_plans)
    print(f"\n📍 ZIP Codes with NO Plans: {len(no_plans)}")
    if no_plans:
        print("\nSample ZIPs with no plans:")
        for zip_code, state, county in no_plans[:10]:
            print(f"  {zip_code} ({state}) - {county}")
    else:
        print("  ✅ All ZIP codes have at least one plan!")
    
    # ZIPs with most plans
    query_most_plans = """
    WITH zip_plan_counts AS (
        SELECT 
            zc.zip_code,
            zc.state_code,
            c.county_name,
            COUNT(DISTINCT p.plan_id) as plan_count
        FROM zip_counties zc
        JOIN counties c ON zc.county_fips = c.county_fips
        JOIN plan_service_areas psa ON psa.county_fips = zc.county_fips
        JOIN plans p ON p.service_area_id = psa.service_area_id
        GROUP BY zc.zip_code, zc.state_code, c.county_name
    )
    SELECT zip_code, state_code, county_name, plan_count
    FROM zip_plan_counts
    ORDER BY plan_count DESC
    LIMIT 10;
    """
    
    most_plans = conn.run(query_most_plans)
    print(f"\n📊 ZIP Codes with MOST Plans (Top 10):")
    for zip_code, state, county, count in most_plans:
        print(f"  {zip_code} ({state}) - {county}: {count:,} plans")
    
    # ZIPs with least plans (but > 0)
    query_least_plans = """
    WITH zip_plan_counts AS (
        SELECT 
            zc.zip_code,
            zc.state_code,
            c.county_name,
            COUNT(DISTINCT p.plan_id) as plan_count
        FROM zip_counties zc
        JOIN counties c ON zc.county_fips = c.county_fips
        JOIN plan_service_areas psa ON psa.county_fips = zc.county_fips
        JOIN plans p ON p.service_area_id = psa.service_area_id
        GROUP BY zc.zip_code, zc.state_code, c.county_name
    )
    SELECT zip_code, state_code, county_name, plan_count
    FROM zip_plan_counts
    WHERE plan_count > 0
    ORDER BY plan_count ASC
    LIMIT 10;
    """
    
    least_plans = conn.run(query_least_plans)
    print(f"\n📉 ZIP Codes with LEAST Plans (Top 10):")
    for zip_code, state, county, count in least_plans:
        print(f"  {zip_code} ({state}) - {county}: {count} plans")

def analyze_state_coverage(conn):
    """Analyze state-level coverage"""
    print("\n" + "="*80)
    print("STATE COVERAGE ANALYSIS")
    print("="*80)
    
    # Average plans per ZIP by state
    query = """
    WITH zip_plan_counts AS (
        SELECT 
            zc.state_code,
            zc.zip_code,
            COUNT(DISTINCT p.plan_id) as plan_count
        FROM zip_counties zc
        JOIN plan_service_areas psa ON psa.county_fips = zc.county_fips
        JOIN plans p ON p.service_area_id = psa.service_area_id
        GROUP BY zc.state_code, zc.zip_code
    )
    SELECT 
        state_code,
        COUNT(DISTINCT zip_code) as zip_count,
        AVG(plan_count)::INTEGER as avg_plans_per_zip,
        MIN(plan_count) as min_plans,
        MAX(plan_count) as max_plans
    FROM zip_plan_counts
    GROUP BY state_code
    ORDER BY avg_plans_per_zip ASC;
    """
    
    results = conn.run(query)
    print(f"\n📊 Average Plans per ZIP Code by State:")
    print(f"{'State':<8} {'ZIPs':<8} {'Avg Plans':<12} {'Min':<8} {'Max':<8}")
    print("-" * 50)
    for state, zip_count, avg_plans, min_plans, max_plans in results:
        print(f"{state:<8} {zip_count:<8} {avg_plans:<12} {min_plans:<8} {max_plans:<8}")
    
    # States with lowest average
    print(f"\n🔻 States with LOWEST average plans per ZIP:")
    for state, zip_count, avg_plans, min_plans, max_plans in results[:5]:
        print(f"  {state}: {avg_plans} plans/ZIP (range: {min_plans}-{max_plans})")

def analyze_plan_details(conn):
    """Analyze what plan details we have"""
    print("\n" + "="*80)
    print("PLAN DETAIL COVERAGE ANALYSIS")
    print("="*80)
    
    # Check column completeness
    query_basics = """
    SELECT 
        COUNT(*) as total_plans,
        COUNT(plan_id) as has_plan_id,
        COUNT(plan_marketing_name) as has_name,
        COUNT(issuer_name) as has_issuer,
        COUNT(plan_type) as has_type,
        COUNT(metal_level) as has_metal_level,
        COUNT(service_area_id) as has_service_area,
        COUNT(CASE WHEN is_new_plan IS NOT NULL THEN 1 END) as has_new_flag,
        COUNT(plan_attributes) as has_attributes_json
    FROM plans;
    """
    
    result = conn.run(query_basics)[0]
    total = result[0]
    
    print(f"\n📋 Basic Plan Fields Coverage (out of {total:,} plans):")
    print(f"  Plan ID: {result[1]:,} ({result[1]/total*100:.1f}%)")
    print(f"  Marketing Name: {result[2]:,} ({result[2]/total*100:.1f}%)")
    print(f"  Issuer Name: {result[3]:,} ({result[3]/total*100:.1f}%)")
    print(f"  Plan Type: {result[4]:,} ({result[4]/total*100:.1f}%)")
    print(f"  Metal Level: {result[5]:,} ({result[5]/total*100:.1f}%)")
    print(f"  Service Area: {result[6]:,} ({result[6]/total*100:.1f}%)")
    print(f"  New Plan Flag: {result[7]:,} ({result[7]/total*100:.1f}%)")
    print(f"  Attributes JSON: {result[8]:,} ({result[8]/total*100:.1f}%)")
    
    # Check rates table
    query_rates = """
    SELECT 
        COUNT(DISTINCT plan_id) as plans_with_rates,
        COUNT(*) as total_rate_records
    FROM rates;
    """
    
    rate_result = conn.run(query_rates)[0]
    print(f"\n💰 Rate Data Coverage:")
    print(f"  Plans with rates: {rate_result[0]:,} ({rate_result[0]/total*100:.1f}%)")
    print(f"  Total rate records: {rate_result[1]:,}")
    
    # Check plan types
    query_types = """
    SELECT plan_type, COUNT(*) as count
    FROM plans
    GROUP BY plan_type
    ORDER BY count DESC;
    """
    
    types = conn.run(query_types)
    print(f"\n🏥 Plan Types:")
    for plan_type, count in types:
        print(f"  {plan_type or 'NULL'}: {count:,} plans ({count/total*100:.1f}%)")
    
    # Check metal levels
    query_metals = """
    SELECT metal_level, COUNT(*) as count
    FROM plans
    GROUP BY metal_level
    ORDER BY count DESC;
    """
    
    metals = conn.run(query_metals)
    print(f"\n🥇 Metal Levels:")
    for metal, count in metals:
        print(f"  {metal or 'NULL'}: {count:,} plans ({count/total*100:.1f}%)")
    
    # Sample plan attributes JSON
    query_sample = """
    SELECT plan_attributes
    FROM plans
    WHERE plan_attributes IS NOT NULL
    LIMIT 1;
    """
    
    sample = conn.run(query_sample)
    if sample and sample[0][0]:
        print(f"\n📄 Sample Plan Attributes JSON keys:")
        attrs = sample[0][0]
        if isinstance(attrs, str):
            attrs = json.loads(attrs)
        for key in sorted(attrs.keys()):
            print(f"  - {key}")

def analyze_state_detail_variance(conn):
    """Analyze how plan detail coverage varies by state"""
    print("\n" + "="*80)
    print("PLAN DETAIL VARIANCE BY STATE")
    print("="*80)
    
    query = """
    SELECT 
        state_code,
        COUNT(*) as total_plans,
        COUNT(plan_type) as has_type,
        COUNT(CASE WHEN plan_type = 'HMO' THEN 1 END) as hmo_plans,
        COUNT(CASE WHEN plan_type = 'PPO' THEN 1 END) as ppo_plans,
        COUNT(CASE WHEN plan_type = 'EPO' THEN 1 END) as epo_plans,
        COUNT(CASE WHEN plan_type = 'POS' THEN 1 END) as pos_plans,
        COUNT(DISTINCT issuer_id) as unique_issuers,
        COUNT(DISTINCT service_area_id) as unique_service_areas
    FROM plans
    GROUP BY state_code
    ORDER BY state_code;
    """
    
    results = conn.run(query)
    print(f"\n📊 Plan Details by State:")
    print(f"{'State':<8} {'Plans':<8} {'HMO':<8} {'PPO':<8} {'EPO':<8} {'POS':<8} {'Issuers':<10} {'Areas':<8}")
    print("-" * 80)
    
    for row in results:
        state, total, has_type, hmo, ppo, epo, pos, issuers, areas = row
        print(f"{state:<8} {total:<8} {hmo:<8} {ppo:<8} {epo:<8} {pos:<8} {issuers:<10} {areas:<8}")
    
    # States with most/least variety
    print(f"\n🏆 States with MOST Issuers:")
    sorted_by_issuers = sorted(results, key=lambda x: x[7], reverse=True)
    for row in sorted_by_issuers[:5]:
        print(f"  {row[0]}: {row[7]} issuers, {row[1]} plans")
    
    print(f"\n🔻 States with LEAST Issuers:")
    for row in sorted_by_issuers[-5:]:
        print(f"  {row[0]}: {row[7]} issuers, {row[1]} plans")

def show_schema_info():
    """Display schema and queryable fields"""
    print("\n" + "="*80)
    print("DATABASE SCHEMA & QUERYABLE FIELDS")
    print("="*80)
    
    schema_info = {
        "counties": {
            "description": "County reference data",
            "key_fields": ["county_fips", "county_name", "state_code"],
            "indexes": ["state_code"]
        },
        "zip_counties": {
            "description": "ZIP to county mappings (handles multi-county ZIPs)",
            "key_fields": ["zip_code", "county_fips", "state_code", "ratio"],
            "indexes": ["zip_code", "county_fips", "state_code"]
        },
        "service_areas": {
            "description": "Service area definitions",
            "key_fields": ["service_area_id", "state_code", "issuer_id", "covers_entire_state"],
            "indexes": ["state_code"]
        },
        "plan_service_areas": {
            "description": "Maps service areas to counties (enables ZIP → Plans lookup)",
            "key_fields": ["service_area_id", "county_fips"],
            "indexes": ["service_area_id", "county_fips"]
        },
        "plans": {
            "description": "Main plan attributes (from CMS PUF)",
            "key_fields": [
                "plan_id", "state_code", "issuer_id", "issuer_name",
                "service_area_id", "plan_marketing_name", "plan_type",
                "metal_level", "is_new_plan", "plan_attributes (JSONB)"
            ],
            "indexes": ["state_code", "service_area_id", "metal_level", "issuer_id", "plan_type"]
        },
        "rates": {
            "description": "Age-based premium rates",
            "key_fields": ["plan_id", "age", "individual_rate", "individual_tobacco_rate"],
            "indexes": ["plan_id", "age"],
            "status": "⚠️ Partially loaded (plan ID format issues)"
        },
        "benefits": {
            "description": "Detailed benefit coverage",
            "key_fields": ["plan_id", "benefit_name", "is_covered", "cost_sharing_details"],
            "indexes": ["plan_id", "benefit_name"],
            "status": "❌ Not loaded yet (future enhancement)"
        }
    }
    
    for table, info in schema_info.items():
        print(f"\n📋 {table.upper()}")
        print(f"   {info['description']}")
        print(f"   Fields: {', '.join(info['key_fields'])}")
        print(f"   Indexed: {', '.join(info['indexes'])}")
        if 'status' in info:
            print(f"   Status: {info['status']}")
    
    print("\n" + "="*80)
    print("EASILY QUERYABLE OPERATIONS")
    print("="*80)
    
    queryable = {
        "✅ Fast ZIP → Plans lookup": "Indexed path: zip_counties → plan_service_areas → plans",
        "✅ Filter by State": "Indexed on state_code in multiple tables",
        "✅ Filter by Metal Level": "Indexed on plans.metal_level",
        "✅ Filter by Plan Type": "Indexed on plans.plan_type (HMO, PPO, EPO, POS)",
        "✅ Filter by Issuer": "Indexed on plans.issuer_id",
        "✅ Find Statewide Plans": "service_areas.covers_entire_state = true",
        "⚠️ Age-based Rates": "Partially available (rates table needs fixing)",
        "❌ Benefit Details": "Not yet loaded (future enhancement)"
    }
    
    for operation, details in queryable.items():
        print(f"\n{operation}")
        print(f"   {details}")

def main():
    print("Connecting to ACA Plans Database...")
    print(f"Host: {DB_HOST}")
    print(f"Database: {DB_NAME}")
    
    try:
        conn = connect_db()
        print("✅ Connected successfully!\n")
        
        # Run all analyses
        show_schema_info()
        analyze_zip_coverage(conn)
        analyze_state_coverage(conn)
        analyze_plan_details(conn)
        analyze_state_detail_variance(conn)
        
        print("\n" + "="*80)
        print("ANALYSIS COMPLETE")
        print("="*80)
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
