-- ACA Plan API Database Schema
-- PostgreSQL database for ACA marketplace plan data

-- Drop existing tables if they exist
DROP TABLE IF EXISTS rates CASCADE;
DROP TABLE IF EXISTS benefits CASCADE;
DROP TABLE IF EXISTS plan_service_areas CASCADE;
DROP TABLE IF EXISTS service_areas CASCADE;
DROP TABLE IF EXISTS plans CASCADE;
DROP TABLE IF EXISTS zip_counties CASCADE;
DROP TABLE IF EXISTS counties CASCADE;

-- Counties table (reference data)
CREATE TABLE counties (
    county_fips VARCHAR(5) PRIMARY KEY,
    county_name VARCHAR(100),
    state_code VARCHAR(2) NOT NULL,
    state_name VARCHAR(100)
);

CREATE INDEX idx_counties_state ON counties(state_code);

-- ZIP to County mapping (handles multi-county ZIPs)
CREATE TABLE zip_counties (
    zip_code VARCHAR(5),
    county_fips VARCHAR(5) REFERENCES counties(county_fips),
    state_code VARCHAR(2),
    ratio DECIMAL(10, 6),
    PRIMARY KEY (zip_code, county_fips)
);

CREATE INDEX idx_zip_counties_zip ON zip_counties(zip_code);
CREATE INDEX idx_zip_counties_county ON zip_counties(county_fips);
CREATE INDEX idx_zip_counties_state ON zip_counties(state_code);

-- Service Areas (defines geographic coverage for plans)
CREATE TABLE service_areas (
    service_area_id VARCHAR(50),
    state_code VARCHAR(2),
    issuer_id VARCHAR(20),
    service_area_name VARCHAR(200),
    covers_entire_state BOOLEAN,
    market_coverage VARCHAR(50),
    PRIMARY KEY (service_area_id, state_code)
);

CREATE INDEX idx_service_areas_state ON service_areas(state_code);

-- Plan-Service Area junction (many-to-many via counties)
CREATE TABLE plan_service_areas (
    service_area_id VARCHAR(50),
    county_fips VARCHAR(5),
    state_code VARCHAR(2),
    PRIMARY KEY (service_area_id, county_fips)
);

CREATE INDEX idx_psa_service_area ON plan_service_areas(service_area_id);
CREATE INDEX idx_psa_county ON plan_service_areas(county_fips);

-- Plans table (main plan attributes)
CREATE TABLE plans (
    plan_id VARCHAR(50) PRIMARY KEY,
    state_code VARCHAR(2) NOT NULL,
    issuer_id VARCHAR(20),
    issuer_name VARCHAR(200),
    service_area_id VARCHAR(50),
    plan_marketing_name VARCHAR(300),
    plan_type VARCHAR(50),
    metal_level VARCHAR(50),
    is_new_plan BOOLEAN,
    plan_attributes JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_plans_state ON plans(state_code);
CREATE INDEX idx_plans_service_area ON plans(service_area_id);
CREATE INDEX idx_plans_metal_level ON plans(metal_level);
CREATE INDEX idx_plans_issuer ON plans(issuer_id);
CREATE INDEX idx_plans_type ON plans(plan_type);

-- Rates table (age-based premium rates)
CREATE TABLE rates (
    plan_id VARCHAR(50) REFERENCES plans(plan_id),
    age INTEGER,
    individual_rate DECIMAL(10, 2),
    individual_tobacco_rate DECIMAL(10, 2),
    PRIMARY KEY (plan_id, age)
);

CREATE INDEX idx_rates_plan ON rates(plan_id);
CREATE INDEX idx_rates_age ON rates(age);

-- Benefits table (detailed cost-sharing and benefits)
CREATE TABLE benefits (
    plan_id VARCHAR(50) REFERENCES plans(plan_id),
    benefit_name VARCHAR(200),
    is_covered BOOLEAN,
    cost_sharing_details JSONB,
    PRIMARY KEY (plan_id, benefit_name)
);

CREATE INDEX idx_benefits_plan ON benefits(plan_id);
CREATE INDEX idx_benefits_name ON benefits(benefit_name);

-- Summary statistics view
CREATE OR REPLACE VIEW plan_summary AS
SELECT 
    state_code,
    metal_level,
    COUNT(*) as plan_count,
    AVG((SELECT individual_rate FROM rates WHERE rates.plan_id = plans.plan_id AND age = 40)) as avg_rate_age_40
FROM plans
GROUP BY state_code, metal_level;
