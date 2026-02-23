# ⚔ SwordSuite

**Unified Reconnaissance & Exploitation Framework**

A professional desktop GUI that chains three industry-standard penetration testing tools into a single, cohesive workflow — from initial discovery all the way through to SQL injection exploitation.

```
Dork's Eye  →  Katana  →  SQLMap
  Discover      Map        Exploit
```

---

## Overview

Running a full recon-to-exploitation chain typically means juggling three terminal windows, copy-pasting URLs between tools, and remembering dozens of flags. SwordSuite replaces that with a single dark-themed desktop application where:

- Results flow automatically from one tool to the next
- Every flag is exposed through a well-labelled form — no docs required
- Live output is colour-coded and readable in real time
- The Recon Chain panel runs the entire pipeline with one click

---

## Interface

The application uses a fixed left sidebar for navigation and a full-height content area for each tool panel. All panels share a common output terminal widget with ANSI colour support, auto-scroll, and copy-all.

```
┌──────────────┬─────────────────────────────────────────────────────┐
│  ⚔ SwordSuite│  Panel header                                       │
│──────────────│─────────────────────────────────────────────────────│
│  MAIN        │  ┌─── Config ──────────┐  ┌─── Results ───────────┐│
│  🏠 Dashboard│  │                     │  │                       ││
│              │  │  Forms / sliders    │  │  Table / tree view    ││
│  TOOLS       │  │  for tool flags     │  │                       ││
│  👁 Dork's Eye│  │                     │  │  Live terminal output ││
│  ⚔ Katana   │  │  ▶ Run   ■ Stop     │  │                       ││
│  💉 SQLMap   │  │                     │  │                       ││
│              │  └─────────────────────┘  └───────────────────────┘│
│  WORKFLOW    │                                                      │
│  ⛓ Chain    │                                                      │
│  💾 Sessions │                                                      │
│──────────────│                                                      │
│  ● dorks-eye │                                                      │
│  ● katana    │                                                      │
│  ● sqlmap    │                                                      │
└──────────────┴─────────────────────────────────────────────────────┘
```

---

## Features

### Dashboard

- Live tool-installation status for all three external tools, with exact binary paths and install instructions when missing
- Running totals across all saved sessions: dork results, endpoints found, SQL injections confirmed
- Quick-start buttons that navigate directly to a panel or start a new chain
- Recent session list with per-session stats

### Dork's Eye Panel

- **65+ built-in dorks** across 9 categories selectable from a checkbox tree:
  - SQL Injection (error pages, WordPress, MySQL/MSSQL/Oracle, injectable params)
  - Admin Panels (generic, phpMyAdmin, cPanel, Plesk, Joomla, WordPress, Drupal)
  - Sensitive Files (.env, config.php, db files, backups, SSH keys, .htpasswd, .git)
  - Directory Listing (Apache, Nginx, uploads, backup, images)
  - Login Pages (generic, default creds, VPN, webmail)
  - Exposed Documents (xlsx, docx, pdf, csv, txt, xml, json)
  - Technology Fingerprinting (PHP version, Swagger, Spring actuator, GraphQL, Jenkins, Kibana, Grafana)
  - Camera & IoT (IP cameras, Axis, Netgear, Cisco, printers)
  - Custom (paste your own dorks)
- **`{target}` templating** — enter a domain once in the top bar, all dorks substitute `site:{target}` automatically
- **Three search modes:**
  - DuckDuckGo auto-search (no API key, results parsed into the table automatically)
  - Google browser launch (opens each dork in your default browser)
  - Bing browser launch
- Results table showing URL, page title, snippet, and source dork
- Filter results by keyword, right-click context menu for individual actions
- One-click **Send to Katana** or **Send to SQLMap** — URLs appear pre-loaded in the target field
- Export all results to TXT or JSON

### Katana Panel

| Control | Flag | Description |
|---------|------|-------------|
| Depth | `-d` | How many link-hops deep to crawl (1–10) |
| Concurrency | `-c` | Parallel request count (1–50) |
| Rate Limit | `-rl` | Max requests per second |
| Timeout | — | Per-request timeout in seconds |
| JS Crawling | `-jc` | Parse and follow JavaScript-discovered links |
| Headless | `-headless` | Use a headless browser for JS-heavy apps |
| Form Extraction | `-form-extraction` | Record every HTML form found |
| Known Files | `-kf all` | Flag common sensitive filenames |
| Passive Mode | `-ps` | No active requests — passive only |
| Cookies | `-H Cookie:` | Pass session cookies |
| Custom Headers | `-H` | Additional request headers |
| Proxy | — | Route through Burp or MITM proxy |

- Discovered endpoints organised in a table with **type badges** (`endpoint` / `form` / `js` / `file`) and filterable by type or URL substring
- Live command preview updates as you adjust settings — you always see the exact `katana` command being built
- One-click **Send to SQLMap**, or export the full endpoint list

### SQLMap Panel

**Target options**
- URL, HTTP method (GET/POST/PUT/DELETE), POST body data, cookies, specific parameter to test, custom headers, proxy, Tor, per-request delay

