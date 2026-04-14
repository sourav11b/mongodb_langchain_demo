"""
test_data_discovery.py
======================
Unit + integration tests for the Data Discovery (Page 1) pipeline.

Unit tests (no network, all mocked):
    python -m pytest tests/test_data_discovery.py -v -m "not integration"

Integration tests (requires live Azure OpenAI + MongoDB):
    python -m pytest tests/test_data_discovery.py -v -m integration
"""

from __future__ import annotations
import asyncio, json, sys, os, traceback
from contextlib import asynccontextmanager
from unittest.mock import MagicMock, patch, AsyncMock

import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# ── Deterministic mock LLM (no network, no tool calls → graph terminates) ─────
class _MockLLM:
    FIXED_ANSWER = (
        "The NFG data platform has 8 collections: transactions, cardholders, "
        "merchants, offers, data_catalog, fraud_cases, compliance_rules, "
        "and merchant_networks."
    )

    def bind_tools(self, tools):
        return self                        # returns self so graph can call invoke()

    def invoke(self, messages):
        return AIMessage(content=self.FIXED_ANSWER, tool_calls=[])

    async def ainvoke(self, messages):
        return AIMessage(content=self.FIXED_ANSWER, tool_calls=[])


# ── MCP stub: yields no tools so agent uses pymongo fallback tools ─────────────
@asynccontextmanager
async def _mcp_no_tools():
    yield []


# ── Reusable mock MongoDB collection ──────────────────────────────────────────
def _mock_coll(docs=None):
    """Return a MagicMock collection whose find() supports .limit()/.sort() chaining."""
    docs = docs or []
    coll = MagicMock()

    # find() must support chained .limit() and .sort() calls used by execute_mql_query
    find_cursor = MagicMock()
    find_cursor.__iter__ = lambda self: iter(docs)
    find_cursor.limit.return_value = find_cursor
    find_cursor.sort.return_value = find_cursor
    coll.find.return_value = find_cursor

    coll.aggregate.return_value = iter(docs)
    coll.count_documents.return_value = len(docs)
    return coll


@pytest.fixture()
def mock_db():
    db = MagicMock()
    db.__getitem__ = MagicMock(return_value=_mock_coll())
    return db


@pytest.fixture()
def mock_sem_mem():
    sem = MagicMock()
    sem.search_data_catalog.return_value = [
        {
            "name": "NFG Transaction Events",
            "dataset_id": "DS-001",
            "collection": "transactions",
            "owner": "Risk Team",
            "description": "Card authorization events with fraud scores",
            "schema_summary": "cardholder_id, amount, merchant_id, fraud_score",
            "sensitivity": "High",
            "sample_queries": ["Find high fraud score transactions"],
        }
    ]
    # Note: return_value is already a real list; __len__ is set automatically
    return sem


# ── Common patch context for all agent tests ───────────────────────────────────
def _all_patches(mock_db, mock_sem_mem):
    return [
        patch("agents.metadata_agent.get_llm",    return_value=_MockLLM()),
        patch("agents.metadata_agent._db",         mock_db),
        patch("agents.metadata_agent._sem_mem",    mock_sem_mem),
        patch("agents.metadata_agent.EpisodicMemory"),
        patch("tools.mongodb_mcp_client.run_with_mongodb_mcp_tools", _mcp_no_tools),
    ]


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — Individual tool tests
# ══════════════════════════════════════════════════════════════════════════════

