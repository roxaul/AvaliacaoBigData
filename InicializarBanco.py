"""
=============================================================================
 Top 1000 Steam Games (2024-2026) — Dataset Builder
 Author : Auto-generated scraper by Waddah Ali
 Output : steam_games_2026.csv
=============================================================================
 This script collects metadata for the top ~1000 Steam games using three
 complementary sources:
   1. Steam Search page  → discover AppIDs (top sellers)
   2. Steam appdetails API → official metadata
   3. Steam store page    → user-defined tags & Steam Deck status
   4. SteamSpy API        → 24-hour peak / concurrent players
 Then it cleans, merges, and exports everything to a Kaggle-ready CSV.
=============================================================================
"""

import time
import re
import json
import random
import warnings
import logging
from datetime import datetime

import requests
from bs4 import BeautifulSoup
import pandas as pd

# ---------------------------------------------------------------------------
# Try importing fake_useragent; fall back to a static list if unavailable
# ---------------------------------------------------------------------------
try:
    from fake_useragent import UserAgent
    _ua = UserAgent()

    def _get_ua() -> str:
        return _ua.random
except Exception:
    _UA_LIST = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/605.1.15 "
        "(KHTML, like Gecko) Version/17.4 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edg/123.0.0.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) "
        "Gecko/20100101 Firefox/124.0",
    ]

    def _get_ua() -> str:
        return random.choice(_UA_LIST)

# Try importing tqdm for progress bars; fall back silently
try:
    from tqdm import tqdm
except ImportError:
    def tqdm(iterable, **kwargs):
        total = kwargs.get("total", None)
        desc = kwargs.get("desc", "")
        for i, item in enumerate(iterable, 1):
            if total:
                print(f"\r{desc} {i}/{total}", end="", flush=True)
            yield item
        print()  # newline after progress

warnings.filterwarnings("ignore")

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("steam_scraper")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SLEEP_SECONDS = 1.5
TARGET_COUNT = 1000
SEARCH_PAGE_SIZE = 25  # Steam returns 25 results per search page
STEAM_SEARCH_URL = "https://store.steampowered.com/search/"
STEAM_API_URL = "https://store.steampowered.com/api/appdetails"
STEAMSPY_API_URL = "https://steamspy.com/api.php"
SESSION = requests.Session()

# Cookies to bypass Steam's age-check and mature-content gates
STEAM_COOKIES = {
    "birthtime": "568022401",       # indicates user is old enough
    "mature_content": "1",          # allows mature content
    "wants_mature_content": "1",
    "lastagecheckage": "1-0-1988",
    "Steam_Language": "english",
}


# ═══════════════════════════════════════════════════════════════════════════
#  PHASE 1 — Discovery: collect AppIDs from the Steam Search page
# ═══════════════════════════════════════════════════════════════════════════

def _make_headers() -> dict:
    """Return request headers with a rotated User-Agent."""
    return {
        "User-Agent": _get_ua(),
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }


def discover_appids(target: int = TARGET_COUNT) -> list[int]:
    """
    Scrape Steam's top-seller search results to collect *target* unique AppIDs.
    Returns a list of integer AppIDs.
    """
    appids: list[int] = []
    seen: set[int] = set()
    start = 0
    consecutive_empty = 0

    log.info("Phase 1 — Discovering AppIDs from Steam Search (target=%d) …", target)

    while len(appids) < target:
        params = {
            "filter": "topsellers",
            "category1": "998",          # Games only
            "cc": "us",
            "l": "english",
            "start": start,
            "count": 100,                # request more per page
            "ndl": 1,
            "snr": "1_7_7_globaltopsellers_702",
        }
        try:
            resp = SESSION.get(
                SEARCH_URL := STEAM_SEARCH_URL,
                params=params,
                headers=_make_headers(),
                cookies=STEAM_COOKIES,
                timeout=30,
            )
            resp.raise_for_status()
        except requests.RequestException as exc:
            log.warning("Search request failed (start=%d): %s", start, exc)
            consecutive_empty += 1
            if consecutive_empty > 5:
                log.error("Too many consecutive failures — stopping discovery.")
                break
            time.sleep(SLEEP_SECONDS * 2)
            continue

        soup = BeautifulSoup(resp.text, "lxml")
        rows = soup.select("a[data-ds-appid]")

        if not rows:
            # Also try the JSON-style infinite-scroll response
            # Steam sometimes returns JSON with an "results_html" key
            try:
                data = resp.json()
                html_fragment = data.get("results_html", "")
                soup2 = BeautifulSoup(html_fragment, "lxml")
                rows = soup2.select("a[data-ds-appid]")
            except Exception:
                pass

        if not rows:
            consecutive_empty += 1
            if consecutive_empty > 5:
                log.warning("No more results found — stopping at %d AppIDs.", len(appids))
                break
            start += SEARCH_PAGE_SIZE
            time.sleep(SLEEP_SECONDS)
            continue

        consecutive_empty = 0
        for row in rows:
            raw = row.get("data-ds-appid", "")
            # Sometimes the attribute contains comma-separated IDs (bundles)
            for part in raw.split(","):
                part = part.strip()
                if part.isdigit():
                    aid = int(part)
                    if aid not in seen:
                        seen.add(aid)
                        appids.append(aid)
                        if len(appids) >= target:
                            break
            if len(appids) >= target:
                break

        log.info("  … collected %d / %d AppIDs so far", len(appids), target)
        start += len(rows)
        time.sleep(SLEEP_SECONDS)

    log.info("Phase 1 complete — %d AppIDs collected.", len(appids))
    return appids


