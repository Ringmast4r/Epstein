# Community Tools for Epstein Files

Since the DOJ removed bulk ZIP downloads on Feb 11, 2026, the community built alternatives.

---

## Tool 1: epstein-files-downloader (CLI)

- **Repo:** https://github.com/Surebob/epstein-files-downloader
- **Language:** Python
- **Purpose:** Automated archival of all 12 DOJ datasets

### Requirements
- Python 3.8+
- aria2c (multi-protocol download manager with torrent support)

### Install aria2c
```
Windows:  winget install aria2.aria2       (or scoop install aria2)
macOS:    brew install aria2
Linux:    sudo apt install aria2
```

### Commands
```bash
epstein-dl download --all                # Everything (~338 GB)
epstein-dl download --torrents           # Fastest - uses Archive.org magnet links
epstein-dl download --zips               # Direct ZIP files (datasets 1-8, 12 only)
epstein-dl download --scrape-dataset9    # Scrapes ~533K individual PDFs from DOJ
epstein-dl status                        # Check download progress
epstein-dl verify                        # Validate SHA256 checksums
```

### What It Covers
- Torrent downloads via aria2c for Archive.org mirrors
- Direct ZIP downloads for datasets 1-8 and 12
- PDF scraping for Dataset 9 (~533,786 individual files, DOJ never offered ZIP)
- Resume support (won't restart from scratch)
- Configurable parallel download count
- Progress tracking

---

## Tool 2: Epstein-Files Archive Index

- **Repo:** https://github.com/yung-megafone/Epstein-Files
- **Purpose:** Community archive index aggregating all download sources
- **Note:** Repo is marked VOLATILE - sync forks regularly

### What It Provides
- Official DOJ download links (where still alive)
- BitTorrent magnet links for each dataset
- Internet Archive mirror links
- SHA256/SHA1 hash verification data
- Consolidated single-archive download option

### Consolidated Archive
All 12 datasets combined into one 206.18 GB tar.zst file:
```
Magnet: magnet:?xt=urn:btih:f5cbe5026b1f86617c520d0a9cd610d6254cbe85
SHA256: 29acc987cd7fadfbbf94444ed165750b84d82c85af3703bab74308ea9e91e910
```

### Recommended Torrent Clients
- qBittorrent (open source)
- Transmission (open source)

### File Organization Inside Archive
```
./pdfs/      - Court documents, depositions, flight logs
./media/     - Images, video, audio evidence
./metadata/  - Extracted text, OCR data, file info
```

Each dataset has an accompanying checksums.csv for verification.

### Dataset Availability Status
| Dataset | ZIP (DOJ) | Torrent | Archive.org |
|---------|-----------|---------|-------------|
| 1-8     | Dead*     | No      | Yes         |
| 9       | Never had | Yes     | No          |
| 10      | Dead      | Yes     | No          |
| 11      | Dead      | Yes     | Yes         |
| 12      | Dead*     | No      | Yes         |

*ZIPs were removed ~Feb 11, 2026. Individual PDF links still work on DOJ site.

---

## Tool 3: Internet Archive Mirror

- **Collection:** "Epstein-Data-Sets-So-Far" on archive.org
- **Coverage:** Datasets 1-8, 11-12
- **Total files archived:** 1,366,140 PDFs
- **Access:** Standard HTTP download, no torrent client needed

---

## Tool 4: WikiEpstein

- **URL:** https://wikiepstein.com
- **Purpose:** Curated index linking to all official DOJ file listings
- **Goal:** Crowdsource metadata and cross-link documents, images, and files
- **Not a host** - points to official sources

---

## Tool 5: Google Pinpoint Database

- **URL:** https://journaliststudio.google.com/pinpoint/search?collection=c109fa8e7dcf42c1
- **Purpose:** Searchable database of the Epstein files with Google's AI search
- **Useful for:** Keyword searching across the entire document collection without downloading

---

## Tool 6: Epstein Archive (GitHub Pages)

- **URL:** https://epstein-docs.github.io/
- **Purpose:** Community-organized browsable archive

---

## Tool 7: FBI Vault

- **URL:** https://vault.fbi.gov/jeffrey-epstein
- **Purpose:** Separate FBI FOIA release of Epstein records (predates the EFTA release)
- **Note:** Different files from the DOJ EFTA datasets
