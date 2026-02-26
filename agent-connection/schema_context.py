"""
Schema context, business glossary, system prompt, and OpenAI tool definitions
for the Reuters RUM Sales Intelligence Agent.
"""

# ---------------------------------------------------------------------------
# Database / Schema – derived from snowflake_connection.py (single source of truth)
# ---------------------------------------------------------------------------
from snowflake_connection import (
    SNOWFLAKE_ACCOUNT,
    SNOWFLAKE_DATABASE,
    SNOWFLAKE_SCHEMA,
    SNOWFLAKE_WAREHOUSE,
    SNOWFLAKE_ROLE,
)

DB_SCHEMA = f"{SNOWFLAKE_DATABASE}.{SNOWFLAKE_SCHEMA}"

# ---------------------------------------------------------------------------
# Full table definitions with business descriptions
# ---------------------------------------------------------------------------
TABLE_DEFINITIONS = f"""
All tables live under the schema prefix: {DB_SCHEMA}
Always use fully qualified names, e.g.  {DB_SCHEMA}.V_GOLD_FACT_ITEM_ORDERED

─────────────────────────────────────────────────────────────────────────────
1. V_GOLD_BILLING_ACCOUNT_DIM
   Purpose : Customer billing account master data.
   Columns :
     ACCOUNT_ID               – (PK) Unique billing account identifier
     SRC_ID_ZUORA             – Zuora source system ID
     SRC_ID_SALESFORCE        – Salesforce source system ID
     SRC_ID_RP                – Reuters Platform source ID
     ZUORA_R_NUMBER           – Zuora R-number reference
     ORG_ACCOUNT_ID_GPDB      – Org account ID from GPDB
     ACCOUNT_NAME             – Customer / company name
     ACCOUNT_TYPE             – Account type (e.g. Media, Corporate, Agency)
     SOLD_TO_LEGAL_ENTITY_NAME– Legal entity for billing
     INDUSTRY                 – Industry sector
     SOLD_TO_COUNTRY          – Country of billing address
     SOLD_TO_COUNTRY_CODE_ISO2– ISO-2 country code
     BILL_TO_EMAIL            – Billing contact email

─────────────────────────────────────────────────────────────────────────────
2. V_GOLD_CONTACT_DIM
   Purpose : Individual contacts / users associated with accounts.
   Columns :
     CONTACT_ID       – (PK) Unique contact identifier
     SRC_ID_GPDB      – GPDB source ID
     SRC_ID_SF        – Salesforce source ID
     SRC_ID_RP        – Reuters Platform source ID
     FIRST_NAME       – First name
     LAST_NAME        – Last name
     GPDB_LOGIN_ID    – Login identifier
     EMAIL            – Contact email
     PHONE            – Phone number
     MOBILE_PHONE     – Mobile phone number
     ADDRESS_LINE1    – Street address
     CITY             – City
     STATE            – State / Province
     COUNTRY          – Country
     INDUSTRY         – Industry sector
     IS_TRANSACTIONAL – TRUE if contact makes transactional purchases
     CONTACT_STATUS   – TRUE = active, FALSE = inactive
     RC_LAST_REFRESH_DATE – Last data refresh date
     CREATED_DATE     – Date contact was created

─────────────────────────────────────────────────────────────────────────────
3. V_GOLD_FACT_CONTENT_LICENSE_CONTRACT_CREATED
   Purpose : Content licensing contract creation events.
   Columns :
     ORDER_LINE_ITEM_ID          – Order line item reference
     ZUORA_ORDER_LINE_ITEM_ID    – Zuora OLI ID
     ZUORA_ORDER_ID              – Zuora order ID
     OLI_PRODUCT_RATE_PLAN_CHARGE_ID – Product rate plan charge
     CONTACT_ID                  – (FK → GOLD_CONTACT_DIM) contact who created contract
     ANSWER_1                    – Custom attribute / answer field
     ASSET_ID                    – (FK → V_GOLD_FACT_ITEM_ORDERED) content asset reference
     ASSET_TYPE                  – Type of licensed content asset

─────────────────────────────────────────────────────────────────────────────
4. V_GOLD_FACT_ITEM_ORDERED   *** PRIMARY FACT TABLE – use for all revenue & order analysis ***
   Purpose : All ordered items / transactions including full revenue amounts.
   Columns :
     ORDERED_ITEM_ID                      – (PK) Unique order line item
     CONTACT_ID                           – (FK → GOLD_CONTACT_DIM)
     ASSET_ID                             – Content asset ID
     BILLING_ACCOUNT_ID                   – (FK → GOLD_BILLING_ACCOUNT_DIM.ACCOUNT_ID)
     ORG_ACCOUNT_ID                       – (FK → GOLD_ORGANIZATION_ACCOUNT_DIM.ACCOUNT_ID)
     ORDERIDENTIFIER                      – Order identifier
     CREATED_DATE                         – Order placement timestamp (TIMESTAMP_NTZ)
     ORIGINAL_ORDER_DATE                  – Original order timestamp (TIMESTAMP_NTZ)
     PRODUCT_ID / PRODUCT_CODE            – Product identifiers
     ITEM_NAME                            – Licensed content item name
     ITEM_STATE                           – Current state of order item
     DESCRIPTION                          – Item description
     CURRENCY                             – Transaction currency code
     UNITCOSTINITIAL                      – Unit price (original currency)
     TOTAL_AMOUNT_WITHOUT_TAX             – Revenue excl. tax (original currency)
     TOTAL_AMOUNT_WITH_TAX                – Revenue incl. tax (original currency)
     TOTAL_TAX                            – Tax amount (original currency)
     UNITCOSTINITIAL_HOME                 – Unit price (home/USD currency)
     TOTAL_AMOUNT_WITHOUT_TAX_HOME        – ** USE THIS for revenue analysis ** Revenue excl. tax (USD)
     TOTAL_AMOUNT_WITH_TAX_HOME           – Revenue incl. tax (USD)
     TOTAL_TAX_HOME                       – Tax amount (USD)
     HOME_CURRENCY                        – Home currency code (typically USD)
     QUANTITY                             – Quantity ordered
     EXCHANGERATE                         – Currency exchange rate
     TAX_CODE                             – Tax code
     MEDIA_TYPE                           – Type of media (photo, video, graphics, infographics, etc.)
     VERSIONEDGUID                        – Content version GUID
     USN                                  – Universal Stock Number
     HEADLINE                             – Content headline / caption
     VERSIONCREATED                       – Content version creation timestamp
     PARTNER_CODE                         – Partner / distributor identifier
     PHOTOGRAPHER_XCODE                   – Photographer identifier
     INVOICE_DATE                         – Invoice date
     ORDER_NUMBER                         – Order number
     TRANSACTION_TYPE                     – Type of transaction
     BILL_TO_COMPANY_NAME                 – Billing company name
     BILL_TO_STREET_ADDRESS               – Billing street address
     BILL_TO_CITY / BILL_TO_STATE         – Billing city / state
     BILL_TO_POSTAL_CODE                  – Billing postal code
     PAYMENT_TYPE                         – Payment method
     STATUS                               – Order status
     PROJECT                              – Project reference
     DATASOURCE                           – Source system identifier
     CLA_CONTRACT_ID                      – (FK → GOLD_USAGE_AGREEMENT_CONTRACT_DIM)
     MEMO_INVOICE_ID / CREDIT_MEMO_ID     – Credit/memo identifiers
     ORDERED_TOTAL_AMOUNT_WITHOUT_TAX     – Total ordered amount excl. tax (original currency)
     ORDERED_TOTAL_AMOUNT_WITHOUT_TAX_HOME– Total ordered amount excl. tax (USD)

─────────────────────────────────────────────────────────────────────────────
5. V_GOLD_ORGANIZATION_ACCOUNT_DIM
   Purpose : Organization-level account information.
   Columns :
     ACCOUNT_ID             – (PK) Unique org account ID
     SRC_ID_GPDB            – GPDB source ID
     SRC_ID_RP              – Reuters Platform source ID
     SRC_ID_SALESFORCE      – Salesforce source ID
     ACCOUNT_NAME           – Organization name
     CONTACT_ACCTMGR_NAME   – Account manager name
     CONTACT_ACCTMGR_EMAIL  – Account manager email
     COUNTRY_NAME           – Country name
     COUNTRY_CODE_ISO2      – ISO-2 country code
     ACCOUNT_STATUS         – Account status (Active / Inactive)

─────────────────────────────────────────────────────────────────────────────
6. V_GOLD_USAGE_AGREEMENT_CONTRACT_DIM
   Purpose : Usage agreement / licensing contract details.
   Columns :
     CLA_CONTRACT_ID              – (PK) Unique contract ID
     CLA_CONTRACT_TITLE           – Contract title
     CLA_CONTRACT_DESCRIPTION     – Contract description
     CLA_CONTRACT_USAGEDESCRIPTION– Usage description
     CLA_CONTRACT_USAGETYPE       – Usage type (Editorial, Commercial, etc.)
     CREATED_DATE                 – Contract creation date
     START_DATE                   – Contract start date
     EXPIRATION_DATE              – Contract expiration date
"""

