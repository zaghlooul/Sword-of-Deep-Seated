# ⚔ SwordSuite

**Unified Reconnaissance & Exploitation Framework**

A professional desktop GUI that combines three industry-standard security tools into a single, cohesive workflow:

| Tool | Role |
|------|------|
| **Dork's Eye** | Discover exposed assets using Google dork queries |
| **Katana** | Deep-crawl targets to map endpoints, forms, and JS |
| **SQLMap** | Automated SQL injection detection and exploitation |

---

## Screenshots

SwordSuite uses a dark, professional UI with a sidebar for navigation and panel-specific toolbars.

---

## Features

### Dork's Eye Panel
- 70+ built-in dorks across 8 categories (SQL Injection, Admin Panels, Sensitive Files, Directory Listings, Login Pages, Exposed Docs, Tech Fingerprinting, Camera/IoT)
- DuckDuckGo auto-search (no API key required) + Google / Bing browser launch
- Results table with URL, title, snippet, dork source
- One-click "Send to Katana" or "Send to SQLMap"
- Export results to TXT or JSON

### Katana Panel
- Full control over all major katana flags: depth, concurrency, rate limit, JS crawling, headless mode, form extraction
- HTTP options: custom headers, cookies, proxy
- Output filters by endpoint type (endpoint, form, JS, file)
- Real-time terminal output with ANSI colour support
- One-click "Send to SQLMap"

### SQLMap Panel
- Complete parameter control: level, risk, technique selection (Boolean/Error/Union/Stacked/Time/Inline)
- DBMS selection, proxy, Tor, tamper scripts
- Enumeration actions: --dbs, --tables, --columns, --dump
- Advanced: OS shell, SQL shell, file read/write
- Findings table + database structure tree + dump viewer
- Live output with colour-coded severity

### Recon Chain
- Visual pipeline: Dork's Eye → Katana → SQLMap
- Configure all three steps and run with one click
- Real-time step status indicators
- Passes results automatically between stages

### Sessions
- Save and load scan sessions (JSON)
- Export to plain text
- Session statistics at a glance

---

## Requirements

- Python 3.10+
- PyQt6
- requests

External tools (optional but required for full functionality):

- **dorks-eye** — `pip install dorks-eye`
- **katana** — `go install github.com/projectdiscovery/katana/cmd/katana@latest`
- **sqlmap** — `apt install sqlmap` or `pip install sqlmap`

---

## Installation

```bash
git clone <repo>
cd Sword-of-Deep-Seated
bash install.sh
```

Or manually:

```bash
pip install -r requirements.txt
python main.py
```

---

## Keyboard Shortcuts

| Shortcut | Panel |
|----------|-------|
| Ctrl+1 | Dashboard |
| Ctrl+2 | Dork's Eye |
| Ctrl+3 | Katana |
| Ctrl+4 | SQLMap |
| Ctrl+5 | Recon Chain |
| Ctrl+6 | Sessions |

---

## Legal Notice

This tool is intended for **authorised security testing only**. Always obtain explicit written permission before testing any system you do not own. The authors accept no liability for misuse.
