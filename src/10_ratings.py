"""Step 10 (Act III): do audiences notice?

Per film:
  prior_ties   share of its people pairs that had already worked together on an
               EARLIER film in our sample (strictly earlier year): a tight circle
  n_comms      number of Act I communities its people come from: a bridge film
  franchise    film is in a TMDB collection
Film types for the figure: tight circle (prior_ties > 0, at most 2 communities),
bridge (3+ communities, no prior ties), other.

Models (OLS): rating ~ prior_ties + n_comms + franchise + decade + main genres.
  robustness: + log(votes); non-franchise films only.
Check: ratings shuffled across films within each decade (NPERM runs), refit,
two-sided permutation p-value for each coefficient.

Directors: betweenness in their decade's network vs. mean rating of their
films that decade (Spearman, same within-decade shuffle as check). Only
directors with 2+ films that decade: a one-film director's neighbours are all
in the same cast (a clique), so their betweenness is 0 by construction and the
correlation would just measure "made more films" (film count vs rating is
reported separately as rho_films).

Needs results/film_network.tsv from step 8.  Run from project/:
  python3 src/10_ratings.py
"""
import itertools, os
import numpy as np, pandas as pd, networkx as nx
import statsmodels.formula.api as smf
from scipy.stats import spearmanr

NPERM = 1000
rng = np.random.default_rng(42)
films = pd.read_csv("data/processed/films.tsv", sep="\t")
fp = pd.read_csv("data/processed/film_people.tsv", sep="\t")
net = pd.read_csv("results/film_network.tsv", sep="\t")[["tconst", "n_comms", "comm_share"]]
names = pd.read_csv("data/processed/people.tsv", sep="\t", usecols=[0, 1]).set_index("nconst").primaryName

# --- prior ties: walk through the films year by year -------------------------
year = films.set_index("tconst").year
cast = fp.groupby("tconst").nconst.apply(lambda s: sorted(set(s)))
worked, prior = set(), {}
for y, ts in films.groupby("year").tconst:
    pairs = {t: list(itertools.combinations(cast.get(t, []), 2)) for t in ts}
    for t, ps in pairs.items():   # same-year films do not count as "earlier"
        prior[t] = np.mean([p in worked for p in ps]) if ps else np.nan
    for ps in pairs.values():
        worked.update(ps)

d = films.merge(net, on="tconst")
d["prior_ties"] = d.tconst.map(prior)
d["franchise"] = d.collection.notna().astype(int)
d["log_votes"] = np.log10(d.votes)
top_genres = d.genres.str.split(",").explode().value_counts().index[:8]
for g in top_genres:
    d[f"g_{g.replace('-', '_')}"] = d.genres.str.contains(g).astype(int)
gcols = " + ".join(c for c in d if c.startswith("g_"))
d = d.dropna(subset=["prior_ties"])
d["type"] = np.select([(d.prior_ties > 0) & (d.n_comms <= 2), (d.n_comms >= 3) & (d.prior_ties == 0)],
                      ["tight circle", "bridge"], "other")

# --- regressions + within-decade permutation ---------------------------------
TERMS = ["prior_ties", "n_comms", "franchise"]
models = {"main": f"rating ~ prior_ties + n_comms + franchise + C(decade) + {gcols}",
          "with_votes": f"rating ~ prior_ties + n_comms + franchise + log_votes + C(decade) + {gcols}",
          "non_franchise": f"rating ~ prior_ties + n_comms + C(decade) + {gcols}"}
