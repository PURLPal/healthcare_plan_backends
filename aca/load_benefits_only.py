#!/usr/bin/env python3
"""
Load ONLY benefits data to existing ACA database
Does not reload plans, rates, service areas, etc.
"""

import csv
import json
import psycopg2
import sys
import tempfile
import os
from datetime import datetime

def connect_db(connection_string):
    """Connect to PostgreSQL database"""
    return psycopg2.connect(connection_string)

def load_benefits(conn):
    """Load benefits and cost-sharing data (optimized with COPY)"""
    print("\n=== Loading Benefits ===")
    cur = conn.cursor()
    
    # Get valid plan IDs and create base plan ID mapping
    print("Building plan ID lookup...")
    cur.execute("SELECT plan_id FROM plans")
    valid_plan_ids = set(row[0] for row in cur.fetchall())
    print(f"Found {len(valid_plan_ids):,} valid plan IDs in database")
    
    # Create base plan ID lookup (14 chars -> first variant)
    # Optimization: Only keep first variant to reduce memory
    base_to_plan = {}
    for plan_id in valid_plan_ids:
        base_id = plan_id[:14]
        if base_id not in base_to_plan:
            base_to_plan[base_id] = plan_id
    
    print(f"Created lookup for {len(base_to_plan):,} base plan IDs")
    
    matched = 0
    skipped = 0
    
    print("Processing benefits file with streaming COPY...")
    
    # Create temporary file for COPY
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as tmp_file:
        tmp_filename = tmp_file.name
        
        with open('data/raw/benefits-and-cost-sharing-puf.csv', 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            writer = csv.writer(tmp_file, delimiter='\t')
            
            for i, row in enumerate(reader):
                if i % 100000 == 0 and i > 0:
                    print(f"  Processed {i:,} rows ({matched:,} matched, {skipped:,} skipped)...")
                
                plan_id = row['PlanId']
                benefit_name = row['BenefitName']
                is_covered = row.get('IsCovered', '') == 'Covered'
                
                # Match plan ID
                if plan_id in valid_plan_ids:
                    matched_plan_id = plan_id
                else:
                    base_id = plan_id[:14]
                    matched_plan_id = base_to_plan.get(base_id)
                
                if not matched_plan_id:
                    skipped += 1
                    continue
                
                # Build cost_sharing JSON (optimized)
                cost_sharing = {}
                
                # Only add non-empty fields
                for key, field in [
                    ('copay_inn_tier1', 'CopayInnTier1'),
                    ('copay_inn_tier2', 'CopayInnTier2'),
                    ('copay_oon', 'CopayOutofNet'),
                    ('coins_inn_tier1', 'CoinsInnTier1'),
                    ('coins_inn_tier2', 'CoinsInnTier2'),
                    ('coins_oon', 'CoinsOutofNet')
                ]:
                    value = row.get(field)
                    if value and value != 'Not Applicable':
                        cost_sharing[key] = value
                
                # Additional fields
                if row.get('Exclusions'):
                    cost_sharing['exclusions'] = row['Exclusions']
                if row.get('Explanation'):
                    cost_sharing['explanation'] = row['Explanation']
                if row.get('QuantLimitOnSvc') == 'Yes':
                    cost_sharing['has_quantity_limit'] = True
                    if row.get('LimitQty'):
                        cost_sharing['limit_quantity'] = row['LimitQty']
                    if row.get('LimitUnit'):
                        cost_sharing['limit_unit'] = row['LimitUnit']
                
                # Write to temp file for COPY
                cost_sharing_json = json.dumps(cost_sharing) if cost_sharing else None
                writer.writerow([
                    matched_plan_id,
                    benefit_name,
                    is_covered,
                    cost_sharing_json
                ])
                matched += 1
    
    print(f"\n✓ Prepared {matched:,} benefit records for import (skipped {skipped:,})")
    
    # Use COPY for bulk insert (much faster than INSERT)
    print("Importing with PostgreSQL COPY (this is fast)...")
    with open(tmp_filename, 'r') as f:
        cur.copy_expert("""
            COPY benefits (plan_id, benefit_name, is_covered, cost_sharing_details)
            FROM STDIN WITH (FORMAT CSV, DELIMITER E'\\t', NULL '')
        """, f)
    
    # Clean up temp file
    os.unlink(tmp_filename)
    
    conn.commit()
    print(f"✓ Loaded {matched:,} benefit records")
    
    # Print statistics
    print("\n=== Benefits Summary ===")
    
    cur.execute("SELECT COUNT(*) FROM benefits")
    total_benefits = cur.fetchone()[0]
    print(f"Total benefit records: {total_benefits:,}")
    
    cur.execute("SELECT COUNT(DISTINCT benefit_name) FROM benefits")
    unique_benefits = cur.fetchone()[0]
    print(f"Unique benefit types: {unique_benefits}")
    
    cur.execute("SELECT COUNT(DISTINCT plan_id) FROM benefits")
    plans_with_benefits = cur.fetchone()[0]
    print(f"Plans with benefits: {plans_with_benefits:,}")
    
    print("\nTop 10 Benefits by Coverage:")
    cur.execute("""
        SELECT benefit_name, COUNT(*) as plan_count
        FROM benefits
        WHERE is_covered = true
        GROUP BY benefit_name
        ORDER BY plan_count DESC
        LIMIT 10
    """)
    for benefit_name, count in cur.fetchall():
        print(f"  {benefit_name}: {count:,} plans")

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 load_benefits_only.py <connection_string>")
        print("Example: python3 load_benefits_only.py 'host=localhost dbname=aca_plans user=postgres password=xxx'")
        sys.exit(1)
    
    connection_string = sys.argv[1]
    
    print("=" * 60)
    print("ACA Benefits Data Loader (Benefits Only)")
    print("=" * 60)
    print(f"Started: {datetime.now()}")
    
    try:
        print("\nConnecting to database...")
        conn = connect_db(connection_string)
        print("✓ Connected")
        
        # Check if plans exist
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM plans")
        plan_count = cur.fetchone()[0]
        
        if plan_count == 0:
            print("\n✗ Error: No plans found in database!")
            print("Please load plans first using the full load_data.py script")
            sys.exit(1)
        
        print(f"✓ Found {plan_count:,} plans in database")
        
        load_benefits(conn)
        
        conn.close()
        
        print(f"\n✓ Benefits load complete! ({datetime.now()})")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
