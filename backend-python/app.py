import os
import json
import uuid
import re
from datetime import datetime
from decimal import Decimal
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from dotenv import load_dotenv
import snowflake.connector
from openai import OpenAI

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app, origins=['http://localhost:3000'])

# Anthropic/LiteLLM Configuration (from environment variables)
ANTHROPIC_BASE_URL = os.getenv('ANTHROPIC_BASE_URL', 'https://litellm.int.thomsonreuters.com/v1')
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_AUTH_TOKEN')
ANTHROPIC_MODEL = os.getenv('ANTHROPIC_MODEL', 'anthropic/claude-opus-4-5')

# Snowflake connection settings - PAT Token Authentication (from environment variables)
SNOWFLAKE_ACCOUNT = os.getenv('SNOWFLAKE_ACCOUNT')
SNOWFLAKE_USER = os.getenv('SNOWFLAKE_USER')
SNOWFLAKE_PAT_TOKEN = os.getenv('SNOWFLAKE_TOKEN')
SNOWFLAKE_WAREHOUSE = os.getenv('SNOWFLAKE_WAREHOUSE')
SNOWFLAKE_DATABASE = os.getenv('SNOWFLAKE_DATABASE', 'MYDATASPACE')
SNOWFLAKE_SCHEMA = os.getenv('SNOWFLAKE_SCHEMA')
SNOWFLAKE_ROLE = os.getenv('SNOWFLAKE_ROLE')

# Database Schema Information for Claude
DATABASE_SCHEMA = """
You are a SQL expert. Generate Snowflake SQL queries based on the user's question.
Use the following database schema:

DATABASE: MYDATASPACE
SCHEMA: A206448_DATA_HACKATHON_2026_IDT_AUTOMATES

=== TABLE: V_GOLD_FACT_ITEM_ORDERED ===
Description: Main fact table containing order line items with revenue data
Columns:
- ORDERIDENTIFIER (VARCHAR): Unique order identifier
- BILLING_ACCOUNT_ID (VARCHAR): Link to billing account
- CONTACT_ID (VARCHAR): Link to contact
- ASSET_ID (VARCHAR): Asset/content identifier
- MEDIA_TYPE (VARCHAR): Type of media (Photo, Video, etc.)
- PHOTOGRAPHER_XCODE (VARCHAR): Photographer identifier
- STATUS (VARCHAR): Order status
- CURRENCY (VARCHAR): Transaction currency
- TOTAL_AMOUNT_WITHOUT_TAX (NUMBER): Amount in local currency
- TOTAL_AMOUNT_WITHOUT_TAX_HOME (NUMBER): Amount in USD (use this for revenue calculations)
- CREATED_DATE (TIMESTAMP): Order creation date

=== TABLE: V_GOLD_BILLING_ACCOUNT_DIM ===
Description: Customer billing account dimension
Columns:
- ACCOUNT_ID (VARCHAR): Primary key, links to BILLING_ACCOUNT_ID in fact table
- ACCOUNT_NAME (VARCHAR): Customer/company name
- INDUSTRY (VARCHAR): Industry classification
- SOLD_TO_COUNTRY (VARCHAR): Country of the customer
- SOLD_TO_STATE (VARCHAR): State/region
- SOLD_TO_CITY (VARCHAR): City

=== TABLE: V_GOLD_CONTACT_DIM ===
Description: Contact/user dimension
Columns:
- CONTACT_ID (VARCHAR): Primary key
- FIRST_NAME (VARCHAR): Contact first name
- LAST_NAME (VARCHAR): Contact last name
- EMAIL (VARCHAR): Contact email
- CONTACT_STATUS (VARCHAR): Active/Inactive status

=== TABLE: V_GOLD_ORGANIZATION_ACCOUNT_DIM ===
Description: Organization account dimension
Columns:
- ORGANIZATION_ACCOUNT_ID (VARCHAR): Primary key
- ORGANIZATION_ACCOUNT_NAME (VARCHAR): Organization name
- ORGANIZATION_ACCOUNT_TYPE (VARCHAR): Type of organization

=== TABLE: V_GOLD_USAGE_AGREEMENT_CONTRACT_DIM ===
Description: License/contract agreements
Columns:
- CLA_CONTRACT_ID (VARCHAR): Contract identifier
- CLA_CONTRACT_USAGETYPE (VARCHAR): Usage type (Editorial, Commercial, etc.)
- CLA_CONTRACT_STATUS (VARCHAR): Contract status

=== TABLE: V_GOLD_FACT_CONTENT_LICENSE_CONTRACT_CREATED ===
Description: Content licensing events
Columns:
- LICENSE_ID (VARCHAR): License identifier
- CONTRACT_ID (VARCHAR): Related contract
- CONTENT_ID (VARCHAR): Content/asset identifier
- CREATED_DATE (TIMESTAMP): License creation date

IMPORTANT RULES:
1. Always use TOTAL_AMOUNT_WITHOUT_TAX_HOME for revenue calculations (it's in USD)
2. Join V_GOLD_FACT_ITEM_ORDERED with V_GOLD_BILLING_ACCOUNT_DIM using BILLING_ACCOUNT_ID = ACCOUNT_ID
3. Use DATE_TRUNC for date grouping
4. Always add LIMIT clause (default 100) unless user asks for all data
5. Return ONLY the SQL query, no explanations or markdown
6. Use proper Snowflake SQL syntax
"""