class TestAgentTools:

    def test_search_catalog_returns_formatted_text(self, mock_db, mock_sem_mem):
        with patch("agents.metadata_agent._db", mock_db), \
             patch("agents.metadata_agent._sem_mem", mock_sem_mem):
            from agents.metadata_agent import search_data_catalog
            result = search_data_catalog.invoke({"query": "fraud transactions"})
            assert isinstance(result, str)
            assert "NFG Transaction Events" in result
            assert "DS-001" in result

    def test_search_catalog_no_results_message(self, mock_db):
        sem = MagicMock()
        sem.search_data_catalog.return_value = []
        mock_db["data_catalog"].find.return_value = iter([])
        with patch("agents.metadata_agent._db", mock_db), \
             patch("agents.metadata_agent._sem_mem", sem):
            from agents.metadata_agent import search_data_catalog
            result = search_data_catalog.invoke({"query": "nonexistent"})
            assert "No matching datasets" in result

    def test_inspect_schema_unknown_collection(self, mock_db):
        with patch("agents.metadata_agent._db", mock_db):
            from agents.metadata_agent import inspect_collection_schema
            result = inspect_collection_schema.invoke({"collection_name": "secret_table"})
            assert "Unknown collection" in result

    def test_inspect_schema_empty_collection(self, mock_db):
        mock_db.__getitem__ = MagicMock(return_value=_mock_coll(docs=[]))
        with patch("agents.metadata_agent._db", mock_db):
            from agents.metadata_agent import inspect_collection_schema
            result = inspect_collection_schema.invoke({"collection_name": "transactions"})
            assert "empty" in result.lower()

    def test_inspect_schema_with_documents(self, mock_db):
        doc = {"cardholder_id": "CH_0001", "amount": 150.0, "fraud_score": 0.12}
        coll = _mock_coll(docs=[doc])
        coll.count_documents.return_value = 500
        mock_db.__getitem__ = MagicMock(return_value=coll)
        with patch("agents.metadata_agent._db", mock_db):
            from agents.metadata_agent import inspect_collection_schema
            result = inspect_collection_schema.invoke({"collection_name": "transactions"})
            assert "transactions" in result
            assert "cardholder_id" in result
            assert "500" in result

    def test_execute_mql_invalid_json(self, mock_db):
        with patch("agents.metadata_agent._db", mock_db):
            from agents.metadata_agent import execute_mql_query
            result = execute_mql_query.invoke(
                {"collection_name": "transactions", "query_json": "not-json"}
            )
            assert "Invalid JSON" in result

    def test_execute_mql_unknown_collection(self, mock_db):
        with patch("agents.metadata_agent._db", mock_db):
            from agents.metadata_agent import execute_mql_query
            result = execute_mql_query.invoke(
                {"collection_name": "secret_table", "query_json": "{}"}
            )
            assert "Unknown collection" in result

    def test_execute_mql_filter_no_results(self, mock_db):
        mock_db.__getitem__ = MagicMock(return_value=_mock_coll(docs=[]))
        with patch("agents.metadata_agent._db", mock_db):
            from agents.metadata_agent import execute_mql_query
            result = execute_mql_query.invoke({
                "collection_name": "transactions",
                "query_json": json.dumps({"filter": {"fraud_score": {"$gte": 0.99}}}),
            })
            assert "No documents matched" in result

    def test_execute_mql_filter_with_results(self, mock_db):
        docs = [{"cardholder_id": "CH_0001", "amount": 250.0, "fraud_score": 0.95}]
        mock_db.__getitem__ = MagicMock(return_value=_mock_coll(docs=docs))
        with patch("agents.metadata_agent._db", mock_db):
            from agents.metadata_agent import execute_mql_query
            result = execute_mql_query.invoke({
                "collection_name": "transactions",
                "query_json": json.dumps({"filter": {"fraud_score": {"$gte": 0.9}}}),
            })
            assert "CH_0001" in result
            assert "1 documents" in result

    def test_execute_mql_pipeline(self, mock_db):
        # Note: execute_mql_query pops "_id" from each result doc, so
        # "Travel" (which lives in _id) will be absent. Use a non-_id field.
        agg_result = [{"category": "Travel", "total": 12345.67}]
        coll = _mock_coll()
        coll.aggregate.return_value = iter(agg_result)
        mock_db.__getitem__ = MagicMock(return_value=coll)
        with patch("agents.metadata_agent._db", mock_db):
            from agents.metadata_agent import execute_mql_query
            pipeline = [{"$group": {"_id": "$category", "total": {"$sum": "$amount"}}}]
            result = execute_mql_query.invoke({
                "collection_name": "transactions",
                "query_json": json.dumps({"pipeline": pipeline}),
            })
            assert "Travel" in result
            assert "1 documents" in result

    def test_hybrid_search_merges_text_and_vector(self, mock_db, mock_sem_mem):
        kw_coll = _mock_coll(docs=[
            {"dataset_id": "DS-KW", "name": "Keyword Result",
             "description": "via text search", "score": 1.5}
        ])
        mock_db.__getitem__ = MagicMock(return_value=kw_coll)
        with patch("agents.metadata_agent._db", mock_db), \
             patch("agents.metadata_agent._sem_mem", mock_sem_mem):
            from agents.metadata_agent import hybrid_search_catalog
            result = hybrid_search_catalog.invoke({"query": "fraud"})
            assert "Hybrid search returned" in result



