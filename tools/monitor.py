#!/usr/bin/env python3
"""
Epstein Files Index Monitor

Tracks DOJ EFTA file releases across 12 datasets.
- Seed mode (--seed): Builds initial manifests from community GitHub repos
- Monitor mode (default): Checks DOJ listing pages for changes

No PDFs are stored — only the manifest/index.
"""

import argparse
import csv
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote

import requests
from bs4 import BeautifulSoup

# --- Constants ---

REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFESTS_DIR = REPO_ROOT / "manifests"
CHANGELOG_PATH = REPO_ROOT / "CHANGELOG.md"
SUMMARY_PATH = MANIFESTS_DIR / "summary.json"
README_PATH = REPO_ROOT / "README.md"
BANNER_PATH = REPO_ROOT / "banner.svg"

DATA_DROP_DATE = datetime(2025, 12, 19, tzinfo=timezone.utc)  # First DOJ release

DOJ_BASE = "https://www.justice.gov"
DOJ_LISTING = f"{DOJ_BASE}/epstein/doj-disclosures"
DOJ_FILES = f"{DOJ_BASE}/epstein/files"
DOJ_COOKIE = "justiceGovAgeVerified=true"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Cookie": DOJ_COOKIE,
}

DATASETS = {
    1:  {"efta_start": 1,       "efta_end": 3158,    "pages": 63},
    2:  {"efta_start": 3159,    "efta_end": 3857,    "pages": 12},
    3:  {"efta_start": 3858,    "efta_end": 5704,    "pages": 37},
    4:  {"efta_start": 5705,    "efta_end": 8408,    "pages": 4},
    5:  {"efta_start": 8409,    "efta_end": 8584,    "pages": 3},
    6:  {"efta_start": 8585,    "efta_end": 9015,    "pages": 1},
    7:  {"efta_start": 9016,    "efta_end": 9675,    "pages": 1},
    8:  {"efta_start": 9676,    "efta_end": 39024,   "pages": 220},
    9:  {"efta_start": 39025,   "efta_end": 1262781, "pages": 1975},
    10: {"efta_start": 1262782, "efta_end": 2205654, "pages": 10028},
    11: {"efta_start": 2205655, "efta_end": 2730264, "pages": 2596},
    12: {"efta_start": 2730265, "efta_end": 2731498, "pages": 3},
}

# Community GitHub sources for seeding
SEED_SOURCES = [
    {
        "name": "Surebob/epstein-files-downloader",
        "type": "scraper_config",
        "url": "https://api.github.com/repos/Surebob/epstein-files-downloader/contents/epstein_downloader/config.py",
    },
    {
        "name": "yung-megafone/Epstein-Files",
        "type": "structure",
        "url": "https://api.github.com/repos/yung-megafone/Epstein-Files/contents/STRUCTURE.md",
    },
]


# --- Helpers ---

def get_session():
    s = requests.Session()
    s.headers.update(HEADERS)
    return s


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def today_str():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def efta_url(ds_num, efta_num):
    return f"{DOJ_FILES}/DataSet%20{ds_num}/EFTA{efta_num:08d}.pdf"


def listing_url(ds_num, page=0):
    return f"{DOJ_LISTING}/data-set-{ds_num}-files?page={page}"


def csv_path(ds_num):
    return MANIFESTS_DIR / f"dataset-{ds_num:02d}.csv"


def load_manifest(ds_num):
    """Load a dataset manifest CSV into a dict keyed by efta_number."""
    path = csv_path(ds_num)
    manifest = {}
    if path.exists():
        with open(path, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                manifest[row["efta_number"]] = row
    return manifest


def save_manifest(ds_num, manifest):
    """Save a manifest dict to CSV, sorted by efta_number."""
    path = csv_path(ds_num)
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = sorted(manifest.values(), key=lambda r: r["efta_number"])
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["efta_number", "filename", "url", "first_seen", "last_verified"])
        writer.writeheader()
        writer.writerows(rows)


