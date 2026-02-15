# DOJ Epstein Library: Website Structure & File Naming Analysis

## Base URLs

| Resource | URL |
|----------|-----|
| Main Library | https://www.justice.gov/epstein |
| DOJ Disclosures | https://www.justice.gov/epstein/doj-disclosures |
| Court Records | https://www.justice.gov/epstein/court-records |
| Full-Text Search | https://www.justice.gov/epstein/search |
| Dataset N listing | https://www.justice.gov/epstein/doj-disclosures/data-set-{N}-files |
| Dataset N page P | https://www.justice.gov/epstein/doj-disclosures/data-set-{N}-files?page={P} |

---

## File Naming Convention

### Pattern
```
EFTA{8-digit zero-padded number}.pdf
```

- **Prefix:** EFTA (Epstein Files Transparency Act)
- **Number:** 8 digits, zero-padded, globally sequential across all datasets
- **Extension:** Always .pdf (even for image-heavy content)

### Examples
```
EFTA00000001.pdf  (first file in Dataset 1)
EFTA00039025.pdf  (first file in Dataset 9)
EFTA02731498.pdf  (file in Dataset 12)
```

### Direct Download URL Pattern
```
https://www.justice.gov/epstein/files/DataSet%20{N}/EFTA{number}.pdf
```

Where `{N}` = dataset number (1-12), space encoded as `%20`

### Examples
```
https://www.justice.gov/epstein/files/DataSet%201/EFTA00000001.pdf
https://www.justice.gov/epstein/files/DataSet%209/EFTA00039025.pdf
https://www.justice.gov/epstein/files/DataSet%2010/EFTA01262782.pdf
```

---

## Dataset Map

### EFTA Number Ranges (first file observed on page 1)

| Dataset | First EFTA # | Pages | Est. Files | Size | Content |
|---------|-------------|-------|------------|------|---------|
| 1 | 00000001 | 63 | ~3,150 | 1.23 GB | FBI 302s, police reports (2005-2008) |
| 2 | 00003159 | 12 | ~600 | 630 MB | FBI 302s, police reports (2005-2008) |
| 3 | 00003858 | ? | ~49+ | 595 MB | FBI 302s, police reports (2005-2008) |
| 4 | 00005705 | 4 | ~200 | 351 MB | FBI 302s, police reports (2005-2008) |
| 5 | 00008409 | 3 | ~150 | 61.4 MB | FBI 302s, police reports (2005-2008) |
| 6 | 00008585 | 1 | 12 | 51.2 MB | FBI 302s, police reports (2005-2008) |
| 7 | 00009016 | 1 | 16 | 96.9 MB | FBI 302s, police reports (2005-2008) |
| 8 | 00009676 | 220 | ~11,000 | 10.67 GB | FBI 302s, police reports (2005-2008) |
| 9 | 00039025 | 1,975 | **533,786** | ~143 GB | Emails, private correspondence, DOJ internal docs re: 2008 NPA |
| 10 | 01262782 | 10,028 | **50,403** | 78.6 GB | 180,000 images + 2,000 videos from Epstein properties |
| 11 | 02205655 | 2,596 | **331,655** | 25.5 GB | Financial ledgers, flight manifests, property seizure records |
| 12 | 02730265 | 3 | ~150 | 114 MB | Late productions, supplemental items |

**Total: ~931,000+ files across ~360+ GB**

### Key Observations

1. **Numbers are NOT contiguous.** Dataset 3 shows clear gaps (3858, 3862, 3868, then jumps to 3919). You cannot simply enumerate EFTA00000001 through EFTA02731498 and expect every number to exist.

2. **Numbers are globally sequential** - Dataset 1 starts at 00000001, Dataset 2 picks up at 00003159, etc. Each dataset occupies its own range of the global EFTA namespace.

3. **Within a dataset, numbers can skip.** This means you need the actual file listing, not just the range.

4. **50 files per page** on the DOJ listing pages (with occasional variation of 45-51).

5. **Pages are zero-indexed** in the URL parameter (`?page=0` is page 1).

---

## Website Pagination Structure

Each data-set-N-files page shows:
- ~50 files per page
- Navigation: `1 2 3 4 5 6 7 8 9 ... Next Last`
- URL format: `?page={0-based index}`
- Pages beyond the first are being **403-blocked** by Akamai bot protection when accessed programmatically