# Initialize OpenAI-compatible client for LiteLLM proxy
claude_client = OpenAI(
    api_key=ANTHROPIC_API_KEY,
    base_url=ANTHROPIC_BASE_URL
)

# Global Snowflake connection
_connection = None

def get_connection():
    global _connection
    if _connection is None or _connection.is_closed():
        print("\n" + "="*60)
        print("Connecting to Snowflake with PAT token...")
        print(f"Account: {SNOWFLAKE_ACCOUNT}")
        print(f"User: {SNOWFLAKE_USER}")
        print(f"Database: {SNOWFLAKE_DATABASE}")
        print(f"Schema: {SNOWFLAKE_SCHEMA}")
        print("="*60 + "\n")

        _connection = snowflake.connector.connect(
            account=SNOWFLAKE_ACCOUNT,
            user=SNOWFLAKE_USER,
            authenticator="programmatic_access_token",
            token=SNOWFLAKE_PAT_TOKEN,
            warehouse=SNOWFLAKE_WAREHOUSE,
            database=SNOWFLAKE_DATABASE,
            schema=SNOWFLAKE_SCHEMA,
            role=SNOWFLAKE_ROLE,
            session_parameters={
                "QUERY_TAG": "hackathon_2026_reuters"
            },
        )

        print("\n[OK] Successfully connected to Snowflake!")
        print(f"  Database: {SNOWFLAKE_DATABASE}")
        print(f"  Schema: {SNOWFLAKE_SCHEMA}")
        print(f"  Warehouse: {SNOWFLAKE_WAREHOUSE}\n")

    return _connection

def execute_query(sql):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(sql)
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        rows = cursor.fetchall()
        results = [dict(zip(columns, row)) for row in rows]
        return results, columns
    finally:
        cursor.close()

def generate_sql_with_claude(question):
    """Use Claude LLM to generate SQL from natural language question"""
    try:
        print(f"[LLM] Sending question to Claude: {question}")

        response = claude_client.chat.completions.create(
            model=ANTHROPIC_MODEL,
            max_tokens=1024,
            messages=[
                {
                    "role": "user",
                    "content": f"""{DATABASE_SCHEMA}

User Question: {question}

Generate a Snowflake SQL query to answer this question. Return ONLY the SQL query, nothing else. No markdown, no explanations."""
                }
            ]
        )

        # Extract SQL from response (OpenAI format)
        response_text = response.choices[0].message.content.strip()

        # Clean up the response - remove markdown code blocks if present
        if "```" in response_text:
            # Extract content between code blocks
            match = re.search(r'```(?:sql)?\s*([\s\S]*?)\s*```', response_text)
            if match:
                response_text = match.group(1).strip()

        print(f"[LLM] Generated SQL:\n{response_text}\n")
        return response_text

    except Exception as e:
        print(f"[LLM ERROR] Claude API error: {e}")
        raise Exception(f"Failed to generate SQL: {str(e)}")

