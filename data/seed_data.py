"""
Seed MongoDB with rich, realistic Nexus Financial Group (VaultIQ) demo datasets.
Covers: time-series transactions, geospatial merchants/cardholders,
        vector-enabled offers & catalog, graph merchant_networks,
        fraud_cases, and compliance_rules.

Run:  python -m data.seed_data
"""

from __future__ import annotations
import random, math, sys, os
from datetime import datetime, timedelta, timezone
from typing import Any

from faker import Faker
from pymongo import MongoClient, GEOSPHERE, ASCENDING
from pymongo.operations import SearchIndexModel

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import MONGODB_URI, MONGODB_DB_NAME, COLLECTIONS

fake = Faker()
random.seed(42)

# ── constants ──────────────────────────────────────────────────────────────────
CARD_TIERS   = ["Green", "Gold", "Platinum", "Centurion"]
CATEGORIES   = ["Restaurant", "Travel", "Shopping", "Entertainment",
                 "Healthcare", "Fuel", "Grocery", "Electronics", "Hotel", "Airlines"]
CURRENCIES   = ["USD", "GBP", "EUR", "AED", "SGD", "JPY"]
RISK_COUNTRIES = ["NG", "RO", "UA", "VN", "ID", "PH"]

# Major US + global city hubs (lon, lat)
CITY_HUBS = {
    "New York":    (-74.0060, 40.7128),
    "Los Angeles": (-118.2437, 34.0522),
    "Chicago":     (-87.6298, 41.8781),
    "London":      (-0.1276, 51.5074),
    "Dubai":       (55.2708, 25.2048),
    "Singapore":   (103.8198, 1.3521),
    "Tokyo":       (139.6917, 35.6895),
    "Sydney":      (151.2093, -33.8688),
}


def jitter(lon: float, lat: float, radius_km: float = 15) -> tuple[float, float]:
    """Add random offset to a coordinate within radius_km kilometres."""
    r = radius_km / 111.0
    dlon = random.uniform(-r, r)
    dlat = random.uniform(-r, r)
    return round(lon + dlon, 6), round(lat + dlat, 6)


def rand_ts(days_back: int = 365) -> datetime:
    offset = timedelta(
        days=random.randint(0, days_back),
        hours=random.randint(0, 23),
        minutes=random.randint(0, 59),
    )
    return datetime.now(timezone.utc) - offset


# ── Cardholders ────────────────────────────────────────────────────────────────
def make_cardholders(n: int = 60) -> list[dict]:
    docs = []
    cities = list(CITY_HUBS.keys())
    for i in range(n):
        city = random.choice(cities)
        lon, lat = CITY_HUBS[city]
        lon, lat = jitter(lon, lat, 5)
        tier = random.choices(CARD_TIERS, weights=[30, 35, 25, 10])[0]
        docs.append({
            "cardholder_id": f"CH_{i+1:04d}",
            "name": fake.name(),
            "email": fake.email(),
            "phone": fake.phone_number(),
            "card_tier": tier,
            "member_since": rand_ts(365 * 8).isoformat(),
            "home_city": city,
            "home_location": {"type": "Point", "coordinates": [lon, lat]},
            "annual_spend_usd": round(random.uniform(5000, 500000), 2),
            "preferred_categories": random.sample(CATEGORIES, 3),
            "travel_frequency": random.choice(["frequent", "occasional", "rare"]),
            "profile_text": (
                f"{fake.name()} is a {tier} card member based in {city}. "
                f"They frequently spend on {', '.join(random.sample(CATEGORIES, 2))} "
                f"and travel {random.choice(['domestically', 'internationally'])} "
                f"for {'business' if random.random() > 0.4 else 'leisure'}. "
                f"Annual spend approximately ${random.randint(10,500)}K."
            ),
            "risk_score": round(random.uniform(0.01, 0.3), 3),
            "embedding": [],  # populated after Voyage AI call
            "kyc_verified": random.random() > 0.05,
            "pep_flag": random.random() < 0.02,   # politically exposed person
        })
    return docs


