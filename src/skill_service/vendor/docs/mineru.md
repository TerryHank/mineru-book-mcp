# MinerU standalone integration

This package keeps the book-to-skill file architecture and adds the standalone
`scripts/mineru.py` from Nebutra/MinerU-Skill. It is a zero-dependency Python
standard-library wrapper around MinerU's cloud API. It does not register an MCP
server, require a ChatGPT connector, or include any MCP configuration.

## Quick start

Run from the skill root:

```text
python scripts/mineru.py report.pdf --stdout
python scripts/mineru.py report.pdf --json
python scripts/mineru.py scan.pdf --ocr --lang ch
uv run scripts/mineru.py report.pdf --stdout
```

The free Agent API needs no account or token for files up to 10 MB and 20 pages.
The script automatically escalates to the Standard API when `MINERU_TOKEN` is
set and the input is large, batched, HTML, or requests extra formats.

## Power mode

Set `MINERU_TOKEN` in the process environment only:

```powershell
$env:MINERU_TOKEN = '<token held outside this skill>'
python scripts/mineru.py reports --output out --workers 8 --resume
python scripts/mineru.py report.pdf --format docx --format latex
```

Standard API limits are 200 MB and 200 pages. The script reports expired or
invalid tokens and points to https://mineru.net/apiManage/token. Do not put a
token in this repository, a ZIP, a prompt, or a generated skill.

## Supported inputs and options

PDF, PNG/JPG/JPEG/JP2/WebP/GIF/BMP, DOC/DOCX, PPT/PPTX, XLS/XLSX, HTML and
remote URLs are supported. Useful options include `--output/-o`, `--api`,
`--model`, repeated `--format`, `--ocr`, `--lang`, `--pages`, `--workers/-w`,
`--resume`, `--stdout`, `--json`, `--engine`, `--split`, `--chunk`, and
`--doctor`.

The source script is self-contained and can be used without the book-to-skill
generator. `scripts/extract.py` remains the structured-corpus entry point for
book-to-skill. To combine both stages, first run `scripts/mineru.py` to create
Markdown, then pass the resulting Markdown to `scripts/extract.py --backend
local` and continue with the normal chapter-generation workflow.

## ChatGPT attachments

ChatGPT conversation attachments are not automatically local paths or public
URLs. This standalone script can process a path exposed by the host, but it
cannot fetch an attachment that the host has not exposed. Do not invent a URL or
open a separate upload page as a workaround. Use the host's native file export,
an authorized local path, or an authorized remote URL.

## Output and privacy

Default output is `output/document-name/document-name.md`, with extracted images
when the Standard API returns them. Remote parsing uploads document content to
MinerU. Use the local engine or another offline parser for confidential or
air-gapped material. This package contains no API server configuration and no
credential values.

## Upstream basis

The standalone parser follows the public Nebutra/MinerU-Skill workflow:
https://github.com/Nebutra/MinerU-Skill. The upstream skill is MIT licensed and
its parser is kept as `scripts/mineru.py`; the book-to-skill generator remains
the surrounding architecture.