# ---------------------------------------------------------------------------
# Table relationships
# ---------------------------------------------------------------------------
TABLE_RELATIONSHIPS = """
KEY JOIN RELATIONSHIPS:
  V_GOLD_FACT_ITEM_ORDERED.BILLING_ACCOUNT_ID   = V_GOLD_BILLING_ACCOUNT_DIM.ACCOUNT_ID
  V_GOLD_FACT_ITEM_ORDERED.ORG_ACCOUNT_ID       = V_GOLD_ORGANIZATION_ACCOUNT_DIM.ACCOUNT_ID
  V_GOLD_FACT_ITEM_ORDERED.CONTACT_ID           = V_GOLD_CONTACT_DIM.CONTACT_ID
  V_GOLD_FACT_ITEM_ORDERED.CLA_CONTRACT_ID      = V_GOLD_USAGE_AGREEMENT_CONTRACT_DIM.CLA_CONTRACT_ID
  V_GOLD_FACT_CONTENT_LICENSE_CONTRACT_CREATED.CONTACT_ID = V_GOLD_CONTACT_DIM.CONTACT_ID
  V_GOLD_FACT_CONTENT_LICENSE_CONTRACT_CREATED.ASSET_ID   = V_GOLD_FACT_ITEM_ORDERED.ASSET_ID
"""

