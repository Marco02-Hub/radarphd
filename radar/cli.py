from __future__ import annotations

import argparse


def main() -> None:
    p = argparse.ArgumentParser(prog="radar", description="Radar PhD")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("run-once", help="monitoraggio + notifiche Telegram/email + export JSON")
    sub.add_parser("export", help="solo export JSON in docs/data/")
    args = p.parse_args()

    from . import db
    from .export import export
    con = db.connect()
    if args.cmd == "run-once":
        from .monitor import run_once
        from .notify import send_all
        send_all(run_once(con))
    export(con)


if __name__ == "__main__":
    main()
