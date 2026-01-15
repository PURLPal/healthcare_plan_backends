"""
ACA Plan API - Lambda Function
Handles all API endpoints for ACA marketplace plan queries
"""
import json
import os
import pg8000.native

# OpenAPI specification
OPENAPI_SPEC = '''openapi: 3.0.3
info:
  title: ACA Plan API
  description: Database-backed API for ACA marketplace plan lookup by ZIP code. 19,000+ plans, Individual market.
  version: 1.0.0
servers:
  - url: https://aca.purlpal-api.com/aca
paths:
  /states.json:
    get:
      summary: List all states with plan counts
  /state/{state}/info.json:
    get:
      summary: Get state information
  /zip/{zipcode}.json:
    get:
      summary: Get plans by ZIP code
  /zip/{zipcode}_{metal_level}.json:
    get:
      summary: Get plans by metal level (Bronze, Silver, Gold, Platinum, Catastrophic)
  /plan/{planId}.json:
    get:
      summary: Get individual plan details
For full schema, visit: https://github.com/yourusername/aca-api/blob/main/openapi.yaml
'''

# Database connection from environment variables
DB_HOST = os.environ.get('DB_HOST')
DB_PORT = int(os.environ.get('DB_PORT', '5432'))
DB_NAME = os.environ.get('DB_NAME')
DB_USER = os.environ.get('DB_USER')
DB_PASSWORD = os.environ.get('DB_PASSWORD')

# Global connection for reuse across Lambda invocations
_db_connection = None

def get_db_connection():
    """Get database connection (reuses existing connection if available)."""
    global _db_connection
    
    # Try to reuse existing connection
    if _db_connection is not None:
        try:
            # Test connection is still alive
            _db_connection.run("SELECT 1")
            return _db_connection
        except:
            # Connection is dead, create new one
            _db_connection = None
    
    # Create new connection
    _db_connection = pg8000.native.Connection(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        ssl_context=True  # Enable SSL for RDS
    )
    return _db_connection

def lambda_handler(event, context):
    """Main Lambda handler for all ACA API endpoints."""
    
    # Parse request - API Gateway v2 uses different field names
    http_method = event.get('requestContext', {}).get('http', {}).get('method', 'GET')
    raw_path = event.get('rawPath', event.get('path', ''))
    query_params = event.get('queryStringParameters') or {}
    
    # Strip stage prefix (/prod, /dev, etc.) from path
    stage = event.get('requestContext', {}).get('stage', '')
    if stage and raw_path.startswith(f'/{stage}/'):
        path = raw_path[len(f'/{stage}'):]
    else:
        path = raw_path
    
    # CORS headers
    headers = {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type'
    }
    
    # Handle OPTIONS (CORS preflight)
    if http_method == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': headers,
            'body': ''
        }
    
    try:
        # Route to appropriate handler
        if path == '/aca/openapi.yaml':
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'text/yaml',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'GET, OPTIONS',
                    'Access-Control-Allow-Headers': 'Content-Type'
                },
                'body': OPENAPI_SPEC
            }
        elif path.startswith('/aca/zip/'):
            return handle_zip_query(path, query_params, headers)
        elif path.startswith('/aca/state/'):
            return handle_state_query(path, headers)
        elif path.startswith('/aca/plan/'):
            return handle_plan_query(path, headers)
        elif path == '/aca/states.json':
            return handle_states_list(headers)
        else:
            return {
                'statusCode': 404,
                'headers': headers,
                'body': json.dumps({'error': 'Endpoint not found'})
            }
    
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': 'Internal server error', 'message': str(e)})
        }

def handle_states_list(headers):
    """Return list of all states with plan counts"""
    conn = get_db_connection()
    
    # Get state summary
    state_rows = conn.run("""
        SELECT 
            state_code,
            COUNT(*) as plan_count
        FROM plans
        GROUP BY state_code
        ORDER BY state_code
    """)
    
    states = []
    total_plans = 0
    
    for row in state_rows:
        plan_count = row[1]
        total_plans += plan_count
        
        states.append({
            'abbrev': row[0],
            'plan_count': plan_count,
            'info_url': f'/aca/state/{row[0]}/info.json'
        })
    
    response = {
        'state_count': len(states),
        'total_plans': total_plans,
        'states': states
    }
    
    return {
        'statusCode': 200,
        'headers': headers,
        'body': json.dumps(response)
    }

