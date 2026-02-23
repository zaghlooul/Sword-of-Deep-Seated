"""
SwordSuite — Dork Engine
Built-in Google dork database + DuckDuckGo-based search runner.
"""
from __future__ import annotations

import html
import re
import time
import urllib.parse
from dataclasses import dataclass
from typing import Callable, Dict, Generator, List, Optional

import requests


# ---------------------------------------------------------------------------
# Dork database
# ---------------------------------------------------------------------------
DORK_DB: Dict[str, List[tuple[str, str]]] = {
    "SQL Injection": [
        ("MySQL error pages",       'intext:"mysql_fetch_array()" intext:"on line"'),
        ("SQL syntax errors",       'intext:"You have an error in your SQL syntax"'),
        ("MSSQL errors",            'intext:"Incorrect syntax near" intext:"Microsoft OLE DB"'),
        ("Oracle errors",           'intext:"ORA-01756" OR intext:"ORA-00933"'),
        ("PHP SQL errors",          'intext:"pg_exec(): Query failed" intext:"WARNING"'),
        ("Generic SQLi params",     'inurl:index.php?id= site:{target}'),
        ("Login bypass targets",    'inurl:login.php intext:"username" intext:"password" site:{target}'),
        ("View.php targets",        'inurl:view.php?id= site:{target}'),
        ("Item.php targets",        'inurl:item.php?id= site:{target}'),
        ("Product.php targets",     'inurl:product.php?id= site:{target}'),
    ],
    "Admin Panels": [
        ("Generic admin login",     'inurl:admin/login.php site:{target}'),
        ("Admin panel",             'inurl:/admin/index.php site:{target}'),
        ("phpMyAdmin",              'inurl:phpmyadmin site:{target}'),
        ("cPanel login",            'inurl:2083 OR inurl:2082 site:{target}'),
        ("WHM panel",               'inurl:2086 OR inurl:2087 site:{target}'),
        ("Plesk panel",             'inurl:8880 OR inurl:8443 site:{target}'),
        ("Joomla admin",            'inurl:administrator/index.php site:{target}'),
        ("WordPress admin",         'inurl:wp-admin/login.php site:{target}'),
        ("Drupal admin",            'inurl:user/login site:{target}'),
        ("CMS admin generic",       'intitle:"admin panel" OR intitle:"control panel" site:{target}'),
    ],
    "Sensitive Files": [
        ("Exposed .env files",      'inurl:.env site:{target}'),
        ("Exposed config files",    'inurl:config.php site:{target}'),
        ("Database config",         'inurl:db_config.php OR inurl:database.php site:{target}'),
        ("Backup files",            'inurl:.sql OR inurl:.bak OR inurl:.backup site:{target}'),
        ("Log files",               'inurl:access.log OR inurl:error.log site:{target}'),
        ("SSH keys",                'inurl:id_rsa site:{target}'),
        (".htpasswd exposed",       'inurl:.htpasswd site:{target}'),
        ("WordPress config",        'inurl:wp-config.php site:{target}'),
        ("Git folder exposed",      'inurl:.git/config site:{target}'),
        ("DS_Store files",          'inurl:.DS_Store site:{target}'),
    ],
    "Directory Listing": [
        ("Apache listing",          'intitle:"Index of" intext:"Apache" site:{target}'),
        ("Nginx listing",           'intitle:"Index of" intext:"nginx" site:{target}'),
        ("Generic index",           'intitle:"Index of /" site:{target}'),
        ("Uploads directory",       'intitle:"Index of" inurl:uploads site:{target}'),
        ("Backup directory",        'intitle:"Index of" inurl:backup site:{target}'),
        ("Images directory",        'intitle:"Index of" inurl:images site:{target}'),
    ],
    "Login Pages": [
        ("Generic login",           'intitle:"Login" OR intitle:"Sign In" site:{target}'),
        ("Default credentials hint",'intitle:"Login" intext:"default password" site:{target}'),
        ("Admin login",             'intitle:"Administrator Login" site:{target}'),
        ("VPN login",               'intitle:"SSL VPN" OR intitle:"VPN Login" site:{target}'),
        ("Webmail login",           'intitle:"Webmail" inurl:webmail site:{target}'),
    ],
    "Exposed Documents": [
        ("Excel files",             'filetype:xlsx OR filetype:xls site:{target}'),
        ("Word documents",          'filetype:docx OR filetype:doc site:{target}'),
        ("PDF files",               'filetype:pdf site:{target}'),
        ("CSV files",               'filetype:csv site:{target}'),
        ("Text files",              'filetype:txt site:{target}'),
        ("XML files",               'filetype:xml site:{target}'),
        ("JSON API",                'filetype:json site:{target}'),
    ],
    "Technology Fingerprinting": [
        ("PHP version disclosure",  'intext:"PHP Version" site:{target}'),
        ("Server header Apache",    'intitle:"Apache HTTP Server" site:{target}'),
        ("Powered by disclosure",   'intext:"Powered by" site:{target}'),
        ("Error page fingerprint",  'intitle:"500 Internal Server Error" site:{target}'),
        ("Swagger/API docs",        'inurl:swagger OR inurl:api-docs site:{target}'),
        ("Spring Boot actuator",    'inurl:actuator site:{target}'),
        ("GraphQL endpoint",        'inurl:graphql OR inurl:/gql site:{target}'),
        ("Jenkins CI",              'intitle:"Dashboard [Jenkins]" site:{target}'),
        ("Kibana dashboard",        'intitle:"Kibana" site:{target}'),
        ("Grafana dashboard",       'intitle:"Grafana" site:{target}'),
    ],
    "Camera & IoT": [
        ("IP cameras",              'inurl:viewerframe?mode=motion'),
        ("Axis cameras",            'intitle:"AXIS" inurl:view/index.shtml'),
        ("Webcam index",            'inurl:/mjpg/video.mjpg'),
        ("Netgear devices",         'intitle:"NETGEAR" inurl:start.htm'),
        ("Cisco router login",      'intitle:"Cisco Systems" inurl:login.html'),
        ("Printer management",      'intitle:"Printer Status" inurl:hp/device/info_configuration.htm'),
    ],
    "Custom": [
        ("Paste your dork here",    ''),
    ],
}