def load_summary():
    if SUMMARY_PATH.exists():
        with open(SUMMARY_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"datasets": {}, "last_check": None, "last_change": None}


def save_summary(summary):
    SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(SUMMARY_PATH, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)


def append_changelog(entries):
    """Prepend new changelog entries under today's date."""
    if not entries:
        return
    date = today_str()
    new_section = f"## {date}\n"
    for entry in entries:
        new_section += f"- {entry}\n"
    new_section += "\n"

    existing = ""
    if CHANGELOG_PATH.exists():
        with open(CHANGELOG_PATH, "r", encoding="utf-8") as f:
            existing = f.read()

    header = "# Changelog\n\nAll detected changes to the Epstein Files index, newest first.\n\n"
    if existing.startswith("# Changelog"):
        body = existing.split("\n\n", 2)
        rest = body[2] if len(body) > 2 else ""
        content = header + new_section + rest
    else:
        content = header + new_section + existing

    with open(CHANGELOG_PATH, "w", encoding="utf-8") as f:
        f.write(content)


def update_readme():
    """Update the day counter in README.md and regenerate the SVG banner."""
    days = (datetime.now(timezone.utc) - DATA_DROP_DATE).days

    # Update README day count
    if README_PATH.exists():
        content = README_PATH.read_text(encoding="utf-8")
        content = re.sub(
            r"It has been \*\*\d+ days?\*\*",
            f"It has been **{days} days**",
            content,
        )
        README_PATH.write_text(content, encoding="utf-8")

    # Generate SVG banner
    generate_banner(days)


def generate_banner(days):
    """Generate a red SVG banner with the arrest counter."""
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="900" height="430" viewBox="0 0 900 430">
  <defs>
    <filter id="glow">
      <feGaussianBlur stdDeviation="2" result="blur"/>
      <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
  </defs>

  <!-- Background -->
  <rect width="900" height="430" rx="12" fill="#0d0d0d"/>
  <rect x="4" y="4" width="892" height="422" rx="10" fill="none" stroke="#cc0000" stroke-width="3"/>

  <!-- Red pulse bar top -->
  <rect x="4" y="4" width="892" height="6" rx="3" fill="#cc0000" opacity="0.9"/>

  <!-- EXPOSED line -->
  <text x="450" y="52" text-anchor="middle" font-family="Arial,Helvetica,sans-serif" font-size="16" font-weight="bold" fill="#cc0000" letter-spacing="6" filter="url(#glow)">&#x1F534; EXPOSED TRAFFICKERS, ENABLERS, AND CO-CONSPIRATORS &#x1F534;</text>

  <!-- Main arrest counter -->
  <text x="450" y="140" text-anchor="middle" font-family="Arial Black,Impact,Arial,sans-serif" font-size="100" font-weight="900" fill="#ff0000" filter="url(#glow)">0 ARRESTS</text>

  <!-- Days counter -->
  <text x="450" y="195" text-anchor="middle" font-family="Arial,Helvetica,sans-serif" font-size="22" fill="#ff6666">It has been</text>
  <text x="450" y="235" text-anchor="middle" font-family="Arial Black,Impact,Arial,sans-serif" font-size="48" font-weight="900" fill="#ffffff">{days} DAYS</text>
  <text x="450" y="265" text-anchor="middle" font-family="Arial,Helvetica,sans-serif" font-size="18" fill="#ff6666">since the DOJ released 931,000+ files exposing a global trafficking network</text>
  <text x="450" y="288" text-anchor="middle" font-family="Arial,Helvetica,sans-serif" font-size="18" fill="#ff6666">involving billionaires, politicians, and royalty.</text>

  <!-- Nobody line -->
  <text x="450" y="325" text-anchor="middle" font-family="Arial,Helvetica,sans-serif" font-size="20" font-weight="bold" fill="#ffffff">Nobody has been arrested. Nobody has been charged. Not one.</text>

  <!-- Divider -->
  <line x1="150" y1="348" x2="750" y2="348" stroke="#cc0000" stroke-width="1" opacity="0.6"/>

  <!-- Bottom message -->
  <text x="450" y="378" text-anchor="middle" font-family="Arial,Helvetica,sans-serif" font-size="14" fill="#999999" font-style="italic">This is not left vs right. This is not political.</text>
  <text x="450" y="400" text-anchor="middle" font-family="Arial,Helvetica,sans-serif" font-size="14" fill="#999999" font-style="italic">This is raw evil vs. basic human decency.</text>

  <!-- Red pulse bar bottom -->
  <rect x="4" y="420" width="892" height="6" rx="3" fill="#cc0000" opacity="0.9"/>