# ── Merchants ──────────────────────────────────────────────────────────────────
def make_merchants(n: int = 80) -> list[dict]:
    docs = []
    cities = list(CITY_HUBS.keys())
    for i in range(n):
        city = random.choice(cities)
        lon, lat = CITY_HUBS[city]
        lon, lat = jitter(lon, lat, 20)
        cat = random.choice(CATEGORIES)
        name = fake.company()
        docs.append({
            "merchant_id": f"MER_{i+1:04d}",
            "name": name,
            "category": cat,
            "city": city,
            "country": "US" if city in ["New York","Los Angeles","Chicago"] else "INT",
            "location": {"type": "Point", "coordinates": [lon, lat]},
            "mcc_code": str(random.randint(1000, 9999)),
            "rating": round(random.uniform(3.0, 5.0), 1),
            "nfg_preferred_partner": random.random() > 0.6,
            "description": (
                f"{name} is a {cat.lower()} merchant located in {city}. "
                f"Rated {round(random.uniform(3,5),1)}/5 by Nexus Financial Group cardholders. "
                f"{'NFG preferred partner with exclusive offers.' if random.random()>0.5 else 'Accepts all major cards.'}"
            ),
            "annual_nfg_volume_usd": round(random.uniform(50000, 10_000_000), 2),
            "risk_flag": random.random() < 0.08,
            "embedding": [],
        })
    return docs


# ── Offers (vector search) ─────────────────────────────────────────────────────
def make_offers(merchants: list, n: int = 60) -> list[dict]:
    offer_types = ["cashback", "points_multiplier", "travel_credit", "lounge_access", "dining_discount"]
    docs = []
    for i in range(n):
        mer = random.choice(merchants)
        otype = random.choice(offer_types)
        benefit = (
            f"{random.randint(2,15)}% cashback" if otype == "cashback" else
            f"{random.randint(2,5)}x Membership Rewards points" if otype == "points_multiplier" else
            f"${random.randint(50,300)} travel credit" if otype == "travel_credit" else
            f"Complimentary {random.choice(['Priority Pass','Centurion Lounge'])} access" if otype == "lounge_access" else
            f"{random.randint(10,30)}% off dining"
        )
        text = (
            f"Exclusive {otype.replace('_',' ').title()} offer at {mer['name']} in {mer['city']}. "
            f"Benefit: {benefit}. Valid for {random.choice(CARD_TIERS[1:])} and above cards. "
            f"Category: {mer['category']}. Limited time offer ending {(datetime.now()+timedelta(days=random.randint(7,90))).strftime('%B %d, %Y')}."
        )
        docs.append({
            "offer_id":       f"OFF_{i+1:04d}",
            "merchant_id":    mer["merchant_id"],
            "merchant_name":  mer["name"],
            "city":           mer["city"],
            "location":       mer["location"],
            "category":       mer["category"],
            "offer_type":     otype,
            "benefit_text":   benefit,
            "description":    text,
            "eligible_tiers": random.sample(CARD_TIERS[1:], random.randint(1, 3)),
            "valid_until":    (datetime.now(timezone.utc) + timedelta(days=random.randint(7,90))).isoformat(),
            "redemption_count": random.randint(0, 500),
            "embedding": [],
        })
    return docs


