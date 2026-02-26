"""
Reuters RUM Sales Intelligence Agent  –  v2 (TR Inference API)
───────────────────────────────────────────────────────────────
Natural-language interface to Snowflake powered by the Thomson Reuters
internal AI inference endpoint (aiopenarena) running Claude Sonnet 4.6.

Usage
-----
  1.  Set TR_API_TOKEN in your environment (or add a .env file).
  2.  Run:  python agent_v2.py
  3.  Type questions in plain English.

Architecture
------------
  User question
      │
      ▼
  TR Inference API (Claude Sonnet 4.6)
      │  ← SQL enclosed in <sql>...</sql> tags
      ▼
  execute_sql()  →  Snowflake
      │
      ▼
  Results fed back to Claude via conversation_id
      │
      ▼
  Business narrative answer (no <sql> tags → final turn)
"""

from __future__ import annotations

import decimal
import json
import os
import re
import sys
import time
from datetime import date, datetime
from typing import Any

import requests
import snowflake.connector

# Fix Windows console encoding to support Unicode / emojis
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

# Load .env file if present (optional dependency)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# schema_context is optional – system prompt is now supplied by the user
try:
    from schema_context import SYSTEM_PROMPT as _DEFAULT_SYSTEM_PROMPT
except ImportError:
    _DEFAULT_SYSTEM_PROMPT = ""

from snowflake_connection import get_connection

# Optional: rich tables in the terminal
try:
    from tabulate import tabulate
    _HAS_TABULATE = True
except ImportError:
    _HAS_TABULATE = False


# ─────────────────────────────────────────────────────────────────────────────
# TR Inference API constants
# ─────────────────────────────────────────────────────────────────────────────

TR_INFERENCE_URL  = "https://aiopenarena.gcs.int.thomsonreuters.com/v1/inference"
TR_WORKFLOW_ID    = "04d8d46e-0806-4653-b8ba-e718d919c567"
TR_MODEL_KEY      = "anthropic_direct.claude-v4-6-sonnet"

# System-prompt suffix that teaches Claude to emit SQL inside XML tags
_SQL_TOOL_INSTRUCTIONS = """
─── SQL Tool Instructions ───────────────────────────────────────────────────
You have access to a Snowflake SQL execution tool.
When you need data to answer a question, output a block in this exact format:

<tool_call>
  <description>One-line description of what this query retrieves</description>
  <sql>
    SELECT … FROM … WHERE …
  </sql>
</tool_call>

Rules:
- Only use SELECT or WITH queries – never INSERT / UPDATE / DELETE / DROP.
- Always use fully-qualified table names as described in the schema context.
- You may issue multiple sequential tool calls (one per message).
- When you have enough data, respond with a plain business-narrative answer
  (no <tool_call> blocks) to conclude the conversation turn.
─────────────────────────────────────────────────────────────────────────────
"""


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

class _JSONEncoder(json.JSONEncoder):
    """Serialise Snowflake result types that are not JSON-native."""

    def default(self, obj: Any) -> Any:
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        if isinstance(obj, decimal.Decimal):
            return float(obj)
        return super().default(obj)


def _indent(text: str, spaces: int = 4) -> str:
    prefix = " " * spaces
    return "\n".join(prefix + line for line in text.splitlines())


def _hr(char: str = "─", width: int = 68) -> str:
    return char * width


def _extract_tool_calls(text: str) -> list[dict]:
    """
    Parse all <tool_call> blocks from *text*.
    Returns a list of dicts with 'description' and 'sql' keys.
    """
    calls = []
    pattern = re.compile(
        r"<tool_call>\s*"
        r"(?:<description>(.*?)</description>\s*)?"
        r"<sql>(.*?)</sql>\s*"
        r"</tool_call>",
        re.DOTALL | re.IGNORECASE,
    )
    for m in pattern.finditer(text):
        calls.append({
            "description": (m.group(1) or "Running query…").strip(),
            "sql": m.group(2).strip(),
        })
    return calls


def _strip_tool_calls(text: str) -> str:
    """Remove all <tool_call> blocks from *text*, returning the remainder."""
    return re.sub(
        r"<tool_call>.*?</tool_call>",
        "",
        text,
        flags=re.DOTALL | re.IGNORECASE,
    ).strip()


# ─────────────────────────────────────────────────────────────────────────────
# Agent
# ─────────────────────────────────────────────────────────────────────────────

