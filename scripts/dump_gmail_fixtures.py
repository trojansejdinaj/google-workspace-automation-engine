from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from gw_engine.clients import build_service, settings_from_env
from gw_engine.config import load_config
from gw_engine.gmail_adapter import GmailAdapter
from gw_engine.gmail_decode import decode_message_bodies
from gw_engine.logger import JsonlLogger

EMAIL_RE = re.compile(r"([A-Za-z0-9._%+-]+)@([A-Za-z0-9.-]+\.[A-Za-z]{2,})")


def _mask_email_addresses(text: str) -> str:
    def repl(match: re.Match[str]) -> str:
        local = match.group(1)
        domain = match.group(2)
        if not local:
            return f"***@{domain}"
        return f"{local[0]}***@{domain}"

    return EMAIL_RE.sub(repl, text)


def _header_value(message: dict[str, Any], name: str) -> str:
    payload = message.get("payload")
    if not isinstance(payload, dict):
        return ""

    headers = payload.get("headers")
    if not isinstance(headers, list):
        return ""

    target = name.lower()
    for header in headers:
        if not isinstance(header, dict):
            continue
        h_name = str(header.get("name") or "").strip().lower()
        if h_name == target:
            return str(header.get("value") or "")
    return ""


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, sort_keys=True)
        f.write("\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Dump Gmail messages to local JSON fixtures for parser tests."
    )
    parser.add_argument("--query", required=True, help="Gmail search query")
    parser.add_argument("--max-results", type=int, default=25, help="Maximum messages to fetch")
    parser.add_argument(
        "--out",
        default="tests/fixtures/gmail",
        help="Output directory for fixture JSON files",
    )
    parser.add_argument(
        "--mask-emails",
        action="store_true",
        help="Mask email addresses in from/to metadata and index",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    cfg = load_config()
    settings = settings_from_env()
    service = build_service(cfg=cfg, api="gmail", settings=settings)

    logger = JsonlLogger(path=out_dir / "_dump.log.jsonl", component="fixture_dump")
    adapter = GmailAdapter(service=service, logger=logger, run_id="fixture-dump")

    max_results = max(1, int(args.max_results))
    message_ids = adapter.search_message_ids(query=args.query, max_results=max_results)
    messages = adapter.fetch_messages(message_ids, format="full")

    index_rows: list[dict[str, Any]] = []
    chosen_counts = {"plain": 0, "html": 0, "none": 0}

    for message in messages:
        message_id = str(message.get("id") or "")
        if not message_id:
            continue

        decode = decode_message_bodies(message)
        chosen = str(decode.get("chosen") or "none")
        if chosen not in chosen_counts:
            chosen = "none"
        chosen_counts[chosen] += 1

        msg_path = out_dir / f"msg_{message_id}.json"
        _write_json(msg_path, message)

        subject = _header_value(message, "Subject")
        from_val = _header_value(message, "From")
        date_val = _header_value(message, "Date")

        if args.mask_emails:
            subject = _mask_email_addresses(subject)
            from_val = _mask_email_addresses(from_val)

        index_rows.append(
            {
                "id": message_id,
                "subject": subject,
                "from": from_val,
                "date": date_val,
                "chosen": chosen,
            }
        )

    _write_json(out_dir / "_index.json", index_rows)

    print(f"query={args.query}")
    print(f"ids_found={len(message_ids)}")
    print(f"fetched_count={len(messages)}")
    print(f"written_count={len(index_rows)}")
    print(f"chosen_plain={chosen_counts['plain']}")
    print(f"chosen_html={chosen_counts['html']}")
    print(f"chosen_none={chosen_counts['none']}")
    print(f"out_dir={out_dir}")


if __name__ == "__main__":
    main()
