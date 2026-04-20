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

## License

**All Rights Reserved, Josh Cullen Santos, 2026-.**

The purpose of this log is to establish authorship. Content is published for visibility and proof-of-priority — NOT for reuse. Permission to reproduce any work here must be obtained in writing.

## Integrity verification

- Latest commit SHA + signature: see `git log -1`
- Verify OpenTimestamps for any entry: `ots verify entries/<file>.md.ots`
- Independent backup: any public GitHub clone serves as an off-site witness

---

_Signal Log is part of [Signal Network](https://github.com/) — Josh's private AI infrastructure._
