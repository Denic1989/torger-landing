#!/usr/bin/env python3
"""
Torger landing counters updater.

Reads real counts from the bot DB, rewrites index.html, commits and pushes
to GitHub Pages (torgerbot.ru).

Usage:
  python3 /root/torger-landing/update_counters.py [--dry-run]

DB path: configurable via TORGER_DB env var (default /root/deploy/torger/data/torger_bot.db)
"""

import os
import re
import sqlite3
import subprocess
import sys

REPO = "/root/torger-landing"
INDEX = os.path.join(REPO, "index.html")
DB = os.environ.get("TORGER_DB", "/root/deploy/torger/data/torger_bot.db")


def get_counts(db_path: str):
    """Реальные счётчики из БД бота."""
    if not os.path.exists(db_path):
        raise SystemExit(f"DB not found: {db_path}")
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        auctions = con.execute("SELECT COUNT(*) FROM auctions").fetchone()[0]
        users = con.execute(
            "SELECT COUNT(*) FROM users "
            "WHERE user_id > 0 OR (username NOT LIKE 'test_%' "
            "AND username NOT LIKE 'phone_%')"
        ).fetchone()[0]
    finally:
        con.close()
    return auctions, users


def update_index(path: str, auctions: int, users: int) -> bool:
    src = open(path, encoding="utf-8").read()

    # id="auctionCount">N< — число внутри тега с id
    new_src, n_auc = re.subn(r'(id="auctionCount">)\d+(<)', rf"\g<1>{auctions}\g<2>", src)
    new_src, n_usr = re.subn(r'(id="userCount">)\d+(<)', rf"\g<1>{users}\g<2>", new_src)

    if n_auc != 1 or n_usr != 1:
        raise SystemExit(f"Pattern mismatch: auctionCount hits={n_auc}, userCount hits={n_usr}")

    if new_src == src:
        return False  # уже актуально
    open(path, "w", encoding="utf-8").write(new_src)
    return True


def git_push(changed: bool):
    if not changed:
        print("No changes — counters already up to date.")
        return
    subprocess.run(["git", "-C", REPO, "add", "index.html"], check=True)
    subprocess.run(["git", "-C", REPO, "commit", "-m",
                    "Update counters: {} auctions, {} users".format(*get_counts(DB))],
                   check=True, capture_output=True)
    subprocess.run(["git", "-C", REPO, "push", "origin", "main"], check=True, capture_output=True)
    print("Pushed to origin/main.")


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    a, u = get_counts(DB)
    print(f"Counts: auctions={a}, users={u}")
    changed = update_index(INDEX, a, u)
    if dry:
        print("DRY-RUN: would push" if changed else "DRY-RUN: nothing to do")
    else:
        git_push(changed)