class ReutersRUMAgentV2:
    """
    Conversational AI agent that translates natural-language analyst questions
    into Snowflake SQL, executes them, and returns business-narrative answers.

    LLM backend: Thomson Reuters aiopenarena inference API (Claude Sonnet 4.6).
    """

    MAX_ROWS   = 50    # rows fetched per query
    MAX_LOOPS  = 5     # max tool-call iterations per question

    # ── Initialisation ────────────────────────────────────────────────────────

    # Fallback bearer token (replace when expired; prefer env-var TR_API_TOKEN)
    _FALLBACK_TOKEN = ("")

    def __init__(self, system_prompt: str = "") -> None:
        self._api_token = os.getenv("TR_API_TOKEN", "") or self._FALLBACK_TOKEN
        if not self._api_token:
            raise EnvironmentError(
                "TR_API_TOKEN is not set.\n"
                "  PowerShell : $env:TR_API_TOKEN = 'eyJ...'\n"
                "  or add it to a .env file in this folder."
            )

        # System prompt supplied by the caller; append SQL tool instructions.
        # Falls back to schema_context.SYSTEM_PROMPT if nothing was provided.
        base = system_prompt.strip() or _DEFAULT_SYSTEM_PROMPT
        self._system_prompt: str = base + "\n" + _SQL_TOOL_INSTRUCTIONS

        # conversation_id returned by the TR API – reused for multi-turn.
        # Can be seeded from env-var or the .tr_conversation_id file written
        # by tr_api_test.py so an existing session is resumed automatically.
        self._conversation_id: str | None = (
            os.getenv("TR_CONVERSATION_ID")
            or self._load_conversation_id_from_file()
        )

        # Rolling plain-text transcript fed as context when conversation_id
        # is None (first turn) or when we need to inject tool results mid-turn.
        self._transcript: list[dict] = []   # [{"role": "user"|"assistant", "content": str}]
        self._query_count = 0               # queries run in the current turn

        print("🔗  Connecting to Snowflake …")
        self.conn = get_connection()
        print("✅  Snowflake connection established.\n")

    # ── Key-file helper ──────────────────────────────────────────────────────

    @staticmethod
    def _looks_like_id(s: str) -> bool:
        """Return True if *s* looks like a UUID or short numeric ID, not prose."""
        import re as _re
        return bool(_re.fullmatch(
            r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
            r"|[0-9]+",
            s.strip(), _re.IGNORECASE
        ))

    @staticmethod
    def _load_conversation_id_from_file() -> str | None:
        """Read a persisted conversation_id written by tr_api_test.py."""
        key_file = os.path.join(os.path.dirname(__file__), ".tr_conversation_id")
        try:
            with open(key_file) as f:
                cid = f.read().strip()
            if cid:
                print(f"🔑  Resuming conversation: {cid}")
                return cid
        except FileNotFoundError:
            pass
        return None

    # ── TR Inference API call ─────────────────────────────────────────────────

    def _call_api(self, query: str) -> str:
        """
        Send *query* to the TR inference endpoint and return the assistant's
        response text.  Raises RuntimeError on HTTP / API errors.
        """
        payload = {
            "workflow_id"           : TR_WORKFLOW_ID,
            "query"                 : query,
            "is_persistence_allowed": False,
            "modelparams": {
                TR_MODEL_KEY: {
                    "max_tokens"      : "64000",
                    "enable_websearch": "false",
                    "top_k"           : "250",
                    "temperature"     : "0.1",
                    "effort"          : "high",
                    "system_prompt"   : self._system_prompt,
                    "enable_reasoning": "false",
                }
            },
            "input_variables" : {},
            "conversation_id" : self._conversation_id,
        }

        headers = {
            "Content-Type" : "application/json",
            "Authorization": f"bearer {self._api_token}",
        }

        try:
            resp = requests.post(
                TR_INFERENCE_URL,
                headers=headers,
                data=json.dumps(payload),
                timeout=120,
            )
            resp.raise_for_status()
        except requests.exceptions.Timeout:
            raise RuntimeError("TR Inference API request timed out (120 s).")
        except requests.exceptions.HTTPError as exc:
            raise RuntimeError(
                f"TR Inference API HTTP error {exc.response.status_code}: "
                f"{exc.response.text[:400]}"
            )
        except requests.exceptions.RequestException as exc:
            raise RuntimeError(f"TR Inference API request failed: {exc}")

        data = resp.json()

        # ── Extract conversation_id ───────────────────────────────────────────
        # Confirmed shape: top-level "conversation_id" (may be null)
        conv_id = data.get("conversation_id") or data.get("connection_id")
        if conv_id:
            self._conversation_id = conv_id

        # ── Extract assistant text ────────────────────────────────────────────
        # Confirmed response path (from live API inspection):
        #   data["result"]["answer"]["anthropic_direct.claude-v4-6-sonnet"]
        result_obj  = data.get("result") or {}
        answer_obj  = result_obj.get("answer") or {}

        # Primary: model key inside result.answer
        answer = answer_obj.get(TR_MODEL_KEY, "").strip()

        # Fallback 1: any non-empty string value in result.answer
        if not answer:
            for v in answer_obj.values():
                if isinstance(v, str) and v.strip():
                    answer = v.strip()
                    break

        # Fallback 2: well-known top-level / result keys
        if not answer:
            for src in (data, result_obj):
                for k in ("response", "output", "text", "message", "content"):
                    v = src.get(k, "")
                    if isinstance(v, str) and v.strip():
                        answer = v.strip()
                        break
                if answer:
                    break

        if not answer:
            print("\n  ⚠️  DEBUG – full API response:")
            print(json.dumps(data, indent=2))
            raise RuntimeError(
                "TR Inference API returned an unrecognised response shape "
                "(see debug output above)."
            )
        return answer

    # ── SQL execution ─────────────────────────────────────────────────────────

    def execute_sql(self, sql: str) -> dict:
        """
        Execute *sql* safely (SELECT-only) and return a result dict.
        Always returns a dict with either 'error' or 'columns'+'rows' keys.
        """
        sql_clean  = sql.strip()
        normalised = sql_clean.upper().lstrip("(").lstrip()
        if not (normalised.startswith("SELECT") or normalised.startswith("WITH")):
            return {"error": "Only SELECT / WITH queries are permitted."}

        try:
            t0 = time.perf_counter()
            with self.conn.cursor(snowflake.connector.DictCursor) as cur:
                cur.execute(sql_clean)
                rows    = cur.fetchmany(self.MAX_ROWS)
                columns = [d[0] for d in cur.description]
                elapsed = round(time.perf_counter() - t0, 2)

            self._query_count += 1
            return {
                "columns"    : columns,
                "rows"       : rows,
                "row_count"  : len(rows),
                "truncated"  : len(rows) == self.MAX_ROWS,
                "elapsed_sec": elapsed,
            }

        except snowflake.connector.errors.ProgrammingError as exc:
            return {"error": str(exc)}
        except Exception as exc:
            return {"error": f"Unexpected error: {exc}"}

    # ── Result rendering ──────────────────────────────────────────────────────

    def _render_table(self, result: dict) -> str:
        """Return a formatted table string from a successful SQL result."""
        if result.get("row_count", 0) == 0:
            return "  (no rows returned)"

        rows    = result["rows"]
        columns = result["columns"]

        if _HAS_TABULATE:
            data = [[row.get(c, "") for c in columns] for row in rows]
            return tabulate(data, headers=columns,
                            tablefmt="rounded_outline", floatfmt=".2f")

        col_widths = [
            max(len(str(c)), max((len(str(r.get(c, ""))) for r in rows), default=0))
            for c in columns
        ]
        sep   = "+" + "+".join("-" * (w + 2) for w in col_widths) + "+"
        hdr   = "|" + "|".join(f" {c:<{w}} " for c, w in zip(columns, col_widths)) + "|"
        lines = [sep, hdr, sep]
        for row in rows:
            lines.append(
                "|" + "|".join(
                    f" {str(row.get(c,'')):<{w}} "
                    for c, w in zip(columns, col_widths)
                ) + "|"
            )
        lines.append(sep)
        return "\n".join(lines)

    # ── Core ask() loop ───────────────────────────────────────────────────────

    def ask(self, question: str) -> str:
        """
        Process one natural-language question using the TR inference API.

        Loop:
          1. First turn  – embed schema context + SQL tool instructions directly
                           in the query text so the model receives them even if
                           the TR workflow's server-side system prompt overrides
                           the system_prompt field in modelparams.
          2. Claude responds with one or more <tool_call><sql>…</sql></tool_call>
             blocks.
          3. Each SQL is executed against Snowflake; results are collected.
          4. Follow-up turn – send results and ask for a narrative answer.
          5. Repeat until no <tool_call> blocks appear → return final answer.
        """
        self._query_count = 0
        final_answer = "⚠️  Could not produce a final answer within the allowed iterations."

        # ── Turn 1: send the question directly. The schema context lives in
        # system_prompt (modelparams). We keep it plain so the workflow
        # doesn't strip or reinterpret XML wrappers.
        current_query = question

        for iteration in range(self.MAX_LOOPS):
            # ── Call the TR inference API ──
            try:
                response_text = self._call_api(current_query)
            except RuntimeError as exc:
                return f"❌  API error: {exc}"

            # ── Check for SQL tool calls ──
            tool_calls = _extract_tool_calls(response_text)

            if not tool_calls:
                # No <tool_call> blocks → final narrative answer
                final_answer = _strip_tool_calls(response_text)
                break

            # ── Execute each SQL query and collect results ──
            results_block = ""
            for call in tool_calls:
                desc = call["description"]
                sql  = call["sql"]

                print(f"\n  🔍  {desc}")
                print(_indent(f"SQL ↓\n{sql}"))

                result = self.execute_sql(sql)

                if "error" in result:
                    print(f"  ❌  SQL error: {result['error']}")
                    results_block += (
                        f"\n[Result for: {desc}]\n"
                        f"ERROR: {result['error']}\n"
                    )
                else:
                    note = (
                        f"  ✅  {result['row_count']} row(s) "
                        f"in {result['elapsed_sec']}s"
                    )
                    if result.get("truncated"):
                        note += f"  (first {self.MAX_ROWS} rows shown)"
                    print(note)
                    if result["row_count"] > 0:
                        print(_indent(self._render_table(result)))

                    result_json = json.dumps(result, cls=_JSONEncoder, indent=2)
                    results_block += (
                        f"\n[Result for: {desc}]\n"
                        f"```json\n{result_json}\n```\n"
                    )

            # ── Follow-up turn: send results, ask for narrative answer ──
            # Keep the original question in plain text so the model stays focused.
            # The conversation_id ensures server-side history is preserved.
            narrative_only = _strip_tool_calls(response_text).strip()
            context_note   = f"\nYour earlier analysis:\n{narrative_only}\n" if narrative_only else ""
            current_query = (
                f"Original question: {question}\n"
                f"{context_note}\n"
                f"Snowflake query results:\n{results_block}\n\n"
                f"Using the data above, write a clear, concise business-narrative "
                f"answer to the original question. "
                f"Do NOT output any <tool_call> blocks."
            )

        return final_answer

    # ── Utilities ─────────────────────────────────────────────────────────────

    def reset(self) -> None:
        """Clear conversation history and start a fresh context window."""
        self._conversation_id = None
        self._transcript.clear()
        # Remove the persisted key file so the next run starts fresh
        key_file = os.path.join(os.path.dirname(__file__), ".tr_conversation_id")
        try:
            os.remove(key_file)
        except FileNotFoundError:
            pass
        print("🔄  Conversation history cleared.\n")

    def close(self) -> None:
        """Close the Snowflake connection."""
        if self.conn and not self.conn.is_closed():
            self.conn.close()
            print("🔒  Snowflake connection closed.")

    # ── Interactive CLI ───────────────────────────────────────────────────────

    def chat(self) -> None:
        """Start an interactive conversational session in the terminal."""

        # ── Collect system prompt from user if not already supplied ──────────
        if not self._system_prompt.strip().replace(_SQL_TOOL_INSTRUCTIONS, "").strip():
            print(_hr("═"))
            print("  📋  No system prompt detected.")
            print("  Enter your system prompt below.")
            print("  • Single-line  : just type and press Enter.")
            print("  • Multi-line   : end each line with \\  (backslash).")
            print("  • Blank line   : finish input.")
            print(_hr())
            lines: list[str] = []
            while True:
                try:
                    line = input("  📝  " if not lines else "       ").rstrip()
                except (EOFError, KeyboardInterrupt):
                    break
                if line.endswith("\\"):
                    lines.append(line[:-1])   # strip continuation backslash
                elif line == "":
                    break
                else:
                    lines.append(line)
                    break
            # Allow multi-line continuation after the first non-continuation line
            # (user may keep typing continuation lines)
            if lines and lines[-1].strip():
                while True:
                    try:
                        line = input("       ").rstrip()
                    except (EOFError, KeyboardInterrupt):
                        break
                    if line.endswith("\\"):
                        lines.append(line[:-1])
                    elif line == "":
                        break
                    else:
                        lines.append(line)
                        break
            user_supplied = "\n".join(lines).strip()
            if user_supplied:
                self._system_prompt = user_supplied + "\n" + _SQL_TOOL_INSTRUCTIONS
                print(f"\n  ✅  System prompt set ({len(user_supplied)} chars).")
            else:
                print("  ⚠️   No system prompt entered – using default schema context.")
                self._system_prompt = _DEFAULT_SYSTEM_PROMPT + "\n" + _SQL_TOOL_INSTRUCTIONS

        prompt_preview = self._system_prompt.replace(_SQL_TOOL_INSTRUCTIONS, "").strip()
        preview_line   = (prompt_preview[:60] + "…") if len(prompt_preview) > 60 else prompt_preview

        banner = f"""
{_hr("=")}
  Reuters RUM Sales Intelligence Agent  🤖  v2
  Powered by TR Inference API (Claude Sonnet 4.6) + Snowflake
{_hr("─")}
  System prompt  : {preview_line}
{_hr("─")}
  Example questions:
    • "Which content categories generated the highest licensing revenue?"
    • "Show me customer acquisition trends by region for last year"
    • "Top 10 accounts by revenue with their account managers"
{_hr("─")}
  Commands:  reset  →  clear conversation  |  sysprompt → change prompt  |  exit  →  quit
{_hr("═")}
"""
        print(banner)

        while True:
            try:
                user_input = input("💬  You: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n\n👋  Session ended. Goodbye!")
                break

            if not user_input:
                continue

            if user_input.lower() in {"exit", "quit", "bye", "q"}:
                print("👋  Goodbye!")
                break

            if user_input.lower() == "reset":
                self.reset()
                continue

            if user_input.lower() in {"sysprompt", "system prompt", "sp"}:
                print("  Enter new system prompt (blank line to finish):")
                lines: list[str] = []
                while True:
                    try:
                        line = input("  📝  ").rstrip()
                    except (EOFError, KeyboardInterrupt):
                        break
                    if line.endswith("\\"):
                        lines.append(line[:-1])
                    elif line == "":
                        break
                    else:
                        lines.append(line)
                new_sp = "\n".join(lines).strip()
                if new_sp:
                    self._system_prompt = new_sp + "\n" + _SQL_TOOL_INSTRUCTIONS
                    self.reset()   # clear conversation so new prompt takes effect
                    print(f"  ✅  System prompt updated ({len(new_sp)} chars). Conversation reset.\n")
                else:
                    print("  ⚠️   No input – system prompt unchanged.\n")
                continue

            print(f"\n{_hr()}")
            print("🤔  Analysing your question …\n")
            t_start = time.perf_counter()

            try:
                answer = self.ask(user_input)
            except Exception as exc:
                print(f"\n⚠️  Unexpected error during processing: {exc}")
                continue

            elapsed = round(time.perf_counter() - t_start, 1)
            print(f"\n{_hr()}")
            print("🎯  Agent:\n")
            for line in answer.splitlines():
                print(f"   {line}")
            print(f"\n{_hr('─')}")
            print(
                f"   ⏱  {elapsed}s total  |  "
                f"🗄  {self._query_count} SQL query(ies) executed"
            )
            print(_hr())

        self.close()


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Reuters RUM Sales Intelligence Agent v2"
    )
    parser.add_argument(
        "--system-prompt", "-s",
        metavar="TEXT",
        default="",
        help="System prompt text to use for the session.",
    )
    parser.add_argument(
        "--system-prompt-file", "-f",
        metavar="PATH",
        default="",
        help="Path to a text file whose contents become the system prompt.",
    )
    args = parser.parse_args()

    # Priority: --system-prompt-file > --system-prompt > TR_SYSTEM_PROMPT env-var
    system_prompt = ""
    if args.system_prompt_file:
        try:
            with open(args.system_prompt_file, encoding="utf-8") as _f:
                system_prompt = _f.read().strip()
            print(f"📄  System prompt loaded from: {args.system_prompt_file}")
        except OSError as exc:
            print(f"❌  Cannot read system prompt file: {exc}")
            sys.exit(1)
    elif args.system_prompt:
        system_prompt = args.system_prompt.strip()
    else:
        system_prompt = os.getenv("TR_SYSTEM_PROMPT", "")

    try:
        agent = ReutersRUMAgentV2(system_prompt=system_prompt)
        agent.chat()
    except EnvironmentError as exc:
        print(f"\n❌  Configuration error:\n   {exc}")
        sys.exit(1)
    except Exception as exc:
        print(f"\n❌  Failed to start agent: {exc}")
        sys.exit(1)
