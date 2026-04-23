# 🏦 VaultIQ — NextGen AI Financial Intelligence Suite

> **Built on the [LangChain × MongoDB Partnership](https://blog.langchain.com/announcing-the-langchain-mongodb-partnership-the-ai-agent-stack-that-runs-on-the-database-you-already-trust/)**
> *"The AI Agent Stack That Runs On The Database You Already Trust"*

This showcase demonstrates every key feature of the **`langchain-mongodb`** package — applied to real-world financial services use cases for **Nexus Financial Group (NFG)** using **MongoDB Atlas**, **LangChain + LangGraph**, **Voyage AI**, and **Azure OpenAI GPT-4o**.

---

## 📑 Pages

The app consists of **10 pages** — a home page plus 9 functional pages:

| # | Page | What It Does |
|---|------|-------------|
| 🏠 | **Home** (`app.py`) | Landing page with architecture overview, blog feature matrix, and navigation to all pages |
| 1 | **🔍 Data Discovery** | Multi-turn chat agent for querying the enterprise data catalog. Uses Atlas Vector Search, Hybrid Search (`$rankFusion`), Text-to-MQL via MCP Server, and cross-session semantic memory |
| 2 | **🚨 Fraud Intelligence** | Autonomous agent that detects impossible-travel fraud, traces merchant fraud rings via `$graphLookup`, blocks cards, files SARs, and notifies cardholders |
| 3 | **🎁 Personalised Offers** | Cardholder concierge that recommends offers using Hybrid Search (vector + BM25 fused server-side), geospatial `$near` for nearby merchants, and pre-filtering by card tier/category |
| 4 | **⚖️ Compliance Agent** | Regulatory agent for BSA, FATCA, OFAC, GDPR, PSD2. Retrieves compliance rules via vector search, generates MQL for threshold analysis, and detects AML layering via `$graphLookup` |
| 5 | **⚙️ Setup & Data** | Seed data & embeddings, Atlas status panel (connection, doc count, index count), drop/reload all collections, MongoDB MCP Server configuration |
| 6 | **🗄️ Database Agent** | Natural-language database queries using `MongoDBDatabaseToolkit`. Auto-discovers schemas, generates MQL, validates with query checker, executes — shows generated MQL and full agent trace |
| 7 | **🕸️ Knowledge Graph** | Builds a knowledge graph from unstructured text using `MongoDBGraphStore` with LLM entity extraction. Query with `MongoDBGraphRAGRetriever` for multi-hop answers via `$graphLookup` traversal |
| 8 | **🍃 LangChain MongoDB** | Live showcase of **all 10 `langchain-mongodb` modules** — each with a runnable demo, code snippet, scores, and raw results (see below) |
| 9 | **🔗 Unified Pipeline** | Single aggregate query combining `$rankFusion` (hybrid search), `$geoWithin` (geo filter), `$lookup` (time-series transaction stats), and `$graphLookup` (merchant network traversal) — results reranked by Voyage AI `rerank-2` |

---

## 🍃 `langchain-mongodb` Feature Coverage

Page 8 provides a dedicated demo for **every module** in the package:

| # | Module | Category | What the Demo Shows |
|---|--------|----------|-------------------|
| 1 | `MongoDBAtlasVectorSearch` | Retrieval | Semantic similarity search with scores via `similarity_search_with_score()` |
| 2 | `MongoDBAtlasFullTextSearchRetriever` | Retrieval | BM25-style keyword search with Atlas Search, scores via `include_scores=True` |
| 3 | `MongoDBAtlasHybridSearchRetriever` | Retrieval | Vector + text combined via reciprocal rank fusion, backed by a `vectorstore` |
| 4 | `MongoDBChatMessageHistory` | Memory | Store/retrieve multi-turn conversations with session isolation |
| 5 | `MongoDBCache` | Caching | Exact-match LLM response cache — shows miss ms vs hit ms and speedup factor |
| 6 | `MongoDBAtlasSemanticCache` | Caching | Meaning-based LLM cache — "Explain X" and "What is X?" return the same cached answer |
| 7 | `MongoDBGraphStore` + `GraphRAGRetriever` | Knowledge Graph | LLM entity extraction → graph storage → `$graphLookup` traversal → multi-hop answers |
| 8 | `MongoDBLoader` | Data Loading | Load MongoDB documents as LangChain `Document` objects |
| 9 | `MongoDBRecordManager` | Data Loading | Deduplicate document ingestion with key tracking |
| 10 | `MongoDBDatabaseToolkit` | Agent Toolkit | Sample NL queries → generated MQL → agent execution with full tool trace |

---

## 🔗 Blog Feature Matrix

| Blog Feature | Description | P1 Discovery | P2 Fraud | P3 Offers | P4 Compliance | P6 DB Agent | P7 Graph | P8 Showcase |
|---|---|---|---|---|---|---|---|---|
| 🔵 **Atlas Vector Search** | Semantic retrieval over enterprise data | ✅ | ✅ | ✅ | ✅ | — | — | ✅ |
| 🟢 **Hybrid Search** | `$rankFusion`: vector + BM25 fused server-side | ✅ | — | ✅ | — | — | — | ✅ |
| 🟡 **Text-to-MQL** | NL → MQL via MongoDBDatabaseToolkit / MCP | ✅ | — | — | ✅ | ✅ | — | ✅ |
| 🟣 **MongoDB Checkpointer** | Persistent LangGraph state in Atlas | ✅ | ✅ | ✅ | ✅ | ✅ | — | — |
| 🔴 **LangSmith Observability** | End-to-end agent traces + evaluations | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — |
| 🕸️ **GraphRAG** | MongoDBGraphStore + `$graphLookup` traversal | — | — | — | — | — | ✅ | ✅ |
| 💾 **Caching** | MongoDBCache + MongoDBAtlasSemanticCache | — | — | — | — | — | — | ✅ |
| 📥 **Data Loading** | MongoDBLoader + MongoDBRecordManager | — | — | — | — | — | — | ✅ |

---

## 🚀 Use Cases (Detail)

### 🔍 Use Case 1 — Semantic Metadata Layer (Data Discovery)
**Blog features:** 🔵 Atlas Vector Search · 🟢 Hybrid Search · 🟡 Text-to-MQL · 🟣 Checkpointer · 🔴 LangSmith

Multi-turn chat agent that lets business analysts query VaultIQ's enterprise data catalog in plain English.

- **Text-to-MQL** via MongoDB MCP Server — `find`, `aggregate`, `collection-schema`, `list-collections` and 8 more tools
- **Atlas Vector Search** on the `data_catalog` collection for semantic dataset discovery
- **Native Atlas `$rankFusion` Hybrid Search** — single aggregation pipeline fuses `$vectorSearch` + `$search` (BM25) server-side
- **MongoDB Checkpointer** — multi-turn session state + semantic memory consolidation

### 🚨 Use Case 2 — Fraud Intelligence Agent
**Blog features:** 🔵 Atlas Vector Search · 🟣 Checkpointer · 🔴 LangSmith

Autonomous agent that scans transaction streams, detects impossible-travel patterns, and traces merchant fraud rings.

- **Atlas Vector Search** on `fraud_cases` for semantic playbook and case retrieval
- `$graphLookup` for merchant fraud ring detection (depth ≤ 2)
- **MongoDB Checkpointer** — `FraudAgentState` persists across reasoning steps
- Time-series aggregation for fraud trend analysis

### 🎁 Use Case 3 — Personalised Offers Concierge
**Blog features:** 🔵 Atlas Vector Search · 🟢 Hybrid Search · 🟣 Checkpointer · 🔴 LangSmith

Multi-turn cardholder chat agent that recommends hyper-relevant offers and nearby merchants.

- **Hybrid Search** (`hybrid_search_offers`) — `$vectorSearch` (Voyage AI) + `$search` (BM25) fused via `$rankFusion`
- **Atlas Vector Search** with pre-filtering by `card_tier` and `category`
- Geospatial `$near` queries for nearby preferred partner merchants
- **MongoDB Checkpointer** — full conversation history persisted

### ⚖️ Use Case 4 — AML & Compliance Intelligence Agent
**Blog features:** 🔵 Atlas Vector Search · 🟡 Text-to-MQL · 🟣 Checkpointer · 🔴 LangSmith

Autonomous regulatory agent operating across BSA, FATCA, OFAC, GDPR, and PSD2.

- **Atlas Vector Search** — compliance rules indexed with Voyage AI; retrieved by semantic similarity
- **Text-to-MQL** — generates MQL aggregation pipelines from plain-language instructions
- `$graphLookup` for AML layering detection across the merchant network graph
- FastMCP tools for OFAC screening and SAR filing

### 🗄️ Use Case 5 — Natural-Language Database Agent
**Blog features:** 🟡 Text-to-MQL · 🟣 Checkpointer · 🔴 LangSmith

Query any MongoDB collection with plain English using the official `MongoDBDatabaseToolkit`.

- **MongoDBDatabaseToolkit** provides 4 tools: `query_mongodb`, `info_mongodb`, `list_mongodb`, `check_query_mongodb`
- Auto-discovers collection schemas, generates MQL, validates queries, executes them
- Shows the generated MQL query alongside the answer
- LangGraph ReAct agent with full tool trace

### 🕸️ Use Case 6 — Knowledge Graph Agent
**Blog features:** 🕸️ GraphRAG · 🔴 LangSmith

Build a knowledge graph from unstructured financial text, then query it with multi-hop natural language questions.

- **MongoDBGraphStore** — LLM entity extraction (12 entity types, 14 relationship types)
- **MongoDBGraphRAGRetriever** — extracts entities from questions, traverses via `$graphLookup`
- Build graph from fraud cases, compliance rules, merchant networks, or custom text
- Entity explorer for direct graph traversal

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│           Streamlit UI (VaultIQ · Nexus Financial Group)                 │
│  P1 Discovery │ P2 Fraud │ P3 Offers │ P4 Compliance │ P6 DB Agent     │
│  P7 Knowledge Graph │ P8 langchain-mongodb Showcase │ P5 Setup         │
├──────────────────────────────────────────────────────────────────────────┤
│                  LangGraph Agent Orchestration                           │
│   Agent Node (Azure GPT-4o)  ◄──►  Tool Node                           │
│   MongoDBDatabaseToolkit · FastMCP · pymongo                             │
├──────────────────────────────────────────────────────────────────────────┤
│                           MongoDB Atlas                                  │
│   $vectorSearch  ──┐                                                     │
│   $search (BM25) ──┴─► $rankFusion (server-side RRF) = Hybrid Search   │
│   $graphLookup · $near (geo) · Time-Series · Checkpointer               │
│   MongoDBGraphStore (Knowledge Graph) · MongoDBCache (LLM caching)      │
│   Voyage AI embeddings  (voyage-finance-2, 1024-dim)                    │
├──────────────────────────────────────────────────────────────────────────┤
│  MongoDB MCP Server (Text-to-MQL)  │  LangSmith Observability           │
│  FastMCP custom tool server        │  Traces · Evals                     │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 📁 Project Structure

```
├── app.py                          # Home page
├── pages/
│   ├── 1_🔍_Data_Discovery.py      # Use Case 1 — Data catalog chat
│   ├── 2_🚨_Fraud_Intelligence.py  # Use Case 2 — Autonomous fraud agent
│   ├── 3_🎁_Personalised_Offers.py # Use Case 3 — Offers concierge
│   ├── 4_⚖️_Compliance_Agent.py    # Use Case 4 — AML/BSA compliance
│   ├── 5_⚙️_Setup_&_Data.py        # Setup, seeding, Atlas status
│   ├── 6_🗄️_Database_Agent.py      # Use Case 5 — NL database queries
│   ├── 7_🕸️_Knowledge_Graph.py     # Use Case 6 — GraphRAG agent
│   ├── 8_🍃_LangChain_MongoDB.py   # All 10 langchain-mongodb modules
│   └── 9_🔗_Unified_Pipeline.py   # 4-feature aggregate + Voyage reranker
├── agents/
│   ├── data_discovery_agent.py     # P1 agent with MCP + hybrid search
│   ├── fraud_agent.py              # P2 autonomous fraud detection
│   ├── offers_agent.py             # P3 offers concierge
│   ├── compliance_agent.py         # P4 regulatory agent
│   ├── database_agent.py           # P6 MongoDBDatabaseToolkit agent
│   └── graphrag_agent.py           # P7 MongoDBGraphStore agent
├── tools/
│   ├── mcp_client.py               # MongoDB MCP Server client
│   ├── fraud_tools.py              # Fraud detection tools
│   ├── compliance_tools.py         # Compliance/OFAC tools
│   ├── langchain_mongodb_showcase.py  # P8 demo functions
│   └── unified_pipeline.py          # P9 unified aggregate + Voyage reranker
├── data/
│   └── seed_data.py                # Seed data + vector/FTS index creation
├── embeddings/
│   └── voyage_client.py            # Voyage AI embedding generation
├── config.py                       # All env vars and config
└── requirements.txt
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
streamlit run app.py
```

### Seed Data
Navigate to **⚙️ Setup & Data** (Page 5) in the app, or run from CLI:
```bash
python -m data.seed_data
python -m embeddings.voyage_client
```

The Setup page also provides:
- **Atlas Status Panel** — connection status, MongoDB version, document count, search index count
- **🗑️ Drop All Collections** — clean slate (with confirmation)
- **🔄 Full Reload** — seed + embed + index in one click

---

## 🖥️ NiceGUI Edition (Alternative UI)

An **async-native** alternative to the Streamlit app — same agents, same tools, same MongoDB backend.

```bash
pip install nicegui
python nicegui_app/main.py   # port 8502
```

| Route | Page |
|---|---|
| `/` | Home / navigation |
| `/setup` | Setup & Seeding |
| `/discovery` | Data Discovery (multi-turn chat) |
| `/fraud` | Fraud Intelligence (scenario injection) |
| `/offers` | Personalised Offers (AI concierge) |
| `/compliance` | Compliance Audit (BSA/AML/OFAC) |

Both apps share the same `agents/`, `config.py`, `data/`, and `tools/` modules.

---

## 📄 References

- **[LangChain × MongoDB Partnership Blog](https://blog.langchain.com/announcing-the-langchain-mongodb-partnership-the-ai-agent-stack-that-runs-on-the-database-you-already-trust/)** — the blog this showcase is built around
- [langchain-mongodb PyPI](https://pypi.org/project/langchain-mongodb/) — the official integration package
- [Atlas Vector Search + LangChain](https://mongodb.com/docs/atlas/ai-integrations/langchain)
- [MongoDB GraphRAG docs](https://www.mongodb.com/docs/atlas/ai-integrations/langchain/graph-rag/)
- [LangGraph (open-source)](https://github.com/langchain-ai/langgraph)
- [MongoDB MCP Server](https://www.npmjs.com/package/mongodb-mcp-server)

---

> *This demo uses synthetic data only. No real cardholder PII. Built for Nexus Financial Group · VaultIQ Platform · LangChain × MongoDB showcase purposes.*
