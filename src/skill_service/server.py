import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path

import yaml
from .common import FastMCP, VENDOR, attach, launch, safe_path, uploaded

mcp = FastMCP("mineru-book-mcp")
attach(mcp)


def checked(cmd, env=None, timeout=600):
    result = subprocess.run(cmd, capture_output=True, timeout=timeout, env=env)
    if result.returncode:
        raise RuntimeError("Processing failed")
    return result


@mcp.tool()
def start_parse(upload_id: str, api: str = "agent", allow_cloud: bool = False,
                allow_local_fallback: bool = True) -> dict:
    """MinerU first for PDF/Office/images. Optional local fallback; no LLM generation.
    api agent is token-free; standard/auto use MINERU_TOKEN from server environment.
    Native MD/TXT goes directly to book-to-skill. Poll job_status for results.
    """
    source = uploaded(upload_id)
    if api not in {"agent", "standard", "auto"}:
        raise ValueError("Unknown API.")
    def process(folder):
        origin = "local"
        inputs = [source]
        failure = False
        if source.suffix.lower() not in {".md", ".txt"}:
            if not allow_cloud:
                raise ValueError("Cloud processing must be explicitly authorized.")
            try:
                result = checked([sys.executable, str(VENDOR / "mineru.py"), str(source),
                                  "--api", api, "--output", str(folder / "normalized"),
                                  "--json", "--timeout", "180"], timeout=240)
                report = json.loads(result.stdout)
                rows = report["results"]
                if report["failed"] or len(rows) != 1 or not rows[0].get("markdown_path"):
                    raise ValueError("Incomplete parse")
                inputs = [safe_path(folder, Path(rows[0]["markdown_path"]).resolve().relative_to(folder).as_posix())]
                origin = "mineru-" + rows[0]["api"]
            except Exception:
                if not allow_local_fallback:
                    raise
                failure = True
        env = dict(os.environ, BOOK_SKILL_WORKDIR=str(folder / "corpus"), PYTHONIOENCODING="utf-8")
        checked([sys.executable, str(VENDOR / "scripts/extract.py"),
                 *map(str, inputs), "--mode", "text", "--install-missing", "no"], env=env)
        return {"engine": origin, "mineru_failed": failure, "next": "Read corpus and workflow; host LLM drafts skill files, then call package_skill."}
    return launch(process)


@mcp.tool()
def package_skill(slug: str, files: dict[str, str]) -> dict:
    """Validate and ZIP host-authored knowledge Skill Markdown. Does not generate text."""
    import re
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug) or len(slug) > 64:
        raise ValueError("Invalid slug.")
    if not {"SKILL.md", "glossary.md", "patterns.md", "cheatsheet.md"} <= files.keys():
        raise ValueError("Required supporting files missing.")
    if len(files) > 128 or sum(len(v) for v in files.values()) > 1000000:
        raise ValueError("Bundle too large.")
    for path in files:
        if not re.fullmatch(r"(SKILL\.md|glossary\.md|patterns\.md|cheatsheet\.md|chapters/[a-z0-9-]+\.md)", path):
            raise ValueError("Only knowledge Markdown files allowed.")
    if not any(k.startswith("chapters/") for k in files):
        raise ValueError("At least one chapter required.")
    front = files["SKILL.md"].split("---", 2)
    if len(front) != 3 or front[0].strip():
        raise ValueError("Missing frontmatter.")
    meta = yaml.safe_load(front[1])
    if not isinstance(meta, dict) or meta.get("name") != slug or not meta.get("description"):
        raise ValueError("Invalid name/description.")
    def process(folder):
        root = folder / slug
        root.mkdir()
        for name, text in files.items():
            path = safe_path(root, name)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        for name, text in files.items():
            for target in re.findall(r"\]\(([^)]+\.md)\)", text):
                if "://" not in target:
                    path = (safe_path(root, name).parent / target).resolve()
                    if not path.is_relative_to(root) or not path.is_file():
                        raise ValueError("Broken or escaping link.")
        checked([sys.executable, str(VENDOR / "tools/scan_generated_skill.py"), str(root)])
        with zipfile.ZipFile(folder / (slug + ".zip"), "w", zipfile.ZIP_DEFLATED) as archive:
            for file in root.rglob("*.md"):
                archive.write(file, file.relative_to(folder).as_posix())
        return {"slug": slug, "validation": "frontmatter, links, security scan"}
    return launch(process)


def main():
    mcp.run(transport="stdio")
