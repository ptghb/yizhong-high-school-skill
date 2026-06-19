#!/usr/bin/env python3
"""Export structured JSON from the local Tangshan No.1 High School history index."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ask import build_summary, dedupe_sentences, detect_question_type, page_label, sort_for_question_type
from query_index import DEFAULT_DB_PATH, search


def build_payload(question: str, matches: list[dict[str, object]]) -> dict[str, object]:
    question_type = detect_question_type(question)
    selected = []

    if matches:
        from ask import choose_sentences  # local import keeps script startup simple

        selected = choose_sentences(question, matches)
        selected = dedupe_sentences(sort_for_question_type(question_type, selected))

    return {
        "question": question,
        "question_type": question_type,
        "summary": build_summary(question_type, selected),
        "key_points": [
            {
                "text": str(item["sentence"]).strip(),
                "page_start": int(item["page_start"]),
                "page_end": int(item["page_end"]),
                "page_label": page_label(int(item["page_start"]), int(item["page_end"])),
                "score": round(float(item["score"]), 6),
            }
            for item in selected
        ],
        "passages": [
            {
                "rank": index,
                "page_start": int(match["page_start"]),
                "page_end": int(match["page_end"]),
                "page_label": page_label(int(match["page_start"]), int(match["page_end"])),
                "score": round(float(match["score"]), 6),
                "dense_score": round(float(match.get("dense_score", 0.0)), 6),
                "fts_score": round(float(match.get("fts_score", 0.0)), 6),
                "bonus": round(float(match.get("bonus", 0.0)), 6),
                "text": str(match["text"]).strip(),
            }
            for index, match in enumerate(matches, start=1)
        ],
        "meta": {
            "top_k": len(matches),
            "has_answer": bool(selected),
            "source": "local_sqlite_index",
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export structured JSON from the local Tangshan No.1 High School history index."
    )
    parser.add_argument("question", help="要导出的问题。")
    parser.add_argument(
        "--db",
        default=str(DEFAULT_DB_PATH),
        help="SQLite 索引路径。",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="导出的召回片段数。",
    )
    parser.add_argument(
        "--output",
        help="输出 JSON 文件路径；不传则打印到标准输出。",
    )
    parser.add_argument(
        "--compact",
        action="store_true",
        help="输出紧凑 JSON，而不是格式化 JSON。",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    db_path = Path(args.db).resolve()
    if not db_path.exists():
        raise FileNotFoundError(
            f"Index not found: {db_path}. Run install.sh first to build the local index."
        )

    matches = search(args.question, db_path, max(1, args.top_k))
    payload = build_payload(args.question, matches)

    if args.compact:
        json_text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    else:
        json_text = json.dumps(payload, ensure_ascii=False, indent=2)

    if args.output:
        output_path = Path(args.output).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json_text + "\n", encoding="utf-8")
    else:
        print(json_text)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
