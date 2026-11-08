"""Rebuild the Blue Mesa Water Report.

Usage:
    python3 scripts/build.py            # download fresh data from Reclamation, then build
    python3 scripts/build.py --offline  # build from the CSVs already in data/

Writes data/blue_mesa_daily.csv, data/summary.json and index.html.
"""
import csv
import datetime
import json
import pathlib
import statistics
import sys
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
SITE = 913  # Blue Mesa Reservoir in Reclamation's Upper Colorado hydrologic database
SOURCES = {  # Reclamation datatype id -> local file, column name
    42: ("release_cfs.csv", "total release"),
    17: ("storage_af.csv", "storage"),
    49: ("elevation_ft.csv", "pool elevation"),
}
FULL_POOL_FT = 7519.4
AF_PER_CFS_DAY = 1.98347
FIRST_DAY = "1968-12-01"  # first day with release data


def download():
    for dtype, (name, _) in SOURCES.items():
        url = f"https://www.usbr.gov/uc/water/hydrodata/reservoir_data/{SITE}/csv/{dtype}.csv"
        print("downloading", url)
        req = urllib.request.Request(url, headers={"User-Agent": "blue-mesa-water-report"})
        with urllib.request.urlopen(req, timeout=60) as r:
            (DATA / name).write_bytes(r.read())


def load(name, col):
    with open(DATA / name, newline="") as f:
        return {r["datetime"]: r[col] for r in csv.DictReader(f)}


def num(v):
    try:
        return float(v) if v not in ("", None) else None
    except ValueError:
        return None


