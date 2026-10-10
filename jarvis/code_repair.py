"""Repair common AI-generated syntax errors in JSX/TSX before deploy."""

import re
from pathlib import Path
from typing import Dict, List, Tuple

# Truncated Tailwind tokens often cut mid-word at line end
_TRUNCATED_TAILWIND = {
    "transiti": "transition-shadow",
    "transition-": "transition-shadow",
    "backdrop-blur": "backdrop-blur-lg",
    "hover:shadow-2xl transiti": "hover:shadow-2xl transition-shadow",
    "rounded-xl overflow": "rounded-xl overflow-hidden shadow-xl",
    "hover:bg-accent transiti": "hover:bg-accent transition",
}


def _fix_embedded_duplicate_tags(content: str) -> Tuple[str, List[str]]:
    """e.g. <h2 className="... mb<h2 className="... mb-6">Title</h2>"""
    fixes: List[str] = []
    pattern = re.compile(
        r"<(h[1-6])\s+className=\"([^\"<]*)(<h[1-6]\s+className=\"([^\"]*)\">([^<]*)</h[1-6]>)",
        re.IGNORECASE,
    )

    def repl(m: re.Match) -> str:
        fixes.append(f"embedded duplicate <{m.group(1)}>")
        return f'<{m.group(1)} className="{m.group(4)}">{m.group(5)}</{m.group(1)}>'

    return pattern.sub(repl, content), fixes


def _fix_merged_jsx_attributes(content: str) -> Tuple[str, List[str]]:
    """e.g. onClick={handleSave<button ... or }))}type="text\""""
    fixes: List[str] = []
    patterns = [
        (
            re.compile(r"(\w+)=\{([a-zA-Z_$][\w$]*)(<button\b)", re.IGNORECASE),
            lambda m: f'{m.group(1)}={{{m.group(2)}}}\n                {m.group(3)}',
            "merged attr with <button",
        ),
        (
            re.compile(r"(\}\))\}(type=\"[^\"]+\")", re.IGNORECASE),
            lambda m: f"{m.group(1)}\n        />\n        <input\n          {m.group(2)}",
            "merged closing input attrs",
        ),
    ]
    for pattern, repl_fn, label in patterns:
        def _sub(m: re.Match, fn=repl_fn, lbl=label) -> str:
            fixes.append(lbl)
            return fn(m)

        content = pattern.sub(_sub, content)
    return content, fixes


def _fix_truncated_classnames(content: str) -> Tuple[str, List[str]]:
    fixes: List[str] = []
    lines = content.split("\n")
    out: List[str] = []

    for line in lines:
        if 'className="' not in line:
            out.append(line)
            continue

        # Unclosed className on this line (odd quotes after last className=)
        idx = line.rfind('className="')
        tail = line[idx + len('className="'):] if idx >= 0 else ""
        if tail.count('"') == 0 and tail.strip() and not tail.rstrip().endswith("/>"):
            stripped = tail.rstrip()
            completed = _TRUNCATED_TAILWIND.get(stripped)
            if not completed:
                for partial, full in _TRUNCATED_TAILWIND.items():
                    if stripped.endswith(partial) or stripped == partial:
                        completed = full
                        break
            if completed:
                line = line[: idx + len('className="')] + completed + '"'
                if line.rstrip().endswith('"') and not line.rstrip().endswith('">') and ">" not in line[idx:]:
                    line = line.rstrip() + ">"
                fixes.append(f"truncated className → {completed[:40]}")
            elif re.search(r"[a-z]$", stripped) and " " in stripped:
                line = line.rstrip() + '-shadow"'
                fixes.append("truncated className (heuristic close)")

        out.append(line)

    return "\n".join(out), fixes


def _fix_duplicate_adjacent_blocks(content: str) -> Tuple[str, List[str]]:
    """Remove immediate duplicate JSX opening lines (same tag twice in a row)."""
    fixes: List[str] = []
    lines = content.split("\n")
    out: List[str] = []
    prev_stripped = ""

    for line in lines:
        s = line.strip()
        if s and s == prev_stripped and s.startswith("<") and not s.startswith("</"):
            fixes.append("duplicate adjacent JSX line")
            continue
        out.append(line)
        prev_stripped = s

    return "\n".join(out), fixes