def handle_state_query(path, headers):
    """Handle state-level queries"""
    # Extract state code from path
    parts = path.split('/')
    state_code = parts[3].upper()
    
    conn = get_db_connection()
    
    # Get state summary
    state_rows = conn.run("""
        SELECT COUNT(*) FROM plans WHERE state_code = :state
    """, state=state_code)
    
    plan_count = state_rows[0][0] if state_rows else 0
    
    if plan_count == 0:
        return {
            'statusCode': 404,
            'headers': headers,
            'body': json.dumps({'error': 'State not found or no plans available'})
        }
    
    response = {
        'state_abbrev': state_code,
        'plan_count': plan_count
    }
    
    return {
        'statusCode': 200,
        'headers': headers,
        'body': json.dumps(response)
    }

def handle_zip_query(path, query_params, headers):
    """Handle ZIP code plan queries"""
    # Extract ZIP code and optional metal level filter
    parts = path.split('/')
    zip_file = parts[3]  # e.g., "02108.json" or "02108_Silver.json"
    
    # Remove .json extension
    zip_part = zip_file.replace('.json', '')
    
    # Check for metal level filter
    metal_level = None
    if '_' in zip_part:
        zip_code, metal_level = zip_part.split('_', 1)
    else:
        zip_code = zip_part
    
    # Validate ZIP code
    if not zip_code.isdigit() or len(zip_code) != 5:
        return {
            'statusCode': 400,
            'headers': headers,
            'body': json.dumps({'error': 'Invalid ZIP code format'})
        }
    
    conn = get_db_connection()
    
    # Get counties for this ZIP code
    county_rows = conn.run("""
        SELECT DISTINCT
            c.county_fips,
            c.county_name,
            c.state_code,
            zc.ratio
        FROM zip_counties zc
        JOIN counties c ON zc.county_fips = c.county_fips
        WHERE zc.zip_code = :zip
        ORDER BY zc.ratio DESC
    """, zip=zip_code)
    
    if not county_rows:
        return {
            'statusCode': 404,
            'headers': headers,
            'body': json.dumps({
                'error': 'ZIP code not found',
                'zip_code': zip_code
            })
        }
    
    counties = [{
        'fips': row[0],
        'name': row[1],
        'state': row[2],
        'ratio': float(row[3]) if row[3] else 1.0
    } for row in county_rows]
    
    # Get ALL plans for ALL counties in a single query
    county_fips_list = [c['fips'] for c in counties]
    
    if metal_level:
        plan_rows = conn.run("""
            SELECT DISTINCT ON (psa.county_fips, p.plan_id)
                psa.county_fips,
                p.plan_id,
                p.issuer_name,
                p.plan_marketing_name,
                p.plan_type,
                p.metal_level,
                p.is_new_plan,
                p.plan_attributes,
                r.individual_rate as rate_age_40
            FROM plans p
            INNER JOIN plan_service_areas psa ON p.service_area_id = psa.service_area_id
            LEFT JOIN rates r ON p.plan_id = r.plan_id AND r.age = 40
            WHERE psa.county_fips = ANY(:county_fips) 
              AND p.metal_level = :metal
            ORDER BY psa.county_fips, p.plan_id, p.metal_level
        """, county_fips=county_fips_list, metal=metal_level)
    else:
        plan_rows = conn.run("""
            SELECT DISTINCT ON (psa.county_fips, p.plan_id)
                psa.county_fips,
                p.plan_id,
                p.issuer_name,
                p.plan_marketing_name,
                p.plan_type,
                p.metal_level,
                p.is_new_plan,
                p.plan_attributes,
                r.individual_rate as rate_age_40
            FROM plans p
            INNER JOIN plan_service_areas psa ON p.service_area_id = psa.service_area_id
            LEFT JOIN rates r ON p.plan_id = r.plan_id AND r.age = 40
            WHERE psa.county_fips = ANY(:county_fips)
            ORDER BY psa.county_fips, p.plan_id, p.metal_level
        """, county_fips=county_fips_list)
    
    # Group plans by county
    plans_by_county_fips = {}
    for row in plan_rows:
        county_fips = row[0]
        if county_fips not in plans_by_county_fips:
            plans_by_county_fips[county_fips] = []
        
        plan_attributes = row[7] if row[7] else {}
        
        plan_data = {
            'plan_id': row[1],
            'issuer_name': row[2],
            'plan_name': row[3],
            'plan_type': row[4],
            'metal_level': row[5],
            'is_new_plan': row[6],
            'rate_age_40': float(row[8]) if row[8] else None,
            'plan_details': plan_attributes
        }
        plans_by_county_fips[county_fips].append(plan_data)
    
    # Build county response with plans
    counties_with_plans = []
    all_plans = []
    seen_plan_ids = set()
    plans_by_metal = {}
    
    for county in counties:
        county_fips = county['fips']
        county_plans = plans_by_county_fips.get(county_fips, [])
        
        # Add to all_plans if not already present (for backwards compatibility)
        for plan_data in county_plans:
            if plan_data['plan_id'] not in seen_plan_ids:
                seen_plan_ids.add(plan_data['plan_id'])
                all_plans.append(plan_data)
                
                metal = plan_data['metal_level']
                if metal not in plans_by_metal:
                    plans_by_metal[metal] = []
                plans_by_metal[metal].append(plan_data)
        
        # Add county with its plans
        county_with_plans = {
            'name': county['name'],
            'fips': county['fips'],
            'state': county['state'],
            'ratio': county['ratio'],
            'plans': county_plans,
            'plan_count': len(county_plans),
            'plans_available': len(county_plans) > 0
        }
        counties_with_plans.append(county_with_plans)
    
    # Count plans by metal level
    plan_counts_by_metal = {metal: len(plans) for metal, plans in plans_by_metal.items()}
    
    # Build response
    multi_county = len(counties) > 1
    states = list(set(c['state'] for c in counties))
    
    response = {
        'zip_code': zip_code,
        'multi_county': multi_county,
        'multi_state': len(states) > 1,
        'states': states,
        'primary_state': counties[0]['state'] if counties else None,
        'counties': counties_with_plans,
        'plans': all_plans,
        'plan_count': len(all_plans),
        'plan_counts_by_metal_level': plan_counts_by_metal
    }
    
    return {
        'statusCode': 200,
        'headers': headers,
        'body': json.dumps(response)
    }