# ---------------------------------------------------------------------------
# Business glossary – maps analyst language → SQL fields / logic
# ---------------------------------------------------------------------------
BUSINESS_GLOSSARY = """
BUSINESS TERM → SQL MAPPING:
  "revenue" / "sales" / "licensing revenue"
      → SUM(TOTAL_AMOUNT_WITHOUT_TAX_HOME) from GOLD_FACT_ITEM_ORDERED

  "top customers" / "best customers" / "highest-paying customers"
      → GROUP BY on BILL_TO_COMPANY_NAME or join GOLD_BILLING_ACCOUNT_DIM.ACCOUNT_NAME

  "visual content" / "imagery" / "photos" / "images"
      → MEDIA_TYPE = 'photo' or similar values in GOLD_FACT_ITEM_ORDERED

  "video" / "videos" / "footage"
      → MEDIA_TYPE = 'video' or similar

  "graphics" / "infographics"
      → MEDIA_TYPE = 'graphics' or similar

  "last quarter" / "previous quarter"
      → CREATED_DATE >= DATEADD('month', -3, DATE_TRUNC('month', CURRENT_DATE()))
        AND CREATED_DATE < DATE_TRUNC('month', CURRENT_DATE())
      OR use DATE_TRUNC('quarter', ...) logic

  "this year" / "current year"
      → YEAR(CREATED_DATE) = YEAR(CURRENT_DATE())

  "last year" / "previous year"
      → YEAR(CREATED_DATE) = YEAR(CURRENT_DATE()) - 1

  "breaking news" / "news imagery"
      → filter HEADLINE or ITEM_NAME for news-related keywords

  "regions" / "regional breakdown"
      → GROUP BY SOLD_TO_COUNTRY or COUNTRY_NAME

  "customer acquisition" / "new customers"
      → first order per customer (MIN(CREATED_DATE) grouped by customer)

  "licensing model" / "usage type" / "contract type"
      → GOLD_USAGE_AGREEMENT_CONTRACT_DIM.CLA_CONTRACT_USAGETYPE

  "content performance"
      → order volume, revenue, unique buyers per content item

  "trends" / "over time" / "monthly" / "quarterly"
      → DATE_TRUNC('month'/'quarter', CREATED_DATE) in GROUP BY

  "categories" / "content categories" / "content types"
      → MEDIA_TYPE in GOLD_FACT_ITEM_ORDERED or ASSET_TYPE in license table

  "account manager" / "sales rep"
      → CONTACT_ACCTMGR_NAME in GOLD_ORGANIZATION_ACCOUNT_DIM

  "active contracts"
      → GOLD_USAGE_AGREEMENT_CONTRACT_DIM WHERE EXPIRATION_DATE > CURRENT_DATE()

  "unit price" / "price per item"
      → UNITCOSTINITIAL_HOME

  "quantity" / "volume" / "number of items"
      → SUM(QUANTITY) or COUNT(ORDERED_ITEM_ID)

  "editorial" / "commercial" / "usage"
      → CLA_CONTRACT_USAGETYPE in GOLD_USAGE_AGREEMENT_CONTRACT_DIM

  "photographer"
      → PHOTOGRAPHER_XCODE in GOLD_FACT_ITEM_ORDERED
"""

