-- ============================================================================
-- RUM Visual Content Analytics - Snowflake Database Schema
-- ============================================================================
-- This script creates the database, schema, tables, and sample data for
-- the Reuters Media visual content analytics platform.
-- ============================================================================

-- Create database and schema
CREATE DATABASE IF NOT EXISTS RUM_ANALYTICS;
USE DATABASE RUM_ANALYTICS;
CREATE SCHEMA IF NOT EXISTS PUBLIC;
USE SCHEMA PUBLIC;

-- Create warehouse for compute
CREATE WAREHOUSE IF NOT EXISTS RUM_ANALYTICS_WH
  WITH WAREHOUSE_SIZE = 'X-SMALL'
  AUTO_SUSPEND = 300
  AUTO_RESUME = TRUE
  INITIALLY_SUSPENDED = TRUE;

-- ============================================================================
-- CONTENT CATEGORIES REFERENCE TABLE
-- ============================================================================
CREATE OR REPLACE TABLE CONTENT_CATEGORIES (
    CATEGORY_ID VARCHAR(50) PRIMARY KEY,
    CATEGORY_NAME VARCHAR(100) NOT NULL,
    CATEGORY_DESCRIPTION VARCHAR(500),
    CREATED_AT TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

INSERT INTO CONTENT_CATEGORIES VALUES
    ('CAT001', 'Breaking News', 'Time-sensitive news imagery and photographs'),
    ('CAT002', 'Sports', 'Sports events, athletes, and competitions'),
    ('CAT003', 'Entertainment', 'Celebrity, film, music, and entertainment content'),
    ('CAT004', 'Business', 'Corporate, financial, and business imagery'),
    ('CAT005', 'Politics', 'Political events, leaders, and government'),
    ('CAT006', 'Lifestyle', 'Human interest, travel, and lifestyle content');

-- ============================================================================
-- VISUAL CONTENT MASTER TABLE
-- ============================================================================
CREATE OR REPLACE TABLE VISUAL_CONTENT (
    CONTENT_ID VARCHAR(50) PRIMARY KEY,
    TITLE VARCHAR(500) NOT NULL,
    CATEGORY VARCHAR(100) NOT NULL,
    UPLOAD_DATE DATE NOT NULL,
    PHOTOGRAPHER VARCHAR(200),
    CONTENT_FORMAT VARCHAR(50) NOT NULL,
    REGION VARCHAR(100),
    KEYWORDS ARRAY,
    FILE_SIZE_MB NUMBER(10,2),
    RESOLUTION VARCHAR(50),
    IS_EXCLUSIVE BOOLEAN DEFAULT FALSE,
    CREATED_AT TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    UPDATED_AT TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- ============================================================================
-- CUSTOMERS TABLE
-- ============================================================================
CREATE OR REPLACE TABLE CUSTOMERS (
    CUSTOMER_ID VARCHAR(50) PRIMARY KEY,
    CUSTOMER_NAME VARCHAR(200) NOT NULL,
    SEGMENT VARCHAR(50) NOT NULL,
    INDUSTRY VARCHAR(100),
    REGION VARCHAR(100) NOT NULL,
    ACQUISITION_DATE DATE NOT NULL,
    LIFETIME_VALUE NUMBER(15,2) DEFAULT 0,
    SUBSCRIPTION_TIER VARCHAR(50),
    CONTACT_EMAIL VARCHAR(200),
    IS_ACTIVE BOOLEAN DEFAULT TRUE,
    CREATED_AT TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    UPDATED_AT TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- ============================================================================
-- LICENSING REVENUE TABLE
-- ============================================================================
CREATE OR REPLACE TABLE LICENSING_REVENUE (
    TRANSACTION_ID VARCHAR(50) PRIMARY KEY,
    CONTENT_ID VARCHAR(50) NOT NULL REFERENCES VISUAL_CONTENT(CONTENT_ID),
    CUSTOMER_ID VARCHAR(50) NOT NULL REFERENCES CUSTOMERS(CUSTOMER_ID),
    REVENUE NUMBER(15,2) NOT NULL,
    TRANSACTION_DATE DATE NOT NULL,
    QUARTER VARCHAR(10) NOT NULL,
    YEAR NUMBER(4) NOT NULL,
    LICENSE_TYPE VARCHAR(50) NOT NULL,
    REGION VARCHAR(100),
    USAGE_RIGHTS VARCHAR(200),
    LICENSE_DURATION_DAYS NUMBER(5),
    CREATED_AT TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- ============================================================================
-- CONTENT ENGAGEMENT TABLE
-- ============================================================================
CREATE OR REPLACE TABLE CONTENT_ENGAGEMENT (
    ENGAGEMENT_ID VARCHAR(50) PRIMARY KEY,
    CONTENT_ID VARCHAR(50) NOT NULL REFERENCES VISUAL_CONTENT(CONTENT_ID),
    DATE DATE NOT NULL,
    VIEWS NUMBER(10) DEFAULT 0,
    DOWNLOADS NUMBER(10) DEFAULT 0,
    PREVIEWS NUMBER(10) DEFAULT 0,
    ENGAGEMENT_SCORE NUMBER(5,2),
    TIME_ON_PAGE NUMBER(10,2),
    SEARCH_APPEARANCES NUMBER(10) DEFAULT 0,
    CREATED_AT TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- ============================================================================
-- INDEXES FOR PERFORMANCE
-- ============================================================================
-- Create clustering keys for frequently queried columns
ALTER TABLE VISUAL_CONTENT CLUSTER BY (CATEGORY, UPLOAD_DATE);
ALTER TABLE LICENSING_REVENUE CLUSTER BY (YEAR, QUARTER, REGION);
ALTER TABLE CONTENT_ENGAGEMENT CLUSTER BY (DATE);

-- ============================================================================
-- VIEWS FOR COMMON QUERIES
-- ============================================================================

-- Revenue by Category View
CREATE OR REPLACE VIEW V_REVENUE_BY_CATEGORY AS
SELECT
    vc.CATEGORY,
    lr.YEAR,
    lr.QUARTER,
    COUNT(DISTINCT lr.TRANSACTION_ID) as TRANSACTION_COUNT,
    SUM(lr.REVENUE) as TOTAL_REVENUE,
    AVG(lr.REVENUE) as AVG_REVENUE,
    COUNT(DISTINCT lr.CUSTOMER_ID) as UNIQUE_CUSTOMERS
FROM VISUAL_CONTENT vc
JOIN LICENSING_REVENUE lr ON vc.CONTENT_ID = lr.CONTENT_ID
GROUP BY vc.CATEGORY, lr.YEAR, lr.QUARTER;

-- Content Performance View
CREATE OR REPLACE VIEW V_CONTENT_PERFORMANCE AS
SELECT
    vc.CONTENT_ID,
    vc.TITLE,
    vc.CATEGORY,
    vc.CONTENT_FORMAT,
    vc.REGION as CONTENT_REGION,
    SUM(ce.VIEWS) as TOTAL_VIEWS,
    SUM(ce.DOWNLOADS) as TOTAL_DOWNLOADS,
    AVG(ce.ENGAGEMENT_SCORE) as AVG_ENGAGEMENT,
    COALESCE(SUM(lr.REVENUE), 0) as TOTAL_REVENUE
FROM VISUAL_CONTENT vc
LEFT JOIN CONTENT_ENGAGEMENT ce ON vc.CONTENT_ID = ce.CONTENT_ID
LEFT JOIN LICENSING_REVENUE lr ON vc.CONTENT_ID = lr.CONTENT_ID
GROUP BY vc.CONTENT_ID, vc.TITLE, vc.CATEGORY, vc.CONTENT_FORMAT, vc.REGION;

-- Customer Analytics View
CREATE OR REPLACE VIEW V_CUSTOMER_ANALYTICS AS
SELECT
    c.CUSTOMER_ID,
    c.CUSTOMER_NAME,
    c.SEGMENT,
    c.INDUSTRY,
    c.REGION,
    c.ACQUISITION_DATE,
    COUNT(DISTINCT lr.TRANSACTION_ID) as TOTAL_TRANSACTIONS,
    SUM(lr.REVENUE) as TOTAL_SPEND,
    AVG(lr.REVENUE) as AVG_TRANSACTION_VALUE,
    MAX(lr.TRANSACTION_DATE) as LAST_PURCHASE_DATE
FROM CUSTOMERS c
LEFT JOIN LICENSING_REVENUE lr ON c.CUSTOMER_ID = lr.CUSTOMER_ID
GROUP BY c.CUSTOMER_ID, c.CUSTOMER_NAME, c.SEGMENT, c.INDUSTRY, c.REGION, c.ACQUISITION_DATE;

-- Regional Revenue Trends View
CREATE OR REPLACE VIEW V_REGIONAL_TRENDS AS
SELECT
    lr.REGION,
    lr.YEAR,
    lr.QUARTER,
    vc.CATEGORY,
    SUM(lr.REVENUE) as TOTAL_REVENUE,
    COUNT(DISTINCT lr.CUSTOMER_ID) as ACTIVE_CUSTOMERS,
    COUNT(DISTINCT lr.CONTENT_ID) as LICENSED_CONTENT_COUNT
FROM LICENSING_REVENUE lr
JOIN VISUAL_CONTENT vc ON lr.CONTENT_ID = vc.CONTENT_ID
GROUP BY lr.REGION, lr.YEAR, lr.QUARTER, vc.CATEGORY;

-- ============================================================================
-- STAGE FOR SEMANTIC MODEL
-- ============================================================================
CREATE STAGE IF NOT EXISTS SEMANTIC_MODELS
  DIRECTORY = (ENABLE = TRUE)
  COMMENT = 'Stage for storing Cortex Analyst semantic model files';

-- Upload semantic model (run this after creating the YAML file)
-- PUT file://rum_content_model.yaml @SEMANTIC_MODELS AUTO_COMPRESS=FALSE;

-- ============================================================================
-- GRANTS FOR ANALYST ROLE
-- ============================================================================
CREATE ROLE IF NOT EXISTS ANALYST_ROLE;

GRANT USAGE ON DATABASE RUM_ANALYTICS TO ROLE ANALYST_ROLE;
GRANT USAGE ON SCHEMA RUM_ANALYTICS.PUBLIC TO ROLE ANALYST_ROLE;
GRANT SELECT ON ALL TABLES IN SCHEMA RUM_ANALYTICS.PUBLIC TO ROLE ANALYST_ROLE;
GRANT SELECT ON ALL VIEWS IN SCHEMA RUM_ANALYTICS.PUBLIC TO ROLE ANALYST_ROLE;
GRANT USAGE ON WAREHOUSE RUM_ANALYTICS_WH TO ROLE ANALYST_ROLE;
GRANT READ ON STAGE SEMANTIC_MODELS TO ROLE ANALYST_ROLE;

-- Grant Cortex access
GRANT DATABASE ROLE SNOWFLAKE.CORTEX_USER TO ROLE ANALYST_ROLE;

-- ============================================================================
-- END OF SCHEMA
-- ============================================================================
