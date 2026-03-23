#!/usr/bin/env python3
"""
database/openfda_scraper.py

Improved scraper for openFDA + DailyMed + custom URLs.
- Use: python database/openfda_scraper.py --drugs "oxycodone,alprazolam"
- Or:  python database/openfda_scraper.py --csv examples/controlled_substances_sample.csv
- Provide openFDA API key with env var OPENFDA_API_KEY or --api-key argument.

Outputs:
  - merges/updates data/drug_database.json with structured entries
  - assigns sequential IDs for controlled substances: CS-0001, CS-0002, ...
  - each drug entry includes date_fetched and last_verified in ISO8601 UTC
"""
from __future__ import annotations
import argparse
import json
import logging
import os
import time
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

# Optional dependencies
try:
    import requests
    from bs4 import BeautifulSoup
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
except Exception:
    raise SystemExit("Install dependencies first: pip install requests beautifulsoup4")

# Configuration
DATA_PATH = Path("data/drug_database.json")
RATE_LIMIT_SECONDS = float(os.environ.get("SCRAPER_RATE_LIMIT", "0.6"))
REQUEST_TIMEOUT = 20
OPENFDA_BASE = "https://api.fda.gov/drug/label.json"
USER_AGENT = "MedicationTrackerScraper/1.0 (+https://github.com/AidanColvin/date-calculator)"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def requests_session(retries: int = 3, backoff: float = 0.5) -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": USER_AGENT, "Accept": "application/json"})
    retry = Retry(total=retries, backoff_factor=backoff,
                  status_forcelist=(429, 500, 502, 503, 504),
                  allowed_methods=frozenset(["GET", "POST"]))
    s.mount("https://", HTTPAdapter(max_retries=retry))
    s.mount("http://", HTTPAdapter(max_retries=retry))
    return s


def load_database(path: Path = DATA_PATH) -> Dict[str, Any]:
    if not path.exists():
        return {"metadata": {"database_version": "0.0.1", "last_updated": None, "total_drugs": 0, "data_sources": []},
                "drugs": {}, "aliases": {}, "drug_classes": {}}
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def save_database(db: Dict[str, Any], path: Path = DATA_PATH):
    if not path.parent.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(db, fh, indent=2, sort_keys=True, default=str)
    logging.info("Saved database to %s", str(path))


def normalize_key(name: str) -> str:
    return name.lower().strip().replace(" ", "_")


def next_cs_id(db: Dict[str, Any]) -> str:
    ids = []
    for entry in db.get("drugs", {}).values():
        i = entry.get("id")
        if isinstance(i, str) and i.startswith("CS-"):
            try:
                ids.append(int(i.split("-")[1]))
            except Exception:
                continue
    next_num = max(ids) + 1 if ids else 1
    return f"CS-{next_num:04d}"


def make_session_with_key(api_key: Optional[str]) -> requests.Session:
    s = requests_session()
    if api_key:
        s.params = {"api_key": api_key}
    return s