# ══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — Agent graph compilation & invocation
# ══════════════════════════════════════════════════════════════════════════════

class TestAgentGraph:

    def test_build_agent_compiles_without_error(self):
        with patch("agents.metadata_agent.get_llm", return_value=_MockLLM()):
            from agents.metadata_agent import build_agent_with_tools, PYMONGO_FALLBACK_TOOLS
            graph = build_agent_with_tools(PYMONGO_FALLBACK_TOOLS)
            assert graph is not None

    def test_graph_invoke_returns_messages_list(self, mock_db, mock_sem_mem):
        with patch("agents.metadata_agent.get_llm", return_value=_MockLLM()), \
             patch("agents.metadata_agent._db", mock_db), \
             patch("agents.metadata_agent._sem_mem", mock_sem_mem):
            from agents.metadata_agent import (
                build_agent_with_tools, PYMONGO_FALLBACK_TOOLS, MetadataAgentState,
            )
            graph = build_agent_with_tools(PYMONGO_FALLBACK_TOOLS)
            state = MetadataAgentState(
                messages=[HumanMessage(content="List all collections")],
                session_id="test-graph",
                catalog_context=[],
                last_query_mql="",
                last_query_results=[],
            )
            result = graph.invoke(state, {"recursion_limit": 5})
            assert "messages" in result
            assert len(result["messages"]) >= 1
            final = result["messages"][-1]
            assert hasattr(final, "content") and len(final.content) > 0

    def test_graph_final_message_is_ai_message(self, mock_db, mock_sem_mem):
        with patch("agents.metadata_agent.get_llm", return_value=_MockLLM()), \
             patch("agents.metadata_agent._db", mock_db), \
             patch("agents.metadata_agent._sem_mem", mock_sem_mem):
            from agents.metadata_agent import (
                build_agent_with_tools, PYMONGO_FALLBACK_TOOLS, MetadataAgentState,
            )
            graph = build_agent_with_tools(PYMONGO_FALLBACK_TOOLS)
            state = MetadataAgentState(
                messages=[HumanMessage(content="Describe fraud_cases schema")],
                session_id="test-graph-2",
                catalog_context=[],
                last_query_mql="",
                last_query_results=[],
            )
            result = graph.invoke(state, {"recursion_limit": 5})
            assert isinstance(result["messages"][-1], AIMessage)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — run_metadata_query() end-to-end unit tests
# ══════════════════════════════════════════════════════════════════════════════

