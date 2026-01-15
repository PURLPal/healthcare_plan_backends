#!/usr/bin/env python3
"""
Fast bulk loader for provider and pharmacy data using COPY.
Much faster than row-by-row inserts.
"""

import json
import glob
import os
import sys
import tempfile
import csv
from pathlib import Path

try:
    import pg8000.native
except ImportError:
    print("Error: pg8000 not installed. Run: pip3 install pg8000")
    sys.exit(1)


def load_providers_bulk(conn, json_dir):
    """Load all provider JSON files using COPY FROM"""
    provider_files = glob.glob(f"{json_dir}/*_providers.json")
    
    print(f"\n📋 Loading providers from {len(provider_files)} state files...")
    
    # Create temporary CSV file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as csvfile:
        csv_path = csvfile.name
        writer = csv.writer(csvfile)
        
        total_count = 0
        for file_path in sorted(provider_files):
            state = Path(file_path).stem.split('_')[0].upper()
            print(f"  Processing {state}...", end=' ', flush=True)
            
            with open(file_path, 'r') as f:
                data = json.load(f)
                providers = data.get('providers', [])
            
            if not providers:
                print(f"⚠️  No providers")
                continue
            
            state_count = 0
            for provider in providers:
                writer.writerow([
                    provider.get('npi'),
                    state,
                    provider.get('first_name'),
                    provider.get('last_name'),
                    provider.get('middle_name'),
                    provider.get('credentials'),
                    provider.get('specialty'),
                    provider.get('gender'),
                    provider.get('practice_address'),
                    provider.get('practice_address2'),
                    provider.get('practice_city'),
                    provider.get('practice_state'),
                    provider.get('practice_zip'),
                    provider.get('practice_phone')
                ])
                state_count += 1
            
            total_count += state_count
            print(f"✅ {state_count:,} providers")
    
    print(f"\n  Bulk loading {total_count:,} providers into database...")
    
    # Use COPY to bulk load
    with open(csv_path, 'r', encoding='utf-8') as f:
        conn.run("""
            COPY providers (
                npi, state_abbrev, first_name, last_name, middle_name,
                credentials, specialty, gender, practice_address, practice_address2,
                practice_city, practice_state, practice_zip, practice_phone
            ) FROM STDIN WITH (FORMAT CSV, NULL '')
        """, stream=f)
    
    os.unlink(csv_path)
    return total_count


