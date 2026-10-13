#!/usr/bin/env python3
"""
CLAIM LAGOS - Seed public Lagos geo hierarchy into PostGIS.

Sources (public, free):
- temikeezy/nigeria-geojson-data (GitHub) - states, LGAs, wards with coordinates
- HDX COD-AB Nigeria - administrative boundaries (download GeoJSON separately if needed)

PLACEHOLDER: All records are marked is_placeholder=TRUE.
Replace with official Lagos State / INEC LCDA, Ward and Polling Unit boundaries
when available. Senatorial districts and Divisions are derived/approximate.

Usage (inside container or with DATABASE_URL set):
    python scripts/seed_geo_public.py
"""

import asyncio
import json
import os
from pathlib import Path
from uuid import uuid4

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://claim:claim_secret_change_me@localhost:5432/claim_lagos",
)

# Public data endpoints / local fallbacks
TEMIKEEZY_BASE = "https://raw.githubusercontent.com/temikeezy/nigeria-geojson-data/main/data"
LAGOS_STATE_NAME = "Lagos"


async def fetch_json(url: str) -> dict | list:
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.get(url)
        r.raise_for_status()
        return r.json()


async def seed():
    engine = create_async_engine(DATABASE_URL, echo=False)

    async with engine.begin() as conn:
        # Clear existing public placeholders for Lagos (safe for re-run)
        await conn.execute(
            text("DELETE FROM geo_hierarchy WHERE source = 'public' AND name = :n OR parent_id IN (SELECT id FROM geo_hierarchy WHERE name = :n AND level = 'state')"),
            {"n": LAGOS_STATE_NAME},
        )

        # 1. State
        state_id = str(uuid4())
        await conn.execute(
            text("""
                INSERT INTO geo_hierarchy (id, level, name, code, source, is_placeholder)
                VALUES (:id, 'state', :name, 'LA', 'public', TRUE)
            """),
            {"id": state_id, "name": LAGOS_STATE_NAME},
        )
        print(f"Inserted State: {LAGOS_STATE_NAME} ({state_id})")

        # 2. Approximate Senatorial Districts (Lagos has 3)
        senatorial = [
            ("Lagos Central", "LA-C"),
            ("Lagos East", "LA-E"),
            ("Lagos West", "LA-W"),
        ]
        sen_ids = {}
        for name, code in senatorial:
            sid = str(uuid4())
            sen_ids[name] = sid
            await conn.execute(
                text("""
                    INSERT INTO geo_hierarchy (id, level, name, code, parent_id, source, is_placeholder)
                    VALUES (:id, 'senatorial', :name, :code, :parent, 'public', TRUE)
                """),
                {"id": sid, "name": name, "code": code, "parent": state_id},
            )
        print(f"Inserted {len(senatorial)} Senatorial Districts (approximate)")

        # 3. LGAs from public source
        try:
            lgas_data = await fetch_json(f"{TEMIKEEZY_BASE}/lgas.json")
            lagos_lgas = lgas_data.get(LAGOS_STATE_NAME, [])
        except Exception as e:
            print(f"Could not fetch lgas.json: {e}. Using static fallback list.")
            lagos_lgas = [
                "Agege", "Ajeromi-Ifelodun", "Alimosho", "Amuwo-Odofin", "Apapa",
                "Badagry", "Epe", "Eti-Osa", "Ibeju-Lekki", "Ifako-Ijaiye",
                "Ikeja", "Ikorodu", "Kosofe", "Lagos Island", "Lagos Mainland",
                "Mushin", "Ojo", "Oshodi-Isolo", "Shomolu", "Surulere",
            ]

        lga_ids = {}
        for lga_name in lagos_lgas:
            lid = str(uuid4())
            lga_ids[lga_name] = lid
            await conn.execute(
                text("""
                    INSERT INTO geo_hierarchy (id, level, name, parent_id, source, is_placeholder)
                    VALUES (:id, 'lga', :name, :parent, 'public', TRUE)
                """),
                {"id": lid, "name": lga_name, "parent": state_id},
            )
        print(f"Inserted {len(lga_ids)} LGAs")

        # 4. LCDAs - Lagos specific (static known list, mapped under parent LGA where possible)
        # These are placeholders; official mapping needed.
        lcdas = [
            ("Agbado/Oke-Odo", "Alimosho"),
            ("Agboyi-Ketu", "Kosofe"),
            ("Ayobo-Ipaja", "Alimosho"),
            ("Bariga", "Shomolu"),
            ("Egbe-Idimu", "Alimosho"),
            ("Ejigbo", "Oshodi-Isolo"),
            ("Igando-Ikotun", "Alimosho"),
            ("Ikosi-Isheri", "Kosofe"),
            ("Isolo", "Oshodi-Isolo"),
            ("Mosan-Okunola", "Alimosho"),
            ("Odi Olowo-Ojuwoye", "Mushin"),
            ("Ojodu", "Ikeja"),
            ("Ojokoro", "Ifako-Ijaiye"),
            ("Onigbongbo", "Ikeja"),
            ("Orile Agege", "Agege"),
        ]
        for lcda_name, parent_lga in lcdas:
            parent = lga_ids.get(parent_lga, state_id)
            await conn.execute(
                text("""
                    INSERT INTO geo_hierarchy (id, level, name, parent_id, source, is_placeholder, metadata)
                    VALUES (:id, 'lcda', :name, :parent, 'public', TRUE, :meta)
                """),
                {
                    "id": str(uuid4()),
                    "name": lcda_name,
                    "parent": parent,
                    "meta": json.dumps({"note": "Lagos LCDA - official boundary pending"}),
                },
            )
        print(f"Inserted {len(lcdas)} LCDAs (placeholder mapping)")

        # 5. Wards - attempt public list (point data only; polygons later from HDX)
        try:
            wards_data = await fetch_json(f"{TEMIKEEZY_BASE}/wards.json")
            lagos_wards = [w for w in wards_data if w.get("State") == LAGOS_STATE_NAME]
        except Exception as e:
            print(f"Could not fetch wards.json: {e}. Skipping detailed wards for now.")
            lagos_wards = []

        ward_count = 0
        for w in lagos_wards[:500]:  # safety limit on small VPS
            lga_name = w.get("LGA")
            parent = lga_ids.get(lga_name, state_id)
            lat = w.get("Latitude")
            lon = w.get("Longitude")
            centroid_wkt = f"POINT({lon} {lat})" if lat and lon else None
            await conn.execute(
                text("""
                    INSERT INTO geo_hierarchy (id, level, name, parent_id, source, is_placeholder, centroid)
                    VALUES (
                        :id, 'ward', :name, :parent, 'public', TRUE,
                        CASE WHEN :wkt IS NOT NULL THEN ST_GeomFromText(:wkt, 4326) ELSE NULL END
                    )
                """),
                {
                    "id": str(uuid4()),
                    "name": w.get("Ward", "Unknown Ward"),
                    "parent": parent,
                    "wkt": centroid_wkt,
                },
            )
            ward_count += 1
        print(f"Inserted {ward_count} Wards (point centroids from public source)")

        print("\n✅ Geo seed complete. All records marked is_placeholder=TRUE.")
        print("Next: download HDX GeoJSON for polygon geometries and run an update script.")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
