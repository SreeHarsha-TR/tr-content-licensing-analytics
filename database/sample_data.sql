-- ============================================================================
-- RUM Visual Content Analytics - Sample Data
-- ============================================================================
-- This script populates the database with realistic sample data for testing
-- ============================================================================

USE DATABASE RUM_ANALYTICS;
USE SCHEMA PUBLIC;

-- ============================================================================
-- GENERATE VISUAL CONTENT SAMPLE DATA
-- ============================================================================

-- Create a sequence for generating IDs
CREATE OR REPLACE SEQUENCE SEQ_CONTENT START = 1 INCREMENT = 1;
CREATE OR REPLACE SEQUENCE SEQ_CUSTOMER START = 1 INCREMENT = 1;
CREATE OR REPLACE SEQUENCE SEQ_TRANSACTION START = 1 INCREMENT = 1;
CREATE OR REPLACE SEQUENCE SEQ_ENGAGEMENT START = 1 INCREMENT = 1;

-- Insert sample visual content (1000+ items)
INSERT INTO VISUAL_CONTENT (CONTENT_ID, TITLE, CATEGORY, UPLOAD_DATE, PHOTOGRAPHER, CONTENT_FORMAT, REGION, IS_EXCLUSIVE)
SELECT
    'CNT' || LPAD(SEQ_CONTENT.NEXTVAL::VARCHAR, 6, '0'),
    CASE MOD(ROW_NUMBER() OVER (ORDER BY SEQ4()), 20)
        WHEN 0 THEN 'Breaking: Major Event Coverage'
        WHEN 1 THEN 'Championship Finals Highlights'
        WHEN 2 THEN 'Celebrity Red Carpet Arrival'
        WHEN 3 THEN 'CEO Annual Shareholder Meeting'
        WHEN 4 THEN 'World Leaders Summit Discussion'
        WHEN 5 THEN 'Travel Destination Feature'
        WHEN 6 THEN 'Emergency Response Coverage'
        WHEN 7 THEN 'Olympic Athlete Training'
        WHEN 8 THEN 'Film Premiere Event'
        WHEN 9 THEN 'Stock Market Trading Floor'
        WHEN 10 THEN 'Election Campaign Rally'
        WHEN 11 THEN 'Food and Cuisine Photography'
        WHEN 12 THEN 'Natural Disaster Coverage'
        WHEN 13 THEN 'Soccer World Cup Match'
        WHEN 14 THEN 'Music Festival Performance'
        WHEN 15 THEN 'Tech Conference Keynote'
        WHEN 16 THEN 'Government Press Conference'
        WHEN 17 THEN 'Wellness and Fitness Feature'
        WHEN 18 THEN 'Weather Event Documentation'
        ELSE 'Tennis Grand Slam Final'
    END || ' - ' || ROW_NUMBER() OVER (ORDER BY SEQ4()),
    CASE MOD(ROW_NUMBER() OVER (ORDER BY SEQ4()), 6)
        WHEN 0 THEN 'Breaking News'
        WHEN 1 THEN 'Sports'
        WHEN 2 THEN 'Entertainment'
        WHEN 3 THEN 'Business'
        WHEN 4 THEN 'Politics'
        ELSE 'Lifestyle'
    END,
    DATEADD(day, -UNIFORM(0, 730, RANDOM()), CURRENT_DATE()),
    CASE MOD(ROW_NUMBER() OVER (ORDER BY SEQ4()), 10)
        WHEN 0 THEN 'Sarah Johnson'
        WHEN 1 THEN 'Michael Chen'
        WHEN 2 THEN 'Emma Williams'
        WHEN 3 THEN 'David Garcia'
        WHEN 4 THEN 'Lisa Anderson'
        WHEN 5 THEN 'James Wilson'
        WHEN 6 THEN 'Maria Rodriguez'
        WHEN 7 THEN 'Robert Taylor'
        WHEN 8 THEN 'Jennifer Martinez'
        ELSE 'Christopher Lee'
    END,
    CASE MOD(ROW_NUMBER() OVER (ORDER BY SEQ4()), 3)
        WHEN 0 THEN 'Photo'
        WHEN 1 THEN 'Video'
        ELSE 'Graphic'
    END,
    CASE MOD(ROW_NUMBER() OVER (ORDER BY SEQ4()), 4)
        WHEN 0 THEN 'North America'
        WHEN 1 THEN 'EMEA'
        WHEN 2 THEN 'APAC'
        ELSE 'LATAM'
    END,
    CASE WHEN UNIFORM(0, 10, RANDOM()) > 8 THEN TRUE ELSE FALSE END
FROM TABLE(GENERATOR(ROWCOUNT => 1200));