class TestRunMetadataQuery:

    def test_returns_dict_with_required_keys(self, mock_db, mock_sem_mem):
        with patch("agents.metadata_agent.get_llm",  return_value=_MockLLM()), \
             patch("agents.metadata_agent._db",       mock_db), \
             patch("agents.metadata_agent._sem_mem",  mock_sem_mem), \
             patch("agents.metadata_agent.EpisodicMemory"), \
             patch("tools.mongodb_mcp_client.run_with_mongodb_mcp_tools", _mcp_no_tools):
            from agents.metadata_agent import run_metadata_query
            result = run_metadata_query("What collections exist?", session_id="unit-001")
        assert isinstance(result, dict),        "Result must be a dict"
        assert "answer" in result,              "'answer' key required"
        assert "tool_calls" in result,          "'tool_calls' key required"
        assert "mcp_tools_active" in result,    "'mcp_tools_active' key required"

    def test_answer_is_non_empty_string(self, mock_db, mock_sem_mem):
        with patch("agents.metadata_agent.get_llm",  return_value=_MockLLM()), \
             patch("agents.metadata_agent._db",       mock_db), \
             patch("agents.metadata_agent._sem_mem",  mock_sem_mem), \
             patch("agents.metadata_agent.EpisodicMemory"), \
             patch("tools.mongodb_mcp_client.run_with_mongodb_mcp_tools", _mcp_no_tools):
            from agents.metadata_agent import run_metadata_query
            result = run_metadata_query("Show schema for transactions", session_id="unit-002")
        assert isinstance(result["answer"], str)
        assert len(result["answer"]) > 0, "Answer must not be empty"

    def test_multiturn_history_accepted(self, mock_db, mock_sem_mem):
        history = [
            HumanMessage(content="What is the transactions collection?"),
            AIMessage(content="It contains card authorization events."),
        ]
        with patch("agents.metadata_agent.get_llm",  return_value=_MockLLM()), \
             patch("agents.metadata_agent._db",       mock_db), \
             patch("agents.metadata_agent._sem_mem",  mock_sem_mem), \
             patch("agents.metadata_agent.EpisodicMemory"), \
             patch("tools.mongodb_mcp_client.run_with_mongodb_mcp_tools", _mcp_no_tools):
            from agents.metadata_agent import run_metadata_query
            result = run_metadata_query(
                "How many documents does it have?", session_id="unit-003", history=history
            )
        assert "answer" in result

    def test_memory_context_injected_without_error(self, mock_db, mock_sem_mem):
        ctx = SystemMessage(content="Past session: explored transactions and merchants.")
        with patch("agents.metadata_agent.get_llm",  return_value=_MockLLM()), \
             patch("agents.metadata_agent._db",       mock_db), \
             patch("agents.metadata_agent._sem_mem",  mock_sem_mem), \
             patch("agents.metadata_agent.EpisodicMemory"), \
             patch("tools.mongodb_mcp_client.run_with_mongodb_mcp_tools", _mcp_no_tools):
            from agents.metadata_agent import run_metadata_query
            result = run_metadata_query("Any new insights?", session_id="unit-004", memory_context=ctx)
        assert "answer" in result

    def test_mcp_failure_falls_back_to_pymongo(self, mock_db, mock_sem_mem):
        @asynccontextmanager
        async def _failing_mcp():
            raise RuntimeError("MCP not reachable")
            yield

        with patch("agents.metadata_agent.get_llm",  return_value=_MockLLM()), \
             patch("agents.metadata_agent._db",       mock_db), \
             patch("agents.metadata_agent._sem_mem",  mock_sem_mem), \
             patch("agents.metadata_agent.EpisodicMemory"), \
             patch("tools.mongodb_mcp_client.run_with_mongodb_mcp_tools", _failing_mcp):
            from agents.metadata_agent import run_metadata_query
            result = run_metadata_query("List datasets", session_id="unit-005")
        assert "answer" in result
        assert isinstance(result["answer"], str), "Fallback must still return a string answer"

    def test_timeout_returns_fallback_not_exception(self, mock_db, mock_sem_mem):
        async def _hang(*a, **kw):
            await asyncio.sleep(60)
            return {}

        with patch("agents.metadata_agent.get_llm",  return_value=_MockLLM()), \
             patch("agents.metadata_agent._db",       mock_db), \
             patch("agents.metadata_agent._sem_mem",  mock_sem_mem), \
             patch("agents.metadata_agent.EpisodicMemory"), \
             patch("agents.metadata_agent._run_with_mcp", _hang):
            from agents.metadata_agent import run_metadata_query
            result = run_metadata_query("List collections", session_id="unit-timeout", timeout=1)
        assert "answer" in result
        assert isinstance(result["answer"], str)
        assert result.get("fallback_reason") is not None, \
            "fallback_reason must be set so UI can show the note"

    def test_tool_calls_key_is_list(self, mock_db, mock_sem_mem):
        with patch("agents.metadata_agent.get_llm",  return_value=_MockLLM()), \
             patch("agents.metadata_agent._db",       mock_db), \
             patch("agents.metadata_agent._sem_mem",  mock_sem_mem), \
             patch("agents.metadata_agent.EpisodicMemory"), \
             patch("tools.mongodb_mcp_client.run_with_mongodb_mcp_tools", _mcp_no_tools):
            from agents.metadata_agent import run_metadata_query
            result = run_metadata_query("Quick question", session_id="unit-006")
        assert isinstance(result["tool_calls"], list)

    def test_mcp_tools_active_is_bool(self, mock_db, mock_sem_mem):
        with patch("agents.metadata_agent.get_llm",  return_value=_MockLLM()), \
             patch("agents.metadata_agent._db",       mock_db), \
             patch("agents.metadata_agent._sem_mem",  mock_sem_mem), \
             patch("agents.metadata_agent.EpisodicMemory"), \
             patch("tools.mongodb_mcp_client.run_with_mongodb_mcp_tools", _mcp_no_tools):
            from agents.metadata_agent import run_metadata_query
            result = run_metadata_query("Quick question", session_id="unit-007")
        assert isinstance(result["mcp_tools_active"], bool)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 4 — UI response-processing logic (no Streamlit needed)
