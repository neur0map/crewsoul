from __future__ import annotations
import json
import logging
from typing import Any
from backend.agents.base import BaseAgent
from backend.providers.base import ProviderBase
from backend.runner.events import EventEmitter

logger = logging.getLogger(__name__)

PROFILE_PROMPT = """You are a personality researcher. Given the following search results about the character "{character}", create a detailed personality profile in JSON format.

Search results:
{search_results}

Return ONLY valid JSON with this exact structure:
{{
  "character": "{character}",
  "source_material": ["list of source works"],
  "speech_patterns": {{
    "syntax": "description of how they construct sentences",
    "vocabulary": ["key words/phrases they use"],
    "avoid": ["words/patterns they never use"],
    "examples": ["3-5 iconic quotes"]
  }},
  "core_values": ["list of 3-5 core values"],
  "emotional_tendencies": {{
    "default_state": "usual emotional state",
    "under_pressure": "how they react to pressure",
    "humor": "style of humor",
    "anger": "how they express anger"
  }},
  "knowledge_boundaries": {{
    "knows_about": ["domains of knowledge"],
    "does_not_know": ["things outside their knowledge"],
    "adaptation_rule": "how to handle unfamiliar topics"
  }},
  "anti_patterns": ["things this character would NEVER do"]
}}"""

SOUL_PROMPT = """You are a system prompt engineer. Given this personality profile, write an initial SOUL.md system prompt for an AI to embody this character.

Profile:
{profile}

Write the SOUL.md in markdown with these sections:
# SOUL
(one paragraph identity statement)

## Speech
(bullet points on speech patterns, syntax, vocabulary)

## Core Values
(bullet points)

## Boundaries
(what the character would never do)

## Vibe
(emotional tone and style)

## Continuity
(how to handle session context)

Keep it under 1500 words to leave room for refinement. Be specific and actionable — avoid vague instructions."""


class ResearcherAgent(BaseAgent):
    agent_name = "researcher"

    def __init__(self, provider: ProviderBase, model: str, emitter: EventEmitter, search: Any) -> None:
        super().__init__(provider=provider, model=model, emitter=emitter)
        self.search = search

    async def research(self, character: str, job_id: str) -> tuple[dict, str]:
        search_results = await self.search.search(f"{character} personality traits speech patterns character analysis")
        search_text = "\n".join(
            f"- {r['title']}: {r['description']}" if isinstance(r, dict) else str(r)
            for r in (search_results if isinstance(search_results, list) else [search_results])
        )
        profile_response = await self.call(messages=[{"role": "user", "content": PROFILE_PROMPT.format(character=character, search_results=search_text)}], job_id=job_id)
        profile_text = profile_response.content.strip()
        if profile_text.startswith("```"):
            profile_text = profile_text.split("\n", 1)[1].rsplit("```", 1)[0]
        profile = json.loads(profile_text)
        soul_response = await self.call(messages=[{"role": "user", "content": SOUL_PROMPT.format(profile=json.dumps(profile, indent=2))}], job_id=job_id)
        logger.info("[researcher] Profile generated for %s, initial SOUL.md: %d words", character, len(soul_response.content.split()))
        return profile, soul_response.content