# ── Data Catalog (semantic metadata layer) ─────────────────────────────────────
DATA_CATALOG_ENTRIES = [
    {
        "dataset_id": "DS_001", "name": "Transaction Ledger",
        "collection": "transactions", "owner": "Risk & Data Engineering",
        "description": "Complete record of all Nexus Financial Group card transactions globally. Contains approved, declined, and pending transactions with fraud scores, merchant details, geolocation, and device metadata. Time-series data going back 10 years.",
        "tags": ["transactions","fraud","real-time","PII","financial"],
        "schema_summary": "transaction_id, cardholder_id, merchant_id, amount, currency, timestamp, location(geo), fraud_score, status, channel",
        "sensitivity": "RESTRICTED", "row_count_approx": 50_000_000,
        "sample_queries": ["Show high-value transactions above $5000 last week", "Find declined transactions in London", "List fraud-flagged transactions by Platinum cardholders"],
    },
    {
        "dataset_id": "DS_002", "name": "Cardholder Profiles",
        "collection": "cardholders", "owner": "Customer Intelligence",
        "description": "Enriched profiles of all Nexus Financial Group cardholders including demographics, spending patterns, travel preferences, risk scores, and KYC/AML flags. Used for personalisation, risk management, and compliance.",
        "tags": ["cardholders","PII","KYC","AML","personalisation"],
        "schema_summary": "cardholder_id, name, email, card_tier, home_location(geo), annual_spend_usd, preferred_categories, risk_score, pep_flag, kyc_verified",
        "sensitivity": "HIGHLY_RESTRICTED", "row_count_approx": 140_000_000,
        "sample_queries": ["Find Centurion cardholders in New York with >$1M annual spend", "List cardholders with PEP flag", "Show top spenders in travel category"],
    },
    {
        "dataset_id": "DS_003", "name": "Merchant Network",
        "collection": "merchants", "owner": "Global Merchant Services",
        "description": "Global merchant directory with geospatial data, MCC codes, NFG preferred partner status, and annual volume. Includes risk flags for high-risk merchants and relationship graph data.",
        "tags": ["merchants","geo","network","B2B","GMNS"],
        "schema_summary": "merchant_id, name, category, location(geo), mcc_code, nfg_preferred_partner, annual_nfg_volume_usd, risk_flag",
        "sensitivity": "INTERNAL", "row_count_approx": 3_500_000,
        "sample_queries": ["Show preferred partner restaurants in Chicago", "Find high-risk merchants with volume >$500K", "List airline merchants globally"],
    },
    {
        "dataset_id": "DS_004", "name": "Personalised Offers Engine",
        "collection": "offers", "owner": "Marketing & Loyalty",
        "description": "Active and historical cardholder offers including cashback, points multipliers, travel credits, and lounge access. Vector-indexed for semantic offer matching based on cardholder preferences and context.",
        "tags": ["offers","loyalty","marketing","rewards","personalisation"],
        "schema_summary": "offer_id, merchant_id, offer_type, benefit_text, eligible_tiers, valid_until, location(geo), embedding(vector)",
        "sensitivity": "INTERNAL", "row_count_approx": 25_000,
        "sample_queries": ["Find dining offers near Times Square", "List cashback offers for Platinum cardholders", "Show travel credits expiring this month"],
    },
    {
        "dataset_id": "DS_005", "name": "Fraud Investigation Cases",
        "collection": "fraud_cases", "owner": "Global Fraud & Risk",
        "description": "Structured and unstructured fraud case records including investigation notes, evidence links, resolution status, and financial impact. Linked to transactions and cardholder profiles via graph relationships.",
        "tags": ["fraud","investigations","risk","AML","compliance"],
        "schema_summary": "case_id, cardholder_id, transaction_ids[], case_type, severity, status, investigation_notes(text), financial_impact_usd, created_at",
        "sensitivity": "RESTRICTED", "row_count_approx": 180_000,
        "sample_queries": ["Show open high-severity fraud cases", "Find cases involving cross-border transactions", "List cases resolved in Q1 with recovery >$10K"],
    },
    {
        "dataset_id": "DS_006", "name": "Compliance & Regulatory Rules",
        "collection": "compliance_rules", "owner": "Legal & Compliance",
        "description": "Repository of AML/KYC rules, regulatory requirements (BSA, FATCA, PSD2, GDPR), transaction monitoring thresholds, and country-specific restrictions. Vector-indexed for natural language rule lookup.",
        "tags": ["compliance","AML","KYC","regulatory","BSA","FATCA","GDPR"],
        "schema_summary": "rule_id, rule_name, category, jurisdiction, threshold, rule_text(unstructured), effective_date, embedding(vector)",
        "sensitivity": "INTERNAL", "row_count_approx": 12_000,
        "sample_queries": ["What are the BSA reporting thresholds?", "Find GDPR rules related to data retention", "List AML rules for high-risk countries"],
    },
    {
        "dataset_id": "DS_007", "name": "Merchant Relationship Graph",
        "collection": "merchant_networks", "owner": "Network Intelligence",
        "description": "Graph representation of merchant relationships, ownership hierarchies, shared infrastructure patterns, and fraud ring associations. Used for graph-based fraud detection and network analysis.",
        "tags": ["graph","network","merchants","fraud-rings","relationships"],
        "schema_summary": "node_id, merchant_id, node_type, edges[{target_id, relationship, strength}], cluster_id, risk_cluster_flag",
        "sensitivity": "RESTRICTED", "row_count_approx": 8_000_000,
        "sample_queries": ["Find merchants connected to known fraud rings", "Show ownership hierarchy for merchant MER_0042", "Identify merchant clusters with shared bank accounts"],
    },
]