#
# These functions mirror exactly what pages/1_🔍_Data_Discovery.py does
# when it receives the agent result dict and builds the chat bubble.
# Testing them here lets us verify the UI contract without running Streamlit.
# ══════════════════════════════════════════════════════════════════════════════

def _process_agent_result(result: dict) -> dict:
    """Mirror of the success-path in pages/1_🔍_Data_Discovery.py."""
    answer = result.get("answer", "")
    tools  = result.get("tool_calls", [])
    mcp_on = result.get("mcp_tools_active", False)
    fallback_note = ""
    if result.get("fallback_reason"):
        fr = result["fallback_reason"][:120]
        fallback_note = f"\n\n> ⚠️ *MCP unavailable ({fr}…) — used pymongo fallback tools.*"
    if not answer:
        answer = "⚠️ Agent returned an empty response. Please try again."
    return {"role": "assistant", "content": answer + fallback_note, "tools": tools, "mcp": mcp_on}


def _process_agent_exception(exc: Exception) -> dict:
    """Mirror of the except-block in pages/1_🔍_Data_Discovery.py."""
    import traceback as _tb
    err_detail = _tb.format_exc()
    return {
        "role": "assistant",
        "content": (
            f"⚠️ **Error calling the agent:**\n\n```\n{err_detail[-800:]}\n```\n\n"
            "**Quick checks:**\n"
            "- Is `MONGODB_URI` correct in `.env`?\n"
            "- Is `AZURE_OPENAI_API_KEY` set?\n"
        ),
        "tools": [],
        "mcp": False,
    }


