"""Step 3: build the cleaned, committed dataset in data/processed/.

Hollywood = TMDB origin_country contains "US".
Fair decade comparison = top N films per decade by IMDb votes (old films
collect fewer votes, so a fixed vote threshold over-samples recent decades
and keeps only franchise "survivors" from the 1980s).
Nodes = director(s) + top-4 billed actors of each film.
"""
import json
import subprocess
import pandas as pd

N_PER_DECADE = 400
L = lambda x: x if isinstance(x, list) else []

tm = pd.DataFrame([json.loads(l) for l in open("data/interim/tmdb_raw.jsonl")]).drop_duplicates("imdb_id")
films = pd.read_csv("data/interim/films_10k.tsv", sep="\t").merge(tm, left_on="tconst", right_on="imdb_id")
films = films[films.origin_country.apply(lambda x: "US" in L(x)) & (films.overview.fillna("").str.len() > 20)].copy()
films["decade"] = films.startYear // 10 * 10
films = (films.sort_values("numVotes", ascending=False)
              .groupby("decade").head(N_PER_DECADE)
              .sort_values(["startYear", "primaryTitle"]))
for c in ["keywords", "production_companies", "genres_tmdb"]:
    if c in films:
        films[c] = films[c].apply(lambda x: "|".join(L(x)))
films = films.rename(columns={"primaryTitle": "title_imdb", "startYear": "year",
                              "averageRating": "rating", "numVotes": "votes"})
keep = ["tconst", "tmdb_id", "title_imdb", "year", "decade", "rating", "votes", "genres",
        "runtimeMinutes", "overview", "tagline", "keywords", "collection",
        "production_companies", "budget", "revenue", "fetched_at"]
films[keep].to_csv("data/processed/films.tsv", sep="\t", index=False)

fp = pd.read_csv("data/interim/film_people_10k.tsv", sep="\t")
fp = fp[fp.tconst.isin(films.tconst)]
fp["role"] = fp.category.map({"actor": "actor", "actress": "actor", "director": "director"})
fp[["tconst", "nconst", "role", "category", "ordering"]].to_csv(
    "data/processed/film_people.tsv", sep="\t", index=False)

ids = set(fp.nconst)
open("data/interim/_ids.txt", "w").write("\n".join(sorted(ids)))
subprocess.run("zcat < data/raw/name.basics.tsv.gz | awk -F'\\t' 'NR==FNR{k[$1]=1;next} "
               "FNR==1 || ($1 in k){print $1\"\\t\"$2\"\\t\"$3\"\\t\"$4\"\\t\"$5}' "
               "data/interim/_ids.txt - > data/processed/people.tsv", shell=True, check=True)

print(films.groupby("decade").agg(films=("tconst", "size"), min_votes=("votes", "min"),
                                  mean_rating=("rating", "mean"),
                                  franchise=("collection", lambda s: s.notna().mean())).round(2).to_string())
print("film-person rows", len(fp), "| people", len(ids))
