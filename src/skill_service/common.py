"""MCP transport, bounded uploads, isolated jobs and verified artifact downloads."""
import base64
import hashlib
import os
import re
import secrets
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from mcp.server.fastmcp import FastMCP as FastMCP

VENDOR = Path(__file__).parent / "vendor"
ROOT = Path(os.environ.get("SKILL_SERVICE_DATA", "./service-data")).resolve()
ROOT.mkdir(parents=True, exist_ok=True)
LOCK = threading.RLock()
POOL = ThreadPoolExecutor(max_workers=2)
JOBS = {}
UPLOADS = {}
MAX_FILE = 32 * 1024 * 1024
CHUNK = 256 * 1024


def safe_path(root, relative):
    if not relative or "\\" in relative or ":" in relative:
        raise ValueError("Use a relative POSIX path.")
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError("Path escapes its root.")
    return path


def launch(fn):
    with LOCK:
        if sum(j["status"] in ("queued", "running") for j in JOBS.values()) >= 2:
            raise ValueError("Two jobs already active; wait and retry.")
        key = secrets.token_hex(16)
        folder = ROOT / key
        folder.mkdir()
        JOBS[key] = {"status": "queued", "folder": folder, "files": []}
    def run():
        JOBS[key]["status"] = "running"
        try:
            detail = fn(folder) or {}
            files = []
            for path in sorted(folder.rglob("*")):
                if path.is_file() and not path.is_symlink():
                    data = path.read_bytes()
                    files.append({"path": path.relative_to(folder).as_posix(),
                                  "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
            JOBS[key].update(status="done", files=files, detail=detail)
        except Exception as exc:
            # Do not return third-party error bodies which may contain credentials.
            JOBS[key].update(status="failed", error=type(exc).__name__)
    POOL.submit(run)
    return {"job_id": key, "status": "queued"}


def uploaded(key):
    entry = UPLOADS.get(key)
    if not entry or not entry["sealed"]:
        raise ValueError("Upload must be finished.")
    return entry["path"]


def attach(mcp):
    @mcp.tool()
    def create_upload(filename: str, size: int, sha256: str) -> dict:
        """Create an isolated upload. Then send <=256 KiB decoded base64 chunks."""
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}\.(pdf|md|txt|png|jpg|jpeg|docx|doc|ppt|pptx|xls|xlsx|html|json)", filename):
            raise ValueError("Use a simple ASCII filename and supported extension.")
        if not 0 < size <= MAX_FILE or not re.fullmatch(r"[0-9a-f]{64}", sha256):
            raise ValueError("Invalid size or SHA-256; maximum upload is 32 MiB.")
        key = secrets.token_hex(16)
        folder = ROOT / ("upload-" + key)
        folder.mkdir()
        path = folder / filename
        path.touch()
        UPLOADS[key] = dict(path=path, size=size, sha256=sha256, sealed=False)
        return {"upload_id": key, "chunk_bytes": CHUNK}

    @mcp.tool()
    def upload_chunk(upload_id: str, offset: int, data_base64: str) -> dict:
        """Append one chunk; exact offset makes interrupted uploads detectable."""
        if len(data_base64) > 4 * ((CHUNK + 2) // 3):
            raise ValueError("Chunk too large.")
        data = base64.b64decode(data_base64, validate=True)
        with LOCK:
            entry = UPLOADS[upload_id]
            path = entry["path"]
            if entry["sealed"] or offset != path.stat().st_size:
                raise ValueError("Wrong offset or already sealed.")
            if not data or len(data) > CHUNK or offset + len(data) > entry["size"]:
                raise ValueError("Invalid chunk size.")
            with path.open("ab") as stream:
                stream.write(data)
        return {"received": offset + len(data)}

    @mcp.tool()
    def finish_upload(upload_id: str) -> dict:
        """Seal an upload only after size and SHA-256 agree."""
        with LOCK:
            entry = UPLOADS[upload_id]
            data = entry["path"].read_bytes()
            if len(data) != entry["size"] or hashlib.sha256(data).hexdigest() != entry["sha256"]:
                raise ValueError("Upload size/hash mismatch.")
            entry["sealed"] = True
        return {"upload_id": upload_id, "verified": True}

    @mcp.tool()
    def job_status(job_id: str) -> dict:
        """Poll a submitted job. done includes artifact paths, sizes and hashes."""
        with LOCK:
            j = JOBS[job_id]
            return {k: v for k, v in j.items() if k != "folder"}

    @mcp.tool()
    def read_artifact(job_id: str, path: str, offset: int = 0, length: int = 262144) -> dict:
        """Download completed artifacts as base64 chunks; verify final SHA-256."""
        job = JOBS[job_id]
        if job["status"] != "done" or path not in {f["path"] for f in job["files"]}:
            raise ValueError("Not a completed artifact.")
        if offset < 0 or not 1 <= length <= CHUNK:
            raise ValueError("Invalid range.")
        file = safe_path(job["folder"], path)
        with file.open("rb") as stream:
            stream.seek(offset)
            data = stream.read(length)
        return {"data_base64": base64.b64encode(data).decode(), "offset": offset,
                "next_offset": offset + len(data), "eof": offset + len(data) >= file.stat().st_size}

    @mcp.tool()
    def read_workflow(path: str = "SKILL.md", offset: int = 0, length: int = 12000) -> dict:
        """Read bundled Skill instructions/references. These guide the host LLM."""
        if not path.endswith(".md") or offset < 0 or not 1 <= length <= 20000:
            raise ValueError("Invalid Markdown request.")
        text = safe_path(VENDOR, path).read_text(encoding="utf-8")
        return {"text": text[offset:offset + length], "next_offset": offset + length,
                "eof": offset + length >= len(text)}
