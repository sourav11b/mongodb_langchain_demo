"""
test_offers_prompts.py
======================
Unit tests for the Personalised Offers (Page 3) Quick Start prompts.
Each test invokes the underlying @tool with the exact prompt values
and asserts non-empty, feature-relevant results.

Run:  python -m pytest tests/test_offers_prompts.py -v
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
    return coll


@pytest.fixture()
def mock_db():
    db = MagicMock()
    db.__getitem__ = MagicMock(return_value=_mock_coll())
    return db


@pytest.fixture()
def mock_sem_mem():
    return MagicMock()


class TestOffersQuickStartPrompts:
    """One test per Quick Start button on the Personalised Offers page."""

    # ── 🔵 Vector Search: find_relevant_offers ──
    def test_qs_offer_search(self, mock_db, mock_sem_mem):
        mock_sem_mem.search_offers.return_value = [
            {"merchant_name": "The Capital Grille", "city": "New York",
             "benefit_text": "3x points on dining", "category": "Dining",
             "valid_until": "2026-12-31", "merchant_id": "MER_0010"},
        ]
        mock_db.merchants.find_one.return_value = None
        with patch("agents.offers_agent._db", mock_db), \
             patch("agents.offers_agent._sem_mem", mock_sem_mem):
            from agents.offers_agent import find_relevant_offers
            result = find_relevant_offers.invoke(
                {"query": "dining and entertainment offers", "card_tier": "Platinum"}
            )
            assert isinstance(result, str)
            assert "Capital Grille" in result
            assert "1 offers" in result

    # ── 🟢 Hybrid Search: hybrid_search_offers ──
    def test_qs_hybrid_search(self, mock_db, mock_sem_mem):
        offers_coll = _mock_coll(docs=[
            {"merchant_name": "Marriott Bonvoy", "benefit_text": "Free hotel upgrade",
             "category": "Travel"},
        ])
        mock_db.offers = offers_coll
        with patch("agents.offers_agent._db", mock_db), \
             patch("agents.offers_agent._sem_mem", mock_sem_mem), \
             patch("agents.offers_agent.embed_texts", return_value=[[0.1]*1024]):
            from agents.offers_agent import hybrid_search_offers
            result = hybrid_search_offers.invoke(
                {"query": "travel rewards with hotel upgrades", "category": "Travel"}
            )
            assert isinstance(result, str)
            assert "Marriott Bonvoy" in result or "hotel upgrade" in result

    # ── 📍 Geospatial: find_nearby_offers ──
    def test_qs_nearby_offers(self, mock_db):
        merchants = [
            {"merchant_id": "MER_0020", "name": "Joe's Pizza", "category": "Dining"},
        ]
        offers = [
            {"merchant_name": "Joe's Pizza", "category": "Dining",
             "benefit_text": "10% cashback", "valid_until": "2026-09-30",
             "merchant_id": "MER_0020"},
        ]
        merch_cursor = MagicMock()
        merch_cursor.__iter__ = lambda self: iter(merchants)
        merch_cursor.limit = MagicMock(return_value=merch_cursor)
        mock_db.merchants.find.return_value = merch_cursor

        offer_cursor = MagicMock()
        offer_cursor.__iter__ = lambda self: iter(offers)
        offer_cursor.limit = MagicMock(return_value=offer_cursor)
        mock_db.offers.find.return_value = offer_cursor

        with patch("agents.offers_agent._db", mock_db):
            from agents.offers_agent import find_nearby_offers
            result = find_nearby_offers.invoke(
                {"longitude": -73.985, "latitude": 40.758, "radius_km": 3.0}
            )
            assert isinstance(result, str)
            assert "Joe's Pizza" in result
            assert "1 offers" in result

    # ── 💰 Spending: get_spending_summary ──
    def test_qs_spending_summary(self, mock_db):
        agg_results = [
            {"_id": "Dining", "total": 1250.00, "count": 8, "avg": 156.25},
            {"_id": "Travel", "total": 3400.00, "count": 2, "avg": 1700.00},
        ]
        mock_db.transactions.aggregate.return_value = iter(agg_results)
        with patch("agents.offers_agent._db", mock_db):
            from agents.offers_agent import get_spending_summary
            result = get_spending_summary.invoke(
                {"cardholder_id": "CH_0001", "period_days": 30}
            )
            assert isinstance(result, str)
            assert "Dining" in result
            assert "Travel" in result
            assert "$4,650.00" in result  # grand total

    # ── 🎯 Points: get_points_estimate ──
    def test_qs_points_estimate(self, mock_db):
        agg_results = [
            {"_id": "Dining", "total_spend": 1250.00},
            {"_id": "Travel", "total_spend": 3400.00},
        ]
        mock_db.transactions.aggregate.return_value = iter(agg_results)
        with patch("agents.offers_agent._db", mock_db):
            from agents.offers_agent import get_points_estimate
            result = get_points_estimate.invoke(
                {"cardholder_id": "CH_0001", "period_days": 30}
            )
            assert isinstance(result, str)
            assert "pts" in result
            # Dining: 1250*4=5000, Travel: 3400*5=17000 → total 22000
            assert "22,000" in result

    # ── 👤 Profile: get_cardholder_info ──
    def test_qs_cardholder_profile(self, mock_db):
        mock_db.cardholders.find_one.return_value = {
            "cardholder_id": "CH_0003", "name": "Emily Zhang",
            "card_tier": "Platinum", "member_since": "2019-03-15",
            "home_city": "San Francisco",
            "preferred_categories": ["Dining", "Travel", "Shopping"],
        }
        with patch("agents.offers_agent._db", mock_db):
            from agents.offers_agent import get_cardholder_info
            result = get_cardholder_info.invoke({"cardholder_id": "CH_0003"})
            assert isinstance(result, str)
            assert "Emily Zhang" in result
            assert "Platinum" in result
            assert "San Francisco" in result
            assert "Dining" in result
