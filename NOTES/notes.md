# Epstein Files: Research Notes

## The Bulk Download Problem

The DOJ is deliberately making it harder to access these files. Here's what happened:

### What They Did
- On **Jan 30, 2026** the DOJ released 3.5 million pages across 12 data sets
- Initially, Data Sets 1-8 and 11 had **"Download all files (zip)"** links
- Data Sets 9 and 10 were already individual-PDF-only from the start
- By **Feb 11, 2026**, the DOJ **removed all ZIP download links** from the Epstein Library
- Now EVERY file must be downloaded individually as a PDF - one at a time
- Wayback Machine captures prove the ZIP links existed just days before removal

### Why This Matters
- 3.5 million pages across ~1 million+ individual PDFs
- Without bulk download, independent verification is nearly impossible
- Researchers can't easily check if the release is complete or if files get quietly changed/removed
- Caroline Hendrie (Society of Professional Journalists): "When documents of extraordinary public interest are released, agencies should ensure they remain meaningfully accessible and verifiable."

### Source
- [Discrepancy Report: DOJ Drops Bulk Downloads](https://discrepancyreport.com/doj-drops-bulk-downloads-from-epstein-library/)

---

## Community Download Tools

See **[tools.md](tools.md)** for full documentation of 7 community tools.

Quick summary: The two main options are the [Python CLI downloader](https://github.com/Surebob/epstein-files-downloader) and the [community archive torrent](https://github.com/yung-megafone/Epstein-Files) (~360 GB total).

---

## DOJ Website Structure & Naming Convention

See **[doj-website-analysis.md](doj-website-analysis.md)** for the complete technical breakdown.

Quick summary:
- All files named `EFTA{8-digit number}.pdf`
- Direct URL: `https://www.justice.gov/epstein/files/DataSet%20{N}/EFTA{number}.pdf`
- 12 datasets, ~931,000 files, ~360+ GB total
- EFTA numbers are globally sequential but NOT contiguous (gaps exist)
- DOJ has Akamai bot protection and removed bulk downloads

---

## Key Names Surfaced in the Files

### Named by Rep. Khanna on the House Floor (Feb 10, 2026)
- **Leslie Wexner** - billionaire, appears to have been labeled an FBI co-conspirator in 2019
- 5 other unnamed individuals (Khanna read 6 total; Deputy AG Blanche disputed their relevance)

### Prominent Figures in Documents
- **Elon Musk** - email exchanges from 2012-2013 discussing visiting Epstein's island
- **Bill Gates** - communications with Epstein documented
- **Prince Andrew** - name appears hundreds of times including in private emails
- **Steve Bannon** - email correspondence released by House committee
- **Larry Summers** - email correspondence released
- **Reid Hoffman** - email correspondence released
- **Kathryn Ruemmler** (Goldman Sachs CLO) - one of three people Epstein called after 2019 arrest; resigned Feb 2026
- **Howard Lutnick** - named in CNN reporting on emails
- **Richard Branson** - named in CNN reporting on emails

### Note on Names
Being named in the documents does NOT equal guilt. Many names appear in flight logs, contact books, or casual correspondence. The redaction failures have also exposed names of people who were never meant to be public, including victims.

---

## Redaction Failures

- DOJ failed to properly redact victim names across many documents
- Faulty digital redaction techniques allowed public to recover blacked-out content by copy-pasting text from PDFs
- DOJ accidentally published **unredacted nude images** of young women/possible teenagers with faces visible
- Images were largely removed after NYT notified DOJ
- 200+ victims' attorneys called it "the single most egregious violation of victim privacy in one day in United States history"

---

## The Political Angle

- DOJ investigation being directed at Trump's political opponents (Clinton, Summers, Hoffman) at Trump's urging
- Deputy AG Blanche interviewed Maxwell personally
- Maxwell transferred to minimum-security after interview
- DOJ distributed "declassified" binders to far-right influencers before the public release
- Europe has seen more consequences (Prince Andrew stripped of titles) while U.S. reckoning is "muted" (per NPR)
- An Epstein email states Trump "knew about the girls" - released by House committee Nov 2025

---

## Official DOJ Access Points

- **Main Library:** https://www.justice.gov/epstein
- **DOJ Disclosures:** https://www.justice.gov/epstein/doj-disclosures
- **Court Records:** https://www.justice.gov/epstein/court-records

---

## Key Legislation

- **Epstein Files Transparency Act** (H.R. 4405 / Public Law 119-38)
- Introduced July 15, 2025 by Reps. Khanna (D) and Massie (R)
- Passed House 427-1, Senate unanimous, Nov 18, 2025
- Signed by Trump Nov 19, 2025
- Full text: https://www.congress.gov/bill/119th-congress/house-bill/4405/text
