"""Detect template stubs and parse AI code blocks reliably."""

import re
from typing import Dict

# Generic JARVIS dashboard template markers — never ship these as a "website"
_STUB_MARKERS = (
    "PULSE.",
    "Real-time chart data will appear here",
    "System update completed",
    "GENERATING YOUR 3D APP",
    "This module is currently being provisioned",
    "Module is currently being provisioned",
    "{activeTab} Module",
)


def is_template_stub(content: str) -> bool:
    if not content or len(content) < 200:
        return True
    hits = sum(1 for m in _STUB_MARKERS if m in content)
    return hits >= 1


def parse_ai_code_blocks(raw: str) -> Dict[str, str]:
    """Extract filename → source from AI markdown responses."""
    files: Dict[str, str] = {}

    for filepath, content in re.findall(
        r"```(?:[a-zA-Z0-9_-]*)[ \t]*filename=[\"']?([^\"'\n]+)[\"']?\n(.*?)```",
        raw,
        re.DOTALL,
    ):
        files[filepath.strip()] = content.strip()

    if files:
        return files

    for filepath, content in re.findall(
        r"```(?:tsx|typescript|jsx|javascript|js|python|py|css|ts)?\n(?://|#)\s*([^\n]+)\n(.*?)```",
        raw,
        re.DOTALL,
    ):
        p = filepath.strip().lstrip("./")
        if "/" in p or "." in p:
            files[p] = content.strip()

    if files:
        return files

    # Last resort: single large tsx block → App.tsx
    tsx_blocks = re.findall(r"```(?:tsx|jsx|typescript)?\n(.*?)```", raw, re.DOTALL)
    for block in tsx_blocks:
        block = block.strip()
        if "export default" in block and ("React" in block or "function App" in block):
            files["frontend/src/App.tsx"] = block
            break

    py_blocks = re.findall(r"```(?:python|py)\n(.*?)```", raw, re.DOTALL)
    for block in py_blocks:
        block = block.strip()
        if "FastAPI" in block or "fastapi" in block:
            files["backend/main.py"] = block
            break

    return files
