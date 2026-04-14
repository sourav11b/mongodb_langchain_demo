# 🏦 VaultIQ — NextGen AI Financial Intelligence Suite

> **Built on the [LangChain × MongoDB Partnership](https://blog.langchain.com/announcing-the-langchain-mongodb-partnership-the-ai-agent-stack-that-runs-on-the-database-you-already-trust/)**
> *"The AI Agent Stack That Runs On The Database You Already Trust"*

This showcase demonstrates every key feature announced in the official LangChain + MongoDB partnership — applied to four real-world financial services use cases for **Nexus Financial Group (NFG)** using **MongoDB Atlas**, **LangChain + LangGraph**, **Voyage AI**, and **Azure OpenAI GPT-4o**.

---

## 🔗 Blog Feature Coverage

| Blog Feature | Description | P1 Data Discovery | P2 Fraud | P3 Offers | P4 Compliance |
|---|---|---|---|---|---|
| 🔵 **Atlas Vector Search** | Semantic retrieval over enterprise data | ✅ Catalog + memory recall | ✅ Fraud case search | ✅ Offer matching | ✅ Compliance rules |
| 🟢 **Hybrid Search** | `$rankFusion`: `$vectorSearch` + `$search` (BM25) fused **server-side** in Atlas — zero Python merging | ✅ `hybrid_search_catalog` | — | ✅ `hybrid_search_offers` | — |
| 🟡 **Text-to-MQL** | NL → MQL via MongoDBDatabaseToolkit / MCP | ✅ MCP find/aggregate/schema | — | — | ✅ Rule queries |
| 🟣 **MongoDB Checkpointer** | Persistent LangGraph state in Atlas | ✅ Session memory store | ✅ Investigation audit trail | ✅ Chat history | ✅ Regulatory audit |
| 🔴 **LangSmith Observability** | End-to-end agent traces + evaluations | ✅ MCP + retrieval traces | ✅ Autonomous pipeline | ✅ Offer tool traces | ✅ Compliance traces |

---

## 🚀 Use Cases

### 🔍 Use Case 1 — Semantic Metadata Layer (Data Discovery)
**Blog features active:** 🔵 Atlas Vector Search · 🟢 Hybrid Search · 🟡 Text-to-MQL · 🟣 MongoDB Checkpointer · 🔴 LangSmith

Multi-turn chat agent that lets business analysts query VaultIQ's enterprise data catalog in plain English.

- **Text-to-MQL** via MongoDB MCP Server — `find`, `aggregate`, `collection-schema`, `list-collections` and 8 more tools let the agent generate and execute MQL without any hand-coded endpoints
- **Atlas Vector Search** on the `data_catalog` collection for semantic dataset discovery
- **Native Atlas `$rankFusion` Hybrid Search** (`hybrid_search_catalog`) — a **single aggregation pipeline** runs a `$vectorSearch` (Voyage AI semantic embeddings) leg and a `$search` (BM25 full-text) leg in parallel, then fuses them server-side via Reciprocal Rank Fusion. No Python-side score merging.
- **MongoDB Checkpointer** — multi-turn session state + semantic memory consolidation: conversations are distilled by GPT-4o, embedded with Voyage AI (1024-dim), and stored in `session_memories` for cross-session recall via `$vectorSearch`

### 🚨 Use Case 2 — Fraud Intelligence Agent
**Blog features active:** 🔵 Atlas Vector Search · 🟣 MongoDB Checkpointer · 🔴 LangSmith

Autonomous agent that scans transaction streams, detects impossible-travel patterns, traces merchant fraud rings via `$graphLookup`, then blocks cards, files SARs, and notifies cardholders.

- **Atlas Vector Search** on `fraud_cases` for semantic playbook and case retrieval
- **MongoDB Checkpointer** — `FraudAgentState` (severity · actions_taken · fraud_type) persists across reasoning steps, enabling crash recovery and a full audit trail
- **LangSmith** traces every tool invocation, routing decision, and MongoDB retrieval call end-to-end
- `$graphLookup` for merchant fraud ring detection (depth ≤ 2)
- Time-series aggregation for fraud trend analysis

### 🎁 Use Case 3 — Personalised Offers Concierge
**Blog features active:** 🔵 Atlas Vector Search · 🟢 Hybrid Search · 🟣 MongoDB Checkpointer · 🔴 LangSmith

Multi-turn cardholder chat agent that recommends hyper-relevant NFG offers and nearby merchants.

- **Native Atlas `$rankFusion` Hybrid Search** (`hybrid_search_offers`) — implements the blog's *"Hybrid search combining keyword full-text search with vector similarity"* pattern. A **single aggregation pipeline** fuses two sub-pipelines inside Atlas:
  - `$vectorSearch` leg: Voyage AI `voyage-finance-2` embeddings for semantic intent matching
  - `$search` leg: BM25 full-text search over `description`, `benefit_text`, `merchant_name`, `category`
  - Both scored server-side via Reciprocal Rank Fusion — **no Python-side merging**
- **Atlas Vector Search** — `find_relevant_offers` uses pure `$vectorSearch` for intent-based matching
- Geospatial `$near` queries to surface nearby preferred partner merchants
- **MongoDB Checkpointer** — full conversation history persisted in MongoDB for multi-turn context

### ⚖️ Use Case 4 — AML & Compliance Intelligence Agent
**Blog features active:** 🔵 Atlas Vector Search · 🟡 Text-to-MQL · 🟣 MongoDB Checkpointer · 🔴 LangSmith

Autonomous regulatory agent operating across BSA, FATCA, OFAC, GDPR, and PSD2.

- **Atlas Vector Search** — 10 compliance rules vector-indexed with Voyage AI; agent retrieves relevant regulations by semantic similarity (not keyword matching) via `$vectorSearch`
- **Text-to-MQL** — agent generates MQL aggregation pipelines from plain-language instructions to query transaction thresholds and case histories
- **MongoDB Checkpointer** — all compliance actions written to MongoDB for full regulatory audit trail
- `$graphLookup` for AML layering detection across the merchant network graph
- FastMCP tools for OFAC screening and SAR filing

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────┐
│               Streamlit UI (VaultIQ · Nexus Financial Group)              │
│         Chat pages (P1, P3)  │  Autonomous agents (P2, P4)               │
├──────────────────────────────┴──────────────────────────────────────────┤
│                  LangGraph Agent Orchestration                            │
│   Agent Node (Azure GPT-4o)  ◄──►  Tool Node                            │
│                                    MongoDB MCP + pymongo                  │
├─────────────────────────────────────────────────────────────────────────┤
│                           MongoDB Atlas                                   │
│   $vectorSearch  ──┐                                                     │
│   $search (BM25) ──┴─► $rankFusion (server-side RRF) = Hybrid Search    │
│   $graphLookup · $near (geo) · Time-Series · Checkpointer                │
│   Voyage AI embeddings  (voyage-finance-2, 1024-dim)                     │
├─────────────────────────────────────────────────────────────────────────┤
│  MongoDB MCP Server (Text-to-MQL)  │  LangSmith Observability            │
│  FastMCP custom tool server        │  Traces · Evals                      │
└─────────────────────────────────────────────────────────────────────────┘
```


---

## ⚙️ Setup

### Prerequisites
- Python 3.11+
- Node.js / npx (for MongoDB MCP Server in embedded mode)
- Azure OpenAI deployment (GPT-4o)
- MongoDB Atlas cluster with Vector Search enabled
- Voyage AI API key

### Install
```bash
pip install -r requirements.txt
```

### Configure
```bash
cp .env.example .env
# Fill in MONGODB_URI, AZURE_OPENAI_*, VOYAGE_API_KEY
```

Key `.env` settings:
```bash
# MongoDB MCP Server transport (Text-to-MQL)
MONGODB_MCP_TRANSPORT=embedded   # auto-spawns npx subprocess (default)
# MONGODB_MCP_TRANSPORT=http     # connect to external server

# LangSmith Observability
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=<your-key>
```

### Run
```bash
python -m streamlit run app.py
```

---

## 📄 References

- **[LangChain × MongoDB Partnership Blog](https://blog.langchain.com/announcing-the-langchain-mongodb-partnership-the-ai-agent-stack-that-runs-on-the-database-you-already-trust/)** — the blog this showcase is built around
- [Atlas Vector Search + LangChain](https://mongodb.com/docs/atlas/ai-integrations/langchain)
- [LangSmith MongoDB Checkpointer](https://docs.langchain.com/langsmith/configure-checkpointer)
- [LangGraph (open-source)](https://github.com/langchain-ai/langgraph)
- [MongoDB MCP Server](https://www.npmjs.com/package/mongodb-mcp-server)

---

> *This demo uses synthetic data only. No real cardholder PII. Built for Nexus Financial Group · VaultIQ Platform · LangChain × MongoDB showcase purposes.*
