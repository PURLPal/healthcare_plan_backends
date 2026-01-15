#!/usr/bin/env python3
"""
Load provider and pharmacy data into Medicare Plans PostgreSQL database.
Reads from JSON files and bulk inserts into providers and pharmacies tables.
"""

import json
import glob
import os
import sys
from pathlib import Path

try:
    import pg8000.native
except ImportError:
    print("Error: pg8000 not installed. Run: pip3 install pg8000")
    sys.exit(1)


def load_providers_from_json(conn, json_dir):
    """Load all provider JSON files into providers table"""
    provider_files = glob.glob(f"{json_dir}/*_providers.json")
    
    print(f"\n📋 Loading providers from {len(provider_files)} state files...")
    
    total_inserted = 0
    batch_size = 1000
    
    for file_path in sorted(provider_files):
        state = Path(file_path).stem.split('_')[0].upper()
        print(f"  Loading {state}...", end=' ')
        
        with open(file_path, 'r') as f:
            data = json.load(f)
            providers = data.get('providers', [])
        
        if not providers:
            print(f"⚠️  No providers found")
            continue
        
        # Batch insert
        batch = []
        state_count = 0
        
        for provider in providers:
            batch.append((
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
            ))
            
            if len(batch) >= batch_size:
                for row in batch:
                    conn.run("""
                        INSERT INTO providers (
                            npi, state_abbrev, first_name, last_name, middle_name,
                            credentials, specialty, gender, practice_address, practice_address2,
                            practice_city, practice_state, practice_zip, practice_phone
                        ) VALUES (:npi, :state, :first, :last, :middle, :cred, :spec, :gender, 
                                  :addr1, :addr2, :city, :pstate, :zip, :phone)
                        ON CONFLICT (npi) DO UPDATE SET
                            updated_at = CURRENT_TIMESTAMP
                    """, npi=row[0], state=row[1], first=row[2], last=row[3], middle=row[4],
                         cred=row[5], spec=row[6], gender=row[7], addr1=row[8], addr2=row[9],
                         city=row[10], pstate=row[11], zip=row[12], phone=row[13])
                state_count += len(batch)
                batch = []
        
        # Insert remaining
        if batch:
            for row in batch:
                conn.run("""
                    INSERT INTO providers (
                        npi, state_abbrev, first_name, last_name, middle_name,
                        credentials, specialty, gender, practice_address, practice_address2,
                        practice_city, practice_state, practice_zip, practice_phone
                    ) VALUES (:npi, :state, :first, :last, :middle, :cred, :spec, :gender, 
                              :addr1, :addr2, :city, :pstate, :zip, :phone)
                    ON CONFLICT (npi) DO UPDATE SET
                        updated_at = CURRENT_TIMESTAMP
                """, npi=row[0], state=row[1], first=row[2], last=row[3], middle=row[4],
                     cred=row[5], spec=row[6], gender=row[7], addr1=row[8], addr2=row[9],
                     city=row[10], pstate=row[11], zip=row[12], phone=row[13])
            state_count += len(batch)
        
        total_inserted += state_count
        print(f"✅ {state_count:,} providers")
    
    # pg8000.native auto-commits
    return total_inserted