def fetch_openfda_label(session: requests.Session, drug_name: str, api_key: Optional[str]) -> Optional[Dict[str, Any]]:
    """
    Query openFDA for drug label information using generic name.
    Returns first result dict or None.
    """
    params = {"search": f'openfda.generic_name:"{drug_name}"', "limit": 1}
    if api_key:
        params["api_key"] = api_key
    logging.info("openFDA: searching for %s", drug_name)
    try:
        r = session.get(OPENFDA_BASE, params=params, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        j = r.json()
        results = j.get("results")
        if results:
            return results[0]
        logging.debug("openFDA no results for %s", drug_name)
        return None
    except requests.HTTPError as e:
        logging.warning("openFDA HTTP error for %s: %s", drug_name, e)
    except Exception as e:
        logging.warning("openFDA fetch error for %s: %s", drug_name, e)
    finally:
        time.sleep(RATE_LIMIT_SECONDS)
    return None


def fetch_dailymed_search(session: requests.Session, drug_name: str) -> Optional[Dict[str, Any]]:
    """
    Lightweight DailyMed search -> find first product page and collect some basic fields.
    This is best-effort and may break if DailyMed changes their UI.
    """
    search_url = "https://dailymed.nlm.nih.gov/dailymed/search.cfm"
    try:
        logging.info("DailyMed: searching for %s", drug_name)
        r = session.get(search_url, params={"query": drug_name}, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        link = soup.select_one("a[href*='drugInfo.cfm?setid=']")
        if not link:
            logging.debug("DailyMed search no link for %s", drug_name)
            return None
        href = link.get("href")
        if href.startswith("/"):
            href = "https://dailymed.nlm.nih.gov" + href
        # Fetch product page
        r2 = session.get(href, timeout=REQUEST_TIMEOUT)
        r2.raise_for_status()
        soup2 = BeautifulSoup(r2.text, "html.parser")
        title_el = soup2.select_one("h1") or soup2.select_one(".product-name")
        title = title_el.get_text(strip=True) if title_el else ""
        def find_text(label):
            el = soup2.find(lambda t: t.name in ["th", "strong"] and label.lower() in t.get_text(strip=True).lower())
            if el:
                td = el.find_next("td")
                if td:
                    return td.get_text(" ", strip=True)
            return None
        generic = find_text("Generic Name") or find_text("Active ingredient") or None
        brand = find_text("Brand Name") or title
        return {"url": href, "brand_name": brand, "generic_name": generic}
    except Exception as e:
        logging.debug("DailyMed fetch error for %s: %s", drug_name, e)
    finally:
        time.sleep(RATE_LIMIT_SECONDS)
    return None


def fetch_custom_url(session: requests.Session, url: str) -> Optional[str]:
    try:
        logging.info("Fetching custom URL: %s", url)
        r = session.get(url, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        return r.text
    except Exception as e:
        logging.warning("Failed to fetch custom URL %s: %s", url, e)
        return None
    finally:
        time.sleep(RATE_LIMIT_SECONDS)


def build_record_from_sources(drug_name: str, openfda: Optional[Dict[str, Any]], dailymed: Optional[Dict[str, Any]],
                              custom_urls: Optional[List[str]]) -> Dict[str, Any]:
    """
    Normalize and combine data from available sources into target schema.
    Fields included match README spec; missing fields will be empty or None.
    """
    record: Dict[str, Any] = {
        "sample": False,
        "id": None,
        "generic_names": [],
        "brand_names": [],
        "drug_class": [],
        "therapeutic_category": None,
        "controlled_substance": None,
        "dea_schedule": None,
        "mechanism_of_action": None,
        "indications": [],
        "contraindications": [],
        "major_interactions": [],
        "dosage_forms": [],
        "typical_dosing": {},
        "monitoring": [],
        "storage": "",
        "date_fetched": utc_now_iso(),
        "source_urls": [],
        "last_verified": utc_now_iso()
    }

    if openfda:
        openfda_meta = openfda.get("openfda", {}) or {}
        for g in openfda_meta.get("generic_name", []):
            if g and g not in record["generic_names"]:
                record["generic_names"].append(g)
        for b in openfda_meta.get("brand_name", []):
            if b and b not in record["brand_names"]:
                record["brand_names"].append(b)
        for df in openfda_meta.get("dosage_form", []):
            if df and df not in record["dosage_forms"]:
                record["dosage_forms"].append(df)
        for cls in openfda_meta.get("pharm_class_mdct", []) + openfda_meta.get("pharm_class_epc", []) + openfda_meta.get("pharm_class_pe", []):
            if cls and cls not in record["drug_class"]:
                record["drug_class"].append(cls)
        if openfda.get("indications_and_usage"):
            v = openfda.get("indications_and_usage")
            if isinstance(v, list):
                record["indications"].append(v[0][:500])
            else:
                record["indications"].append(str(v)[:500])
        record["source_urls"].append({"name": "openFDA (label)", "url": OPENFDA_BASE + f"?search=openfda.generic_name:%22{drug_name}%22"})

    if dailymed:
        if dailymed.get("generic_name") and dailymed["generic_name"] not in record["generic_names"]:
            record["generic_names"].append(dailymed["generic_name"])
        if dailymed.get("brand_name") and dailymed["brand_name"] not in record["brand_names"]:
            record["brand_names"].append(dailymed["brand_name"])
        record["source_urls"].append({"name": "DailyMed", "url": dailymed.get("url")})

    if custom_urls:
        for u in custom_urls:
            record["source_urls"].append({"name": "custom", "url": u})

    cs_keywords = {"opioid", "benzodiazepine", "stimulant", "morphine", "oxycodone", "hydrocodone", "fentanyl", "alprazolam", "methylphenidate", "amphetamine", "oxymorphone", "hydromorphone", "codeine"}
    text_blob = " ".join(record.get("generic_names", []) + record.get("brand_names", []) + record.get("drug_class", [])).lower()
    found_cs = any(kw in text_blob for kw in cs_keywords)
    record["controlled_substance"] = found_cs

    if openfda:
        joined = json.dumps(openfda).lower()
        if "schedule ii" in joined or "schedule 2" in joined:
            record["dea_schedule"] = "II"
            record["controlled_substance"] = True
        elif "schedule iii" in joined or "schedule 3" in joined:
            record["dea_schedule"] = "III"
            record["controlled_substance"] = True
        elif "schedule iv" in joined or "schedule 4" in joined:
            record["dea_schedule"] = "IV"
            record["controlled_substance"] = True
        elif "schedule v" in joined or "schedule 5" in joined:
            record["dea_schedule"] = "V"
            record["controlled_substance"] = True

    if not record["generic_names"]:
        record["generic_names"] = [drug_name]

    return record


def merge_entry(db: Dict[str, Any], store_key: str, entry: Dict[str, Any]) -> str:
    drugs = db.setdefault("drugs", {})
    aliases = db.setdefault("aliases", {})
    meta = db.setdefault("metadata", {"database_version": "0.0.1", "last_updated": None, "total_drugs": 0, "data_sources": []})

    if store_key in drugs:
        existing = drugs[store_key]
        for list_key in ("generic_names", "brand_names", "drug_class", "indications", "contraindications", "dosage_forms", "monitoring", "source_urls", "major_interactions"):
            existing_list = existing.get(list_key, []) or []
            new_list = entry.get(list_key, []) or []
            for item in new_list:
                if isinstance(item, dict) and list_key == "source_urls":
                    if not any(isinstance(e, dict) and e.get("url") == item.get("url") for e in existing_list):
                        existing_list.append(item)
                else:
                    if item and item not in existing_list:
                        existing_list.append(item)
            existing[list_key] = existing_list
        for scalar in ("therapeutic_category", "controlled_substance", "dea_schedule", "mechanism_of_action", "storage", "typical_dosing"):
            if existing.get(scalar) in (None, "", [], {}):
                existing[scalar] = entry.get(scalar)
        existing["last_verified"] = entry.get("last_verified", utc_now_iso())
        existing["date_fetched"] = existing.get("date_fetched") or entry.get("date_fetched")
        assigned = existing.get("id") or next_cs_id(db)
        existing["id"] = assigned
        drugs[store_key] = existing
    else:
        assigned = entry.get("id") or next_cs_id(db)
        entry["id"] = assigned
        drugs[store_key] = entry

    for b in entry.get("brand_names", []):
        if b:
            aliases[b.lower()] = store_key

    meta["last_updated"] = utc_now_iso()
    meta["total_drugs"] = len(drugs)
    ds = meta.setdefault("data_sources", [])
    for s in entry.get("source_urls", []):
        if s and s.get("name") and s.get("name") not in ds:
            ds.append(s.get("name"))
    db["metadata"] = meta
    return assigned


def parse_csv(path: Path) -> List[str]:
    if not path.exists():
        raise FileNotFoundError(f"{path} not found")
    with path.open("r", encoding="utf-8") as fh:
        lines = [line.strip() for line in fh if line.strip()]
    if "," in lines[0] and "generic" in lines[0].lower():
        items = []
        for line in lines[1:]:
            parts = [p.strip() for p in line.split(",")]
            if parts:
                items.append(parts[0])
        return items
    if len(lines) == 1 and "," in lines[0]:
        return [s.strip() for s in lines[0].split(",") if s.strip()]
    return lines


def run_scraper(drugs: List[str], csv_path: Optional[Path], api_key: Optional[str], extra_map: Dict[str, List[str]]):
    session = make_session_with_key(api_key)
    db = load_database()
    for drug in drugs:
        logging.info("=== Processing: %s ===", drug)
        try:
            openfda = fetch_openfda_label(session, drug, api_key)
            dailymed = fetch_dailymed_search(session, drug)
            extras = extra_map.get(drug, []) if extra_map else None
            if extras:
                for u in extras:
                    _ = fetch_custom_url(session, u)
            record = build_record_from_sources(drug, openfda, dailymed, extras)
            assigned = merge_entry(db, normalize_key(drug), record)
            logging.info("Assigned ID %s for %s (controlled_substance=%s)", assigned, drug, record.get("controlled_substance"))
        except Exception as e:
            logging.exception("Failed processing %s: %s", drug, e)
    save_database(db)


def parse_extra_args(extra_args: Optional[List[str]]) -> Dict[str, List[str]]:
    result: Dict[str, List[str]] = {}
    if not extra_args:
        return result
    for item in extra_args:
        if "|" in item:
            name, url = item.split("|", 1)
            result.setdefault(name.strip(), []).append(url.strip())
    return result


def main():
    ap = argparse.ArgumentParser(description="Scrape openFDA/DailyMed and populate data/drug_database.json (controlled substances starter)")
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--drugs", help="Comma-separated list of drug names (generic). Example: --drugs 'oxycodone,alprazolam'")
    group.add_argument("--csv", help="CSV file containing drug names (one per line or a list in one line)")
    ap.add_argument("--api-key", help="openFDA API key (optional). Alternatively set OPENFDA_API_KEY env var.")
    ap.add_argument("--extra-url", action="append", help="Add extra URL for a drug in format 'drug_name|https://...' (can repeat)")
    args = ap.parse_args()

    api_key = args.api_key or os.environ.get("OPENFDA_API_KEY")
    drugs = []
    if args.drugs:
        drugs = [d.strip() for d in args.drugs.split(",") if d.strip()]
    else:
        drugs = parse_csv(Path(args.csv))

    extra_map = parse_extra_args(args.extra_url)
    run_scraper(drugs, Path(args.csv) if args.csv else None, api_key, extra_map)


if __name__ == "__main__":
    main()