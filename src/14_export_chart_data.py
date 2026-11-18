"""Step 14: data for the site's interactive charts -> assets/data/charts.json

Collects the results of steps 6, 8, 10 and 18 (no new analysis) plus the degree and
tie-strength distributions of step 12. Re-run after any of those steps changes.
Run from project/:  python3 src/14_export_chart_data.py
"""
import itertools, json, os
import numpy as np, pandas as pd

R = lambda f: pd.read_csv(f"results/{f}", sep="\t")
films = pd.read_csv("data/processed/films.tsv", sep="\t")
fp = pd.read_csv("data/processed/film_people.tsv", sep="\t").merge(films[["tconst", "decade"]], on="tconst")


def recs(df, digits=5):
    return json.loads(df.round(digits).to_json(orient="records"))


degree, ties = {}, {}
for dec, d in fp.groupby("decade"):
    w = {}
    for _, g in d.groupby("tconst"):
        for e in itertools.combinations(sorted(set(g.nconst)), 2):
            w[e] = w.get(e, 0) + 1
    deg = {}
    for a, b in w:
        deg[a] = deg.get(a, 0) + 1
        deg[b] = deg.get(b, 0) + 1
    k = np.array(list(deg.values()))
    degree[str(dec)] = [[int(x), round(float((k >= x).mean()), 5)] for x in np.unique(k)]
    wv = np.array(list(w.values()))
    ties[str(dec)] = [[int(x), round(float((wv >= x).mean()), 6), int((wv >= x).sum())] for x in range(1, wv.max() + 1)]

dirs = R("director_betweenness.tsv").query("films >= 2")
out = {
    "closure": recs(R("network_closure.tsv")),
    "degree": degree, "ties": ties,
    "plots": recs(R("plot_similarity.tsv"), 6),
    "types": recs(R("ratings_by_type.tsv"), 3),
    "models": recs(R("ratings_models.tsv"), 4),
    "directors": [dict(n=r["name"], dec=int(r.decade), b=round(float(r.betweenness), 6), r=round(float(r.rating), 2),
                       f=int(r.films)) for _, r in dirs.iterrows()],
    "dsum": recs(R("director_summary.tsv"), 3),
}
if os.path.exists("results/gender.tsv"):  # step 18
    w = R("gender_words.tsv")
    out["gender"] = recs(R("gender.tsv"), 4)
    out["gender_words"] = recs(pd.concat([w.head(15), w.tail(15)]), 3)
os.makedirs("assets/data", exist_ok=True)
json.dump(out, open("assets/data/charts.json", "w"), separators=(",", ":"), ensure_ascii=False)
print("charts.json", os.path.getsize("assets/data/charts.json") // 1024, "KB")
