#!/usr/bin/env python3
"""
Load ACA Plan Data into PostgreSQL Database
Processes CSV files and loads into database schema
"""

import csv
import json
import psycopg2
from psycopg2.extras import execute_batch
import sys
from pathlib import Path
from datetime import datetime

def connect_db(connection_string):
    """Connect to PostgreSQL database"""
    return psycopg2.connect(connection_string)

def load_counties_and_zips(conn):
    """Load county reference data and ZIP-to-county mapping"""
    print("\n=== Loading Counties and ZIP Mapping ===")
    cur = conn.cursor()
    
    # Load FIPS to county name mapping
    print("Loading county reference data...")
    with open('data/reference/fips_to_county_name.json') as f:
        fips_data = json.load(f)
    
    counties_data = []
    for fips, info in fips_data.items():
        if len(fips) == 5:  # Valid county FIPS
            counties_data.append((
                fips,
                info['name'],
                info['state'],
                info.get('state_name', '')
            ))
    
    print(f"Inserting {len(counties_data)} counties...")
    execute_batch(cur, """
        INSERT INTO counties (county_fips, county_name, state_code, state_name)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (county_fips) DO NOTHING
    """, counties_data)
    
    # Load ZIP to county mapping
    print("Loading ZIP-to-county mapping...")
    with open('data/reference/unified_zip_to_fips.json') as f:
        zip_data = json.load(f)
    
    zip_counties_data = []
    for zip_code, info in zip_data.items():
        counties = info.get('counties', [])
        primary_state = info.get('primary_state', '')
        
        for county in counties:
            fips = county['fips']
            ratio = county.get('ratio', 1.0)
            zip_counties_data.append((
                zip_code,
                fips,
                primary_state,
                ratio
            ))
    
    print(f"Inserting {len(zip_counties_data)} ZIP-county mappings...")
    execute_batch(cur, """
        INSERT INTO zip_counties (zip_code, county_fips, state_code, ratio)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (zip_code, county_fips) DO UPDATE SET ratio = EXCLUDED.ratio
    """, zip_counties_data)
    
    conn.commit()
    print(f"✓ Loaded {len(counties_data)} counties, {len(zip_counties_data)} ZIP mappings")

def load_service_areas(conn):
    """Load service areas and their county coverage"""
    print("\n=== Loading Service Areas ===")
    cur = conn.cursor()
    
    service_areas = []
    plan_service_areas = []
    service_areas_covering_entire_state = []
    
    with open('data/raw/service-area-puf.csv', 'r') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            # Only load Individual market plans
            if row['MarketCoverage'] != 'Individual':
                continue
            
            service_area_id = row['ServiceAreaId']
            state_code = row['StateCode']
            covers_entire_state = row['CoverEntireState'] == 'Yes'
            
            # Add to service_areas table
            service_areas.append((
                service_area_id,
                state_code,
                row['IssuerId'],
                row['ServiceAreaName'],
                covers_entire_state,
                row['MarketCoverage']
            ))
            
            # Track service areas that cover entire state
            if covers_entire_state:
                service_areas_covering_entire_state.append((service_area_id, state_code))
            
            # Add county coverage
            county_fips = row['County']
            if county_fips and len(county_fips) == 5:
                plan_service_areas.append((
                    service_area_id,
                    county_fips,
                    state_code
                ))
    
    # Remove duplicates
    service_areas = list(set(service_areas))
    plan_service_areas = list(set(plan_service_areas))
    
    print(f"Inserting {len(service_areas)} service areas...")
    execute_batch(cur, """
        INSERT INTO service_areas 
        (service_area_id, state_code, issuer_id, service_area_name, covers_entire_state, market_coverage)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (service_area_id, state_code) DO UPDATE SET
            issuer_id = EXCLUDED.issuer_id,
            service_area_name = EXCLUDED.service_area_name,
            covers_entire_state = EXCLUDED.covers_entire_state
    """, service_areas)
    
    print(f"Inserting {len(plan_service_areas)} plan-service area mappings...")
    execute_batch(cur, """
        INSERT INTO plan_service_areas (service_area_id, county_fips, state_code)
        VALUES (%s, %s, %s)
        ON CONFLICT (service_area_id, county_fips) DO NOTHING
    """, plan_service_areas)
    
    # For service areas that cover entire state, add ALL counties for that state
    if service_areas_covering_entire_state:
        print(f"Processing {len(set(service_areas_covering_entire_state))} service areas covering entire states...")
        statewide_mappings = []
        for service_area_id, state_code in set(service_areas_covering_entire_state):
            # Get all counties for this state
            counties = cur.run("""
                SELECT county_fips FROM counties WHERE state_code = :state
            """, state=state_code)
            
            for county_row in counties:
                county_fips = county_row[0]
                statewide_mappings.append((service_area_id, county_fips, state_code))
        
        # Insert the statewide county mappings
        if statewide_mappings:
            print(f"Adding {len(statewide_mappings)} county mappings for statewide service areas...")
            execute_batch(cur, """
                INSERT INTO plan_service_areas (service_area_id, county_fips, state_code)
                VALUES (%s, %s, %s)
                ON CONFLICT (service_area_id, county_fips) DO NOTHING
            """, statewide_mappings)
    
    conn.commit()
    print(f"✓ Loaded {len(service_areas)} service areas with full county coverage")