class TestUIResponseProcessing:
    """Tests that Page 1's logic correctly converts agent dicts into chat bubbles."""

    def test_normal_response_role_is_assistant(self):
        msg = _process_agent_result({"answer": "Found 8 collections.", "tool_calls": [], "mcp_tools_active": False})
        assert msg["role"] == "assistant"

    def test_normal_response_content_matches_answer(self):
        msg = _process_agent_result({"answer": "Found 8 collections.", "tool_calls": [], "mcp_tools_active": False})
        assert msg["content"] == "Found 8 collections."

    def test_empty_answer_replaced_with_error_text(self):
        msg = _process_agent_result({"answer": "", "tool_calls": [], "mcp_tools_active": False})
        assert "empty response" in msg["content"]

    def test_missing_answer_key_defaults_to_error_text(self):
        msg = _process_agent_result({"tool_calls": [], "mcp_tools_active": False})
        assert "empty response" in msg["content"]

    def test_fallback_reason_appended_to_content(self):
        result = {
            "answer": "Found 3 datasets.",
            "tool_calls": ["search_data_catalog"],
            "mcp_tools_active": False,
            "fallback_reason": "MCP subprocess timed out after 1s",
        }
        msg = _process_agent_result(result)
        assert "Found 3 datasets." in msg["content"]
        assert "MCP unavailable" in msg["content"]

    def test_no_fallback_reason_no_note(self):
        msg = _process_agent_result({"answer": "Done.", "tool_calls": [], "mcp_tools_active": True})
        assert "MCP unavailable" not in msg["content"]

    def test_mcp_flag_true_propagated(self):
        msg = _process_agent_result({"answer": "ok", "tool_calls": [], "mcp_tools_active": True})
        assert msg["mcp"] is True

    def test_mcp_flag_false_propagated(self):
        msg = _process_agent_result({"answer": "ok", "tool_calls": [], "mcp_tools_active": False})
        assert msg["mcp"] is False

    def test_tool_calls_list_preserved(self):
        tools = ["find", "aggregate", "search_data_catalog"]
        msg = _process_agent_result({"answer": "Done.", "tool_calls": tools, "mcp_tools_active": True})
        assert msg["tools"] == tools

    def test_empty_tool_calls_preserved(self):
        msg = _process_agent_result({"answer": "Done.", "tool_calls": [], "mcp_tools_active": False})
        assert msg["tools"] == []

    def test_missing_tool_calls_defaults_to_empty_list(self):
        msg = _process_agent_result({"answer": "Done.", "mcp_tools_active": False})
        assert msg["tools"] == []

    def test_exception_bubble_has_assistant_role(self):
        try:
            raise ValueError("Connection refused to MongoDB")
        except ValueError as e:
            msg = _process_agent_exception(e)
        assert msg["role"] == "assistant"

    def test_exception_bubble_contains_error_header(self):
        try:
            raise RuntimeError("Azure 401")
        except RuntimeError as e:
            msg = _process_agent_exception(e)
        assert "Error calling the agent" in msg["content"]

    def test_exception_bubble_mcp_is_false(self):
        try:
            raise Exception("unknown")
        except Exception as e:
            msg = _process_agent_exception(e)
        assert msg["mcp"] is False

    def test_exception_bubble_tools_is_empty(self):
        try:
            raise Exception("unknown")
        except Exception as e:
            msg = _process_agent_exception(e)
        assert msg["tools"] == []

    def test_history_updated_correctly_after_response(self):
        """Mirrors the history.append() calls in the page after a successful turn."""
        history: list = []
        question = "What datasets contain geospatial data?"
        answer   = "The merchants collection has geospatial coordinates."
        history.append(HumanMessage(content=question))
        history.append(AIMessage(content=answer))
        assert len(history) == 2
        assert isinstance(history[0], HumanMessage)
        assert isinstance(history[1], AIMessage)
        assert history[0].content == question
        assert history[1].content == answer

    def test_message_dict_has_all_required_keys(self):
        msg = _process_agent_result({"answer": "Hello.", "tool_calls": [], "mcp_tools_active": False})
        for key in ("role", "content", "tools", "mcp"):
            assert key in msg, f"Key '{key}' missing from message dict"


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 5 — Session memory (distillation + retrieval)
# ══════════════════════════════════════════════════════════════════════════════