coef_rows, null_store = [], {}
for name, f in models.items():
    data = d if name != "non_franchise" else d[d.franchise == 0]
    fit = smf.ols(f, data).fit(cov_type="HC1")
    terms = [t for t in TERMS if t in fit.params]
    y, X = fit.model.endog, fit.model.exog
    idx = [fit.model.exog_names.index(t) for t in terms]
    groups = [np.flatnonzero(data.decade.values == dec) for dec in sorted(data.decade.unique())]
    null = []
    for _ in range(NPERM):
        yp = y.copy()
        for g in groups:
            yp[g] = rng.permutation(yp[g])
        null.append(np.linalg.lstsq(X, yp, rcond=None)[0][idx])
    null = np.array(null)
    null_store[name] = pd.DataFrame(null, columns=terms)
    for k, t in enumerate(terms):
        coef_rows.append(dict(model=name, term=t, n=int(fit.nobs), coef=fit.params[t],
                              ci_lo=fit.conf_int().loc[t, 0], ci_hi=fit.conf_int().loc[t, 1], p_ols=fit.pvalues[t],
                              null_sd=null[:, k].std(),
                              p_perm=(np.abs(null[:, k]) >= abs(fit.params[t])).mean()))
coefs = pd.DataFrame(coef_rows)

# --- film types per decade, bootstrap CI --------------------------------------
type_rows = []
for (dec, ty), g in d.groupby(["decade", "type"]):
    b = [rng.choice(g.rating.values, len(g)).mean() for _ in range(1000)]
    type_rows.append(dict(decade=dec, type=ty, films=len(g), rating=g.rating.mean(),
                          lo=np.percentile(b, 2.5), hi=np.percentile(b, 97.5)))
types = pd.DataFrame(type_rows)

# --- directors: betweenness vs rating ------------------------------------------
dir_rows = []
fpd = fp.merge(films[["tconst", "decade", "rating"]], on="tconst")
for dec, g in fpd.groupby("decade"):
    G = nx.Graph()
    for _, h in g.groupby("tconst"):
        G.add_edges_from(itertools.combinations(sorted(set(h.nconst)), 2))
        G.add_nodes_from(h.nconst)
    bet = nx.betweenness_centrality(G)
    dr = g[g.role == "director"].groupby("nconst").agg(rating=("rating", "mean"), films=("tconst", "nunique"))
    dr["betweenness"], dr["degree"] = dr.index.map(bet), dr.index.map(dict(G.degree()))
    dr["decade"], dr["name"] = dec, dr.index.map(names)
    dir_rows.append(dr.reset_index())
dirs_all = pd.concat(dir_rows)
rho_films = spearmanr(dirs_all.films, dirs_all.rating).statistic
dirs = dirs_all[dirs_all.films >= 2].copy()
rho = lambda df: spearmanr(df.betweenness, df.rating).statistic
obs = rho(dirs)
null = []
for _ in range(NPERM):
    s = dirs.copy()
    s["rating"] = s.groupby("decade").rating.transform(lambda r: rng.permutation(r.values))
    null.append(rho(s))
null = np.array(null)
dir_summary = pd.DataFrame([dict(decade="all", directors=len(dirs), rho=obs, p_perm=(np.abs(null) >= abs(obs)).mean()),
                            dict(decade="rho_films (all directors)", directors=len(dirs_all), rho=rho_films, p_perm=np.nan)] +
                           [dict(decade=dec, directors=len(g), rho=rho(g), p_perm=np.nan) for dec, g in dirs.groupby("decade")])

os.makedirs("results", exist_ok=True)
d[["tconst", "title_imdb", "year", "decade", "rating", "votes", "franchise", "prior_ties", "n_comms", "comm_share", "type"]
  ].to_csv("results/film_ratings.tsv", sep="\t", index=False)
coefs.to_csv("results/ratings_models.tsv", sep="\t", index=False)
types.to_csv("results/ratings_by_type.tsv", sep="\t", index=False)
dirs_all.to_csv("results/director_betweenness.tsv", sep="\t", index=False)
dir_summary.to_csv("results/director_summary.tsv", sep="\t", index=False)
pd.concat(null_store, names=["model"]).to_csv("results/ratings_null.tsv", sep="\t")

print("share of films with prior ties, by decade:\n", d.groupby("decade").prior_ties.apply(lambda s: (s > 0).mean()).round(2).to_string())
print("\nfilm types:\n", d.type.value_counts().to_string())
print("\n", coefs.round(4).to_string(index=False))
print("\n", types.round(2).to_string(index=False))
print("\ndirectors (betweenness vs rating, Spearman):\n", dir_summary.round(3).to_string(index=False))