def make_data_catalog() -> list[dict]:
    for entry in DATA_CATALOG_ENTRIES:
        entry["embedding"] = []
        entry["last_updated"] = datetime.now(timezone.utc).isoformat()
    return DATA_CATALOG_ENTRIES


# ── Fraud Cases (unstructured + structured) ────────────────────────────────────
FRAUD_TYPES = ["card_not_present","account_takeover","synthetic_identity",
               "first_party_fraud","merchant_collusion","money_laundering"]

def make_fraud_cases(cardholders: list, transactions: list, n: int = 40) -> list[dict]:
    docs = []
    flagged_txns = [t for t in transactions if t["is_flagged"]]
    for i in range(n):
        ch = random.choice(cardholders)
        severity = random.choices(["low","medium","high","critical"], weights=[20,40,30,10])[0]
        ftype = random.choice(FRAUD_TYPES)
        txn_sample = random.sample(flagged_txns, min(3, len(flagged_txns)))
        financial_impact = round(random.uniform(500, 250_000), 2)
        docs.append({
            "case_id": f"CASE_{i+1:05d}",
            "cardholder_id": ch["cardholder_id"],
            "cardholder_name": ch["name"],
            "case_type": ftype,
            "severity": severity,
            "status": random.choice(["open","under_review","escalated","resolved","closed"]),
            "transaction_ids": [t["transaction_id"] for t in txn_sample],
            "financial_impact_usd": financial_impact,
            "recovery_amount_usd": round(financial_impact * random.uniform(0, 0.8), 2) if random.random() > 0.4 else 0,
            "created_at": rand_ts(90),
            "updated_at": rand_ts(10),
            "assigned_analyst": fake.name(),
            "investigation_notes": (
                f"Case opened due to {ftype.replace('_',' ')} pattern detected by ML model. "
                f"Cardholder {ch['name']} flagged for {random.randint(2,8)} suspicious transactions "
                f"totalling ${financial_impact:,.2f} across {random.randint(2,5)} different merchants. "
                f"{'Transactions originating from high-risk country. ' if random.random()>0.5 else ''}"
                f"{'Velocity pattern exceeds 3-sigma threshold. ' if random.random()>0.4 else ''}"
                f"{'Device fingerprint mismatch detected. ' if random.random()>0.5 else ''}"
                f"Recommended action: {random.choice(['Block card','Request verification','Escalate to SAR','Monitor closely'])}."
            ),
            "sar_filed": random.random() < 0.15,
            "cross_border": random.random() < 0.4,
            "embedding": [],
        })
    return docs