**Detection tuning**

| Control | Flag | Range |
|---------|------|-------|
| Level | `--level` | 1 (fast) – 5 (thorough) |
| Risk | `--risk` | 1 (safe) – 3 (aggressive) |
| Techniques | `--technique` | Boolean / Error / Union / Stacked / Time-based / Inline |
| DBMS | `--dbms` | Auto or any of 11 specific databases |
| Tamper | `--tamper` | 14 pre-listed scripts + free-text entry |
| Payload prefix/suffix | `--prefix` / `--suffix` | WAF evasion |

**Enumeration actions**
- `--dbs` · `--tables` · `--columns` · `--dump` · `--current-db` · `--current-user` · `--is-dba`
- Target a specific database (`-D`) and table (`-T`) for focused dumps

**Advanced**
- OS shell (`--os-shell`), SQL shell (`--sql-shell`), file read/write

**Results**
- **Findings table** — confirmed injection parameters surface immediately without scrolling output
- **Database tree** — discovered databases and tables populate a tree view in real time
- **Dump viewer** — tabular dump output collected in a dedicated tab
- Live output tab with colour-coded severity (`[INFO]` cyan, `[WARNING]` orange, injection confirmations green)
- Live command preview

### Recon Chain

A visual three-step pipeline that runs all tools in sequence and pipes results between them automatically.

```
  ① Dork's Eye          ② Katana              ③ SQLMap
  ┌──────────────┐      ┌──────────────┐      ┌──────────────┐
  │  Discover    │  →   │  Map         │  →   │  Exploit     │
  │  65 dorks    │      │  endpoints   │      │  SQLi test   │
  │              │      │              │      │              │
  │  ○ IDLE      │      │  ○ IDLE      │      │  ○ IDLE      │
  └──────────────┘      └──────────────┘      └──────────────┘
```

Each card shows a live status indicator: `○ Idle` → `◉ Running` → `● Done` / `✕ Error`.

- Toggle any step on/off independently
- Per-step configuration (dork categories, crawl depth, SQLMap level/risk) without leaving the panel
- Parameterised URLs discovered by Katana are passed directly to SQLMap — only URLs containing `?` are tested
- Full unified log stream in the terminal below

### Sessions

- All scan data (dork results, endpoints, injections) serialised to `~/.swordsuite/sessions/` as JSON
- Browse sessions in a sortable table with per-session statistics
- Double-click to load; export individual sessions to TXT or JSON; bulk delete
- Session detail card shows counts at a glance before opening

---

## Requirements

### Python dependencies

```
PyQt6 >= 6.5
requests >= 2.28
```

### External tools

The GUI wraps these tools via subprocess. Each tool is detected at startup — a green dot in the sidebar means it is ready.

| Tool | Install |
|------|---------|
| **dorks-eye** | `pip install dorks-eye` |
| **katana** | `go install github.com/projectdiscovery/katana/cmd/katana@latest` |
| | or `apt install katana` on Kali Linux |
| **sqlmap** | `apt install sqlmap` |
| | or `pip install sqlmap` |

> **Note:** If a tool is not installed, its panel still loads. The Dork's Eye panel falls back to browser-based searching, and the other panels display the install command in the terminal when you try to run.

---

## Installation

```bash
git clone <repo-url>
cd Sword-of-Deep-Seated
bash install.sh      # installs Python deps and prints tool install hints
python main.py
```

Manual install:

```bash
pip install PyQt6 requests
python main.py
```

---

## Keyboard Shortcuts

| Shortcut | Panel |
|----------|-------|
| `Ctrl+1` | Dashboard |
| `Ctrl+2` | Dork's Eye |
| `Ctrl+3` | Katana |
| `Ctrl+4` | SQLMap |
| `Ctrl+5` | Recon Chain |
| `Ctrl+6` | Sessions |

---

## Project Structure

```
Sword-of-Deep-Seated/
├── main.py                          Entry point
├── requirements.txt
├── install.sh
├── recon_suite/
│   ├── styles/
│   │   └── theme.py                 Dark QSS stylesheet + colour palette
│   ├── core/
│   │   ├── tool_runner.py           QProcess subprocess wrapper + command builders
│   │   ├── session.py               JSON session save / load / export
│   │   └── dork_engine.py           Built-in dork DB + DuckDuckGo HTML search
│   └── ui/
│       ├── main_window.py           Sidebar navigation, panel routing, shortcuts
│       ├── widgets/
│       │   ├── terminal.py          ANSI-aware scrolling output widget
│       │   └── form_widgets.py      LabeledSlider, MultiCheck, TagInput, RunStopBar…
│       └── panels/
│           ├── dashboard.py
│           ├── dorks_panel.py
│           ├── katana_panel.py
│           ├── sqlmap_panel.py
│           ├── chain_panel.py
│           └── sessions_panel.py
```

---

## Legal Notice

This tool is intended for **authorised security testing only**. Use it only against systems you own or have explicit written permission to test. Unauthorised use against third-party systems may violate computer fraud laws in your jurisdiction. The authors accept no liability for misuse.