def handle_plan_query(path, headers):
    """Handle individual plan detail queries"""
    # Extract plan ID from path
    parts = path.split('/')
    plan_file = parts[3]  # e.g., "21989AK0030001-00.json"
    plan_id = plan_file.replace('.json', '')
    
    conn = get_db_connection()
    
    # Get plan details
    plan_rows = conn.run("""
        SELECT 
            plan_id,
            state_code,
            issuer_name,
            plan_marketing_name,
            plan_type,
            metal_level,
            is_new_plan,
            plan_attributes
        FROM plans
        WHERE plan_id = :plan_id
    """, plan_id=plan_id)
    
    if not plan_rows:
        return {
            'statusCode': 404,
            'headers': headers,
            'body': json.dumps({'error': 'Plan not found'})
        }
    
    row = plan_rows[0]
    plan_attributes = row[7] if row[7] else {}
    
    # Get rates for this plan
    rate_rows = conn.run("""
        SELECT age, individual_rate, individual_tobacco_rate
        FROM rates
        WHERE plan_id = :plan_id
        ORDER BY age
    """, plan_id=plan_id)
    
    rates = [{
        'age': r[0],
        'rate': float(r[1]) if r[1] else None,
        'tobacco_rate': float(r[2]) if r[2] else None
    } for r in rate_rows]
    
    response = {
        'plan_id': row[0],
        'state_code': row[1],
        'issuer_name': row[2],
        'plan_name': row[3],
        'plan_type': row[4],
        'metal_level': row[5],
        'is_new_plan': row[6],
        'plan_details': plan_attributes,
        'rates': rates
    }
    
    return {
        'statusCode': 200,
        'headers': headers,
        'body': json.dumps(response)
    }