# ── Compliance Rules ───────────────────────────────────────────────────────────
COMPLIANCE_RULES_DATA = [
    {"rule_id":"CR_001","rule_name":"BSA CTR Reporting","category":"AML","jurisdiction":"US",
     "threshold_usd":10000,"rule_text":"All cash transactions exceeding $10,000 must be reported to FinCEN via Currency Transaction Report (CTR) within 15 days. Structured transactions designed to evade this threshold constitute a federal crime (structuring).","tags":["BSA","CTR","cash","FinCEN"]},
    {"rule_id":"CR_002","rule_name":"FATCA Foreign Account Reporting","category":"Tax Compliance","jurisdiction":"Global",
     "threshold_usd":50000,"rule_text":"US persons with foreign financial accounts exceeding $50,000 must report under FATCA. Financial institutions must withhold 30% on payments to non-compliant foreign entities. W-8BEN-E forms required for foreign account holders.","tags":["FATCA","foreign","IRS","withholding"]},
    {"rule_id":"CR_003","rule_name":"PSD2 Strong Customer Authentication","category":"Payments","jurisdiction":"EU",
     "threshold_usd":30,"rule_text":"All electronic payments above €30 require Strong Customer Authentication (SCA) with two independent authentication factors. Exemptions apply for low-risk transactions, trusted beneficiaries, and recurring payments with same amount and payee.","tags":["PSD2","SCA","EU","authentication"]},
    {"rule_id":"CR_004","rule_name":"GDPR Data Retention","category":"Data Privacy","jurisdiction":"EU",
     "threshold_usd":0,"rule_text":"Personal data must not be retained longer than necessary for its original purpose. Transaction data may be retained for up to 5 years for AML compliance. Right to erasure (Article 17) applies except where legal retention obligations exist. Data minimisation principle applies.","tags":["GDPR","data-retention","privacy","EU"]},
    {"rule_id":"CR_005","rule_name":"Suspicious Activity Report (SAR) Filing","category":"AML","jurisdiction":"US",
     "threshold_usd":5000,"rule_text":"Financial institutions must file a SAR with FinCEN within 30 days when a transaction involves $5,000 or more and there is reason to suspect illegal activity, structuring, or violations. Tipping-off the subject of a SAR is prohibited.","tags":["SAR","AML","FinCEN","suspicious-activity"]},
    {"rule_id":"CR_006","rule_name":"OFAC Sanctions Screening","category":"Sanctions","jurisdiction":"Global",
     "threshold_usd":0,"rule_text":"All transactions must be screened against OFAC SDN list and other sanctions lists in real-time. Transactions involving sanctioned individuals, entities, or countries must be blocked and reported. Zero tolerance policy - no de minimis threshold.","tags":["OFAC","sanctions","SDN","blocked-persons"]},
    {"rule_id":"CR_007","rule_name":"KYC Enhanced Due Diligence","category":"KYC","jurisdiction":"Global",
     "threshold_usd":0,"rule_text":"Enhanced Due Diligence (EDD) required for: PEPs and their family members, customers from high-risk jurisdictions (FATF grey/black list), correspondent banking relationships, and accounts with unusual activity patterns. Annual review mandatory.","tags":["KYC","EDD","PEP","high-risk"]},
    {"rule_id":"CR_008","rule_name":"Chargeback Fraud Threshold","category":"Fraud","jurisdiction":"Global",
     "threshold_usd":0,"rule_text":"Merchants exceeding 1% chargeback ratio trigger enhanced monitoring. Above 2% results in Excessive Chargeback Program enrollment and potential termination. Card-not-present fraud exceeding 0.5% requires immediate investigation and merchant hold.","tags":["chargeback","fraud","merchant","monitoring"]},
    {"rule_id":"CR_009","rule_name":"Cross-Border Transaction Monitoring","category":"AML","jurisdiction":"Global",
     "threshold_usd":1000,"rule_text":"Transactions to/from FATF-identified high-risk jurisdictions require enhanced scrutiny. Cross-border transfers above $1,000 require beneficiary identification. Real-time screening against country-level sanctions and restrictions mandatory.","tags":["cross-border","AML","FATF","international"]},
    {"rule_id":"CR_010","rule_name":"Velocity Rule - Card Present","category":"Fraud","jurisdiction":"Global",
     "threshold_usd":0,"rule_text":"More than 5 card-present transactions within 1 hour triggers automatic review. More than 3 declined card-present transactions in 30 minutes results in temporary block pending cardholder verification. Distance-based velocity (impossible travel) triggers immediate fraud alert.","tags":["velocity","fraud","real-time","card-present"]},
]

def make_compliance_rules() -> list[dict]:
    rules = []
    for r in COMPLIANCE_RULES_DATA:
        r["effective_date"] = rand_ts(365 * 3).isoformat()
        r["last_reviewed"]  = rand_ts(180).isoformat()
        r["embedding"] = []
        rules.append(r)
    return rules


