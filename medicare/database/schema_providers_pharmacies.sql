-- Add providers and pharmacies tables to existing medicare_plans database
-- Compatible with existing states and zip_codes tables

-- ============================================================================
-- PROVIDERS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS providers (
    npi VARCHAR(10) PRIMARY KEY,
    state_abbrev VARCHAR(2) NOT NULL REFERENCES states(abbrev) ON DELETE CASCADE,
    first_name VARCHAR(100),
    last_name VARCHAR(100) NOT NULL,
    middle_name VARCHAR(100),
    credentials VARCHAR(50),
    specialty VARCHAR(200),
    gender VARCHAR(1),
    
    -- Practice location
    practice_address VARCHAR(200),
    practice_address2 VARCHAR(200),
    practice_city VARCHAR(100),
    practice_state VARCHAR(2),
    practice_zip VARCHAR(5),
    practice_phone VARCHAR(20),
    
    -- Indexing and search (computed index, not generated column)
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for fast searching
CREATE INDEX idx_providers_state ON providers(state_abbrev);
CREATE INDEX idx_providers_zip ON providers(practice_zip);
CREATE INDEX idx_providers_last_name ON providers(LOWER(last_name));
CREATE INDEX idx_providers_first_name ON providers(LOWER(first_name));
CREATE INDEX idx_providers_full_name ON providers(LOWER(COALESCE(first_name, '') || ' ' || COALESCE(last_name, '')));
CREATE INDEX idx_providers_npi ON providers(npi);
CREATE INDEX idx_providers_specialty ON providers(LOWER(specialty));

-- Full-text search index (for advanced search)
CREATE INDEX idx_providers_search ON providers USING gin(
    to_tsvector('english', 
        COALESCE(first_name, '') || ' ' || 
        COALESCE(last_name, '') || ' ' || 
        COALESCE(specialty, '')
    )
);

-- ============================================================================
-- PHARMACIES TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS pharmacies (
    id SERIAL PRIMARY KEY,
    license_number VARCHAR(50) UNIQUE NOT NULL,
    state_abbrev VARCHAR(2) NOT NULL REFERENCES states(abbrev) ON DELETE CASCADE,
    
    -- Pharmacy info
    name VARCHAR(200) NOT NULL,
    chain VARCHAR(100),
    
    -- Location
    address VARCHAR(200),
    address2 VARCHAR(200),
    city VARCHAR(100) NOT NULL,
    state VARCHAR(2),
    zip VARCHAR(5) NOT NULL,
    
    -- Manager info
    manager_first_name VARCHAR(100),
    manager_last_name VARCHAR(100),
    
    -- Capabilities
    controlled_substances BOOLEAN DEFAULT true,
    mail_order BOOLEAN DEFAULT false,
    twenty_four_hour BOOLEAN DEFAULT false,
    
    -- Full address for display
    full_address TEXT,
    
    -- Indexing and search (computed index, not generated column)
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for fast searching
CREATE INDEX idx_pharmacies_state ON pharmacies(state_abbrev);
CREATE INDEX idx_pharmacies_zip ON pharmacies(zip);
CREATE INDEX idx_pharmacies_name ON pharmacies(name_lower);
CREATE INDEX idx_pharmacies_city ON pharmacies(LOWER(city));
CREATE INDEX idx_pharmacies_license ON pharmacies(license_number);
CREATE INDEX idx_pharmacies_chain ON pharmacies(LOWER(chain));

-- Full-text search index
CREATE INDEX idx_pharmacies_search ON pharmacies USING gin(
    to_tsvector('english', 
        COALESCE(name, '') || ' ' || 
        COALESCE(city, '') || ' ' || 
        COALESCE(chain, '')
    )
);

-- ============================================================================
-- VIEWS FOR CONVENIENCE
-- ============================================================================

-- Provider search view with state info
CREATE OR REPLACE VIEW provider_search AS
SELECT 
    p.*,
    s.name as state_name
FROM providers p
JOIN states s ON p.state_abbrev = s.abbrev;

-- Pharmacy search view with state info
CREATE OR REPLACE VIEW pharmacy_search AS
SELECT 
    ph.*,
    s.name as state_name
FROM pharmacies ph
JOIN states s ON ph.state_abbrev = s.abbrev;

-- ============================================================================
-- STATISTICS
-- ============================================================================

-- View to show provider counts by state
CREATE OR REPLACE VIEW provider_stats AS
SELECT 
    s.abbrev,
    s.name,
    COUNT(p.npi) as provider_count
FROM states s
LEFT JOIN providers p ON s.abbrev = p.state_abbrev
GROUP BY s.abbrev, s.name
ORDER BY provider_count DESC;

-- View to show pharmacy counts by state
CREATE OR REPLACE VIEW pharmacy_stats AS
SELECT 
    s.abbrev,
    s.name,
    COUNT(ph.id) as pharmacy_count
FROM states s
LEFT JOIN pharmacies ph ON s.abbrev = ph.state_abbrev
GROUP BY s.abbrev, s.name
ORDER BY pharmacy_count DESC;

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE providers IS 'Healthcare providers from NPPES NPI Registry';
COMMENT ON TABLE pharmacies IS 'Retail and mail-order pharmacies by state';
COMMENT ON COLUMN providers.npi IS 'National Provider Identifier (10 digits)';
COMMENT ON COLUMN providers.specialty IS 'Provider specialty or taxonomy description';
COMMENT ON COLUMN pharmacies.controlled_substances IS 'Licensed to dispense controlled substances';
COMMENT ON COLUMN pharmacies.mail_order IS 'Offers mail-order prescription service';
