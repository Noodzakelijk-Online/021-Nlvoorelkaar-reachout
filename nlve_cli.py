"""Operator CLI for diagnostics, verification, recovery, and data portability."""

from __future__ import annotations

import argparse
import json
import os
import sys

from database.database_manager import DatabaseManager
from services.data_management import DataImporter
from services.diagnostics import ApplicationDoctor, SupportBundleBuilder, verify_local_critical_path
from services.outreach_ledger import OutreachLedger
from utils.backup_manager import BackupManager


def _print(payload) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True, default=str))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="nlve", description="NLvoorelkaar Reachout operator tools")
    subcommands = parser.add_subparsers(dest="command", required=True)
    subcommands.add_parser("doctor", help="Check local readiness without provider network calls")
    subcommands.add_parser("smoke", help="Run the isolated local critical-path smoke test")

    reconcile = subcommands.add_parser("reconcile-sends", help="Fail stale ambiguous send attempts")
    reconcile.add_argument("--minutes", type=int, default=15)

    import_parser = subcommands.add_parser("import-volunteers", help="Import reviewed CSV/JSON candidate data")
    import_parser.add_argument("path")

    export_parser = subcommands.add_parser("export-volunteers", help="Export active volunteer data")
    export_parser.add_argument("path")
    export_parser.add_argument("--format", choices=("json", "csv"), default="json")

    backup_parser = subcommands.add_parser("backup", help="Create and verify a local privacy-filtered backup")
    backup_parser.add_argument("--name", default=None)

    support = subcommands.add_parser("support-bundle", help="Create a privacy-safe diagnostic ZIP")
    support.add_argument("path")
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "doctor":
        result = ApplicationDoctor().run()
        _print(result)
        return 1 if result["status"] == "fail" else 0
    if args.command == "smoke":
        _print(verify_local_critical_path())
        return 0
    if args.command == "support-bundle":
        _print({"path": SupportBundleBuilder().create(args.path)})
        return 0

    database = DatabaseManager()
    if args.command == "reconcile-sends":
        count = database.reconcile_ambiguous_send_attempts(args.minutes, actor="cli_operator")
        _print({"reconciled": count, "next_action": "Review provider history before re-approving any failed draft."})
        return 0
    if args.command == "import-volunteers":
        _print(DataImporter(database.db_path).import_volunteers(os.path.abspath(args.path)))
        return 0
    if args.command == "export-volunteers":
        result = OutreachLedger(database).export_volunteer_data(
            os.path.abspath(args.path), args.format, actor="cli_operator"
        )
        _print(result)
        return 0
    if args.command == "backup":
        manager = BackupManager()
        path = manager.create_backup(args.name)
        verified = bool(path and manager.verify_backup(path))
        _print({"path": path, "verified": verified})
        return 0 if verified else 1
    return 2


if __name__ == "__main__":
    sys.exit(main())
