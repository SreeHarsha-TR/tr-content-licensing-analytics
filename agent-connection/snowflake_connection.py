"""
Snowflake Connection using PAT (Programmatic Access Token)
Connects to the Hackathon 2026 Reuters Semantic schema.
"""

import snowflake.connector
import os
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Configuration – all values loaded from environment variables / .env file
# ---------------------------------------------------------------------------
SNOWFLAKE_ACCOUNT   = os.getenv("SNOWFLAKE_ACCOUNT",   "THOMSONREUTERS-A206448_PROD")
SNOWFLAKE_USER      = os.getenv("SNOWFLAKE_USER",      "")
SNOWFLAKE_PAT       = os.getenv("SNOWFLAKE_TOKEN",     "")
SNOWFLAKE_WAREHOUSE = os.getenv("SNOWFLAKE_WAREHOUSE", "A206448_DATA_HACKATHON_2026_IDT_AUTOMATES_MDS_WH")
SNOWFLAKE_DATABASE  = os.getenv("SNOWFLAKE_DATABASE",  "MYDATASPACE")
SNOWFLAKE_SCHEMA    = os.getenv("SNOWFLAKE_SCHEMA",    "A206448_DATA_HACKATHON_2026_IDT_AUTOMATES")
SNOWFLAKE_ROLE      = os.getenv("SNOWFLAKE_ROLE",      "A206448_DATA_HACKATHON_2026_IDT_AUTOMATES_MDS_OWNER")


def get_connection() -> snowflake.connector.SnowflakeConnection:
    """
    Establish and return a Snowflake connection authenticated via PAT token.

    PAT tokens are passed using the 'token' authenticator combined with
    the 'oauth' authenticator type so the connector treats the value as
    a bearer token (same mechanism as OAuth / external browser tokens).
    """
    conn = snowflake.connector.connect(
        account=SNOWFLAKE_ACCOUNT,
        user=SNOWFLAKE_USER,
        authenticator="programmatic_access_token",  # Dedicated authenticator for PAT tokens
        token=SNOWFLAKE_PAT,
        warehouse=SNOWFLAKE_WAREHOUSE,
        database=SNOWFLAKE_DATABASE,
        schema=SNOWFLAKE_SCHEMA,
        role=SNOWFLAKE_ROLE,
        session_parameters={
            "QUERY_TAG": "hackathon_2026_reuters"
        },
    )
    return conn


def test_connection(conn: snowflake.connector.SnowflakeConnection) -> None:
    """Run a simple query to verify the connection is healthy."""
    with conn.cursor() as cur:
        cur.execute("SELECT CURRENT_USER(), CURRENT_ROLE(), CURRENT_DATABASE(), CURRENT_SCHEMA(), CURRENT_WAREHOUSE()")
        row = cur.fetchone()
        print("✅ Connection successful!")
        print(f"   User       : {row[0]}")
        print(f"   Role       : {row[1]}")
        print(f"   Database   : {row[2]}")
        print(f"   Schema     : {row[3]}")
        print(f"   Warehouse  : {row[4]}")


def sample_query(conn: snowflake.connector.SnowflakeConnection) -> None:
    """Fetch a small sample from one of the Hackathon tables."""
    query = """
        select * from MYDATASPACE.A206448_DATA_HACKATHON_2026_IDT_AUTOMATES.V_GOLD_BILLING_ACCOUNT_DIM LIMIT 5;
    """
    with conn.cursor() as cur:
        cur.execute(query)
        rows = cur.fetchall()
        print("\n📋 Sample rows from GOLD_BILLING_ACCOUNT_DIM:")
        for row in rows:
            print(row)


if __name__ == "__main__":
    conn = None
    try:
        print("🔗 Connecting to Snowflake …")
        conn = get_connection()
        test_connection(conn)
        sample_query(conn)
    except snowflake.connector.errors.DatabaseError as exc:
        print(f"❌ Connection failed: {exc}")
    finally:
        if conn and not conn.is_closed():
            conn.close()
            print("\n🔒 Connection closed.")
