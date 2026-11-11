"""Step 1: filter the IMDb dumps to feature films 1980-2024 and their key people.

Pre-filtered with awk into data/interim/ (see README); this script picks the
director(s) + top-4 billed actors per film and reports sizes at several
vote thresholds. Origin-country (US) filter comes later from TMDB.
"""
import itertools
import pandas as pd

D = "data/interim/"
r = pd.read_csv(D + "ratings_10k.tsv", sep="\t")
b = pd.read_csv(D + "basics_10k.tsv", sep="\t", na_values="\\N",
                usecols=["tconst", "primaryTitle", "startYear", "runtimeMinutes", "genres"])
p = pd.read_csv(D + "principals_10k.tsv", sep="\t", na_values="\\N",
                usecols=["tconst", "ordering", "nconst", "category"])

films = b.merge(r, on="tconst")
actors = (p[p.category.isin(["actor", "actress"])]
          .sort_values(["tconst", "ordering"]).groupby("tconst").head(4))
directors = p[p.category == "director"]
people = pd.concat([actors, directors]).drop_duplicates(["tconst", "nconst"])

films.to_csv(D + "films_10k.tsv", sep="\t", index=False)
people.to_csv(D + "film_people_10k.tsv", sep="\t", index=False)

def size(min_votes, df=films):
    f = df[df.numVotes >= min_votes]
    pp = people[people.tconst.isin(f.tconst)]
    edges = set()
    for _, g in pp.groupby("tconst"):
        edges.update(itertools.combinations(sorted(g.nconst), 2))
    return len(f), pp.nconst.nunique(), len(edges)

print("votes  films  people  edges (worldwide, 1980-2024)")
for t in [10_000, 25_000, 50_000, 100_000]:
    print(t, *size(t))
films["decade"] = (films.startYear // 10) * 10
print("\nfilms >=25k votes per decade:")
print(films[films.numVotes >= 25_000].decade.value_counts().sort_index().to_string())