# ── Merchant Networks (Graph) ──────────────────────────────────────────────────
def make_merchant_networks(merchants: list) -> list[dict]:
    """Create graph nodes & edges simulating ownership / fraud-ring relationships."""
    docs = []
    rel_types = ["same_owner","shared_bank_account","common_device","supply_chain","franchise","suspected_ring"]
    mer_ids = [m["merchant_id"] for m in merchants]
    # Assign to clusters (some legitimate, some suspicious)
    clusters = {mid: random.randint(1, 12) for mid in mer_ids}
    for mer in merchants:
        mid = mer["merchant_id"]
        # Build 2-5 edges to other merchants in similar clusters
        peers = [m for m in mer_ids if m != mid and abs(clusters[m] - clusters[mid]) <= 2]
        edges = []
        for peer in random.sample(peers, min(4, len(peers))):
            edges.append({
                "target_merchant_id": peer,
                "relationship": random.choice(rel_types),
                "strength": round(random.uniform(0.2, 1.0), 2),
                "discovered_at": rand_ts(365).isoformat(),
                "is_suspicious": random.random() < 0.15,
            })
        docs.append({
            "node_id": f"NODE_{mid}",
            "merchant_id": mid,
            "merchant_name": mer["name"],
            "node_type": "merchant",
            "cluster_id": clusters[mid],
            "risk_cluster_flag": clusters[mid] in [3, 7, 11],  # 3 risk clusters
            "edges": edges,
            "betweenness_centrality": round(random.uniform(0, 1), 4),
            "community_risk_score": round(random.uniform(0, 1), 3),
        })
    return docs


# ── Atlas Search Index Definitions ────────────────────────────────────────────

def _vector_fields(*filter_paths: str) -> dict:
    """Build a vectorSearch index definition with optional pre-filter fields."""
    fields: list[dict] = [{
        "type": "vector",
        "path": "embedding",
        "numDimensions": 1024,
        "similarity": "cosine",
    }]
    for path in filter_paths:
        fields.append({"type": "filter", "path": path})
    return {"type": "vectorSearch", "fields": fields}


# Per-collection index definitions with pre-filter support
VECTOR_INDEX_DEFS: dict[str, tuple[str, dict]] = {
    "offers":           ("offers_vector_index",     _vector_fields("eligible_tiers", "category")),
    "data_catalog":     ("catalog_vector_index",    _vector_fields("tags")),
    "compliance_rules": ("compliance_vector_index", _vector_fields("jurisdiction", "category")),
    "merchants":        ("merchants_vector_index",  _vector_fields("category", "risk_tier")),
    "cardholders":      ("cardholders_vector_index",_vector_fields("card_tier", "status")),
    "fraud_cases":      ("fraud_cases_vector_index",_vector_fields("status", "severity")),
}


def create_indexes(db) -> None:
    """Create geospatial, vector, and time-series indexes."""
    print("Creating indexes...")
    # Geospatial
    db.transactions.create_index([("location", GEOSPHERE)])
    db.merchants.create_index([("location", GEOSPHERE)])
    db.cardholders.create_index([("home_location", GEOSPHERE)])
    db.offers.create_index([("location", GEOSPHERE)])
    # Standard
    db.transactions.create_index([("cardholder_id", ASCENDING), ("timestamp", ASCENDING)])
    db.transactions.create_index([("merchant_id", ASCENDING)])
    db.transactions.create_index([("is_flagged", ASCENDING)])
    db.fraud_cases.create_index([("cardholder_id", ASCENDING), ("status", ASCENDING)])
    db.merchant_networks.create_index([("merchant_id", ASCENDING)])
    db.merchant_networks.create_index([("cluster_id", ASCENDING)])
    print("  ✓ Geospatial and standard indexes created")

    # Atlas Vector Search indexes with pre-filter fields
    for coll_name, (idx_name, idx_def) in VECTOR_INDEX_DEFS.items():
        try:
            model = SearchIndexModel(definition=idx_def, name=idx_name, type="vectorSearch")
            db[coll_name].create_search_index(model)
            filter_paths = [f["path"] for f in idx_def.get("fields", []) if f["type"] == "filter"]
            print(f"  ✓ Vector index '{idx_name}' on '{coll_name}' (filters: {filter_paths})")
        except Exception as e:
            print(f"  ⚠ Vector index on '{coll_name}' skipped (Atlas only): {e}")

    # Atlas Full-Text Search indexes — required for $rankFusion hybrid search
    FTS_INDEX_DEFS = [
        (
            "data_catalog",
            "catalog_fts_index",
            {
                "mappings": {
                    "dynamic": False,
                    "fields": {
                        "name":           [{"type": "string"}],
                        "description":    [{"type": "string"}],
                        "tags":           [{"type": "string"}],
                        "schema_summary": [{"type": "string"}],
                    },
                }
            },
        ),
        (
            "offers",
            "offers_fts_index",
            {
                "mappings": {
                    "dynamic": False,
                    "fields": {
                        "description":   [{"type": "string"}],
                        "benefit_text":  [{"type": "string"}],
                        "merchant_name": [{"type": "string"}],
                        "category":      [{"type": "string"}],
                    },
                }
            },
        ),
    ]
    for coll_name, idx_name, definition in FTS_INDEX_DEFS:
        try:
            model = SearchIndexModel(definition=definition, name=idx_name, type="search")
            db[coll_name].create_search_index(model)
            print(f"  ✓ FTS index '{idx_name}' queued on '{coll_name}'")
        except Exception as e:
            print(f"  ⚠ FTS index on '{coll_name}' skipped (Atlas only): {e}")


