from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Préparation de courbes de charge pour Autocalsol")
    subparsers = parser.add_subparsers(dest="command")
    convert = subparsers.add_parser("convert", help="Convertir un XLSX/CSV")
    convert.add_argument("input")
    convert.add_argument("-o", "--output", required=True)
    duplicates = subparsers.add_parser("duplicates", help="Rechercher des doublons")
    duplicates.add_argument("files", nargs="+")
    duplicates.add_argument("-c", "--column")
    duplicates.add_argument("-o", "--output", required=True)
    return parser


def main() -> int:
    parser = _parser()
    args = parser.parse_args()
    if args.command == "convert":
        from autocalsol_tools.converter import convert_to_autocalsol

        results = convert_to_autocalsol(args.input, args.output, progress=print)
        for result in results:
            print(f"{result.path} : {result.row_count} lignes")
        return 0
    if args.command == "duplicates":
        from autocalsol_tools.duplicates import export_duplicates, find_duplicates

        results = find_duplicates(args.files, selected_column=args.column)
        path = export_duplicates(results, args.output)
        print(f"{len(results)} occurrence(s) exportée(s) vers {path}")
        return 0
    from autocalsol_tools.gui import run_gui

    return run_gui()


if __name__ == "__main__":
    raise SystemExit(main())