def load_pharmacies_bulk(conn, json_dir):
    """Load all pharmacy JSON files using COPY FROM"""
    pharmacy_files = glob.glob(f"{json_dir}/*_pharmacies_sample.json")
    
    print(f"\n💊 Loading pharmacies from {len(pharmacy_files)} state files...")
    
    # Create temporary CSV file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as csvfile:
        csv_path = csvfile.name
        writer = csv.writer(csvfile)
        
        total_count = 0
        for file_path in sorted(pharmacy_files):
            state = Path(file_path).stem.split('_')[0].upper()
            print(f"  Processing {state}...", end=' ', flush=True)
            
            with open(file_path, 'r') as f:
                data = json.load(f)
                pharmacies = data.get('retail', [])
            
            if not pharmacies:
                print(f"⚠️  No pharmacies")
                continue
            
            state_count = 0
            for pharmacy in pharmacies:
                # Extract chain name
                name = pharmacy.get('name', '')
                chain = None
                for chain_name in ['CVS', 'Walgreens', 'Rite Aid', 'Walmart', 'Costco', 'Target', 'Safeway', 'Kroger']:
                    if chain_name.lower() in name.lower():
                        chain = chain_name
                        break
                
                # Truncate ZIP to 5 digits if needed
                zip_code = pharmacy.get('zip', '')
                if zip_code and '-' in zip_code:
                    zip_code = zip_code.split('-')[0]
                
                writer.writerow([
                    pharmacy.get('license_number'),
                    state,
                    pharmacy.get('name'),
                    chain,
                    pharmacy.get('address2'),  # address line 1
                    None,  # address2
                    pharmacy.get('city'),
                    pharmacy.get('state'),
                    zip_code[:5] if zip_code else '',
                    pharmacy.get('manager_first_name'),
                    pharmacy.get('manager_last_name'),
                    'true' if pharmacy.get('controlled_substances', True) else 'false',
                    'false',  # mail_order
                    'false',  # twenty_four_hour
                    pharmacy.get('full_address')
                ])
                state_count += 1
            
            total_count += state_count
            print(f"✅ {state_count:,} pharmacies")
    
    print(f"\n  Bulk loading {total_count:,} pharmacies into database...")
    
    # Load to temp table first, then insert with ON CONFLICT handling
    conn.run("CREATE TEMP TABLE pharmacy_temp (LIKE pharmacies INCLUDING DEFAULTS)")
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        conn.run("""
            COPY pharmacy_temp (
                license_number, state_abbrev, name, chain, address, address2,
                city, state, zip, manager_first_name, manager_last_name,
                controlled_substances, mail_order, twenty_four_hour, full_address
            ) FROM STDIN WITH (FORMAT CSV, NULL '')
        """, stream=f)
    
    # Insert from temp, skipping duplicates
    conn.run("""
        INSERT INTO pharmacies 
        SELECT * FROM pharmacy_temp
        ON CONFLICT (license_number, state_abbrev) DO NOTHING
    """)
    
    os.unlink(csv_path)
    return total_count


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 load_providers_pharmacies_fast.py <connection_string> [json_dir]")
        sys.exit(1)
    
    connection_string = sys.argv[1]
    json_dir = sys.argv[2] if len(sys.argv) > 2 else '/Users/andy/DEMOS_FINAL_SPRINT/purlpal_analytics/apps/healthsherpa/public/data'
    
    print("🏥 Medicare Provider & Pharmacy Fast Bulk Loader")
    print("=" * 70)
    print(f"Database: {connection_string.split('dbname=')[1].split()[0]}")
    print(f"JSON Dir: {json_dir}")
    print()
    
    # Connect to database
    print("Connecting to database...", end=' ')
    try:
        conn_params = {}
        for part in connection_string.split():
            if '=' in part:
                key, value = part.split('=', 1)
                if key == 'host':
                    conn_params['host'] = value
                elif key == 'dbname':
                    conn_params['database'] = value
                elif key == 'user':
                    conn_params['user'] = value
                elif key == 'password':
                    conn_params['password'] = value
                elif key == 'port':
                    conn_params['port'] = int(value)
        
        conn_params['ssl_context'] = True
        conn = pg8000.native.Connection(**conn_params)
        print("✅ Connected")
    except Exception as e:
        print(f"❌ Failed: {e}")
        sys.exit(1)
    
    # Clear existing data
    print("\nClearing existing data...")
    conn.run("TRUNCATE TABLE providers, pharmacies")
    print("✅ Tables cleared")
    
    # Load providers
    try:
        provider_count = load_providers_bulk(conn, json_dir)
        print(f"\n✅ Total providers loaded: {provider_count:,}")
    except Exception as e:
        print(f"\n❌ Error loading providers: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # Load pharmacies
    try:
        pharmacy_count = load_pharmacies_bulk(conn, json_dir)
        print(f"\n✅ Total pharmacies loaded: {pharmacy_count:,}")
    except Exception as e:
        print(f"\n❌ Error loading pharmacies: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # Show statistics
    print("\n" + "=" * 70)
    print("📊 Database Statistics")
    print("=" * 70)
    
    result = conn.run("SELECT COUNT(*) FROM providers")
    print(f"Total Providers: {result[0][0]:,}")
    
    result = conn.run("SELECT COUNT(DISTINCT state_abbrev) FROM providers")
    print(f"States with Providers: {result[0][0]}")
    
    result = conn.run("SELECT COUNT(*) FROM pharmacies")
    print(f"Total Pharmacies: {result[0][0]:,}")
    
    result = conn.run("SELECT COUNT(DISTINCT state_abbrev) FROM pharmacies")
    print(f"States with Pharmacies: {result[0][0]}")
    
    print("\nTop 5 States by Provider Count:")
    result = conn.run("""
        SELECT state_abbrev, COUNT(*) as count 
        FROM providers 
        GROUP BY state_abbrev 
        ORDER BY count DESC 
        LIMIT 5
    """)
    for state, count in result:
        print(f"  {state}: {count:,}")
    
    conn.close()
    print("\n✅ Bulk load complete!")


if __name__ == "__main__":
    main()