def build():
    rel, sto, ele = (load(*SOURCES[k]) for k in (42, 17, 49))
    days = sorted(d for d in set(rel) | set(sto) | set(ele) if d >= FIRST_DAY)
    daily = [(d, num(rel.get(d)), num(sto.get(d)), num(ele.get(d))) for d in days]

    with open(DATA / "blue_mesa_daily.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", "release_cfs", "storage_af", "elevation_ft"])
        for d, q, s, e in daily:
            w.writerow([d, "" if q is None else round(q, 1), "" if s is None else round(s), "" if e is None else round(e, 2)])

    # Calendar-year totals
    by = {}
    for d, q, s, e in daily:
        y = int(d[:4])
        a = by.setdefault(y, {"af": 0.0, "days": 0, "min": None, "min_d": None, "max": None, "max_d": None})
        if q is not None:
            a["af"] += q * AF_PER_CFS_DAY
            a["days"] += 1
        if s is not None:
            if a["min"] is None or s < a["min"]:
                a["min"], a["min_d"] = s, d
            if a["max"] is None or s > a["max"]:
                a["max"], a["max_d"] = s, d
    latest = max(by)
    years = [
        {"year": y, "release_af": round(a["af"]), "min_storage_af": round(a["min"]), "min_date": a["min_d"],
         "max_storage_af": round(a["max"]), "max_date": a["max_d"], "partial": a["days"] < 365}
        for y, a in sorted(by.items()) if a["days"] >= 365 or y == latest
    ]
    full = [y for y in years if not y["partial"]]
    fullset = {y["year"] for y in full}

    # Monthly average storage
    mon = {}
    for d, q, s, e in daily:
        if s is None:
            continue
        m = mon.setdefault(d[:7], [0.0, 0, 0.0, 0])
        m[0] += s; m[1] += 1
        if e is not None:
            m[2] += e; m[3] += 1
    monthly = [{"month": k, "storage_af": round(v[0] / v[1]), "elevation_ft": round(v[2] / v[3], 1) if v[3] else None}
               for k, v in sorted(mon.items())]

    # Average release rate by month
    names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    acc = [{"all": [0.0, 0], "cur": [0.0, 0], "prev": [0.0, 0]} for _ in names]
    for d, q, s, e in daily:
        if q is None:
            continue
        y, a = int(d[:4]), acc[int(d[5:7]) - 1]
        for key, ok in (("all", y in fullset), ("cur", y == latest), ("prev", y == latest - 1)):
            if ok:
                a[key][0] += q; a[key][1] += 1
    mean = lambda p: round(p[0] / p[1]) if p[1] else None
    seasonal = [{"month": n, "avg_cfs": mean(a["all"]), "this_year_cfs": mean(a["cur"]), "last_year_cfs": mean(a["prev"])}
                for n, a in zip(names, acc)]

    # Weekly storage for every year, plus the typical (median) year
    wk = {}
    for d, q, s, e in daily:
        if s is None:
            continue
        dt = datetime.date.fromisoformat(d)
        w = min((dt.timetuple().tm_yday - 1) // 7, 52)
        wk.setdefault(dt.year, {}).setdefault(w, []).append(s)
    wyears = sorted(y for y in wk if y >= 1969)
    weekly = {str(y): [round(statistics.mean(wk[y][w])) if w in wk[y] else None for w in range(53)] for y in wyears}
    median = []
    for w in range(53):
        vals = [weekly[str(y)][w] for y in wyears if y < latest and weekly[str(y)][w] is not None]
        median.append(round(statistics.median(vals)) if vals else None)

    # Headline figures
    stored = [(d, s, e) for d, q, s, e in daily if s is not None]
    now = [x for x in stored if x[2] is not None][-1]
    year, md = int(now[0][:4]), now[0][5:]
    high = max(stored, key=lambda x: x[1])
    low = min(stored, key=lambda x: x[1])
    before = [x for x in stored if x[0] < f"{year}-01-01"]
    prev_low = min(before, key=lambda x: x[1])
    last_low = [x for x in before if x[1] <= now[1]]
    same = min((x for x in before if x[0][5:] == md), key=lambda x: x[1])
    st_by_day = {d: s for d, s, e in stored}
    year_ago = st_by_day.get(f"{year - 1}-{md}")
    ytd = {}
    for d, q, s, e in daily:
        y = int(d[:4])
        if q is None or d[5:] > md or (y not in fullset and y != year):
            continue
        ytd[y] = ytd.get(y, 0.0) + q * AF_PER_CFS_DAY
    others = [v for k, v in ytd.items() if k != year]
    ytd_avg = sum(others) / len(others)
    ytd_max = max(ytd.items(), key=lambda x: x[1])
    most = max(full, key=lambda y: y["release_af"])
    least = min(full, key=lambda y: y["release_af"])
    avg = sum(y["release_af"] for y in full) / len(full)
    summary = {
        "as_of": now[0], "year": year, "first_date": daily[0][0],
        "storage_af": round(now[1]), "elevation_ft": now[2],
        "full_pool_ft": FULL_POOL_FT, "below_full_ft": round(FULL_POOL_FT - now[2], 1),
        "year_ago_af": round(year_ago) if year_ago else None,
        "storage_change_af": round(now[1] - year_ago) if year_ago else None,
        "pct_of_record_high": now[1] / high[1], "record_high_af": round(high[1]), "record_high_date": high[0],
        "high_vs_now_af": round(high[1] - now[1]),
        "record_low_af": round(low[1]), "record_low_date": low[0], "above_low_af": round(now[1] - low[1]),
        "last_this_low": last_low[-1][0][:4] if last_low else None,
        "prev_low_af": round(prev_low[1]), "prev_low_date": prev_low[0],
        "same_date_year": int(same[0][:4]), "same_date_af": round(same[1]), "same_date_diff_af": round(same[1] - now[1]),
        "ytd_af": round(ytd[year]), "ytd_avg_af": round(ytd_avg), "ytd_pct_of_avg": ytd[year] / ytd_avg,
        "ytd_rank_low": sorted(ytd.values()).index(ytd[year]) + 1, "ytd_years": len(ytd),
        "ytd_max_year": ytd_max[0], "ytd_max_af": round(ytd_max[1]), "ytd_gap_af": round(ytd_max[1] - ytd[year]),
        "most_year": most["year"], "most_af": most["release_af"],
        "least_year": least["year"], "least_af": least["release_af"], "least_pct_of_avg": least["release_af"] / avg,
        "avg_year_af": round(avg),
    }
    (DATA / "summary.json").write_text(json.dumps(summary, indent=1))

    payload = {"summary": summary, "years": years, "monthly": monthly, "seasonal": seasonal,
               "weekly": {"years": weekly, "median": median}}
    body = (ROOT / "scripts" / "template.html").read_text().replace(
        "/*__DATA__*/", json.dumps(payload, separators=(",", ":")).replace("</", "<\\/"))
    head, rest = body.split("<style>", 1)
    page = ("<!doctype html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1, viewport-fit=cover\">\n"
            + head + "<style>\n  body { margin: 0; }\n" + rest.split("</style>", 1)[0] + "</style>\n</head>\n<body>\n"
            + rest.split("</style>", 1)[1] + "\n</body>\n</html>\n")
    (ROOT / "index.html").write_text(page)
    print(f"built index.html: data through {now[0]}, {round(now[1]):,} acre-feet in storage")


if __name__ == "__main__":
    if "--offline" not in sys.argv:
        download()
    build()
