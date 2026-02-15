#!/usr/bin/env python3
"""
Fetch all flight data from EpsteinExposed.com API and save as JSON.
Also fetches person data for cross-referencing.
"""

import json
import time
import sys
from pathlib import Path

import requests

API_BASE = "https://epsteinexposed.com/api/v1"
OUT_DIR = Path(__file__).resolve().parent.parent / "data"


def fetch_all_flights():
    print("Fetching flights...")
    all_flights = []
    page = 1
    while True:
        resp = requests.get(f"{API_BASE}/flights", params={"per_page": 100, "page": page}, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        flights = data["data"]
        if not flights:
            break
        all_flights.extend(flights)
        total = data["meta"]["total"]
        print(f"  Page {page}: {len(flights)} flights (total so far: {len(all_flights)}/{total})")
        if len(all_flights) >= total:
            break
        page += 1
        time.sleep(0.5)
    return all_flights


def fetch_all_persons():
    print("Fetching persons...")
    all_persons = []
    page = 1
    while True:
        resp = requests.get(f"{API_BASE}/persons", params={"per_page": 100, "page": page}, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        persons = data["data"]
        if not persons:
            break
        all_persons.extend(persons)
        total = data["meta"]["total"]
        print(f"  Page {page}: {len(persons)} persons (total so far: {len(all_persons)}/{total})")
        if len(all_persons) >= total:
            break
        page += 1
        time.sleep(0.5)
    return all_persons


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    flights = fetch_all_flights()
    flights_path = OUT_DIR / "flights.json"
    with open(flights_path, "w", encoding="utf-8") as f:
        json.dump(flights, f, indent=2)
    print(f"\nSaved {len(flights)} flights to {flights_path}")

    persons = fetch_all_persons()
    persons_path = OUT_DIR / "persons.json"
    with open(persons_path, "w", encoding="utf-8") as f:
        json.dump(persons, f, indent=2)
    print(f"Saved {len(persons)} persons to {persons_path}")

    # Stats
    with_passengers = sum(1 for f in flights if f.get("passengerCount", 0) > 0)
    all_passengers = set()
    for f in flights:
        for name in f.get("passengerNames", []):
            all_passengers.add(name)
    print(f"\nFlights with passengers: {with_passengers}/{len(flights)}")
    print(f"Unique passenger names: {len(all_passengers)}")

    dates = [f["date"] for f in flights if f.get("date")]
    if dates:
        print(f"Date range: {min(dates)} to {max(dates)}")


if __name__ == "__main__":
    main()