def dork_for_target(dork_template: str, target: str) -> str:
    """Replace {target} placeholder in a dork template."""
    return dork_template.replace("{target}", target) if target else dork_template.replace(" site:{target}", "")


# ---------------------------------------------------------------------------
# DuckDuckGo HTML search (no API key, respects ToS for low volume)
# ---------------------------------------------------------------------------
@dataclass
class SearchResult:
    url:     str
    title:   str
    snippet: str
    dork:    str = ""


_DDG_URL = "https://html.duckduckgo.com/html/"
_HEADERS = {
    "User-Agent":
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}


def _parse_ddg_html(html_text: str) -> List[SearchResult]:
    """Minimal HTML parser — avoids BeautifulSoup dependency."""
    results: List[SearchResult] = []

    # Find result blocks
    blocks = re.split(r'class="result__body"', html_text)
    for block in blocks[1:]:
        try:
            # URL
            url_m  = re.search(r'class="result__url"[^>]*>([^<]+)<', block)
            # Title
            title_m = re.search(r'class="result__a"[^>]*>([^<]+)<', block)
            # Snippet
            snip_m  = re.search(r'class="result__snippet"[^>]*>(.*?)</a>', block, re.S)

            url     = html.unescape(url_m.group(1).strip())   if url_m   else ""
            title   = html.unescape(title_m.group(1).strip()) if title_m else ""
            snippet = html.unescape(re.sub(r"<[^>]+>", "", snip_m.group(1))).strip() if snip_m else ""

            if url and not url.startswith("http"):
                url = "https://" + url
            if url:
                results.append(SearchResult(url=url, title=title, snippet=snippet))
        except Exception:
            continue

    return results


def search_ddg(
    query: str,
    max_results: int  = 30,
    delay: float      = 1.5,
    progress_cb: Optional[Callable[[str], None]] = None,
) -> List[SearchResult]:
    """
    Perform a DuckDuckGo HTML search and return parsed results.
    `delay` prevents rate limiting.
    """
    results: List[SearchResult] = []
    try:
        if progress_cb:
            progress_cb(f"[DDG] Searching: {query[:80]}…")

        resp = requests.post(
            _DDG_URL,
            data={"q": query, "b": "", "kl": "us-en"},
            headers=_HEADERS,
            timeout=20,
        )
        resp.raise_for_status()
        found = _parse_ddg_html(resp.text)
        results.extend(found[:max_results])

        if progress_cb:
            progress_cb(f"[DDG] Found {len(found)} results.")
    except Exception as exc:
        if progress_cb:
            progress_cb(f"[DDG] Error: {exc}")
    finally:
        time.sleep(delay)

    return results


def build_google_url(query: str) -> str:
    """Build a Google search URL (opens in browser)."""
    return "https://www.google.com/search?q=" + urllib.parse.quote_plus(query)


def build_bing_url(query: str) -> str:
    return "https://www.bing.com/search?q=" + urllib.parse.quote_plus(query)
