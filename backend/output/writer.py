from __future__ import annotations
import json
import logging
from datetime import date
from pathlib import Path
from backend.models import Job

logger = logging.getLogger(__name__)

SOUL_FRONTMATTER = """---
character: {slug}
version: {version}
generator: crewsoul
artifacts:
  profile: ./personality-profile.json
  guardrails: ./guardrails.yml
  evolution: ./evolution-log.json
generated: {date}
loops_completed: {loops}
final_score: {score}
---

"""


class OutputWriter:
    def __init__(self, output_dir: Path) -> None:
        self.output_dir = output_dir

    def _job_dir(self, job: Job) -> Path:
        d = self.output_dir / job.character_slug
        d.mkdir(parents=True, exist_ok=True)
        return d

    def write_soul(self, job: Job, soul_content: str) -> Path:
        job_dir = self._job_dir(job)
        frontmatter = SOUL_FRONTMATTER.format(
            slug=job.character_slug.replace("-", "_"),
            version=job.current_soul_version,
            date=date.today().isoformat(),
            loops=len(job.scores),
            score=f"{job.scores[-1]:.2f}" if job.scores else "0.00",
        )
        path = job_dir / "soul.md"
        path.write_text(frontmatter + soul_content)
        logger.info("Wrote soul.md: %s (%d words)", path, len(soul_content.split()))
        return path

    def write_profile(self, job: Job, profile: dict) -> Path:
        job_dir = self._job_dir(job)
        path = job_dir / "personality-profile.json"
        path.write_text(json.dumps(profile, indent=2))
        logger.info("Wrote profile: %s", path)
        return path

    def append_evolution_log(self, job: Job, loop: int, score: float, changes: str, dimension: str) -> None:
        job_dir = self._job_dir(job)
        path = job_dir / "evolution-log.json"
        entries = []
        if path.exists():
            entries = json.loads(path.read_text())
        entries.append({"loop": loop, "score": score, "dimension": dimension, "changes": changes})
        path.write_text(json.dumps(entries, indent=2))

    def write_conversation(self, job: Job, loop: int, conversation: list[dict]) -> None:
        job_dir = self._job_dir(job)
        convo_dir = job_dir / "conversations"
        convo_dir.mkdir(exist_ok=True)
        path = convo_dir / f"loop-{loop:02d}.json"
        path.write_text(json.dumps(conversation, indent=2))
        logger.info("Wrote conversation: %s", path)

    def write_guardrails(self, job: Job, guardrails: list[dict]) -> None:
        import yaml
        job_dir = self._job_dir(job)
        path = job_dir / "guardrails.yml"
        data = {"character": job.character, "edge_cases": guardrails}
        path.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False))

    def write_fingerprints(self, job: Job, fingerprints: list[dict]) -> None:
        job_dir = self._job_dir(job)
        path = job_dir / "fingerprints.json"
        path.write_text(json.dumps(fingerprints, indent=2))

    def read_fingerprints(self, job: Job) -> list[dict]:
        job_dir = self._job_dir(job)
        path = job_dir / "fingerprints.json"
        if path.exists():
            return json.loads(path.read_text())
        return []

    def append_calibration(self, job: Job, entry: dict) -> None:
        job_dir = self._job_dir(job)
        path = job_dir / "calibration.json"
        entries = []
        if path.exists():
            entries = json.loads(path.read_text())
        entries.append(entry)
        path.write_text(json.dumps(entries, indent=2))
