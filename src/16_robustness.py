"""Step 16: robustness of Act I (step 8) to our sampling choices.

Variants (all from the US pool: TMDB origin US, >= 25k IMDb votes, plot text):
  base_400        400 most-voted films per decade, director + top-4 actors (= step 8)
  n_200, n_300    200 / 300 films per decade (600 is impossible: the 1980s pool has 416)
  top3_actors     400 per decade, director + top-3 actors
  no_franchise    200 per decade, films in a TMDB collection left out first
  all_25k         every film with >= 25k votes (unequal decade sizes)
  half_150        150 films per 5-year window (1980-84 has 151), so 2020-24 is
                  compared with 2015-19 on equal footing
Per variant and period: repeat ties, clustering and modularity against the same
bipartite-shuffle null as step 8 (NNULL runs), returning people (share of credits
by people in the previous period of that variant) and hub share.
Run from project/:  python3 src/16_robustness.py      (~3 min)
"""
import itertools, json, os
import numpy as np, pandas as pd, networkx as nx

NNULL = 20
rng = np.random.default_rng(7)
L = lambda x: x if isinstance(x, list) else []

tm = pd.DataFrame([json.loads(l) for l in open("data/interim/tmdb_raw.jsonl")]).drop_duplicates("imdb_id")
pool = pd.read_csv("data/interim/films_10k.tsv", sep="\t").merge(tm[["imdb_id", "origin_country", "overview", "collection"]],
                                                                  left_on="tconst", right_on="imdb_id")
pool = pool[pool.origin_country.apply(lambda x: "US" in L(x)) & (pool.overview.fillna("").str.len() > 20)].copy()
pool["decade"], pool["half"] = pool.startYear // 10 * 10, pool.startYear // 5 * 5
fp_all = pd.read_csv("data/interim/film_people_10k.tsv", sep="\t")
fp_all = fp_all[fp_all.tconst.isin(pool.tconst)].copy()
act = fp_all[fp_all.category.isin(["actor", "actress"])].sort_values(["tconst", "ordering"])
act["rank"] = act.groupby("tconst").cumcount() + 1
fp_all = pd.concat([act, fp_all[fp_all.category == "director"]])


def project(t, p):
    G = nx.Graph()
    for _, g in pd.DataFrame({"t": t, "p": p}).groupby("t"):
        ppl = sorted(set(g.p))
        G.add_nodes_from(ppl)
        for a, b in itertools.combinations(ppl, 2):
            G.add_edge(a, b, weight=G[a][b]["weight"] + 1 if G.has_edge(a, b) else 1)
    return G


def shuffle(t, p):  # same bipartite null as step 8
    p = rng.permutation(p)
    for _ in range(1000):
        dup = pd.DataFrame({"t": t, "p": p}).duplicated().to_numpy().nonzero()[0]
        if not len(dup):
            break
        for i in dup:
            j = rng.integers(len(p))
            p[i], p[j] = p[j], p[i]
    return p


def stats(G):
    comms = nx.community.louvain_communities(G, weight="weight", seed=1)
    w = np.array([d["weight"] for *_, d in G.edges(data=True)])
    return dict(clust=nx.average_clustering(G), repeat_edges=(w > 1).mean(),
                modularity=nx.community.modularity(G, comms, weight="weight"))


def sample(period, n=None, actors=4, franchise=True):
    f = pool if franchise else pool[pool.collection.isna()]
    if n:
        f = f.sort_values("numVotes", ascending=False).groupby(period).head(n)
    fp = fp_all[fp_all.tconst.isin(f.tconst) & ((fp_all.category == "director") | (fp_all["rank"] <= actors))]
    return fp.merge(f[["tconst", period]], on="tconst").rename(columns={period: "period"})


VARIANTS = {"base_400": ("decade", dict(n=400)), "n_200": ("decade", dict(n=200)), "n_300": ("decade", dict(n=300)),
            "top3_actors": ("decade", dict(n=400, actors=3)), "no_franchise": ("decade", dict(n=200, franchise=False)),
            "all_25k": ("decade", dict()), "half_150": ("half", dict(n=150))}
rows = []
for name, (period, kw) in VARIANTS.items():
    d_all, prev = sample(period, **kw), set()
    for per, d in d_all.groupby("period"):
        t, p = d.tconst.to_numpy(), d.nconst.to_numpy()
        G = project(t, p)
        obs = stats(G)
        null = pd.DataFrame([stats(project(t, shuffle(t, p))) for _ in range(NNULL)])
        credits = d.nconst.value_counts()
        top = credits.iloc[: max(1, int(round(.05 * len(credits))))]
        r = dict(variant=name, period=per, span=10 if period == "decade" else 5, films=d.tconst.nunique(),
                 people=G.number_of_nodes(), people_per_film=G.number_of_nodes() / d.tconst.nunique(),
                 returning_prev=d.nconst.isin(prev).mean() if prev else np.nan, hub_share=top.sum() / credits.sum())
        for k, v in obs.items():
            r.update({k: v, f"{k}_null": null[k].mean(), f"{k}_z": (v - null[k].mean()) / null[k].std(),
                      f"{k}_excess": v - null[k].mean()})
        rows.append(r)
        prev = set(p)
    print(name, "done", flush=True)

res = pd.DataFrame(rows)
os.makedirs("results", exist_ok=True)
res.to_csv("results/robustness.tsv", sep="\t", index=False)
cols = ["variant", "period", "films", "people_per_film", "repeat_edges", "repeat_edges_null", "clust_excess", "clust_z",
        "modularity_excess", "returning_prev", "hub_share"]
print(res[cols].round(3).to_string(index=False))
