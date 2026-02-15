#!/usr/bin/env python3
"""
Import comprehensive URL list from niemasd/Epstein-Files into our manifests.
Reads url_list.txt (1.38M URLs) and builds per-dataset manifest CSVs.
"""

import csv
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFESTS_DIR = REPO_ROOT / "manifests"
URL_LIST = REPO_ROOT / "url_list.txt"
SUMMARY_TSV = REPO_ROOT / "summary.tsv"

DS_PATTERN = re.compile(r"DataSet%20(\d+)/EFTA(\d{8})\.pdf", re.IGNORECASE)
TS = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_existing_manifest(ds_num):
    path = MANIFESTS_DIR / f"dataset-{ds_num:02d}.csv"
    manifest = {}
    if path.exists():
        with open(path, "r", newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                manifest[row["efta_number"]] = row
    return manifest


def save_manifest(ds_num, manifest):
    path = MANIFESTS_DIR / f"dataset-{ds_num:02d}.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = sorted(manifest.values(), key=lambda r: r["efta_number"])
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["efta_number", "filename", "url", "first_seen", "last_verified"])
        writer.writeheader()
        writer.writerows(rows)


def load_sizes():
    """Load file sizes from summary.tsv if available."""
    sizes = {}
    if SUMMARY_TSV.exists():
        with open(SUMMARY_TSV, "r", encoding="utf-8") as f:
            next(f)  # skip header
            for line in f:
                parts = line.strip().split("\t")
                if len(parts) >= 2:
                    name = parts[0]
                    m = re.search(r"EFTA(\d{8})", name)
                    if m:
                        sizes[m.group(1)] = int(parts[1])
    return sizes


def main():
    if not URL_LIST.exists():
        print(f"ERROR: {URL_LIST} not found")
        print("Download it: curl -sL https://raw.githubusercontent.com/niemasd/Epstein-Files/main/url_list.txt.gz | gunzip > url_list.txt")
        sys.exit(1)

    print("Loading URL list...")
    datasets = defaultdict(dict)
    line_count = 0

    with open(URL_LIST, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            line_count += 1
            m = DS_PATTERN.search(line)
            if m:
                ds_num = int(m.group(1))
                efta_num = m.group(2)
                datasets[ds_num][efta_num] = line

    print(f"Parsed {line_count:,} lines")
    print()

    # Merge with existing manifests
    total_new = 0
    total_existing = 0
    for ds_num in sorted(datasets.keys()):
        existing = load_existing_manifest(ds_num)
        new_count = 0
        for efta_num, url in datasets[ds_num].items():
            if efta_num not in existing:
                existing[efta_num] = {
                    "efta_number": efta_num,
                    "filename": f"EFTA{efta_num}.pdf",
                    "url": url,
                    "first_seen": TS,
                    "last_verified": "",
                }
                new_count += 1
            else:
                # Update URL if it was broken
                if "justice.govjustice.gov" in existing[efta_num].get("url", ""):
                    existing[efta_num]["url"] = url
        save_manifest(ds_num, existing)
        total_new += new_count
        total_existing += len(existing)
        print(f"  DS{ds_num:>2}: {len(existing):>10,} total  ({new_count:,} new)")

    print()
    print(f"  Total: {total_existing:,} files indexed ({total_new:,} new)")


if __name__ == "__main__":
    main()
