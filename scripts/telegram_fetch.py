#!/usr/bin/env python3
"""Signal Log — Telegram reader (Telethon).

Pulls messages out of your own Telegram account so a conversation can be read
back and turned into a log entry.

Run this on your own machine, not in CI: the first authentication is
interactive (Telegram sends a login code to your app) and the resulting
session file has to persist between runs. An ephemeral container gets neither.

Setup, once:

    pip install telethon
    export TG_API_ID=123456          # https://my.telegram.org -> API development tools
    export TG_API_HASH=0123abc...
    python3 scripts/telegram_fetch.py --login

Then:

    python3 scripts/telegram_fetch.py --list-chats
    python3 scripts/telegram_fetch.py --peer Casey --search cleanup
    python3 scripts/telegram_fetch.py --peer Casey --from-me --since 2026-06-01
    python3 scripts/telegram_fetch.py --peer Casey --json --out casey.json

The session file is a credential — anyone holding it can read the account.
It is written to .telegram/ which .gitignore already excludes. Keep it there.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SESSION = ROOT / ".telegram" / "signal-log"


def die(msg: str) -> None:
    print(f"error: {msg}", file=sys.stderr)
    raise SystemExit(1)


def display_name(entity) -> str:
    """Human label for a user, group or channel."""
    if entity is None:
        return "?"
    title = getattr(entity, "title", None)
    if title:
        return title
    parts = [getattr(entity, "first_name", None), getattr(entity, "last_name", None)]
    name = " ".join(p for p in parts if p)
    return name or getattr(entity, "username", None) or str(getattr(entity, "id", "?"))


def build_client():
    try:
        from telethon import TelegramClient
    except ImportError:
        die("telethon is not installed. Run: pip install telethon")

    api_id = os.environ.get("TG_API_ID")
    api_hash = os.environ.get("TG_API_HASH")
    if not api_id or not api_hash:
        die(
            "TG_API_ID / TG_API_HASH are not set.\n"
            "  Create an app at https://my.telegram.org -> API development tools, then:\n"
            "    export TG_API_ID=123456\n"
            "    export TG_API_HASH=0123abc..."
        )
    if not api_id.isdigit():
        die("TG_API_ID must be an integer")

    session = os.environ.get("TG_SESSION") or str(DEFAULT_SESSION)
    Path(session).parent.mkdir(parents=True, exist_ok=True)
    return TelegramClient(session, int(api_id), api_hash)


async def resolve_peer(client, peer: str):
    """Find one chat by @username, phone, numeric id, or display name."""
    # Unambiguous handles resolve directly and cost one call.
    try:
        return await client.get_entity(int(peer) if peer.lstrip("-").isdigit() else peer)
    except Exception:
        pass

    needle = peer.casefold()
    exact, partial = [], []
    async for dialog in client.iter_dialogs():
        name = (dialog.name or "").casefold()
        username = (getattr(dialog.entity, "username", None) or "").casefold()
        if needle == name or needle == username:
            exact.append(dialog)
        elif needle in name or (username and needle in username):
            partial.append(dialog)

    hits = exact or partial
    if not hits:
        die(f"no chat matching {peer!r}. Run --list-chats to see what is there.")
    if len(hits) > 1:
        listing = "\n".join(f"  {d.name}  (id={d.id})" for d in hits[:15])
        die(
            f"{peer!r} matches {len(hits)} chats:\n{listing}\n"
            "  Re-run with an exact name, @username, or numeric id."
        )
    return hits[0].entity


async def list_chats(client, limit: int) -> None:
    async for dialog in client.iter_dialogs(limit=limit):
        username = getattr(dialog.entity, "username", None)
        handle = f"  @{username}" if username else ""
        print(f"{dialog.id:>16}  {dialog.name}{handle}")


async def fetch(client, args) -> None:
    entity = await resolve_peer(client, args.peer)
    me = await client.get_me()

    kwargs = {"limit": args.limit}
    if args.search:
        kwargs["search"] = args.search
    if args.since:
        # reverse=True walks forward from `since` rather than backward from now,
        # so an old --since is not truncated by --limit.
        kwargs["offset_date"] = args.since
        kwargs["reverse"] = True

    records = []
    async for message in client.iter_messages(entity, **kwargs):
        if args.until and message.date > args.until:
            continue
        if args.from_me and not message.out:
            continue
        text = message.message or ""
        if not text.strip() and not args.include_empty:
            continue

        if message.out:
            sender = display_name(me)
        else:
            try:
                sender = display_name(await message.get_sender())
            except Exception:
                sender = display_name(entity)

        records.append(
            {
                "id": message.id,
                "date": message.date.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
                "sender": sender,
                "out": bool(message.out),
                "text": text,
            }
        )

    records.sort(key=lambda r: r["id"])

    if args.json:
        payload = json.dumps(
            {"peer": display_name(entity), "count": len(records), "messages": records},
            indent=2,
            ensure_ascii=False,
        )
    else:
        blocks = []
        for record in records:
            body = "\n".join("  " + line for line in record["text"].splitlines())
            blocks.append(f"[{record['date']}] {record['sender']}\n{body}")
        payload = "\n\n".join(blocks)

    if args.out:
        args.out.write_text(payload + "\n", encoding="utf-8")
        print(f"wrote {len(records)} messages -> {args.out}", file=sys.stderr)
    else:
        print(payload)
        if not records:
            print("no messages matched", file=sys.stderr)


async def run(args) -> None:
    client = build_client()
    try:
        await client.connect()

        if args.login:
            await client.start()
            print(f"authenticated as {display_name(await client.get_me())}")
            print("session stored — later runs are non-interactive")
            return

        if not await client.is_user_authorized():
            die("not authenticated. Run: python3 scripts/telegram_fetch.py --login")

        if args.list_chats:
            await list_chats(client, args.limit)
            return

        await fetch(client, args)
    finally:
        await client.disconnect()


def parse_date(value: str) -> datetime:
    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M"):
        try:
            return datetime.strptime(value, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    raise argparse.ArgumentTypeError(f"bad date {value!r} — use YYYY-MM-DD")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Read messages from your own Telegram account via Telethon.",
        epilog="First run: --login. Then: --peer Casey --search cleanup",
    )
    parser.add_argument("--login", action="store_true", help="authenticate and store the session")
    parser.add_argument("--list-chats", action="store_true", help="list chats with their ids")
    parser.add_argument("--peer", help="chat to read: name, @username, phone, or numeric id")
    parser.add_argument("--search", help="only messages containing this text")
    parser.add_argument("--limit", type=int, default=100, help="max messages to pull (default 100)")
    parser.add_argument("--since", type=parse_date, metavar="YYYY-MM-DD")
    parser.add_argument("--until", type=parse_date, metavar="YYYY-MM-DD")
    parser.add_argument("--from-me", action="store_true", help="only messages you sent")
    parser.add_argument("--include-empty", action="store_true", help="keep media-only messages")
    parser.add_argument("--json", action="store_true", help="emit JSON instead of text")
    parser.add_argument("--out", type=Path, help="write to a file instead of stdout")
    args = parser.parse_args()

    if not (args.login or args.list_chats or args.peer):
        parser.error("give --peer NAME (or --login / --list-chats)")

    try:
        asyncio.run(run(args))
    except KeyboardInterrupt:
        raise SystemExit(130)


if __name__ == "__main__":
    main()
