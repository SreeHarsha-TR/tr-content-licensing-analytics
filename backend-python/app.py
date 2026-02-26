import os
import sys
import json
import uuid
import re
from datetime import datetime, date
from decimal import Decimal
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from dotenv import load_dotenv

# ── Add agent-connection directory to Python path ──────────────────────────
AGENT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'agent-connection')
sys.path.insert(0, AGENT_DIR)

from agent_v2 import ReutersRUMAgentV2 # type: ignore
from schema_context import SYSTEM_PROMPT as AGENT_SYSTEM_PROMPT # type: ignore

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app, origins=['http://localhost:3000'])


# ─────────────────────────────────────────────────────────────────────────────
# Tracked Agent – subclass that captures every SQL execution for HTTP responses
# ─────────────────────────────────────────────────────────────────────────────

class TrackedReutersAgent(ReutersRUMAgentV2):
    """
    Extends ReutersRUMAgentV2 to record every SQL query and its result during
    a single `ask()` call so the Flask endpoint can return them to the UI.
    """

    def reset_tracking(self) -> None:
        self._tracked_queries: list[dict] = []

    def execute_sql(self, sql: str) -> dict:
        result = super().execute_sql(sql)
        if not hasattr(self, '_tracked_queries'):
            self._tracked_queries = []
        self._tracked_queries.append({'sql': sql, 'result': result})
        return result

    @property
    def last_sql(self) -> str:
        queries = getattr(self, '_tracked_queries', [])
        return queries[-1]['sql'] if queries else ''

    @property
    def last_result(self) -> dict:
        queries = getattr(self, '_tracked_queries', [])
        return queries[-1]['result'] if queries else {}

    @property
    def all_tracked_queries(self) -> list[dict]:
        return getattr(self, '_tracked_queries', [])


# ─────────────────────────────────────────────────────────────────────────────
# Global agent instance (lazy-initialised on first request)
# ─────────────────────────────────────────────────────────────────────────────

_agent: TrackedReutersAgent | None = None


def get_agent() -> TrackedReutersAgent:
    global _agent
    if _agent is None:
        print("\n[AGENT] Initialising ReutersRUMAgentV2 …")
        _agent = TrackedReutersAgent(system_prompt=AGENT_SYSTEM_PROMPT)
        print("[AGENT] Ready.\n")
    return _agent

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
    elif isinstance(value, (datetime, date)):
        return value.isoformat()
    elif isinstance(value, Decimal):
        return float(value)
    elif hasattr(value, 'item'):
        return value.item()
    else:
        return value


def generate_suggestions(question: str) -> list[str]:
    """Generate follow-up question suggestions based on the current question."""
    q = question.lower()
    suggestions = []

    if 'revenue' in q:
        if 'country' not in q:    suggestions.append('Revenue by country')
        if 'industry' not in q:   suggestions.append('Revenue by industry')
        if 'media' not in q:      suggestions.append('Revenue by media type')
        if 'month' not in q:      suggestions.append('Monthly revenue trend')
    else:
        suggestions.append('Total revenue')
        suggestions.append('Top 10 customers')

    if 'customer' not in q:      suggestions.append('Top customers by revenue')
    if 'photographer' not in q:  suggestions.append('Top photographers')
    if 'status' not in q:        suggestions.append('Orders by status')

    return suggestions[:4]


sessions = {}


# ─────────────────────────────────────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/api/health', methods=['GET'])
def health_check():
    snowflake_connected = False
    try:
        agent = get_agent()
        snowflake_connected = (
            agent.conn is not None and not agent.conn.is_closed()
        )
    except Exception:
        pass

    return jsonify({
        'status': 'healthy',
        'snowflakeConnected': snowflake_connected,
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
    body = request.json
    question   = body.get('question', '')
    session_id = body.get('sessionId', '')

    if not question:
        return jsonify({'success': False, 'error': 'Question is required'}), 400

    start_time = datetime.now()

    try:
        print(f"\n{'='*60}")
        print(f"[AGENT] User question: {question}")
        print(f"{'='*60}")

        agent = get_agent()
        agent.reset_tracking()

        # Delegate the full reasoning + SQL + narrative flow to the agent
        answer = agent.ask(question)

        execution_time = (datetime.now() - start_time).total_seconds() * 1000

        # Pull SQL and tabular data from the last executed query
        sql         = agent.last_sql
        last_result = agent.last_result
        columns     = last_result.get('columns', [])
        raw_rows    = last_result.get('rows', [])

        # Serialize rows for JSON transport
        rows = [
            {k: serialize_value(v) for k, v in row.items()}
            for row in raw_rows
        ]

        print(f"[AGENT] Answer generated. Queries run: {agent._query_count}")

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
    data        = request.json
    rows        = data.get('data', [])
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
        lines   = [','.join(headers)]
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
        agent  = get_agent()
        result = agent.execute_sql(
            f"SELECT DISTINCT MEDIA_TYPE AS NAME "
            f"FROM MYDATASPACE.A206448_DATA_HACKATHON_2026_IDT_AUTOMATES.GOLD_FACT_ITEM_ORDERED "
            f"WHERE MEDIA_TYPE IS NOT NULL ORDER BY MEDIA_TYPE"
        )
        rows = result.get('rows', [])
        return jsonify([{'id': str(i + 1), 'name': r['NAME']} for i, r in enumerate(rows)])
    except Exception:
        return jsonify([
            {'id': '1', 'name': 'Photo'},
            {'id': '2', 'name': 'Video'},
            {'id': '3', 'name': 'Graphic'}
        ])


@app.route('/api/metadata/metrics', methods=['GET'])
def get_metrics():
    return jsonify([
        {'name': 'total_revenue',  'description': 'Total revenue (USD)'},
        {'name': 'order_count',    'description': 'Number of orders'},
        {'name': 'customer_count', 'description': 'Unique customers'},
        {'name': 'asset_count',    'description': 'Unique assets'}
    ])


if __name__ == '__main__':
    port = 3001
    print("")
    print("=" * 60)
    print("  TR Content Licensing Analytics – Python Backend")
    print("  Powered by ReutersRUMAgentV2 (TR Inference API)")
    print("=" * 60)
    print(f"  Server running on: http://localhost:{port}")
    print(f"  Health check:      http://localhost:{port}/api/health")
    print("  LLM:               Claude Sonnet 4.6 via TR aiopenarena")
    print("  Data:              Snowflake (PAT token auth)")
    print("=" * 60)
    print("")

    # Eagerly initialise the agent (connects to Snowflake on startup)
    try:
        get_agent()
    except Exception as e:
        print(f"Warning: Could not initialise agent on startup: {e}")

    app.run(host='0.0.0.0', port=port, debug=True)
