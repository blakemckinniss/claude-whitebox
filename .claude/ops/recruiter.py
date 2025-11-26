#!/usr/bin/env python3
"""Council Recruiter: Selects optimal personas for a given proposal."""
import os, sys, json, re
from pathlib import Path

_script_path = os.path.abspath(__file__)
_script_dir = os.path.dirname(_script_path)
_current = _script_dir
while _current != "/":
    if os.path.exists(os.path.join(_current, ".claude", "lib", "core.py")):
        _project_root = _current
        break
    _current = os.path.dirname(_current)
else:
    raise RuntimeError("Could not find project root")

sys.path.insert(0, os.path.join(_project_root, ".claude", "lib"))
from core import logger

KEYWORD_PERSONAS = {
    r"architect|design|structure": ["architect", "pragmatist"],
    r"security|auth|vulnerab": ["security_analyst", "skeptic"],
    r"perform|optimi|speed": ["optimizer", "pragmatist"],
    r"test|coverage|quality": ["quality_advocate", "skeptic"],
    r"cost|budget|roi": ["economist", "judge"],
    r"risk|danger|fail": ["skeptic", "critic"],
    r"refactor|rewrite|legacy": ["architect", "pragmatist", "critic"],
}
DEFAULT_PERSONAS = ["judge", "critic", "skeptic", "pragmatist", "innovator"]
CORE_PERSONAS = ["judge", "critic"]

def load_persona_library():
    library_path = Path(_project_root) / ".claude" / "config" / "personas" / "library.json"
    if not library_path.exists():
        return {"personas": {}}
    try:
        with open(library_path) as f:
            return json.load(f)
    except:
        return {"personas": {}}

def recruit_council(proposal, max_personas=5):
    library = load_persona_library()
    available = set(library.get("personas", {}).keys())
    if not available:
        return DEFAULT_PERSONAS[:max_personas]
    recruited = set(CORE_PERSONAS)
    proposal_lower = proposal.lower()
    [recruited.update(p for p in personas if p in available) for pat, personas in KEYWORD_PERSONAS.items() if re.search(pat, proposal_lower)]
    [recruited.add(p) for p in DEFAULT_PERSONAS if p in available and len(recruited) < max_personas]
    result = list(recruited)[:max_personas]
    logger.info(f"Recruited {len(result)} personas: {', '.join(result)}")
    return result

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: recruiter.py <proposal>")
        sys.exit(1)
    print(f"Recruited: {', '.join(recruit_council(' '.join(sys.argv[1:])))}")