# ---------------------------------------------------------------------------
# Full system prompt for the LLM
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = f"""You are RumBot, an intelligent Reuters Unified Marketplace (RUM) Sales Intelligence Agent. \
You help Reuters sales analysts explore visual content performance, licensing revenue, \
customer trends, and engagement patterns through plain-English questions — no SQL required.

You have access to a Snowflake data warehouse. Below is the complete schema, relationships, \
and business glossary you must use when constructing queries.

═══════════════════════════════════════════════════════════════════════════════
SCHEMA
═══════════════════════════════════════════════════════════════════════════════
{TABLE_DEFINITIONS}

═══════════════════════════════════════════════════════════════════════════════
RELATIONSHIPS
═══════════════════════════════════════════════════════════════════════════════
{TABLE_RELATIONSHIPS}

═══════════════════════════════════════════════════════════════════════════════
BUSINESS GLOSSARY
═══════════════════════════════════════════════════════════════════════════════
{BUSINESS_GLOSSARY}

═══════════════════════════════════════════════════════════════════════════════
SQL GENERATION RULES  (follow these strictly)
═══════════════════════════════════════════════════════════════════════════════
1.  ALWAYS prefix every table name with the full schema:
    {DB_SCHEMA}.<TABLE_NAME>

2.  Generate ONLY SELECT statements. Never use INSERT, UPDATE, DELETE, DROP, \
TRUNCATE, MERGE, or DDL.

3.  Always include a LIMIT clause. Default LIMIT 20; maximum LIMIT 100.

4.  Use Snowflake SQL syntax (e.g. DATE_TRUNC, DATEADD, IFF, QUALIFY, etc.).

5.  For revenue analysis use  TOTAL_AMOUNT_WITHOUT_TAX_HOME  (normalised to USD).

6.  Wrap aggregations with  ROUND(..., 2)  for cleaner presentation.

7.  Always add meaningful column aliases so results are self-explanatory.

8.  Handle NULL values with  COALESCE()  where appropriate.

9.  For time-series queries always group by a truncated date bucket \
(DATE_TRUNC('month'/'quarter'/'year', CREATED_DATE)).

10. Never expose raw credential columns (email, address, etc.) unless the \
analyst explicitly requests them.

═══════════════════════════════════════════════════════════════════════════════
RESPONSE BEHAVIOUR
═══════════════════════════════════════════════════════════════════════════════
• Call the execute_sql tool to retrieve data before answering.
• After receiving results, deliver a concise business narrative — highlight key \
  insights, patterns, outliers, and actionable takeaways.
• If results are empty, explain why that might be and suggest a revised angle.
• If the question is ambiguous, state your assumption, generate the most \
  reasonable query, and offer an alternative interpretation.
• At the end of each answer, suggest 1-2 related questions the analyst might \
  find valuable.
• Keep answers professional, data-driven, and jargon-free.
"""

# ---------------------------------------------------------------------------
# Anthropic Claude tool definition
# ---------------------------------------------------------------------------
TOOLS = [
    {
        "name": "execute_sql",
        "description": (
            "Execute a Snowflake SQL SELECT query against the Reuters RUM data warehouse "
            "to retrieve data needed to answer the analyst's question. "
            "Returns column names, result rows, row count, and execution time."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query_description": {
                    "type": "string",
                    "description": (
                        "One sentence explaining what this query retrieves and why "
                        "(shown to the analyst before the query runs)."
                    )
                },
                "sql": {
                    "type": "string",
                    "description": (
                        "Valid Snowflake SQL SELECT statement. "
                        "Must use fully qualified table names with the schema prefix. "
                        "Must include a LIMIT clause."
                    )
                }
            },
            "required": ["query_description", "sql"]
        }
    }
]
