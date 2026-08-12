# Signal Log

> Public, tamper-evident, timestamped log of Josh Cullen Santos' original work.
> Every entry is cryptographically anchored. If anyone claims your idea, point them here.

## What this is

A chronological, append-only journal of:

- Creative work (lyrics, music direction, art concepts, copy, brand decisions)
- Business design (KULN, LIMBO, 1Z, Signal Network architecture)
- System designs and inventions
- Strategic thinking and frameworks

Each entry is committed to git the moment it's written. Git commits are:

1. **Cryptographically chained** — every commit includes the SHA of the previous one. Re-ordering or back-dating breaks the chain.
2. **Timestamped by GitHub** — a third-party service that records when it first saw the commit (server-side timestamp you can't fake).
3. **Anchored to Bitcoin blockchain** — via OpenTimestamps, each commit hash is included in a Bitcoin transaction. That transaction is globally witnessed and un-editable.

The result: for any entry on this site, there is mathematical proof of **the latest possible date it could have been written**. Anyone who claims the idea after that date has receipts pointing at you, not them.

## Why it protects against theft

- **Courts accept timestamped digital evidence.** Git log + Bitcoin OTS anchor = legally-citable priority date.
- **Public visibility creates independent witnesses.** Anyone on the internet can see and archive the repo. That's dozens of 3rd-party copies, not just your server.
- **Immutable history** — unlike Google Docs or Notion, a git repo's history can't be silently edited. Every change is tracked and verifiable.

## How entries work

- Written as Markdown in `entries/YYYY-MM-DD-slug.md`
- Rendered to HTML in `public/` by `scripts/build.py`
- Deployed via GitHub Pages on push to `main`
- Each entry gets an OpenTimestamps `.ots` file anchoring its hash to Bitcoin

## Pulling source material from Telegram

A lot of the raw thinking that belongs in this log starts as Telegram messages.
`scripts/telegram_fetch.py` reads them back out of your own account via
[Telethon](https://docs.telethon.dev) so they can be edited into an entry.

```bash
pip install telethon
export TG_API_ID=123456          # https://my.telegram.org -> API development tools
export TG_API_HASH=0123abc...
python3 scripts/telegram_fetch.py --login          # once — Telegram sends a login code
```

Then:

```bash
python3 scripts/telegram_fetch.py --list-chats                     # find the exact chat
python3 scripts/telegram_fetch.py --peer Casey --search cleanup    # search one chat
python3 scripts/telegram_fetch.py --peer Casey --from-me --since 2026-06-01
python3 scripts/telegram_fetch.py --peer Casey --json --out casey.json
```

**Run it locally, not in CI.** Telegram's MTProto handshake does not complete
from the sandboxed build/agent containers, the first login is interactive, and
the session has to survive between runs — none of which an ephemeral container
gives you.

**The session file is a credential.** Anyone holding it can read the account.
It is written to `.telegram/`, which `.gitignore` excludes along with `*.session`.
Never commit it.

If `pip install telethon` fails building the `pyaes` wheel, install with
`pip install --no-build-isolation telethon`.

## License

**All Rights Reserved, Josh Cullen Santos, 2026-.**

The purpose of this log is to establish authorship. Content is published for visibility and proof-of-priority — NOT for reuse. Permission to reproduce any work here must be obtained in writing.

## Integrity verification

- Latest commit SHA + signature: see `git log -1`
- Verify OpenTimestamps for any entry: `ots verify entries/<file>.md.ots`
- Independent backup: any public GitHub clone serves as an off-site witness

---

_Signal Log is part of [Signal Network](https://github.com/) — Josh's private AI infrastructure._