</svg>'''
    BANNER_PATH.write_text(svg, encoding="utf-8")


# --- Scraping DOJ ---

def extract_pdf_links(html, ds_num):
    """Extract EFTA PDF links from a DOJ listing page."""
    soup = BeautifulSoup(html, "html.parser")
    links = []
    pattern = re.compile(rf"/epstein/files/DataSet%20{ds_num}/EFTA(\d{{8}})\.pdf", re.IGNORECASE)
    for a in soup.find_all("a", href=True):
        m = pattern.search(a["href"])
        if m:
            efta_num = m.group(1)
            url = f"{DOJ_BASE}{a['href']}"
            links.append((efta_num, url))
    return links


def extract_total_pages(html):
    """Try to extract total page count from DOJ pagination."""
    soup = BeautifulSoup(html, "html.parser")
    last_link = soup.find("a", title="Go to last page")
    if last_link and last_link.get("href"):
        m = re.search(r"page=(\d+)", last_link["href"])
        if m:
            return int(m.group(1)) + 1  # pages are 0-indexed
    return None


def scrape_doj_page(session, ds_num, page=0):
    """Fetch a single DOJ listing page. Returns (links, total_pages) or (None, None) on failure."""
    url = listing_url(ds_num, page)
    try:
        resp = session.get(url, timeout=30)
        if resp.status_code == 403:
            print(f"  [BLOCKED] Page {page} of Dataset {ds_num} — Akamai 403")
            return None, None
        resp.raise_for_status()
        links = extract_pdf_links(resp.text, ds_num)
        total = extract_total_pages(resp.text)
        return links, total
    except requests.RequestException as e:
        print(f"  [ERROR] Dataset {ds_num} page {page}: {e}")
        return None, None


def check_file_exists(session, url):
    """HEAD request to check if a DOJ PDF still exists."""
    try:
        resp = session.head(url, timeout=15, allow_redirects=True)
        return resp.status_code == 200
    except requests.RequestException:
        return None  # unknown


def detect_new_datasets(session):
    """Check DOJ disclosures page for datasets beyond 12."""
    try:
        resp = session.get(DOJ_LISTING, timeout=30)
        if resp.status_code != 200:
            print(f"  [WARN] Could not fetch disclosures page: HTTP {resp.status_code}")
            return []
        soup = BeautifulSoup(resp.text, "html.parser")
        new_ds = []
        for a in soup.find_all("a", href=True):
            m = re.search(r"data-set-(\d+)-files", a["href"])
            if m:
                ds_num = int(m.group(1))
                if ds_num > 12:
                    new_ds.append(ds_num)
        return sorted(set(new_ds))
    except requests.RequestException as e:
        print(f"  [ERROR] Checking for new datasets: {e}")
        return []


# --- Seed Mode ---

def seed_from_doj(session):
    """
    Seed manifests by scraping page 1 and last page of each dataset from DOJ.
    This gives us a partial but verified file list.
    """
    print("\n=== Seeding from DOJ listing pages ===")
    ts = now_iso()
    changelog = []

    for ds_num, ds_info in DATASETS.items():
        print(f"\nDataset {ds_num}:")
        manifest = load_manifest(ds_num)
        new_count = 0

        # Page 1
        links, total_pages = scrape_doj_page(session, ds_num, page=0)
        if links:
            for efta_num, url in links:
                if efta_num not in manifest:
                    manifest[efta_num] = {
                        "efta_number": efta_num,
                        "filename": f"EFTA{efta_num}.pdf",
                        "url": url,
                        "first_seen": ts,
                        "last_verified": ts,
                    }
                    new_count += 1
                else:
                    manifest[efta_num]["last_verified"] = ts
            print(f"  Page 1: {len(links)} files found")
            if total_pages:
                print(f"  Total pages reported: {total_pages}")
        else:
            print("  Page 1: blocked or failed")

        # Last page (where newest files appear)
        last_page = (total_pages - 1) if total_pages else (ds_info["pages"] - 1)
        if last_page > 0:
            time.sleep(1)
            links, _ = scrape_doj_page(session, ds_num, page=last_page)
            if links:
                for efta_num, url in links:
                    if efta_num not in manifest:
                        manifest[efta_num] = {
                            "efta_number": efta_num,
                            "filename": f"EFTA{efta_num}.pdf",
                            "url": url,
                            "first_seen": ts,
                            "last_verified": ts,
                        }
                        new_count += 1
                    else:
                        manifest[efta_num]["last_verified"] = ts
                print(f"  Last page ({last_page}): {len(links)} files found")
            else:
                print(f"  Last page ({last_page}): blocked or failed")

        if new_count > 0:
            changelog.append(f"**Dataset {ds_num}**: {new_count} files indexed from DOJ listing pages")

        save_manifest(ds_num, manifest)
        print(f"  Total in manifest: {len(manifest)} files")
        time.sleep(1.5)

    return changelog


def seed_from_github(session):
    """
    Seed manifests from community GitHub repos.
    Uses the Surebob config for EFTA ranges and generates known URLs.
    """
    print("\n=== Seeding from community GitHub sources ===")
    ts = now_iso()
    changelog = []

    # Use the known EFTA ranges from Surebob's config to generate file URLs
    # We don't know exact files (gaps exist), but we can use DOJ page scraping
    # to fill in. For now, record what we find from the DOJ pages above.
    # The community repos primarily provide torrent/download links, not per-file manifests.

    # Try fetching the yung-megafone STRUCTURE.md for any file listings
    try:
        resp = session.get(
            "https://api.github.com/repos/yung-megafone/Epstein-Files/contents/STRUCTURE.md",
            headers={"Accept": "application/vnd.github.v3.raw"},
            timeout=15,
        )
        if resp.status_code == 200:
            print("  Fetched yung-megafone/Epstein-Files STRUCTURE.md")
            # Parse for any EFTA references
            efta_refs = re.findall(r"EFTA(\d{8})", resp.text)
            if efta_refs:
                print(f"  Found {len(efta_refs)} EFTA references")
    except requests.RequestException as e:
        print(f"  [WARN] Could not fetch yung-megafone STRUCTURE.md: {e}")

    # Check for DS09 specific data (largest dataset, most community effort)
    ds9_sources = [
        "https://api.github.com/repos/yung-megafone/Epstein-Files/contents/notes/DS09",
    ]
    for src_url in ds9_sources:
        try:
            resp = session.get(src_url, timeout=15)
            if resp.status_code == 200:
                items = resp.json()
                for item in items:
                    if item["name"].endswith(".txt") and "URL" in item["name"].upper():
                        print(f"  Found URL list: {item['name']}")
                        url_resp = session.get(item["download_url"], timeout=30)
                        if url_resp.status_code == 200:
                            urls = [line.strip() for line in url_resp.text.splitlines() if "EFTA" in line]
                            if urls:
                                manifest = load_manifest(9)
                                new_count = 0
                                for url in urls:
                                    m = re.search(r"EFTA(\d{8})", url)
                                    if m and m.group(1) not in manifest:
                                        efta_num = m.group(1)
                                        manifest[efta_num] = {
                                            "efta_number": efta_num,
                                            "filename": f"EFTA{efta_num}.pdf",
                                            "url": url.strip(),
                                            "first_seen": ts,
                                            "last_verified": "",
                                        }
                                        new_count += 1
                                if new_count > 0:
                                    save_manifest(9, manifest)
                                    changelog.append(f"**Dataset 9**: {new_count} files indexed from community URL list ({item['name']})")
                                    print(f"  Added {new_count} new files from {item['name']}")
        except requests.RequestException as e:
            print(f"  [WARN] Could not fetch {src_url}: {e}")

    # Check for checksums/disappeared files in DS09
    try:
        resp = session.get(
            "https://raw.githubusercontent.com/yung-megafone/Epstein-Files/main/notes/DS09/disappeared.csv",
            timeout=15,
        )
        if resp.status_code == 200:
            lines = resp.text.strip().splitlines()
            if len(lines) > 1:
                print(f"  Found {len(lines) - 1} disappeared files in DS09 tracking")
                changelog.append(f"**Dataset 9**: Tracking {len(lines) - 1} files reported as disappeared by community")
    except requests.RequestException:
        pass

    return changelog


def run_seed():
    """Full seed: pull from community + DOJ to build initial manifests."""
    print("=" * 60)
    print("EPSTEIN FILES INDEX MONITOR — SEED MODE")
    print("=" * 60)

    session = get_session()
    all_changelog = []

    all_changelog.extend(seed_from_github(session))
    all_changelog.extend(seed_from_doj(session))

    update_summary()
    update_readme()
    if all_changelog:
        all_changelog.insert(0, "**Initial seed** — built manifests from DOJ pages and community sources")
        append_changelog(all_changelog)

    print("\n" + "=" * 60)
    print("Seed complete. Summary:")
    summary = load_summary()
    for ds_key, ds_data in sorted(summary.get("datasets", {}).items(), key=lambda x: int(x[0])):
        print(f"  Dataset {ds_key}: {ds_data['file_count']} files")
    total = sum(d["file_count"] for d in summary.get("datasets", {}).values())
    print(f"  Total: {total} files indexed")


# --- Monitor Mode ---

def run_monitor():
    """Check DOJ for changes against stored manifests."""
    print("=" * 60)
    print("EPSTEIN FILES INDEX MONITOR — CHECK MODE")
    print("=" * 60)

    session = get_session()
    changelog = []
    ts = now_iso()
    any_changes = False

    # 1. Check for entirely new datasets
    print("\nChecking for new datasets...")
    new_datasets = detect_new_datasets(session)
    if new_datasets:
        for ds in new_datasets:
            changelog.append(f"**NEW DATASET {ds}** detected on DOJ disclosures page")
            any_changes = True
        print(f"  NEW DATASETS FOUND: {new_datasets}")
    else:
        print("  No new datasets (still 12)")

    # 2. Check page 1 and last page of each dataset
    for ds_num, ds_info in DATASETS.items():
        print(f"\nDataset {ds_num}:")
        manifest = load_manifest(ds_num)
        prev_count = len(manifest)
        new_files = []

        # Page 1
        links, total_pages = scrape_doj_page(session, ds_num, page=0)
        if links:
            for efta_num, url in links:
                if efta_num not in manifest:
                    manifest[efta_num] = {
                        "efta_number": efta_num,
                        "filename": f"EFTA{efta_num}.pdf",
                        "url": url,
                        "first_seen": ts,
                        "last_verified": ts,
                    }
                    new_files.append(efta_num)
                else:
                    manifest[efta_num]["last_verified"] = ts
            print(f"  Page 1: {len(links)} files ({len(new_files)} new)")

            # Check if total pages changed
            if total_pages:
                known_pages = ds_info["pages"]
                if total_pages != known_pages:
                    changelog.append(f"**Dataset {ds_num}**: Page count changed from {known_pages} to {total_pages}")
                    any_changes = True
                    print(f"  Page count changed: {known_pages} -> {total_pages}")
        else:
            print("  Page 1: blocked or failed")

        # Last page
        last_page = (total_pages - 1) if total_pages else (ds_info["pages"] - 1)
        if last_page > 0:
            time.sleep(1)
            links, _ = scrape_doj_page(session, ds_num, page=last_page)
            if links:
                new_on_last = 0
                for efta_num, url in links:
                    if efta_num not in manifest:
                        manifest[efta_num] = {
                            "efta_number": efta_num,
                            "filename": f"EFTA{efta_num}.pdf",
                            "url": url,
                            "first_seen": ts,
                            "last_verified": ts,
                        }
                        new_files.append(efta_num)
                        new_on_last += 1
                    else:
                        manifest[efta_num]["last_verified"] = ts
                print(f"  Last page ({last_page}): {len(links)} files ({new_on_last} new)")
            else:
                print(f"  Last page ({last_page}): blocked or failed")

        # 3. Spot-check random files for removals
        if len(manifest) > 10:
            import random
            sample_keys = random.sample(list(manifest.keys()), min(5, len(manifest)))
            removed = []
            for efta_num in sample_keys:
                url = manifest[efta_num]["url"]
                exists = check_file_exists(session, url)
                if exists is False:
                    removed.append(efta_num)
                    print(f"  [REMOVAL?] EFTA{efta_num}.pdf returned non-200")
                time.sleep(0.5)
            if removed:
                efta_list = ", ".join(f"EFTA{n}" for n in removed)
                changelog.append(f"**Dataset {ds_num}**: {len(removed)} files may have been removed ({efta_list})")
                any_changes = True

        if new_files:
            if len(new_files) <= 10:
                efta_range = ", ".join(f"EFTA{n}" for n in sorted(new_files))
            else:
                efta_range = f"EFTA{sorted(new_files)[0]}-EFTA{sorted(new_files)[-1]}"
            changelog.append(f"**Dataset {ds_num}**: {len(new_files)} new files detected ({efta_range})")
            any_changes = True

        save_manifest(ds_num, manifest)
        curr_count = len(manifest)
        if curr_count != prev_count:
            print(f"  Manifest: {prev_count} -> {curr_count} files")
        else:
            print(f"  Manifest: {curr_count} files (no changes)")

        time.sleep(1.5)

    update_summary()
    update_readme()
    if changelog:
        append_changelog(changelog)
        print("\nChanges detected — changelog updated.")
    else:
        print("\nNo changes detected.")

    return any_changes


# --- Summary ---

def update_summary():
    """Rebuild summary.json from manifest CSVs."""
    summary = load_summary()
    ts = now_iso()
    summary["last_check"] = ts

    for ds_num in DATASETS:
        manifest = load_manifest(ds_num)
        ds_key = str(ds_num)
        prev_count = summary.get("datasets", {}).get(ds_key, {}).get("file_count", 0)
        summary.setdefault("datasets", {})[ds_key] = {
            "file_count": len(manifest),
            "last_check": ts,
            "last_change": ts if len(manifest) != prev_count else summary.get("datasets", {}).get(ds_key, {}).get("last_change", ts),
        }
        if len(manifest) != prev_count:
            summary["last_change"] = ts

    save_summary(summary)


# --- CLI ---

def main():
    parser = argparse.ArgumentParser(description="Epstein Files Index Monitor")
    parser.add_argument("--seed", action="store_true", help="Seed manifests from community sources + DOJ")
    args = parser.parse_args()

    MANIFESTS_DIR.mkdir(parents=True, exist_ok=True)

    if args.seed:
        run_seed()
    else:
        run_monitor()


if __name__ == "__main__":
    main()