def load_pharmacies_from_json(conn, json_dir):
    """Load all pharmacy JSON files into pharmacies table"""
    pharmacy_files = glob.glob(f"{json_dir}/*_pharmacies_sample.json")
    
    print(f"\n💊 Loading pharmacies from {len(pharmacy_files)} state files...")
    
    total_inserted = 0
    batch_size = 1000
    
    for file_path in sorted(pharmacy_files):
        state = Path(file_path).stem.split('_')[0].upper()
        print(f"  Loading {state}...", end=' ')
        
        with open(file_path, 'r') as f:
            data = json.load(f)
            pharmacies = data.get('retail', [])
        
        if not pharmacies:
            print(f"⚠️  No pharmacies found")
            continue
        
        # Batch insert
        batch = []
        state_count = 0
        
        for pharmacy in pharmacies:
            # Extract chain name from pharmacy name
            name = pharmacy.get('name', '')
            chain = None
            for chain_name in ['CVS', 'Walgreens', 'Rite Aid', 'Walmart', 'Costco', 'Target', 'Safeway', 'Kroger', 'Albertsons', 'Publix', 'HEB', 'Meijer']:
                if chain_name.lower() in name.lower():
                    chain = chain_name
                    break
            
            batch.append((
                pharmacy.get('license_number'),
                state,
                pharmacy.get('name'),
                chain,
                pharmacy.get('address2'),  # address line 1
                None,  # address2
                pharmacy.get('city'),
                pharmacy.get('state'),
                pharmacy.get('zip'),
                pharmacy.get('manager_first_name'),
                pharmacy.get('manager_last_name'),
                pharmacy.get('controlled_substances', True),
                False,  # mail_order
                False,  # twenty_four_hour
                pharmacy.get('full_address')
            ))
            
            if len(batch) >= batch_size:
                for row in batch:
                    conn.run("""
                        INSERT INTO pharmacies (
                            license_number, state_abbrev, name, chain, address, address2,
                            city, state, zip, manager_first_name, manager_last_name,
                            controlled_substances, mail_order, twenty_four_hour, full_address
                        ) VALUES (:lic, :state, :name, :chain, :addr, :addr2, :city, :pstate, 
                                  :zip, :mfirst, :mlast, :ctrl, :mail, :hrs, :full)
                        ON CONFLICT (license_number) DO UPDATE SET
                            updated_at = CURRENT_TIMESTAMP
                    """, lic=row[0], state=row[1], name=row[2], chain=row[3], addr=row[4],
                         addr2=row[5], city=row[6], pstate=row[7], zip=row[8], mfirst=row[9],
                         mlast=row[10], ctrl=row[11], mail=row[12], hrs=row[13], full=row[14])
                state_count += len(batch)
                batch = []
        
        # Insert remaining
        if batch:
            for row in batch:
                conn.run("""
                    INSERT INTO pharmacies (
                        license_number, state_abbrev, name, chain, address, address2,
                        city, state, zip, manager_first_name, manager_last_name,
                        controlled_substances, mail_order, twenty_four_hour, full_address
                    ) VALUES (:lic, :state, :name, :chain, :addr, :addr2, :city, :pstate, 
                              :zip, :mfirst, :mlast, :ctrl, :mail, :hrs, :full)
                    ON CONFLICT (license_number) DO UPDATE SET
                        updated_at = CURRENT_TIMESTAMP
                """, lic=row[0], state=row[1], name=row[2], chain=row[3], addr=row[4],
                     addr2=row[5], city=row[6], pstate=row[7], zip=row[8], mfirst=row[9],
                     mlast=row[10], ctrl=row[11], mail=row[12], hrs=row[13], full=row[14])
            state_count += len(batch)
        
        total_inserted += state_count
        print(f"✅ {state_count:,} pharmacies")
    
    # pg8000.native auto-commits
    return total_inserted


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 load_providers_pharmacies.py <connection_string> [json_dir]")
        print("\nExample:")
        print('  python3 load_providers_pharmacies.py "host=... dbname=medicare_plans user=medicare_admin password=..."')
        print('  python3 load_providers_pharmacies.py "host=... dbname=..." /path/to/json/files')
        sys.exit(1)
    
    connection_string = sys.argv[1]
    json_dir = sys.argv[2] if len(sys.argv) > 2 else '/Users/andy/DEMOS_FINAL_SPRINT/purlpal_analytics/apps/healthsherpa/public/data'
    
    print("🏥 Medicare Provider & Pharmacy Data Loader")
    print("=" * 70)
    print(f"Database: {connection_string.split('dbname=')[1].split()[0]}")
    print(f"JSON Dir: {json_dir}")
    print()
    
    # Connect to database
    print("Connecting to database...", end=' ')
    try:
        # Parse connection string
        conn_params = {}
        for part in connection_string.split():
            if '=' in part:
                key, value = part.split('=', 1)
                # Map to pg8000 parameter names
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
        
        # Enable SSL for RDS
        conn_params['ssl_context'] = True
        
        conn = pg8000.native.Connection(**conn_params)
        print("✅ Connected")
    except Exception as e:
        print(f"❌ Failed: {e}")
        sys.exit(1)
    
    # Load providers
    try:
        provider_count = load_providers_from_json(conn, json_dir)
        print(f"\n✅ Total providers loaded: {provider_count:,}")
    except Exception as e:
        print(f"\n❌ Error loading providers: {e}")
        import traceback
        traceback.print_exc()
    
    # Load pharmacies
    try:
        pharmacy_count = load_pharmacies_from_json(conn, json_dir)
        print(f"\n✅ Total pharmacies loaded: {pharmacy_count:,}")
    except Exception as e:
        print(f"\n❌ Error loading pharmacies: {e}")
        import traceback
        traceback.print_exc()
    
    # Show statistics
    print("\n" + "=" * 70)
    print("📊 Database Statistics")
    print("=" * 70)
    
    try:
        # Provider counts
        result = conn.run("SELECT COUNT(*) FROM providers")
        print(f"Total Providers: {result[0][0]:,}")
        
        result = conn.run("SELECT COUNT(DISTINCT state_abbrev) FROM providers")
        print(f"States with Providers: {result[0][0]}")
        
        # Pharmacy counts
        result = conn.run("SELECT COUNT(*) FROM pharmacies")
        print(f"Total Pharmacies: {result[0][0]:,}")
        
        result = conn.run("SELECT COUNT(DISTINCT state_abbrev) FROM pharmacies")
        print(f"States with Pharmacies: {result[0][0]}")
        
        # Top 5 states by provider count
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
        
    except Exception as e:
        print(f"Error getting statistics: {e}")
    
    conn.close()
    print("\n✅ Data load complete!")


if __name__ == "__main__":
    main()