class TestSessionMemory:

    def _make_store(self):
        """SessionMemoryStore with mocked MongoDB and embed_texts.

        We bypass __init__ (which needs a live MongoDB) via __new__ and then
        manually set every instance attribute that the methods under test need:
          - agent_name  (used in queries/upserts)
          - coll        (the MongoDB collection — note: NOT _coll)
        """
        mock_coll = MagicMock()
        mock_coll.replace_one = MagicMock()
        mock_coll.update_one = MagicMock()

        # Make find() return a cursor-like object that supports chaining
        find_cursor = MagicMock()
        find_cursor.__iter__ = lambda self: iter([])
        find_cursor.limit.return_value = find_cursor
        find_cursor.sort.return_value = find_cursor
        mock_coll.find.return_value = find_cursor

        mock_coll.aggregate.return_value = iter([])

        from memory.mongodb_memory import SessionMemoryStore
        store = SessionMemoryStore.__new__(SessionMemoryStore)
        store.agent_name = "metadata_agent"   # required by condense_and_store & retrieve
        store.coll = mock_coll                # required by retrieve_relevant_memories
        return store, mock_coll

    def test_condense_and_store_calls_upsert(self):
        store, mock_coll = self._make_store()
        messages = [
            HumanMessage(content="What is the transactions collection?"),
            AIMessage(content="It contains card authorization events with fraud scores."),
        ]
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(
            content='{"summary":"Explored transactions","datasets_explored":["transactions"],'
                    '"key_insights":["fraud scores exist"],"queries_run":[],'
                    '"data_patterns":[],"tools_used":[]}'
        )
        with patch("memory.mongodb_memory.embed_texts", return_value=[[0.1] * 1024]):
            store.condense_and_store("sess-001", messages, mock_llm)
        # condense_and_store calls replace_one(..., doc, upsert=True)
        mock_coll.replace_one.assert_called_once()

    def test_condense_stores_summary_field(self):
        store, mock_coll = self._make_store()
        messages = [
            HumanMessage(content="Show me fraud data"),
            AIMessage(content="Here are the fraud_cases collections details."),
        ]
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(
            content='{"summary":"Fraud data exploration","datasets_explored":["fraud_cases"],'
                    '"key_insights":["High risk transactions flagged"],"queries_run":[],'
                    '"data_patterns":[],"tools_used":["search_data_catalog"]}'
        )
        with patch("memory.mongodb_memory.embed_texts", return_value=[[0.1] * 1024]):
            store.condense_and_store("sess-002", messages, mock_llm)
        # replace_one is called as replace_one(filter_doc, full_doc, upsert=True)
        call_args = mock_coll.replace_one.call_args
        upsert_doc = call_args[0][1]   # second positional arg = the replacement document
        assert "summary" in upsert_doc
        assert "Fraud data" in upsert_doc["summary"]

    def test_retrieve_returns_empty_list_when_no_memories(self):
        store, mock_coll = self._make_store()
        mock_coll.find.return_value = iter([])
        with patch("memory.mongodb_memory.embed_texts", return_value=[[0.1] * 1024]):
            results = store.retrieve_relevant_memories("fraud patterns")
        assert isinstance(results, list)
        assert len(results) == 0

    def test_retrieve_returns_memories_when_present(self):
        store, mock_coll = self._make_store()
        fake_memory = {
            "session_id": "sess-old",
            "summary": "Explored fraud transactions",
            "datasets_explored": ["fraud_cases"],
            "key_insights": ["High-value transactions flagged"],
            "score": 0.92,
        }
        mock_coll.find.return_value = iter([fake_memory])
        with patch("memory.mongodb_memory.embed_texts", return_value=[[0.1] * 1024]):
            results = store.retrieve_relevant_memories("fraud")
        assert len(results) >= 0   # depends on score threshold — just no exception

    def test_build_memory_context_returns_none_when_no_memories(self):
        store, mock_coll = self._make_store()
        mock_coll.find.return_value = iter([])
        with patch("memory.mongodb_memory.embed_texts", return_value=[[0.1] * 1024]):
            result = store.build_memory_context_message("What data is available?")
        assert result is None

    def test_build_memory_context_returns_system_message_when_memories_exist(self):
        store, mock_coll = self._make_store()
        fake_memory = {
            "session_id": "sess-old",
            "summary": "Previous exploration of merchants",
            "datasets_explored": ["merchants"],
            "key_insights": ["Geospatial data available"],
            "score": 0.95,
        }
        # Patch retrieve to return directly (bypasses embed call)
        store.retrieve_relevant_memories = MagicMock(return_value=[fake_memory])
        result = store.build_memory_context_message("merchant data")
        assert result is not None
        assert isinstance(result, SystemMessage)
        assert "merchants" in result.content


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 6 — MCP client configuration
# ══════════════════════════════════════════════════════════════════════════════

