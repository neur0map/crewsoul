import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import AppConfig, load_config
from backend.output.writer import OutputWriter
from backend.routes.chat_routes import router as chat_router
from backend.routes.config_routes import router as config_router
from backend.routes.events_routes import router as events_router
from backend.routes.job_routes import router as job_router
from backend.runner.events import EventEmitter
from backend.runner.queue import JobQueue

logger = logging.getLogger(__name__)


def start_runners(app: FastAPI) -> None:
    """Start preparation and orchestration background tasks from current config.
    Safe to call multiple times — cancels existing tasks first."""
    # Cancel any existing tasks
    for task in getattr(app.state, "background_tasks", []):
        task.cancel()
    app.state.background_tasks = []

    config: AppConfig | None = app.state.config
    if not config:
        return

    from backend.runner.preparation import PreparationPipeline
    from backend.runner.orchestrator import Orchestrator

    active = config.provider.active
    if active == "openai":
        from backend.providers.openai_provider import OpenAIProvider
        provider = OpenAIProvider(api_key=config.provider.openai.api_key)
    else:
        from backend.providers.openrouter_provider import OpenRouterProvider
        provider = OpenRouterProvider(api_key=config.provider.openrouter.api_key)

    app.state.chat_provider = provider
    models = config.provider.active_config().models

    search = None
    if config.search.brave.api_key:
        from backend.search.brave import BraveSearch
        search = BraveSearch(api_key=config.search.brave.api_key)
    elif config.search.perplexity.api_key:
        from backend.search.perplexity import PerplexitySearch
        search = PerplexitySearch(api_key=config.search.perplexity.api_key)

    writer = OutputWriter(output_dir=app.state.output_dir)

    if search:
        prep = PreparationPipeline(
            provider=provider, search=search, emitter=app.state.emitter,
            queue=app.state.queue, writer=writer,
            researcher_model=models.researcher, fetcher_model=models.fetcher,
        )
        app.state.background_tasks.append(asyncio.create_task(prep.run_continuous()))

    orch = Orchestrator(
        provider=provider, emitter=app.state.emitter,
        queue=app.state.queue, writer=writer,
        converser_model=models.converser, target_model=models.target,
        judge_model=models.judge, config=config.orchestration,
        scoring_config=config.scoring,
    )
    app.state.background_tasks.append(asyncio.create_task(orch.run_continuous()))
    logger.info("Background runners started (provider=%s, search=%s)", active, "brave" if config.search.brave.api_key else "perplexity" if config.search.perplexity.api_key else "none")


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.queue.rehydrate()
    app.state.background_tasks = []
    start_runners(app)
    yield
    for task in app.state.background_tasks:
        task.cancel()


def create_app(
    config_path: Path = Path("crewsoul.config.yml"),
    output_dir: Path = Path("output"),
) -> FastAPI:
    app = FastAPI(title="CrewSoul", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
    )

    app.state.config_path = config_path
    app.state.output_dir = output_dir
    app.state.config = load_config(config_path)
    app.state.queue = JobQueue(output_dir=output_dir)
    app.state.emitter = EventEmitter()
    app.state.background_tasks = []

    app.include_router(config_router)
    app.include_router(job_router)
    app.include_router(events_router)
    app.include_router(chat_router)

    # Serve built Svelte frontend
    frontend_dir = Path(__file__).parent.parent / "frontend" / "build"
    if frontend_dir.exists():
        from fastapi.staticfiles import StaticFiles
        app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")

    return app
