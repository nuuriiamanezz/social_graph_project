"""Step 2: fetch TMDB details (origin country, overview, keywords) for every film.

Run on your own laptop from project/:   python3 src/02_fetch_tmdb.py
- reads TMDB_TOKEN from .env (never printed, never committed)
- polite: ~4 requests/second, retries on 429/5xx
- resumable: already-fetched films in data/interim/tmdb_raw.jsonl are skipped,
  so you can stop it (Ctrl+C) and start again any time
- every record stores the time it was fetched (course: log what/when you collected)
"""
import csv, json, os, sys, time, urllib.error, urllib.request
from datetime import datetime, timezone

MIN_VOTES = 25_000          # change to 10_000 to fetch the wider set (~45 min)
FILMS = "data/interim/films_10k.tsv"
OUT = "data/interim/tmdb_raw.jsonl"
PAUSE = 0.25

def load_token():
    for line in open(".env"):
        if line.startswith("TMDB_TOKEN="):
            return line.split("=", 1)[1].strip().strip('"')
    sys.exit("TMDB_TOKEN not found in .env")

TOKEN = load_token()

def get(url, tries=5):
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {TOKEN}",
                                               "accept": "application/json"})
    for i in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if e.code in (429, 500, 502, 503, 504):
                time.sleep(2 ** i); continue
            raise
        except (urllib.error.URLError, TimeoutError):
            time.sleep(2 ** i)
    return None

def fetch(imdb_id):
    found = get(f"https://api.themoviedb.org/3/find/{imdb_id}?external_source=imdb_id")
    hits = (found or {}).get("movie_results") or []
    if not hits:
        return {"imdb_id": imdb_id, "tmdb_id": None}
    time.sleep(PAUSE)
    m = get(f"https://api.themoviedb.org/3/movie/{hits[0]['id']}"
            "?language=en-US&append_to_response=keywords") or {}
    return {
        "imdb_id": imdb_id,
        "tmdb_id": m.get("id"),
        "title": m.get("title"),
        "origin_country": m.get("origin_country", []),
        "production_countries": [c["iso_3166_1"] for c in m.get("production_countries", [])],
        "original_language": m.get("original_language"),
        "overview": m.get("overview"),
        "tagline": m.get("tagline"),
        "keywords": [k["name"] for k in m.get("keywords", {}).get("keywords", [])],
        "production_companies": [c["name"] for c in m.get("production_companies", [])],
        "budget": m.get("budget"), "revenue": m.get("revenue"),
        "collection": (m.get("belongs_to_collection") or {}).get("name"),
    }

films = [row["tconst"] for row in csv.DictReader(open(FILMS), delimiter="\t")
         if int(row["numVotes"]) >= MIN_VOTES]
done = set()
if os.path.exists(OUT):
    done = {json.loads(l)["imdb_id"] for l in open(OUT) if l.strip()}
todo = [f for f in films if f not in done]
print(f"{len(films)} films, {len(done)} already fetched, {len(todo)} to go "
      f"(~{len(todo) * 2 * PAUSE / 60:.0f} min)")

with open(OUT, "a") as out:
    for i, imdb_id in enumerate(todo, 1):
        rec = fetch(imdb_id)
        rec["fetched_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        out.write(json.dumps(rec, ensure_ascii=False) + "\n")
        out.flush()
        if i % 100 == 0:
            print(f"  {i}/{len(todo)}  last: {rec.get('title')}")
        time.sleep(PAUSE)
print("done ->", OUT)