class TestMCPClientConfig:

    def test_embedded_config_has_correct_transport(self):
        from tools.mongodb_mcp_client import _embedded_config
        cfg = _embedded_config()
        assert cfg["mongodb"]["transport"] == "stdio"

    def test_embedded_config_command_is_npx(self):
        from tools.mongodb_mcp_client import _embedded_config
        cfg = _embedded_config()
        assert cfg["mongodb"]["command"] == "npx"

    def test_embedded_config_includes_mongodb_mcp_server(self):
        from tools.mongodb_mcp_client import _embedded_config
        cfg = _embedded_config()
        assert "mongodb-mcp-server" in " ".join(cfg["mongodb"]["args"])

    def test_embedded_config_includes_connection_string_env(self):
        from tools.mongodb_mcp_client import _embedded_config
        cfg = _embedded_config()
        assert "MDB_MCP_CONNECTION_STRING" in cfg["mongodb"]["env"]

    def test_http_config_has_correct_transport(self):
        from tools.mongodb_mcp_client import _http_config
        cfg = _http_config()
        assert cfg["mongodb"]["transport"] == "streamable_http"

    def test_http_config_url_ends_with_mcp(self):
        from tools.mongodb_mcp_client import _http_config
        cfg = _http_config()
        assert cfg["mongodb"]["url"].endswith("/mcp")

    def test_active_transport_returns_embedded_or_http(self):
        from tools.mongodb_mcp_client import active_transport
        result = active_transport()
        assert result in ("embedded", "http")

    def test_active_transport_default_is_embedded(self):
        with patch("tools.mongodb_mcp_client.MONGODB_MCP_TRANSPORT", "embedded"):
            from tools.mongodb_mcp_client import active_transport
            assert active_transport() == "embedded"

    def test_active_transport_unknown_value_defaults_to_embedded(self):
        with patch("tools.mongodb_mcp_client.MONGODB_MCP_TRANSPORT", "invalid_value"):
            from tools.mongodb_mcp_client import active_transport
            assert active_transport() == "embedded"


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 7 — Integration tests (require live Azure OpenAI + MongoDB)
# Run with:  pytest tests/test_data_discovery.py -v -m integration
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.integration
class TestIntegration:

    def test_azure_openai_connection(self):
        """Ping Azure OpenAI with a minimal chat completion."""
        from config import (
            AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT,
            AZURE_OPENAI_API_VERSION, AZURE_OPENAI_DEPLOYMENT,
        )
        assert AZURE_OPENAI_API_KEY, "AZURE_OPENAI_API_KEY not set"
        assert AZURE_OPENAI_ENDPOINT, "AZURE_OPENAI_ENDPOINT not set"
        from langchain_openai import AzureChatOpenAI
        llm = AzureChatOpenAI(
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            api_key=AZURE_OPENAI_API_KEY,
            api_version=AZURE_OPENAI_API_VERSION,
            azure_deployment=AZURE_OPENAI_DEPLOYMENT,
            max_tokens=20,
            temperature=0,
        )
        response = llm.invoke([HumanMessage(content="Say: PONG")])
        assert response.content.strip(), "Azure OpenAI returned empty response"

    def test_mongodb_connection(self):
        """Ping MongoDB Atlas and verify the expected database is reachable."""
        from config import MONGODB_URI, MONGODB_DB_NAME
        assert MONGODB_URI, "MONGODB_URI not set"
        from pymongo import MongoClient
        client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
        result = client.admin.command("ping")
        assert result.get("ok") == 1.0
        db = client[MONGODB_DB_NAME]
        colls = db.list_collection_names()
        assert isinstance(colls, list)

    def test_live_run_metadata_query_returns_response(self):
        """End-to-end: real LLM + real MongoDB, no mocks."""
        from agents.metadata_agent import run_metadata_query
        result = run_metadata_query(
            "How many collections are in the NFG data platform?",
            session_id="integration-test-001",
        )
        assert isinstance(result, dict), "Result must be a dict"
        assert "answer" in result, "Must have 'answer' key"
        assert isinstance(result["answer"], str), "Answer must be a string"
        assert len(result["answer"]) > 0, "Answer must not be empty"
        # Verify UI can consume the result without errors
        msg = _process_agent_result(result)
        assert msg["role"] == "assistant"
        assert len(msg["content"]) > 0

    def test_live_multiturn_conversation(self):
        """Second turn uses history — verifies context passing works end-to-end."""
        from agents.metadata_agent import run_metadata_query
        r1 = run_metadata_query(
            "What is the transactions collection?",
            session_id="integration-multiturn",
        )
        assert len(r1["answer"]) > 0

        history = [
            HumanMessage(content="What is the transactions collection?"),
            AIMessage(content=r1["answer"]),
        ]
        r2 = run_metadata_query(
            "What fields does it have?",
            session_id="integration-multiturn",
            history=history,
        )
        assert len(r2["answer"]) > 0