# ═══════════════════════════════════════════════════════════════════════════
#  PHASE 2 — Metadata via the Steam appdetails API
# ═══════════════════════════════════════════════════════════════════════════

def _parse_date(raw: str) -> str:
    """Try to normalise a date string to YYYY-MM-DD; return as-is on failure."""
    for fmt in ("%b %d, %Y", "%d %b, %Y", "%B %d, %Y", "%d %B, %Y", "%Y-%m-%d", "%Y"):
        try:
            return datetime.strptime(raw.strip(), fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return raw.strip()


def fetch_app_metadata(appid: int) -> dict | None:
    """
    Call the Steam appdetails API for *appid* and return a flat dict with the
    fields we care about, or None on failure.
    """
    params = {"appids": appid, "cc": "us", "l": "english"}
    try:
        resp = SESSION.get(
            STEAM_API_URL,
            params=params,
            headers=_make_headers(),
            cookies=STEAM_COOKIES,
            timeout=30,
        )
        resp.raise_for_status()
        body = resp.json()
    except Exception as exc:
        log.warning("appdetails failed for %d: %s", appid, exc)
        return None

    key = str(appid)
    if key not in body or not body[key].get("success"):
        return None

    data = body[key]["data"]

    # --- Price -----------------------------------------------------------
    price_overview = data.get("price_overview", {})
    if data.get("is_free", False):
        price_usd = 0.0
        discount_pct = 0
    elif price_overview:
        price_usd = price_overview.get("final", 0) / 100.0  # cents → dollars
        discount_pct = price_overview.get("discount_percent", 0)
    else:
        price_usd = 0.0
        discount_pct = 0

    # --- Genres ----------------------------------------------------------
    genres = data.get("genres", [])
    primary_genre = genres[0]["description"] if genres else "Unknown"

    # --- Release date ----------------------------------------------------
    rd = data.get("release_date", {})
    release_str = rd.get("date", "")
    release_date = _parse_date(release_str) if release_str else ""

    # --- Reviews ---------------------------------------------------------
    # The API doesn't always expose review counts directly; we'll try the
    # recommendations field and augment later from scraping if needed.
    recs = data.get("recommendations", {})
    total_reviews = recs.get("total", 0)

    return {
        "AppID": appid,
        "Name": data.get("name", ""),
        "Release_Date": release_date,
        "Primary_Genre": primary_genre,
        "Price_USD": round(price_usd, 2),
        "Discount_Pct": int(discount_pct),
        "Total_Reviews": int(total_reviews),
    }


def fetch_all_metadata(appids: list[int]) -> list[dict]:
    """Fetch metadata for every AppID (Phase 2)."""
    log.info("Phase 2 — Fetching metadata for %d AppIDs …", len(appids))
    results = []
    for appid in tqdm(appids, desc="Metadata", total=len(appids)):
        meta = fetch_app_metadata(appid)
        if meta:
            results.append(meta)
        time.sleep(SLEEP_SECONDS)
    log.info("Phase 2 complete — got metadata for %d games.", len(results))
    return results


# ═══════════════════════════════════════════════════════════════════════════
#  PHASE 3 — Scraping store page for Tags, Reviews & Steam Deck status
# ═══════════════════════════════════════════════════════════════════════════

def scrape_store_page(appid: int) -> dict:
    """
    Scrape the public Steam store page for:
      • User-defined tags  (top 10)
      • Review score percentage
      • Steam Deck compatibility badge
    Returns a dict with those fields.
    """
    result = {
        "All_Tags": "",
        "Review_Score_Pct": 0,
        "Steam_Deck_Status": "Unknown",
    }

    url = f"https://store.steampowered.com/app/{appid}/"
    try:
        resp = SESSION.get(
            url,
            headers=_make_headers(),
            cookies=STEAM_COOKIES,
            timeout=30,
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        log.warning("Store page request failed for %d: %s", appid, exc)
        return result

    html = resp.text

    # --- Tags ----
    # Tags are embedded in a JS call: InitAppTagModal(...)
    tags_match = re.search(
        r'InitAppTagModal\(\s*\d+,\s*(\[.*?\])\s*,',
        html,
        re.DOTALL,
    )
    if tags_match:
        try:
            tag_list = json.loads(tags_match.group(1))
            # Each element: {"tagid":..., "name":"...", "count":...}
            top_tags = [t["name"] for t in tag_list[:10]]
            result["All_Tags"] = ";".join(top_tags)
        except (json.JSONDecodeError, KeyError):
            pass

    # Fallback: look for popular tags in the HTML
    if not result["All_Tags"]:
        soup = BeautifulSoup(html, "lxml")
        tag_links = soup.select("a.app_tag")
        if tag_links:
            top_tags = [t.get_text(strip=True) for t in tag_links[:10]]
            result["All_Tags"] = ";".join(top_tags)

    # --- Review score ---------------------------------------------------
    # Look for review summary tooltip: "XX% of the … reviews"
    review_match = re.search(r'(\d{1,3})%\s+of\s+the', html)
    if review_match:
        result["Review_Score_Pct"] = int(review_match.group(1))

    # --- Steam Deck compatibility ----------------------------------------
    soup = BeautifulSoup(html, "lxml") if "soup" not in dir() else soup # reuse if already made
    # The compatibility info appears in elements with specific class names
    deck_section = soup.select_one('[class*="deck_compat"]') or soup.select_one('[class*="DeckCompat"]')
    if deck_section:
        text = deck_section.get_text(strip=True).lower()
        if "verified" in text:
            result["Steam_Deck_Status"] = "Verified"
        elif "playable" in text:
            result["Steam_Deck_Status"] = "Playable"
        elif "unsupported" in text:
            result["Steam_Deck_Status"] = "Unsupported"

    # Fallback: search raw HTML for deck compatibility JSON/markers
    if result["Steam_Deck_Status"] == "Unknown":
        deck_cat_match = re.search(r'"resolved_category"\s*:\s*(\d)', html)
        if deck_cat_match:
            cat = int(deck_cat_match.group(1))
            result["Steam_Deck_Status"] = {
                1: "Unsupported",
                2: "Playable",
                3: "Verified",
            }.get(cat, "Unknown")

    return result


def scrape_all_store_pages(appids: list[int]) -> dict[int, dict]:
    """Scrape store pages for every AppID (Phase 3)."""
    log.info("Phase 3 — Scraping store pages for %d AppIDs …", len(appids))
    results = {}
    for appid in tqdm(appids, desc="Scraping", total=len(appids)):
        results[appid] = scrape_store_page(appid)
        time.sleep(SLEEP_SECONDS)
    log.info("Phase 3 complete.")
    return results


# ═══════════════════════════════════════════════════════════════════════════
#  PHASE 4 — SteamSpy (24-hour peak / concurrent players)
# ═══════════════════════════════════════════════════════════════════════════

def fetch_steamspy(appid: int) -> int:
    try:
        resp = SESSION.get(
            STEAMSPY_API_URL,
            params={"request": "appdetails", "appid": appid},
            headers=_make_headers(),
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        return int(data.get("ccu", 0))
    except Exception:
        return 0


def fetch_all_steamspy(appids: list[int]) -> dict[int, int]:
    log.info("Phase 4 — Fetching SteamSpy data for %d AppIDs …", len(appids))
    results = {}
    for appid in tqdm(appids, desc="SteamSpy", total=len(appids)):
        results[appid] = fetch_steamspy(appid)
        time.sleep(SLEEP_SECONDS)
    log.info("Phase 4 complete.")
    return results


# ═══════════════════════════════════════════════════════════════════════════
#  PHASE 5 — Merge, clean, and export
# ═══════════════════════════════════════════════════════════════════════════

def build_dataset(
    metadata: list[dict],
    scraped: dict[int, dict],
    steamspy: dict[int, int],
) -> pd.DataFrame:

    df = pd.DataFrame(metadata)

    # Merge scraped data
    df["All_Tags"] = df["AppID"].map(lambda x: scraped.get(x, {}).get("All_Tags", ""))
    df["Steam_Deck_Status"] = df["AppID"].map(
        lambda x: scraped.get(x, {}).get("Steam_Deck_Status", "Unknown")
    )

    # Use scraped review score if API review count is available
    df["Review_Score_Pct"] = df["AppID"].map(
        lambda x: scraped.get(x, {}).get("Review_Score_Pct", 0)
    )

    # SteamSpy concurrent users as 24h peak proxy
    df["24h_Peak_Players"] = df["AppID"].map(lambda x: steamspy.get(x, 0))

    # Boxleiter method: Estimated Owners ≈ Total Reviews × 30
    df["Estimated_Owners"] = df["Total_Reviews"] * 30

    # --- Cleaning -----
    # Drop rows with no name
    df = df.dropna(subset=["Name"])
    df = df[df["Name"].str.strip() != ""]

    # Fill missing / NaN prices with 0.00
    df["Price_USD"] = df["Price_USD"].fillna(0.0).round(2)

    # Ensure integer types (coerce NaN → 0)
    int_cols = [
        "AppID", "Discount_Pct", "Total_Reviews",
        "Review_Score_Pct", "Estimated_Owners", "24h_Peak_Players",
    ]
    for col in int_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

    # Fill remaining NaN strings
    df["All_Tags"] = df["All_Tags"].fillna("")
    df["Steam_Deck_Status"] = df["Steam_Deck_Status"].fillna("Unknown")
    df["Primary_Genre"] = df["Primary_Genre"].fillna("Unknown")
    df["Release_Date"] = df["Release_Date"].fillna("")

    # Reorder columns
    col_order = [
        "AppID", "Name", "Release_Date", "Primary_Genre", "All_Tags",
        "Price_USD", "Discount_Pct", "Review_Score_Pct", "Total_Reviews",
        "Steam_Deck_Status", "Estimated_Owners", "24h_Peak_Players",
    ]
    df = df[[c for c in col_order if c in df.columns]]

    # Remove duplicates
    df = df.drop_duplicates(subset="AppID").reset_index(drop=True)

    return df


def print_summary(df: pd.DataFrame) -> None:
    border = "=" * 60
    print(f"\n{border}")
    print("  DATASET SUMMARY — Top Steam Games (2024-2026)")
    print(border)
    print(f"  Total games collected     : {len(df):,}")
    print(f"  Mean price (USD)          : ${df['Price_USD'].mean():.2f}")
    print(f"  Median price (USD)        : ${df['Price_USD'].median():.2f}")
    print(f"  Free-to-play games        : {(df['Price_USD'] == 0).sum():,}")

    if "Primary_Genre" in df.columns:
        top_genre = df["Primary_Genre"].value_counts().idxmax()
        top_genre_count = df["Primary_Genre"].value_counts().max()
        print(f"  Most common genre         : {top_genre} ({top_genre_count:,} games)")

    if "Total_Reviews" in df.columns:
        print(f"  Mean total reviews        : {df['Total_Reviews'].mean():,.0f}")
        print(f"  Max total reviews         : {df['Total_Reviews'].max():,}")

    if "Estimated_Owners" in df.columns:
        print(f"  Mean estimated owners     : {df['Estimated_Owners'].mean():,.0f}")

    if "24h_Peak_Players" in df.columns:
        print(f"  Max 24h peak players      : {df['24h_Peak_Players'].max():,}")

    deck_counts = df["Steam_Deck_Status"].value_counts()
    print(f"  Steam Deck breakdown      :")
    for status, count in deck_counts.items():
        print(f"      {status:15s} : {count:,}")

    print(f"  Columns                   : {list(df.columns)}")
    print(border + "\n")


# ═══════════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main() -> None:
    start_time = time.time()

    # Phase 1 — Discover AppIDs
    appids = discover_appids(TARGET_COUNT)
    if not appids:
        log.error("No AppIDs discovered. Exiting.")
        return

    # Phase 2 — Fetch metadata from appdetails API
    metadata = fetch_all_metadata(appids)
    if not metadata:
        log.error("No metadata retrieved. Exiting.")
        return

    # Collect the AppIDs that have valid metadata
    valid_appids = [m["AppID"] for m in metadata]

    # Phase 3 — Scrape store pages (tags, reviews, Steam Deck)
    scraped = scrape_all_store_pages(valid_appids)

    # Phase 4 — SteamSpy (24h peak players)
    steamspy = fetch_all_steamspy(valid_appids)

    # Phase 5 — Build, clean, and export
    df = build_dataset(metadata, scraped, steamspy)

    output_path = "steam_games_2026.csv"
    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    log.info("Dataset saved to %s", output_path)

    print_summary(df)

    elapsed = time.time() - start_time
    log.info("Total elapsed time: %.1f minutes (%.0f seconds)", elapsed / 60, elapsed)


if __name__ == "__main__":
    main()