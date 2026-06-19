---
name: "tangshan-yizhong-history"
description: "Retrieves facts from the Tangshan No.1 High School history PDF using a local SQLite vector index. Invoke when users ask about school history, timelines, people, events, or document-grounded answers."
---

# Tangshan No.1 High School History

Use this skill when the user asks about `唐山一中` / `唐山市第一中学` history and the answer should be grounded in the local PDF archive.

This skill is designed to work in a local workspace with:

- PDF text extraction
- lightweight local vector retrieval
- no external middleware
- a single install command

## Install

Run this once inside the workspace:

```bash
bash .trae/skills/tangshan-yizhong-history/install.sh
```

Or:

```bash
make -C .trae/skills/tangshan-yizhong-history install
```

This command creates a local virtual environment, installs dependencies, and reuses the bundled SQLite index by default.

If the bundled index is missing, it falls back to building from the PDF.

To force a rebuild from PDF:

```bash
bash .trae/skills/tangshan-yizhong-history/install.sh --rebuild
```

## Retrieval Command

Before answering, retrieve evidence from the index:

```bash
.trae/skills/tangshan-yizhong-history/.venv/bin/python \
  .trae/skills/tangshan-yizhong-history/query_index.py "你的问题"
```

Example:

```bash
.trae/skills/tangshan-yizhong-history/.venv/bin/python \
  .trae/skills/tangshan-yizhong-history/query_index.py "唐山一中是什么时候建立的？"
```

## Direct Answer Command

If you want a retrieval-grounded answer directly, run:

```bash
.trae/skills/tangshan-yizhong-history/.venv/bin/python \
  .trae/skills/tangshan-yizhong-history/ask.py "唐山一中是什么时候建立的？"
```

Or:

```bash
make -C .trae/skills/tangshan-yizhong-history ask QUESTION="唐山一中是什么时候建立的？"
```

## JSON Export Command

If you want structured output for other agents or scripts, run:

```bash
.trae/skills/tangshan-yizhong-history/.venv/bin/python \
  .trae/skills/tangshan-yizhong-history/export_json.py "唐山一中是什么时候建立的？"
```

Or:

```bash
make -C .trae/skills/tangshan-yizhong-history export-json QUESTION="唐山一中是什么时候建立的？"
```

## Workflow

1. If the index does not exist, run the install command first.
2. Prefer `ask.py` for direct question answering.
3. `ask.py` uses simple question-type templates for founding, timeline, location, people, and honors.
4. Use `query_index.py` when you need more raw evidence or more passages.
5. Use `export_json.py` when another agent or script needs structured fields.
6. Answer only from retrieved evidence.
7. If the evidence is incomplete or conflicting, say so explicitly.
8. Cite page numbers in the answer when possible.

## Answering Rules

- Prefer facts that appear in multiple retrieved passages.
- Keep names, years, and events aligned with the retrieved text.
- Do not invent details not supported by the PDF.
- If OCR noise exists, mention uncertainty instead of guessing.
- When useful, provide a short timeline based on the retrieved passages.

## Good Prompts

- `唐山一中的建校沿革是什么？`
- `校史里提到过哪些重要校址变迁？`
- `校史里出现过哪些重要人物和事件？`
- `文革前后学校经历了哪些变化？`
- `根据校史 PDF，总结唐山一中的发展阶段。`