-- ============================================================================
-- GENERATE CUSTOMER SAMPLE DATA
-- ============================================================================
INSERT INTO CUSTOMERS (CUSTOMER_ID, CUSTOMER_NAME, SEGMENT, INDUSTRY, REGION, ACQUISITION_DATE, SUBSCRIPTION_TIER)
SELECT
    'CUS' || LPAD(SEQ_CUSTOMER.NEXTVAL::VARCHAR, 5, '0'),
    CASE MOD(ROW_NUMBER() OVER (ORDER BY SEQ4()), 30)
        WHEN 0 THEN 'Global News Network'
        WHEN 1 THEN 'Sports Illustrated Media'
        WHEN 2 THEN 'Entertainment Weekly Inc'
        WHEN 3 THEN 'Financial Times Group'
        WHEN 4 THEN 'Political Digest Corp'
        WHEN 5 THEN 'Lifestyle Magazine Co'
        WHEN 6 THEN 'Breaking News 24/7'
        WHEN 7 THEN 'ESPN Digital'
        WHEN 8 THEN 'Hollywood Reporter'
        WHEN 9 THEN 'Bloomberg Media'
        WHEN 10 THEN 'Reuters Partners'
        WHEN 11 THEN 'Travel & Leisure Group'
        WHEN 12 THEN 'CNN International'
        WHEN 13 THEN 'Sky Sports Network'
        WHEN 14 THEN 'Variety Entertainment'
        WHEN 15 THEN 'Wall Street Journal'
        WHEN 16 THEN 'Associated Press'
        WHEN 17 THEN 'National Geographic'
        WHEN 18 THEN 'BBC World Service'
        WHEN 19 THEN 'Fox Sports Media'
        WHEN 20 THEN 'People Magazine'
        WHEN 21 THEN 'Forbes Media'
        WHEN 22 THEN 'The Guardian News'
        WHEN 23 THEN 'Conde Nast'
        WHEN 24 THEN 'NBC Universal'
        WHEN 25 THEN 'Al Jazeera Media'
        WHEN 26 THEN 'Vice Media Group'
        WHEN 27 THEN 'Hearst Corporation'
        WHEN 28 THEN 'Discovery Networks'
        ELSE 'Vox Media'
    END || ' ' || ROW_NUMBER() OVER (ORDER BY SEQ4()),
    CASE MOD(ROW_NUMBER() OVER (ORDER BY SEQ4()), 4)
        WHEN 0 THEN 'Enterprise'
        WHEN 1 THEN 'Mid-Market'
        WHEN 2 THEN 'SMB'
        ELSE 'Agency'
    END,
    CASE MOD(ROW_NUMBER() OVER (ORDER BY SEQ4()), 5)
        WHEN 0 THEN 'Media'
        WHEN 1 THEN 'Publishing'
        WHEN 2 THEN 'Advertising'
        WHEN 3 THEN 'Corporate'
        ELSE 'Government'
    END,
    CASE MOD(ROW_NUMBER() OVER (ORDER BY SEQ4()), 4)
        WHEN 0 THEN 'North America'
        WHEN 1 THEN 'EMEA'
        WHEN 2 THEN 'APAC'
        ELSE 'LATAM'
    END,
    DATEADD(day, -UNIFORM(30, 1095, RANDOM()), CURRENT_DATE()),
    CASE MOD(ROW_NUMBER() OVER (ORDER BY SEQ4()), 3)
        WHEN 0 THEN 'Premium'
        WHEN 1 THEN 'Professional'
        ELSE 'Basic'
    END
FROM TABLE(GENERATOR(ROWCOUNT => 200));

-- ============================================================================
-- GENERATE LICENSING REVENUE SAMPLE DATA
-- ============================================================================
INSERT INTO LICENSING_REVENUE (TRANSACTION_ID, CONTENT_ID, CUSTOMER_ID, REVENUE, TRANSACTION_DATE, QUARTER, YEAR, LICENSE_TYPE, REGION, LICENSE_DURATION_DAYS)
SELECT
    'TXN' || LPAD(SEQ_TRANSACTION.NEXTVAL::VARCHAR, 7, '0'),
    'CNT' || LPAD(UNIFORM(1, 1200, RANDOM())::VARCHAR, 6, '0'),
    'CUS' || LPAD(UNIFORM(1, 200, RANDOM())::VARCHAR, 5, '0'),
    CASE
        WHEN UNIFORM(0, 100, RANDOM()) > 95 THEN UNIFORM(5000, 25000, RANDOM()) -- Premium exclusive
        WHEN UNIFORM(0, 100, RANDOM()) > 80 THEN UNIFORM(1000, 5000, RANDOM()) -- Commercial
        ELSE UNIFORM(50, 1000, RANDOM()) -- Editorial
    END,
    tx_date.date_val,
    'Q' || QUARTER(tx_date.date_val),
    YEAR(tx_date.date_val),
    CASE MOD(ROW_NUMBER() OVER (ORDER BY SEQ4()), 3)
        WHEN 0 THEN 'Editorial'
        WHEN 1 THEN 'Commercial'
        ELSE 'Exclusive'
    END,
    CASE MOD(ROW_NUMBER() OVER (ORDER BY SEQ4()), 4)
        WHEN 0 THEN 'North America'
        WHEN 1 THEN 'EMEA'
        WHEN 2 THEN 'APAC'
        ELSE 'LATAM'
    END,
    CASE MOD(ROW_NUMBER() OVER (ORDER BY SEQ4()), 4)
        WHEN 0 THEN 30
        WHEN 1 THEN 90
        WHEN 2 THEN 180
        ELSE 365
    END