def load_plans(conn):
    """Load plan attributes"""
    print("\n=== Loading Plans ===")
    cur = conn.cursor()
    
    plans_data = []
    
    with open('data/raw/plan-attributes-puf.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            # Only load Individual market medical plans
            if row['MarketCoverage'] != 'Individual':
                continue
            if row['DentalOnlyPlan'] == 'Yes':
                continue
            
            # Build plan attributes JSON
            plan_attributes = {
                'hios_product_id': row['HIOSProductId'],
                'network_id': row['NetworkId'],
                'formulary_id': row['FormularyId'],
                'design_type': row['DesignType'],
                'qhp_type': row['QHPNonQHPTypeId'],
                'plan_effective_date': row['PlanEffectiveDate'],
                'plan_expiration_date': row['PlanExpirationDate'],
                'is_hsa_eligible': row['IsHSAEligible'],
                'national_network': row.get('NationalNetwork', ''),
                'url_enrollment': row.get('URLForEnrollmentPayment', ''),
                'url_sbc': row.get('URLForSummaryofBenefitsCoverage', ''),
                'plan_brochure': row.get('PlanBrochure', ''),
                'deductible_individual': row.get('TEHBDedInnTier1Individual', ''),
                'deductible_family': row.get('TEHBDedInnTier1FamilyPerGroup', ''),
                'moop_individual': row.get('TEHBInnTier1IndividualMOOP', ''),
                'moop_family': row.get('TEHBInnTier1FamilyPerGroupMOOP', '')
            }
            
            plans_data.append((
                row['PlanId'],
                row['StateCode'],
                row['IssuerId'],
                row['IssuerMarketPlaceMarketingName'],
                row['ServiceAreaId'],
                row['PlanMarketingName'],
                row['PlanType'],
                row['MetalLevel'],
                row['IsNewPlan'] == 'New',
                json.dumps(plan_attributes)
            ))
    
    print(f"Inserting {len(plans_data)} plans...")
    execute_batch(cur, """
        INSERT INTO plans 
        (plan_id, state_code, issuer_id, issuer_name, service_area_id, 
         plan_marketing_name, plan_type, metal_level, is_new_plan, plan_attributes)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (plan_id) DO UPDATE SET
            service_area_id = EXCLUDED.service_area_id,
            plan_marketing_name = EXCLUDED.plan_marketing_name,
            plan_attributes = EXCLUDED.plan_attributes
    """, plans_data, page_size=1000)
    
    conn.commit()
    print(f"✓ Loaded {len(plans_data)} plans")

def load_rates(conn):
    """Load premium rates"""
    print("\n=== Loading Rates ===")
    cur = conn.cursor()
    
    # Get valid plan IDs
    cur.execute("SELECT plan_id FROM plans")
    valid_plan_ids = set(row[0] for row in cur.fetchall())
    print(f"Found {len(valid_plan_ids)} valid plan IDs")
    
    rates_data = []
    skipped = 0
    
    print("Processing rate file...")
    with open('data/raw/rate-puf.csv', 'r') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            plan_id = row['PlanId']
            
            # Skip if plan not in our database
            if plan_id not in valid_plan_ids:
                skipped += 1
                continue
            
            # Only load non-tobacco rates
            if row['Tobacco'] != 'No':
                continue
            
            age = row['Age']
            if not age or age == 'Family Option':
                continue
            
            try:
                age_int = int(age)
                if age_int < 0 or age_int > 120:
                    continue
            except ValueError:
                continue
            
            individual_rate = row.get('IndividualRate', '')
            tobacco_rate = row.get('IndividualTobaccoRate', '')
            
            if individual_rate and individual_rate != 'N/A':
                rates_data.append((
                    plan_id,
                    age_int,
                    float(individual_rate) if individual_rate else None,
                    float(tobacco_rate) if tobacco_rate and tobacco_rate != 'N/A' else None
                ))
    
    print(f"Inserting {len(rates_data)} rate records (skipped {skipped} invalid plans)...")
    execute_batch(cur, """
        INSERT INTO rates (plan_id, age, individual_rate, individual_tobacco_rate)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (plan_id, age) DO UPDATE SET
            individual_rate = EXCLUDED.individual_rate,
            individual_tobacco_rate = EXCLUDED.individual_tobacco_rate
    """, rates_data, page_size=10000)
    
    conn.commit()
    print(f"✓ Loaded {len(rates_data)} rate records")

def print_summary(conn):
    """Print database summary statistics"""
    print("\n=== Database Summary ===")
    cur = conn.cursor()
    
    queries = [
        ("Counties", "SELECT COUNT(*) FROM counties"),
        ("ZIP Codes", "SELECT COUNT(DISTINCT zip_code) FROM zip_counties"),
        ("Service Areas", "SELECT COUNT(DISTINCT service_area_id) FROM service_areas"),
        ("Plans", "SELECT COUNT(*) FROM plans"),
        ("Rates", "SELECT COUNT(*) FROM rates"),
        ("States with Plans", "SELECT COUNT(DISTINCT state_code) FROM plans"),
    ]
    
    for name, query in queries:
        cur.execute(query)
        count = cur.fetchone()[0]
        print(f"{name}: {count:,}")
    
    # Plans by metal level
    print("\nPlans by Metal Level:")
    cur.execute("""
        SELECT metal_level, COUNT(*) 
        FROM plans 
        GROUP BY metal_level 
        ORDER BY COUNT(*) DESC
    """)
    for metal_level, count in cur.fetchall():
        print(f"  {metal_level}: {count:,}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 load_data.py <connection_string>")
        print("Example: python3 load_data.py 'host=localhost dbname=aca_plans user=postgres password=xxx'")
        sys.exit(1)
    
    connection_string = sys.argv[1]
    
    print("=" * 60)
    print("ACA Plan Data Loader")
    print("=" * 60)
    print(f"Started: {datetime.now()}")
    
    try:
        print("\nConnecting to database...")
        conn = connect_db(connection_string)
        print("✓ Connected")
        
        load_counties_and_zips(conn)
        load_service_areas(conn)
        load_plans(conn)
        load_rates(conn)
        
        print_summary(conn)
        
        conn.close()
        
        print(f"\n✓ Data load complete! ({datetime.now()})")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
