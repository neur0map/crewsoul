from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from backend.config import AppConfig, load_config, save_config, redact_keys, validate_config

router = APIRouter(prefix="/api/config")


@router.get("")
async def get_config(request: Request):
    config = load_config(request.app.state.config_path)
    if config is None:
        return {"configured": False, "config": None}
    return {"configured": True, "config": redact_keys(config)}


@router.post("")
async def save_config_endpoint(request: Request):
    import logging
    logger = logging.getLogger(__name__)
    data = await request.json()
    logger.info("Config save request received: provider=%s", data.get("provider", {}).get("active", "?"))
    # Merge empty/redacted keys with existing config to preserve secrets
    existing = load_config(request.app.state.config_path)
    if existing:
        for prov in ("openai", "openrouter"):
            incoming_key = data.get("provider", {}).get(prov, {}).get("api_key", "")
            if not incoming_key or "\u2022" in incoming_key:
                if prov in data.get("provider", {}):
                    data["provider"][prov]["api_key"] = getattr(getattr(existing.provider, prov), "api_key", "")
        for search_prov in ("brave", "perplexity"):
            incoming_key = data.get("search", {}).get(search_prov, {}).get("api_key", "")
            if not incoming_key or "\u2022" in incoming_key:
                if search_prov in data.get("search", {}):
                    data["search"][search_prov]["api_key"] = getattr(getattr(existing.search, search_prov), "api_key", "")
    config = AppConfig(**data)
    errors = validate_config(config)
    if errors:
        return JSONResponse(status_code=400, content={"errors": errors})
    save_config(config, request.app.state.config_path)
    request.app.state.config = config

    # Start/restart background runners with new config
    from backend.main import start_runners
    start_runners(request.app)

    return {"status": "saved"}


@router.post("/validate")
async def validate_key(request: Request):
    data = await request.json()
    provider_name = data.get("provider", "openai")
    api_key = data.get("api_key", "")
    if provider_name == "openai":
        from backend.providers.openai_provider import OpenAIProvider
        provider = OpenAIProvider(api_key=api_key, max_retries=0)
    else:
        from backend.providers.openrouter_provider import OpenRouterProvider
        provider = OpenRouterProvider(api_key=api_key, max_retries=0)
    try:
        valid = await provider.validate_key()
        models = await provider.list_models() if valid else []
        return {"valid": valid, "models": models}
    except Exception as e:
        return {"valid": False, "models": [], "error": str(e)}