FROM TABLE(GENERATOR(ROWCOUNT => 15000)) gen
CROSS JOIN (
    SELECT DATEADD(day, -UNIFORM(0, 730, RANDOM()), CURRENT_DATE()) as date_val
    FROM TABLE(GENERATOR(ROWCOUNT => 1))
) tx_date;

-- ============================================================================
-- GENERATE CONTENT ENGAGEMENT SAMPLE DATA
-- ============================================================================
INSERT INTO CONTENT_ENGAGEMENT (ENGAGEMENT_ID, CONTENT_ID, DATE, VIEWS, DOWNLOADS, PREVIEWS, ENGAGEMENT_SCORE, TIME_ON_PAGE, SEARCH_APPEARANCES)
SELECT
    'ENG' || LPAD(SEQ_ENGAGEMENT.NEXTVAL::VARCHAR, 8, '0'),
    'CNT' || LPAD(content_num::VARCHAR, 6, '0'),
    engagement_date,
    UNIFORM(100, 10000, RANDOM()),
    UNIFORM(5, 500, RANDOM()),
    UNIFORM(50, 2000, RANDOM()),
    UNIFORM(20, 100, RANDOM())::NUMBER(5,2),
    UNIFORM(5, 180, RANDOM())::NUMBER(10,2),
    UNIFORM(10, 1000, RANDOM())
FROM (
    SELECT
        UNIFORM(1, 1200, RANDOM()) as content_num,
        DATEADD(day, -seq4(), CURRENT_DATE()) as engagement_date
    FROM TABLE(GENERATOR(ROWCOUNT => 365))
) dates
CROSS JOIN TABLE(GENERATOR(ROWCOUNT => 50));

-- ============================================================================
-- UPDATE CUSTOMER LIFETIME VALUE
-- ============================================================================
UPDATE CUSTOMERS c
SET LIFETIME_VALUE = (
    SELECT COALESCE(SUM(lr.REVENUE), 0)
    FROM LICENSING_REVENUE lr
    WHERE lr.CUSTOMER_ID = c.CUSTOMER_ID
);

-- ============================================================================
-- VERIFY DATA
-- ============================================================================
SELECT 'VISUAL_CONTENT' as TABLE_NAME, COUNT(*) as ROW_COUNT FROM VISUAL_CONTENT
UNION ALL
SELECT 'CUSTOMERS', COUNT(*) FROM CUSTOMERS
UNION ALL
SELECT 'LICENSING_REVENUE', COUNT(*) FROM LICENSING_REVENUE
UNION ALL
SELECT 'CONTENT_ENGAGEMENT', COUNT(*) FROM CONTENT_ENGAGEMENT
UNION ALL
SELECT 'CONTENT_CATEGORIES', COUNT(*) FROM CONTENT_CATEGORIES;

-- ============================================================================
-- SAMPLE QUERIES FOR TESTING
-- ============================================================================

-- Test Query 1: Revenue by category this quarter
SELECT
    vc.CATEGORY,
    SUM(lr.REVENUE) as TOTAL_REVENUE,
    COUNT(DISTINCT lr.TRANSACTION_ID) as TRANSACTIONS
FROM VISUAL_CONTENT vc
JOIN LICENSING_REVENUE lr ON vc.CONTENT_ID = lr.CONTENT_ID
WHERE lr.QUARTER = 'Q' || QUARTER(CURRENT_DATE())
  AND lr.YEAR = YEAR(CURRENT_DATE())
GROUP BY vc.CATEGORY
ORDER BY TOTAL_REVENUE DESC;

-- Test Query 2: Top 10 customers by revenue
SELECT
    c.CUSTOMER_NAME,
    c.SEGMENT,
    SUM(lr.REVENUE) as TOTAL_SPEND
FROM CUSTOMERS c
JOIN LICENSING_REVENUE lr ON c.CUSTOMER_ID = lr.CUSTOMER_ID
GROUP BY c.CUSTOMER_NAME, c.SEGMENT
ORDER BY TOTAL_SPEND DESC
LIMIT 10;

-- Test Query 3: Content engagement metrics
SELECT
    vc.CATEGORY,
    SUM(ce.VIEWS) as TOTAL_VIEWS,
    SUM(ce.DOWNLOADS) as TOTAL_DOWNLOADS,
    AVG(ce.ENGAGEMENT_SCORE) as AVG_ENGAGEMENT
FROM VISUAL_CONTENT vc
JOIN CONTENT_ENGAGEMENT ce ON vc.CONTENT_ID = ce.CONTENT_ID
GROUP BY vc.CATEGORY
ORDER BY TOTAL_VIEWS DESC;

-- ============================================================================
-- END OF SAMPLE DATA
-- ============================================================================