### The DOJ's Anti-Scraping Measures
- Akamai bot detection on the main library page
- 403 errors on paginated requests from non-browser user agents
- Removed ZIP bulk download links (Feb 11, 2026)
- No API or sitemap provided
- No robots.txt allowance for automated crawling

---

## Content Categories by Dataset

### Datasets 1-8: Law Enforcement Records
- FBI "302" reports (interview summaries)
- Palm Beach Police Department reports (2005-2008)
- Early correspondence between Epstein legal team and federal prosecutors
- Evidence from Operation Leap Year (FBI investigation)

### Dataset 9: Communications & Internal DOJ
- Private email correspondence between Epstein and high-profile individuals
- Internal DOJ communications about the 2008 non-prosecution agreement
- This is the largest dataset by file count (533K+ files)
- **Never had a ZIP download** - always individual PDFs only

### Dataset 10: Media Evidence
- 180,000 images seized from Epstein's properties
- 2,000 videos seized from Epstein's properties
- Heavily redacted (black boxes over faces)
- DOJ accidentally published unredacted nude images initially

### Dataset 11: Financial & Travel
- Financial ledgers
- Flight manifests (to/from Epstein's island in USVI)
- Property seizure records
- Wire transfer records
- Bank statements

### Dataset 12: Supplemental
- Late productions requiring additional legal review
- ~150 documents

---

## Other DOJ Sections

### Court Records
- URL: https://www.justice.gov/epstein/court-records
- Separate from the EFTA disclosure datasets
- Contains court filings, indictments, plea agreements

### House Disclosures
- External link to https://oversight.house.gov
- House Oversight Committee released additional records including:
  - 95,000 photos
  - Email correspondence (Epstein with Prince Andrew, Bannon, Summers, Hoffman)

### EFTA First Level Review Protocol
- DOJ document explaining their redaction methodology
- URL: https://www.justice.gov/media/1426281/dl?inline

---

## Strategy for Enumerating All Files

### The Problem
- ~931,000 files across 12 datasets
- No bulk download, no API, no sitemap
- Bot protection blocks automated pagination
- EFTA numbers are non-contiguous (gaps exist)

### Approach 1: Scrape the Listing Pages (Best)
1. Use a real browser (Selenium/Playwright) to bypass Akamai bot detection
2. Iterate through each dataset's listing pages: `?page=0` through `?page={last}`
3. Extract all EFTA filenames from each page
4. Build a complete URL list
5. Download using aria2c with the URL list

**Pros:** Gets the exact files that exist, handles non-contiguous numbers
**Cons:** Slow due to pagination (14,900+ pages total), needs browser automation

### Approach 2: Use Community URL Lists (Fastest)
1. The epstein-files-downloader already scraped ~1 million URLs
2. The yung-megafone/Epstein-Files repo has checksums.csv files listing all files
3. Use these pre-built lists instead of re-scraping

**Pros:** Immediate, verified against DOJ, includes checksums
**Cons:** Depends on community accuracy, may not catch later DOJ additions/removals

### Approach 3: Brute Force Range Scan (Last Resort)
1. For each dataset, construct URLs from known start to estimated end EFTA number
2. Send HEAD requests to check which files exist (200 vs 404)
3. Build list from successful hits

**Pros:** Independent verification
**Cons:** Extremely slow, millions of requests needed, will get rate-limited/blocked

### Recommended Approach: Hybrid
1. **Start with community lists** from GitHub repos (get 99%+ immediately)
2. **Verify against DOJ** by spot-checking random files from the list
3. **Diff against DOJ listing pages** using browser automation on a sample of pages
4. **Use the Wayback Machine** to check what was available before ZIP removal
5. **Cross-reference** with WikiEpstein and Google Pinpoint for completeness

### For Part 2 (Unredacting)
Once files are downloaded:
- Many redactions are just black boxes drawn over text in the PDF layer
- The text underneath often remains in the PDF as selectable/copy-pastable text
- Tools: `pdftotext`, `pypdf`, `pdfplumber` can extract underlying text
- Image-based redactions (where text was rasterized then blacked out) are harder
- OCR + image analysis may recover some content from partial redactions
