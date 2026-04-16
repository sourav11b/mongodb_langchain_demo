"""
NiceGUI — Setup & Seeding page  (/setup)
"""
from __future__ import annotations
import sys, os, logging, asyncio
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from nicegui import ui, app
from nicegui_app.theme import inject_css, nav_bar, page_header

logger = logging.getLogger("vaultiq.nicegui.setup")


@ui.page("/setup")
async def setup_page():
    await ui.context.client.connected()
    inject_css()
    nav_bar("/setup")

    page_header(
        "⚙️ Setup & Database Seeding",
        "Initialize MongoDB collections, indexes, and vector embeddings",
    )

    log_area = ui.log(max_lines=80).classes("w-full h-64 font-mono text-xs")

    def _log(msg: str):
        logger.info(msg)
        log_area.push(msg)

    # ── Environment status ────────────────────────────────────────────────
    from config import MONGODB_URI, MONGODB_DB_NAME, AZURE_OPENAI_ENDPOINT
    with ui.card().classes("w-full"):
        ui.label("Environment").classes("font-bold text-lg")
        with ui.row().classes("gap-4 flex-wrap"):
            _ok = "✅" if MONGODB_URI else "❌"
            ui.label(f"{_ok} MongoDB URI").classes("text-sm")
            _ok = "✅" if AZURE_OPENAI_ENDPOINT else "❌"
            ui.label(f"{_ok} Azure OpenAI").classes("text-sm")
            ui.label(f"📦 Database: {MONGODB_DB_NAME}").classes("text-sm font-mono")

    # ── Action buttons ────────────────────────────────────────────────────
    with ui.row().classes("gap-2 mt-4 flex-wrap"):

        async def seed_data():
            _log("🌱 Seeding database (seed_all)…")
            _log("  Creates: cardholders, merchants, transactions, offers, data_catalog, fraud_cases, compliance_rules, merchant_networks")
            _log("  Also creates geospatial, vector, and FTS indexes.")
            try:
                from data.seed_data import seed_all
                # seed_all prints to stdout — run in executor to not block UI
                await asyncio.get_event_loop().run_in_executor(None, seed_all)
                _log("🌱 Seeding complete!")
                ui.notify("Seeding complete", type="positive")
            except Exception as e:
                _log(f"  ❌ Seeding failed: {e}")
                ui.notify(f"Seeding failed: {e}", type="negative")

        async def create_indexes():
            _log("📐 Creating indexes (requires db connection)…")
            try:
                from pymongo import MongoClient
                from data.seed_data import create_indexes as _create
                client = MongoClient(MONGODB_URI)
                db = client[MONGODB_DB_NAME]
                await asyncio.get_event_loop().run_in_executor(None, _create, db)
                client.close()
                _log("📐 Indexes created (geospatial + vector + FTS).")
                ui.notify("Indexes created", type="positive")
            except Exception as e:
                _log(f"  ❌ Index creation failed: {e}")
                ui.notify(f"Index creation failed: {e}", type="negative")

        async def generate_embeddings():
            _log("🧬 Generating Voyage AI embeddings (python -m embeddings.voyage_client)…")
            _log("  Embeds: offers, data_catalog, compliance_rules, merchants, cardholders, fraud_cases")
            _log("  Model: voyage-finance-2 (1024-dim). This may take 1-2 minutes…")
            try:
                import subprocess
                repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                result = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: subprocess.run(
                        [sys.executable, "-m", "embeddings.voyage_client"],
                        capture_output=True, text=True, cwd=repo_root,
                    ),
                )
                if result.returncode == 0:
                    for line in result.stdout.strip().split("\n"):
                        _log(f"  ✅ {line}")
                    _log("🧬 Embeddings complete!")
                    ui.notify("Embeddings generated", type="positive")
                else:
                    _log(f"  ❌ Embedding failed (exit code {result.returncode})")
                    for line in result.stderr.strip().split("\n")[-10:]:
                        _log(f"  ❌ {line}")
                    ui.notify("Embedding generation failed", type="negative")
            except Exception as e:
                _log(f"  ❌ Embedding generation failed: {e}")
                ui.notify(f"Failed: {e}", type="negative")

        async def full_setup():
            await seed_data()
            await generate_embeddings()

        ui.button("🌱 Seed Data + Indexes", on_click=seed_data, color="primary")
        ui.button("📐 Indexes Only", on_click=create_indexes, color="primary")
        ui.button("🧬 Generate Embeddings (Voyage AI)", on_click=generate_embeddings, color="primary")
        ui.button("🚀 Full Setup (Seed + Embed)", on_click=full_setup, color="deep-purple")

    # ── Collection stats ──────────────────────────────────────────────────
    ui.separator().classes("my-4")
    stats_container = ui.column().classes("w-full")

    async def refresh_stats():
        stats_container.clear()
        with stats_container:
            ui.label("Loading…").classes("text-gray-500 text-sm")
        try:
            import asyncio
            from pymongo import MongoClient

            def _fetch():
                client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
                db = client[MONGODB_DB_NAME]
                return {c: db[c].count_documents({}) for c in db.list_collection_names()}

            counts = await asyncio.get_event_loop().run_in_executor(None, _fetch)
            stats_container.clear()
            with stats_container:
                with ui.row().classes("gap-4 flex-wrap"):
                    for coll_name, cnt in counts.items():
                        with ui.card().classes("stat-card").style("min-width:160px"):
                            ui.label(coll_name).classes("font-bold text-sm text-blue-800")
                            ui.label(f"{cnt:,} docs").classes("text-xl font-bold")
        except Exception as e:
            stats_container.clear()
            with stats_container:
                ui.label(f"❌ Could not load stats: {e}").classes("text-red-600")

    ui.button("🔄 Refresh Collection Stats", on_click=refresh_stats).props("outline")
    asyncio.ensure_future(refresh_stats())
