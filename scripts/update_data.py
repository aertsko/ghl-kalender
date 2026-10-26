#!/usr/bin/env python3
"""Haalt kalender + uitslagen van Heren A en Dames A op bij volleyscores.be
en schrijft data.json voor de kalenderwidget.

- Competitie (met uitslagen en setstanden): de ploegpagina van volleyscores.be.
- Bekerwedstrijden: aangevuld uit de iCal-feed van de ploeg (zonder uitslag).
Bij een fout wordt data.json NIET overschreven, zodat de site nooit leeg valt.
"""
import json, re, sys
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
BXL = ZoneInfo("Europe/Brussels")
UA = {"User-Agent": "GHL-kalenderwidget (golazohaasrodeleuven.be)"}

PLOEGEN = {
    "heren": {"naam": "Heren A", "competitie": "Lotto Volley League", "team_id": 101281},
    "dames": {"naam": "Dames A", "competitie": "Nationale 1 Dames", "team_id": 103159},
}
ONS = "Golazo Haasrode Leuven A"

CLUB_URL = "https://www.volleyscores.be/direct/VB-0122"
TEAM_URL = ("https://www.volleyscores.be/index.php?v=2&ss=0&isActiveSeason=1&t=Ploeg&a=t"
            "&se={se}&pi=&si=&ti={id}&ci=&mm=&ssi=&st=&w=%25&f=&lng=nl")
SEIZOEN_FALLBACK = "13"  # 2026-2027


def huidig_seizoen():
    """Seizoens-ID staat als <input data-gt="se" value=".."> op de clubpagina."""
    try:
        html = requests.get(CLUB_URL, headers=UA, timeout=30).text
        m = re.search(r'data-gt="se"[^>]*value="(\d+)"', html) or re.search(r'value="(\d+)"[^>]*data-gt="se"', html)
        if m:
            return m.group(1)
    except requests.RequestException as e:
        print(f"waarschuwing: clubpagina niet opgehaald ({e})")
    return SEIZOEN_FALLBACK
ICS_URL = "https://www.volleyscores.be/calendar/team/{id}"


def clean(s):
    return re.sub(r"\s+", " ", s or "").strip()


def parse_teampagina(html):
    """Elke wedstrijd staat als <tr> met desktopcellen td.hidden-xs:
    nr, dag, datum, uur, thuis, bezoekers, sporthal, uitslag, sets."""
    soup = BeautifulSoup(html, "html.parser")
    gezien, uit = set(), []
    for tr in soup.find_all("tr"):
        c = [clean(td.get_text()) for td in tr.find_all("td", class_="hidden-xs")]
        if len(c) < 8 or not re.match(r"^[A-Z0-9]+-\w+$", c[0]) or c[0] in gezien:
            continue
        if not re.match(r"\d{2}/\d{2}/\d{4}", c[2]):
            continue
        gezien.add(c[0])
        uitslag = c[7] if re.match(r"^\d+\s*-\s*\d+$", c[7]) else None
        sets = c[8] if len(c) > 8 and uitslag else None
        uit.append([c[0], c[2], c[3], c[4], c[5], c[6], uitslag, sets or None])
    return uit


def parse_ics(text):
    text = re.sub(r"\r?\n[ \t]", "", text)  # gevouwen regels samenvoegen
    out = []
    for blok in text.split("BEGIN:VEVENT")[1:]:
        f = {}
        for line in blok.splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                f[k.split(";")[0]] = v.replace("\\,", ",").strip()
        m = re.match(r"^([^:]+):\s*(.+?)\s+-\s+(.+)$", f.get("SUMMARY", ""))
        if not m or "DTSTART" not in f:
            continue
        dt = datetime.strptime(f["DTSTART"].rstrip("Z"), "%Y%m%dT%H%M%S").replace(tzinfo=timezone.utc).astimezone(BXL)
        loc = [p.strip() for p in f.get("LOCATION", "").split(",")]
        zaal = ", ".join(loc[:2]) if len(loc) >= 2 else f.get("LOCATION", "")
        out.append([m.group(1).strip(), dt.strftime("%d/%m/%Y"), dt.strftime("%H:%M"),
                    m.group(2).strip(), m.group(3).strip(), zaal, None, None])
    return out


def main():
    se = huidig_seizoen()
    print(f"seizoen-ID: {se}")
    data = {"bijgewerkt": datetime.now(BXL).isoformat(timespec="minutes"), "ploegen": {}}
    for key, p in PLOEGEN.items():
        r = requests.get(TEAM_URL.format(se=se, id=p["team_id"]), headers=UA, timeout=30)
        r.raise_for_status()
        wedstrijden = parse_teampagina(r.text)
        if len(wedstrijden) < 5:
            sys.exit(f"{key}: maar {len(wedstrijden)} wedstrijden gevonden — paginaformaat gewijzigd? data.json niet aangepast.")
        try:  # bekerwedstrijden uit de iCal aanvullen
            ics = requests.get(ICS_URL.format(id=p["team_id"]), headers=UA, timeout=30)
            codes = {w[0] for w in wedstrijden}
            wedstrijden += [w for w in parse_ics(ics.text) if w[0] not in codes]
        except requests.RequestException as e:
            print(f"waarschuwing: iCal {key} niet opgehaald ({e})")
        data["ploegen"][key] = {"naam": p["naam"], "competitie": p["competitie"], "ons": ONS,
                                "wedstrijden": wedstrijden}
        gespeeld = sum(1 for w in wedstrijden if w[6])
        print(f"{key}: {len(wedstrijden)} wedstrijden, {gespeeld} met uitslag")

    pad = ROOT / "data.json"
    oud = json.loads(pad.read_text()) if pad.exists() else None
    if oud and oud["ploegen"] == data["ploegen"]:
        print("geen wijzigingen")
        return
    pad.write_text(json.dumps(data, ensure_ascii=False, indent=1))
    print("data.json bijgewerkt")


if __name__ == "__main__":
    main()
