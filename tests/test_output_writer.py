import json
import pytest
from pathlib import Path
from backend.output.writer import OutputWriter
from backend.models import Job


def test_write_soul_md(tmp_output_dir: Path):
    writer = OutputWriter(output_dir=tmp_output_dir)
    job = Job(character="Master Yoda", search_mode="normal")
    job.current_soul_version = 5
    job.scores = [0.5, 0.7, 0.85, 0.91, 0.94]
    soul_content = "# SOUL\n\nYou are Master Yoda."
    writer.write_soul(job, soul_content)
    soul_path = tmp_output_dir / "master-yoda" / "soul.md"
    assert soul_path.exists()
    text = soul_path.read_text()
    assert "character: master_yoda" in text
    assert "# SOUL" in text


def test_write_profile(tmp_output_dir: Path):
    writer = OutputWriter(output_dir=tmp_output_dir)
    job = Job(character="Master Yoda", search_mode="normal")
    profile = {"character": "Master Yoda", "core_values": ["Patience"]}
    writer.write_profile(job, profile)
    path = tmp_output_dir / "master-yoda" / "personality-profile.json"
    assert path.exists()
    data = json.loads(path.read_text())
    assert data["character"] == "Master Yoda"


def test_append_evolution_log(tmp_output_dir: Path):
    writer = OutputWriter(output_dir=tmp_output_dir)
    job = Job(character="Master Yoda", search_mode="normal")
    writer.append_evolution_log(job, loop=1, score=0.7, changes="Added speech rules", dimension="speech")
    writer.append_evolution_log(job, loop=2, score=0.85, changes="Improved boundaries", dimension="adaptation")
    path = tmp_output_dir / "master-yoda" / "evolution-log.json"
    entries = json.loads(path.read_text())
    assert len(entries) == 2
    assert entries[0]["loop"] == 1


def test_write_conversation_log(tmp_output_dir: Path):
    writer = OutputWriter(output_dir=tmp_output_dir)
    job = Job(character="Master Yoda", search_mode="normal")
    convo = [
        {"role": "converser", "tone": "philosophical", "text": "What is wealth?"},
        {"role": "target", "text": "A river it is."},
    ]
    writer.write_conversation(job, loop=1, conversation=convo)
    path = tmp_output_dir / "master-yoda" / "conversations" / "loop-01.json"
    assert path.exists()