def generate_answer_with_claude(question, sql, data):
    """Use Claude to generate a natural language answer based on the query results"""
    try:
        # Limit data for context
        sample_data = data[:10] if len(data) > 10 else data

        response = claude_client.chat.completions.create(
            model=ANTHROPIC_MODEL,
            max_tokens=512,
            messages=[
                {
                    "role": "user",
                    "content": f"""Based on this SQL query and its results, provide a brief, friendly answer to the user's question.

User Question: {question}

SQL Query: {sql}

Results (showing up to 10 rows):
{json.dumps(sample_data, indent=2, default=str)}

Total rows returned: {len(data)}

Provide a concise, helpful summary of the results. Be specific with numbers and insights. Keep it to 2-3 sentences."""
                }
            ]
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        print(f"[LLM ERROR] Claude API error for answer generation: {e}")
        return f"Query executed successfully. Found {len(data)} results."

def generate_suggestions(question):
    """Generate follow-up question suggestions"""
    q = question.lower()
    suggestions = []

    if 'revenue' in q:
        if 'country' not in q: suggestions.append('Revenue by country')
        if 'industry' not in q: suggestions.append('Revenue by industry')
        if 'media' not in q: suggestions.append('Revenue by media type')
        if 'month' not in q: suggestions.append('Monthly revenue trend')
    else:
        suggestions.append('Total revenue')
        suggestions.append('Top 10 customers')

    if 'customer' not in q: suggestions.append('Top customers by revenue')
    if 'photographer' not in q: suggestions.append('Top photographers')
    if 'status' not in q: suggestions.append('Orders by status')

    return suggestions[:4]

def serialize_value(value):
    if value is None:
        return None
    elif isinstance(value, datetime):
        return value.isoformat()
    elif isinstance(value, Decimal):
        return float(value)
    elif hasattr(value, 'item'):
        return value.item()
    else:
        return value

sessions = {}

@app.route('/api/health', methods=['GET'])
def health_check():
    try:
        conn = get_connection()
        connected = not conn.is_closed()
    except:
        connected = False

    return jsonify({
        'status': 'healthy',
        'snowflakeConnected': connected,
        'llmEnabled': True,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/analyst/session', methods=['POST'])
def create_session():
    session_id = str(uuid.uuid4())
    sessions[session_id] = {'messages': [], 'created': datetime.now()}
    return jsonify({'sessionId': session_id})

@app.route('/api/analyst/suggestions', methods=['GET'])
def get_suggestions():
    return jsonify({
        'suggestions': [
            'What is the total revenue?',
            'Show revenue by country',
            'Top 10 customers by revenue',
            'Monthly revenue trend'
        ]
    })

@app.route('/api/analyst/query', methods=['POST'])
def query_analyst():
    data = request.json
    question = data.get('question', '')
    session_id = data.get('sessionId', '')

    if not question:
        return jsonify({'success': False, 'error': 'Question is required'}), 400

    start_time = datetime.now()

    try:
        # Step 1: Use Claude to generate SQL from natural language
        print(f"\n{'='*60}")
        print(f"[QUERY] User question: {question}")
        print(f"{'='*60}")

        sql = generate_sql_with_claude(question)

        # Step 2: Execute the generated SQL query
        rows, columns = execute_query(sql)
        print(f"[QUERY] Returned {len(rows)} rows")

        # Serialize values for JSON response
        for row in rows:
            for key, value in row.items():
                row[key] = serialize_value(value)

        # Step 3: Generate natural language answer using Claude
        answer = generate_answer_with_claude(question, sql, rows)

        execution_time = (datetime.now() - start_time).total_seconds() * 1000

        return jsonify({
            'success': True,
            'answer': answer,
            'sql': sql,
            'data': {
                'columns': columns,
                'rows': rows,
                'rowCount': len(rows),
                'executionTime': execution_time
            },
            'suggestions': generate_suggestions(question),
            'llmGenerated': True
        })

    except Exception as e:
        print(f"[ERROR] {str(e)}")
        return jsonify({
            'success': False,
            'answer': f'Error: {str(e)}',
            'error': str(e)
        }), 500

@app.route('/api/analyst/export', methods=['POST'])
def export_data():
    data = request.json
    rows = data.get('data', [])
    format_type = data.get('format', 'csv')

    if format_type == 'json':
        return Response(
            json.dumps(rows, indent=2),
            mimetype='application/json',
            headers={'Content-Disposition': 'attachment; filename=export.json'}
        )
    else:
        if not rows:
            return Response('', mimetype='text/csv')

        headers = list(rows[0].keys())
        lines = [','.join(headers)]
        for row in rows:
            values = [str(row.get(h, '')) for h in headers]
            lines.append(','.join(values))

        return Response(
            '\n'.join(lines),
            mimetype='text/csv',
            headers={'Content-Disposition': 'attachment; filename=export.csv'}
        )

@app.route('/api/metadata/categories', methods=['GET'])
def get_categories():
    try:
        rows, _ = execute_query("""
            SELECT DISTINCT MEDIA_TYPE as name
            FROM V_GOLD_FACT_ITEM_ORDERED
            WHERE MEDIA_TYPE IS NOT NULL
            ORDER BY MEDIA_TYPE
        """)
        return jsonify([{'id': str(i+1), 'name': r['NAME']} for i, r in enumerate(rows)])
    except:
        return jsonify([
            {'id': '1', 'name': 'Photo'},
            {'id': '2', 'name': 'Video'},
            {'id': '3', 'name': 'Graphic'}
        ])

@app.route('/api/metadata/metrics', methods=['GET'])
def get_metrics():
    return jsonify([
        {'name': 'total_revenue', 'description': 'Total revenue (USD)'},
        {'name': 'order_count', 'description': 'Number of orders'},
        {'name': 'customer_count', 'description': 'Unique customers'},
        {'name': 'asset_count', 'description': 'Unique assets'}
    ])

if __name__ == '__main__':
    port = 3001
    print("")
    print("=" * 60)
    print("  TR Content Licensing Analytics - Python Backend")
    print("  WITH CLAUDE LLM SQL GENERATION")
    print("=" * 60)
    print(f"  Server running on: http://localhost:{port}")
    print(f"  Health check:      http://localhost:{port}/api/health")
    print("  Authentication:    PAT Token")
    print("  LLM:               Claude (Anthropic)")
    print("=" * 60)
    print("")

    # Test connection on startup
    try:
        get_connection()
    except Exception as e:
        print(f"Warning: Could not connect to Snowflake: {e}")

    app.run(host='0.0.0.0', port=port, debug=True)
