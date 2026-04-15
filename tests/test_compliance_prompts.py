"""
test_compliance_prompts.py
==========================
Unit tests for the Compliance Agent (Page 4) Quick Start prompts.
Each test invokes the underlying @tool with the exact prompt values
and asserts non-empty, feature-relevant results.

Run:  python -m pytest tests/test_compliance_prompts.py -v
"""
from __future__ import annotations
import json, sys, os
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


# ── Reusable mock collection ──────────────────────────────────────────────────
def _mock_coll(docs=None):
    docs = docs or []
    coll = MagicMock()
    find_cursor = MagicMock()
    find_cursor.__iter__ = lambda self: iter(docs)
    find_cursor.limit.return_value = find_cursor
    find_cursor.sort.return_value = find_cursor
    coll.find.return_value = find_cursor
    coll.aggregate.return_value = iter(docs)
    coll.count_documents.return_value = len(docs)
    coll.find_one.return_value = docs[0] if docs else None
    coll.distinct.return_value = []
    return coll


@pytest.fixture()
def mock_db():
    db = MagicMock()
    db.__getitem__ = MagicMock(return_value=_mock_coll())
    return db


@pytest.fixture()
def mock_sem_mem():
    return MagicMock()


class TestComplianceQuickStartPrompts:
    """One test per Quick Start button on the Compliance page."""

    # ── 📋 Rule Lookup: search_compliance_rules ──
    def test_qs_rule_lookup(self, mock_db, mock_sem_mem):
        mock_sem_mem.search_compliance_rules.return_value = [
            {"rule_id": "BSA-001", "rule_name": "BSA Currency Transaction Report",
             "jurisdiction": "USA", "category": "AML",
             "rule_text": "Financial institutions must file CTR for cash transactions exceeding $10,000",
             "tags": ["AML", "BSA", "CTR"]},
        ]
        with patch("agents.compliance_agent._db", mock_db), \
             patch("agents.compliance_agent._sem_mem", mock_sem_mem):
            from agents.compliance_agent import search_compliance_rules
            result = search_compliance_rules.invoke(
                {"query": "AML and Know-Your-Customer regulations applicable to high-value wire transfers"}
            )
            assert isinstance(result, str)
            assert "BSA-001" in result or "BSA Currency" in result
            assert "1 found" in result

    # ── 📋 Rule Lookup fallback (when embeddings missing) ──
    def test_qs_rule_lookup_keyword_fallback(self, mock_db, mock_sem_mem):
        mock_sem_mem.search_compliance_rules.return_value = []
        fallback_doc = {
            "rule_id": "KYC-001", "rule_name": "KYC Customer Due Diligence",
            "category": "KYC", "jurisdiction": "USA",
            "rule_text": "Know-Your-Customer verification required for all new accounts",
            "tags": ["KYC", "AML", "due diligence"],
        }
        rules_coll = _mock_coll(docs=[fallback_doc])
        mock_db.compliance_rules = rules_coll
        with patch("agents.compliance_agent._db", mock_db), \
             patch("agents.compliance_agent._sem_mem", mock_sem_mem):
            from agents.compliance_agent import search_compliance_rules
            result = search_compliance_rules.invoke(
                {"query": "AML and Know-Your-Customer regulations applicable to high-value wire transfers"}
            )
            assert isinstance(result, str)
            assert "KYC-001" in result or "KYC Customer" in result
            call_args = rules_coll.find.call_args
            assert "$or" in str(call_args)

    # ── 💰 BSA Thresholds: check_transaction_thresholds ──
    def test_qs_bsa_thresholds(self, mock_db):
        agg_results = [
            {"_id": "CH_0005", "total_volume": 15200.00, "txn_count": 4,
             "max_single_txn": 8500.00, "cash_equivalent": 13700.00},
        ]
        mock_db.transactions.aggregate.return_value = iter(agg_results)
        with patch("agents.compliance_agent._db", mock_db):
            from agents.compliance_agent import check_transaction_thresholds
            result = check_transaction_thresholds.invoke(
                {"cardholder_id": "CH_0005", "days": 30}
            )
            assert isinstance(result, str)
            assert "CH_0005" in result
            assert "15,200.00" in result
            assert "CTR REQUIRED" in result

    # ── 📡 Sanctions Exposure: check_sanctions_exposure ──
    def test_qs_sanctions_exposure(self, mock_db):
        # Seed data sends high-fraud txns to HIGH_RISK countries (NG, RO, UA),
        # not SANCTIONED countries (RU, IR, KP). Tool reports both tiers.
        txns = [
            {"ip_country": "NG", "amount": 35000, "merchant_name": "Lagos Electronics",
             "timestamp": "2026-04-01"},
            {"ip_country": "RO", "amount": 12000, "merchant_name": "Bucharest Trading",
             "timestamp": "2026-04-02"},
            {"ip_country": "US", "amount": 500, "merchant_name": "Walmart",
             "timestamp": "2026-04-03"},
        ]
        find_cursor = MagicMock()
        find_cursor.__iter__ = lambda self: iter(txns)
        mock_db.transactions.find.return_value = find_cursor
        with patch("agents.compliance_agent._db", mock_db):
            from agents.compliance_agent import check_sanctions_exposure
            result = check_sanctions_exposure.invoke({"cardholder_id": "CH_0007"})
            assert isinstance(result, str)
            assert "HIGH-RISK COUNTRY" in result
            assert "Lagos Electronics" in result or "Bucharest" in result
            assert "2" in result  # 2 high-risk txns

    # ── 🕸️ AML Network: aml_network_analysis ──
    def test_qs_aml_network(self, mock_db):
        mock_db.transactions.distinct.return_value = ["MER_0001", "MER_0005"]
        graph_result = [{"merchant_id": "MER_0001", "merchant_name": "Alpha Trading",
                         "risk_cluster_flag": True, "risk_network_size": 3}]
        mock_db.merchant_networks.aggregate.return_value = iter(graph_result)
        mock_db.cardholders.find_one.return_value = {"name": "Test User", "pep_flag": True}
        txn_cursor = MagicMock()
        txn_cursor.__iter__ = lambda self: iter([{"amount": 25000}, {"amount": 30000}])
        mock_db.transactions.find.return_value = txn_cursor

        with patch("agents.compliance_agent._db", mock_db):
            from agents.compliance_agent import aml_network_analysis
            result = aml_network_analysis.invoke({"cardholder_id": "CH_0010"})
            assert isinstance(result, str)
            assert "AML Network" in result
            assert "PEP FLAGGED" in result
            assert "Alpha Trading" in result
            assert "EDD required" in result.lower() or "RISK" in result

    # ── 📄 Case Notes: analyse_fraud_case_notes ──
    def test_qs_case_notes(self, mock_db):
        cases = [
            {"case_id": "FC-001", "case_type": "AML", "severity": "high",
             "financial_impact_usd": 75000, "cardholder_name": "Test User",
             "sar_filed": False, "status": "open",
             "investigation_notes": "Multiple structuring attempts below $10K. "
                                    "Layering via 3 shell companies. SAR recommended."},
        ]
        cases_coll = _mock_coll(docs=cases)
        mock_db.fraud_cases = cases_coll
        with patch("agents.compliance_agent._db", mock_db):
            from agents.compliance_agent import analyse_fraud_case_notes
            result = analyse_fraud_case_notes.invoke({})
            assert isinstance(result, str)
            assert "FC-001" in result
            assert "structuring" in result or "layering" in result
            assert "1 cases" in result
