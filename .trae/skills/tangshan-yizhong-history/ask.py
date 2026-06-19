#!/usr/bin/env python3
"""Answer questions from the local Tangshan No.1 High School history index."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from query_index import (
    DEFAULT_DB_PATH,
    FOUNDING_PASSAGE_TERMS,
    FOUNDING_TERMS,
    YEAR_RE,
    search,
    tokenize,
)

SENTENCE_SPLIT_RE = re.compile(r"(?<=[。！？!?；;])")
FOUNDING_KEY_ENTITIES = ("永平府立中学堂", "华英书院", "唐山第一中学", "唐山市第一中学")
TIMELINE_TERMS = ("沿革", "历史", "历程", "发展", "阶段", "时间线", "变迁")
LOCATION_TERMS = ("校址", "地址", "迁至", "迁到", "搬迁", "坐落", "校区")
PEOPLE_TERMS = ("人物", "校友", "谁", "老师", "校长", "教授", "书记", "主任")
HONOR_TERMS = ("荣誉", "表彰", "称号", "获奖", "实验学校", "文明单位")
YEAR_CAPTURE_RE = re.compile(r"((?:18|19|20)\d{2})年?")


def page_label(page_start: int, page_end: int) -> str:
    return f"第{page_start}页" if page_start == page_end else f"第{page_start}-{page_end}页"


def question_tokens(question: str) -> set[str]:
    return {token for token in tokenize(question) if len(token.strip()) > 1}


def detect_question_type(question: str) -> str:
    if any(term in question for term in FOUNDING_TERMS):
        return "founding"
    if any(term in question for term in LOCATION_TERMS):
        return "location"
    if any(term in question for term in PEOPLE_TERMS):
        return "people"
    if any(term in question for term in HONOR_TERMS):
        return "honor"
    if any(term in question for term in TIMELINE_TERMS):
        return "timeline"
    return "general"


def split_sentences(text: str) -> list[str]:
    normalized = re.sub(r"\s+", " ", text).strip()
    parts = [item.strip() for item in SENTENCE_SPLIT_RE.split(normalized) if item.strip()]
    return parts


def sentence_score(question: str, sentence: str, tokens: set[str]) -> float:
    sentence_tokens = set(tokenize(sentence))
    overlap = len(tokens & sentence_tokens)
    score = overlap * 2.0
    question_type = detect_question_type(question)

    if YEAR_RE.search(sentence):
        score += 1.0

    if any(term in question for term in FOUNDING_TERMS):
        founding_hits = sum(1 for term in FOUNDING_PASSAGE_TERMS if term in sentence)
        score += founding_hits * 1.5
        if founding_hits and YEAR_RE.search(sentence):
            score += 3.0
        entity_hits = sum(1 for term in FOUNDING_KEY_ENTITIES if term in sentence)
        score += entity_hits * 1.5

    if question_type == "timeline" and YEAR_RE.search(sentence):
        score += 2.0
    if question_type == "location":
        location_hits = sum(1 for term in LOCATION_TERMS if term in sentence)
        score += location_hits * 1.2
    if question_type == "people":
        people_hits = sum(1 for term in PEOPLE_TERMS if term in sentence)
        score += people_hits * 1.0
    if question_type == "honor":
        honor_hits = sum(1 for term in HONOR_TERMS if term in sentence)
        score += honor_hits * 1.2

    if len(sentence) < 12:
        score -= 1.0
    if len(sentence) > 180:
        score -= 0.5

    return score


def choose_sentences(question: str, passages: list[dict[str, object]], limit: int = 3) -> list[dict[str, object]]:
    tokens = question_tokens(question)
    candidates: list[dict[str, object]] = []

    for passage in passages:
        for sentence in split_sentences(str(passage["text"])):
            score = sentence_score(question, sentence, tokens)
            if score <= 0:
                continue
            candidates.append(
                {
                    "sentence": sentence,
                    "score": score + float(passage["score"]) * 2.0,
                    "page_start": passage["page_start"],
                    "page_end": passage["page_end"],
                }
            )

    candidates.sort(key=lambda item: item["score"], reverse=True)

    selected: list[dict[str, object]] = []
    seen_sentences: set[str] = set()

    for candidate in candidates:
        sentence = str(candidate["sentence"])
        if sentence in seen_sentences:
            continue
        if any(sentence in str(item["sentence"]) or str(item["sentence"]) in sentence for item in selected):
            continue
        if len(selected) >= limit:
            break
        selected.append(candidate)
        seen_sentences.add(sentence)

    if any(term in question for term in FOUNDING_TERMS) and selected:
        has_year_sentence = any(YEAR_RE.search(str(item["sentence"])) for item in selected)
        if not has_year_sentence:
            for candidate in candidates:
                sentence = str(candidate["sentence"])
                if YEAR_RE.search(sentence):
                    if len(selected) >= limit:
                        selected[-1] = candidate
                    else:
                        selected.append(candidate)
                    break

    if not selected and passages:
        top = passages[0]
        fallback = split_sentences(str(top["text"]))[:2]
        for sentence in fallback:
            selected.append(
                {
                    "sentence": sentence,
                    "score": float(top["score"]),
                    "page_start": top["page_start"],
                    "page_end": top["page_end"],
                }
            )

    return selected


def extract_year(sentence: str) -> int | None:
    match = YEAR_CAPTURE_RE.search(sentence)
    return int(match.group(1)) if match else None


def dedupe_sentences(selected: list[dict[str, object]]) -> list[dict[str, object]]:
    deduped: list[dict[str, object]] = []
    seen: set[str] = set()
    for item in selected:
        sentence = str(item["sentence"]).strip()
        if sentence in seen:
            continue
        seen.add(sentence)
        deduped.append(item)
    return deduped


def sort_for_question_type(question_type: str, selected: list[dict[str, object]]) -> list[dict[str, object]]:
    if question_type != "timeline":
        return selected

    with_year = [item for item in selected if extract_year(str(item["sentence"])) is not None]
    without_year = [item for item in selected if extract_year(str(item["sentence"])) is None]
    with_year.sort(key=lambda item: extract_year(str(item["sentence"])) or 9999)
    return with_year + without_year


def build_summary(question_type: str, selected: list[dict[str, object]]) -> str:
    if not selected:
        return "根据当前检索结果，暂时无法形成稳定结论。"

    first = str(selected[0]["sentence"]).strip()

    if question_type == "founding":
        return f"根据校史，学校建校源头可追溯到以下记载：{first}"
    if question_type == "timeline":
        return f"根据校史，相关发展脉络可概括为：{first}"
    if question_type == "location":
        return f"根据校史，校址相关信息主要包括：{first}"
    if question_type == "people":
        return f"根据校史，相关人物信息主要包括：{first}"
    if question_type == "honor":
        return f"根据校史，相关荣誉与表彰信息主要包括：{first}"
    return f"根据校史检索结果，可直接确认：{first}"


def format_answer(question: str, passages: list[dict[str, object]]) -> str:
    if not passages:
        return "未检索到相关内容，请先确认索引已建立，或换一种问法。"

    question_type = detect_question_type(question)
    selected = choose_sentences(question, passages)
    selected = dedupe_sentences(sort_for_question_type(question_type, selected))
    answer_lines = ["回答：", build_summary(question_type, selected), ""]

    if selected:
        answer_lines.append("要点：")
        for item in selected:
            label = page_label(int(item["page_start"]), int(item["page_end"]))
            answer_lines.append(f"- {item['sentence']}（{label}）")
    else:
        top = passages[0]
        label = page_label(int(top["page_start"]), int(top["page_end"]))
        answer_lines.append("要点：")
        answer_lines.append(f"- {str(top['text']).strip()}（{label}）")

    answer_lines.append("")
    answer_lines.append("依据片段：")

    for index, passage in enumerate(passages[:3], start=1):
        label = page_label(int(passage["page_start"]), int(passage["page_end"]))
        snippet = " ".join(split_sentences(str(passage["text"]))[:2]).strip()
        answer_lines.append(f"- [{index}] {label} {snippet}")

    answer_lines.append("")
    answer_lines.append("说明：以上答案为本地检索后的抽取式归纳，如证据不足请以原文页码为准。")
    return "\n".join(answer_lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Answer questions from the local Tangshan No.1 High School history index."
    )
    parser.add_argument("question", help="要回答的问题。")
    parser.add_argument(
        "--db",
        default=str(DEFAULT_DB_PATH),
        help="SQLite 索引路径。",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="用于生成答案的召回片段数。",
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
    print(format_answer(args.question, matches))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