# ── Transactions ──────────────────────────────────────────────────────────────
def make_transactions(cardholders: list, merchants: list, n: int = 500) -> list[dict]:
    docs = []
    for i in range(n):
        ch = random.choice(cardholders)
        mer = random.choice(merchants)
        is_foreign = ch["home_city"] != mer["city"]
        amount = round(random.lognormvariate(4.5, 1.2), 2)
        fraud_score = round(random.betavariate(1, 15), 4)
        if random.random() < 0.05:      # inject anomalous transactions
            fraud_score = round(random.uniform(0.7, 0.99), 4)
            amount = round(amount * random.uniform(5, 20), 2)
        docs.append({
            "transaction_id": f"TXN_{i+1:06d}",
            "cardholder_id": ch["cardholder_id"],
            "merchant_id":   mer["merchant_id"],
            "merchant_name": mer["name"],
            "category":      mer["category"],
            "amount":        amount,
            "currency":      "USD" if not is_foreign else random.choice(CURRENCIES),
            "timestamp":     rand_ts(180),   # last 6 months
            "location": mer["location"],
            "status":  random.choices(["approved","declined","pending"], weights=[88,8,4])[0],
            "fraud_score": fraud_score,
            "is_flagged": fraud_score > 0.65,
            "channel": random.choice(["online","in-store","contactless","atm"]),
            "device_fingerprint": fake.uuid4(),
            "ip_country": random.choice(["US","GB","AE","SG"]) if not fraud_score > 0.7
                          else random.choice(RISK_COUNTRIES),
            "card_tier": ch["card_tier"],
            # time-series metadata
            "ts_meta": {
                "hour_of_day": random.randint(0, 23),
                "day_of_week": random.randint(0, 6),
                "is_weekend":  random.random() > 0.7,
            }
        })
    return docs


# ── Main Seed Entrypoint ───────────────────────────────────────────────────────
def seed_all(drop_existing: bool = True) -> None:
    client = MongoClient(MONGODB_URI)
    db = client[MONGODB_DB_NAME]

    if drop_existing:
        print(f"Dropping existing database '{MONGODB_DB_NAME}'...")
        client.drop_database(MONGODB_DB_NAME)

    print("Generating synthetic data...")
    cardholders  = make_cardholders(60)
    merchants    = make_merchants(80)
    transactions = make_transactions(cardholders, merchants, 500)
    offers       = make_offers(merchants, 60)
    data_catalog = make_data_catalog()
    fraud_cases  = make_fraud_cases(cardholders, transactions, 40)
    compliance   = make_compliance_rules()
    networks     = make_merchant_networks(merchants)

    print("Inserting documents...")
    db.cardholders.insert_many(cardholders)
    print(f"  ✓ {len(cardholders)} cardholders")
    db.merchants.insert_many(merchants)
    print(f"  ✓ {len(merchants)} merchants")
    db.transactions.insert_many(transactions)
    print(f"  ✓ {len(transactions)} transactions")
    db.offers.insert_many(offers)
    print(f"  ✓ {len(offers)} offers")
    db.data_catalog.insert_many(data_catalog)
    print(f"  ✓ {len(data_catalog)} data catalog entries")
    db.fraud_cases.insert_many(fraud_cases)
    print(f"  ✓ {len(fraud_cases)} fraud cases")
    db.compliance_rules.insert_many(compliance)
    print(f"  ✓ {len(compliance)} compliance rules")
    db.merchant_networks.insert_many(networks)
    print(f"  ✓ {len(networks)} merchant network nodes")

    create_indexes(db)
    client.close()
    print("\n✅ Seed complete!")


if __name__ == "__main__":
    seed_all()