def _fix_continuation_corruption(content: str) -> Tuple[str, List[str]]:
    """Detect and fix AI continuation corruption where the file restarts from scratch.
    
    The AI continuation logic can produce files where the complete code appears
    multiple times (each continuation restarts with imports). This keeps only
    the LAST complete copy, which is the most finished version.
    """
    fixes: List[str] = []
    
    # Detect: if 'import React' (or similar top-of-file markers) appears 3+ times,
    # the file is corrupted with multiple copies
    import_markers = [
        r'^import React',
        r'^import \{ useState',
        r'^from fastapi import',
    ]
    
    for marker_pattern in import_markers:
        marker_re = re.compile(marker_pattern, re.MULTILINE)
        occurrences = list(marker_re.finditer(content))
        
        if len(occurrences) >= 3:
            # Keep from the LAST occurrence of this import to the end
            last_pos = occurrences[-1].start()
            
            # But also look for inline filename= markers just before this position
            # Pattern: ...code...filename="path"\nimport React...
            pre_chunk = content[max(0, last_pos - 200):last_pos]
            fn_match = re.search(r'filename=["\'][^"\']+["\']\s*\n\s*$', pre_chunk)
            if fn_match:
                # Strip the filename= line too
                last_pos = last_pos  # already at import, filename= is before
            
            new_content = content[last_pos:]
            fixes.append(f"removed {len(occurrences)-1} duplicate file copies from AI continuation corruption ({len(content)} → {len(new_content)} chars)")
            content = new_content
            break  # Only fix once
    
    # Also strip stray filename= lines embedded in code
    cleaned = re.sub(
        r'\n\s*filename=["\'][^"\']+["\']\s*\n',
        '\n',
        content
    )
    if cleaned != content:
        fixes.append("stripped stray filename= markers")
        content = cleaned
    
    return content, fixes


def repair_source(content: str, filename: str = "") -> Tuple[str, List[str]]:
    """Apply all repairs; return (fixed_content, list of fix descriptions)."""
    all_fixes: List[str] = []
    for fn in (
        _fix_continuation_corruption,
        _fix_embedded_duplicate_tags,
        _fix_merged_jsx_attributes,
        _fix_truncated_classnames,
        _fix_duplicate_adjacent_blocks,
    ):
        content, fixes = fn(content)
        all_fixes.extend(fixes)
    return content, all_fixes


def repair_file_dict(files: Dict[str, str]) -> Dict[str, str]:
    """Repair all TS/TSX/JS/JSX entries in a generated files dict."""
    out = dict(files)
    for path, content in files.items():
        if not isinstance(content, str):
            continue
        ext = Path(path).suffix.lower()
        if ext not in {".tsx", ".jsx", ".ts", ".js"}:
            continue
        fixed, fixes = repair_source(content, path)
        if fixes:
            out[path] = fixed
    return out


def repair_project_tree(project_path: Path) -> List[str]:
    """Walk project and repair source files on disk. Returns log messages."""
    logs: List[str] = []
    patterns = ("*.tsx", "*.jsx", "*.ts", "*.js")
    skip = {"node_modules", "dist", "build", ".git"}

    for pattern in patterns:
        for fpath in project_path.rglob(pattern):
            if any(p in skip for p in fpath.parts):
                continue
            try:
                original = fpath.read_text(encoding="utf-8")
            except Exception:
                continue
            fixed, fixes = repair_source(original, fpath.name)
            if fixes:
                fpath.write_text(fixed, encoding="utf-8")
                rel = fpath.relative_to(project_path)
                logs.append(f"Repaired {rel}: {', '.join(fixes[:3])}")
    return logs


async def validate_frontend(project_path: Path, fe_subdir: str = "frontend") -> Tuple[bool, str]:
    """Run tsc or vite build to catch JSX syntax errors before dev server starts."""
    import asyncio
    import platform

    fe = project_path / fe_subdir
    if not fe.exists():
        fe = project_path
    if not (fe / "package.json").exists():
        return True, ""

    win = platform.system() == "Windows"
    npx = "npx.cmd" if win else "npx"

    if (fe / "tsconfig.json").exists():
        cmd = [npx, "tsc", "--noEmit", "-p", str(fe / "tsconfig.json")]
    else:
        # Vite + react-babel catches the same JSX errors shown in the browser overlay
        cmd = [npx, "vite", "build", "--emptyOutDir"]

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(fe),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        out, _ = await proc.communicate()
        text = out.decode(errors="replace")
        return proc.returncode == 0, text
    except FileNotFoundError:
        return True, ""
