"""Step 6 (Act II): are plots converging, and do the same people tell the same stories?

Per decade, over all pairs of films:
  sim_all / sim_nonfranchise   mean plot cosine (all films / franchise films left out)
  gap                          pairs that share a person minus pairs that share nobody
  gap_no_same_franchise        same, without pairs from the same collection (only sequels?)
Checks: bootstrap over films (95% CI) and a null where plots are shuffled
across films while the network stays fixed (z-score of the gap).
Run from project/ after step 5:  python3 src/06_plot_similarity.py [--emb]
"""
import os, sys
import numpy as np, pandas as pd, scipy.sparse as sp
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize

B, NPERM = 200, 200
rng = np.random.default_rng(42)
films = pd.read_csv("data/processed/films.tsv", sep="\t")
fp = pd.read_csv("data/processed/film_people.tsv", sep="\t")
txt = pd.read_csv("data/interim/overviews_no_names.tsv", sep="\t").set_index("tconst").text
films["text"] = txt.reindex(films.tconst).fillna("").values

# TF-IDF fitted once on all films, so every decade uses the same weights
vecs = {"tfidf": normalize(TfidfVectorizer(stop_words="english", min_df=2).fit_transform(films.text))}
if "--emb" in sys.argv:  # second method (pip install sentence-transformers)
    from sentence_transformers import SentenceTransformer
    vecs["embedding"] = SentenceTransformer("all-MiniLM-L6-v2").encode(films.text.tolist(), normalize_embeddings=True)

# film x person matrix, so (M M^T)[i,j] > 0 means film i and j share someone
ppl = {p: k for k, p in enumerate(fp.nconst.unique())}
row = pd.Series(films.index, index=films.tconst)
fp = fp[fp.tconst.isin(row.index)]
M = sp.csr_matrix((np.ones(len(fp)), (row[fp.tconst].values, fp.nconst.map(ppl).values)))

def pairmean(S, mask=None):
    iu = np.triu_indices_from(S, 1)
    v = S[iu] if mask is None else S[iu][mask[iu]]
    return v.mean() if len(v) else np.nan

def gap(S, sh, keep=None):
    keep = np.ones_like(sh) if keep is None else keep
    return pairmean(S, sh & keep) - pairmean(S, ~sh & keep)

rows = []
for name, X in vecs.items():
    for dec, fd in films.groupby("decade"):
        i = fd.index.values
        S = X[i] @ X[i].T
        S = S.toarray() if sp.issparse(S) else np.asarray(S)
        sh = (M[i] @ M[i].T).toarray() > 0
        fr = fd.collection.notna().values
        coll = fd.collection.fillna("").to_numpy(dtype=object)
        same = (coll[:, None] == coll[None, :]) & fr[:, None]

        boot = []  # resample films; drop pairs of a film with its own copy
        for _ in range(B):
            b = rng.integers(0, len(i), len(i))
            Sb = np.where(b[:, None] == b[None, :], np.nan, S[np.ix_(b, b)])
            shb = sh[np.ix_(b, b)]
            iu = np.triu_indices(len(b), 1)
            v, s = Sb[iu], shb[iu]
            ok = ~np.isnan(v)
            boot.append((v[ok].mean(), v[ok & s].mean() - v[ok & ~s].mean()))
        boot = np.array(boot)

        null = []  # same network, plots shuffled between films
        for _ in range(NPERM):
            p = rng.permutation(len(i))
            null.append(gap(S[np.ix_(p, p)], sh))
        null = np.array(null)

        g = gap(S, sh)
        lo, hi = np.percentile(boot, [2.5, 97.5], axis=0)
        rows.append(dict(method=name, decade=dec, films=len(i), pairs_shared=int(np.triu(sh, 1).sum()),
                         sim_all=pairmean(S), sim_all_lo=lo[0], sim_all_hi=hi[0],
                         sim_nonfranchise=pairmean(S[np.ix_(~fr, ~fr)]),
                         gap=g, gap_lo=lo[1], gap_hi=hi[1], gap_no_same_franchise=gap(S, sh, ~same),
                         gap_null=null.mean(), gap_null_sd=null.std(), gap_z=(g - null.mean()) / null.std()))

res = pd.DataFrame(rows)
os.makedirs("results", exist_ok=True)
res.to_csv("results/plot_similarity.tsv", sep="\t", index=False)
print(res[["method", "decade", "pairs_shared", "sim_all", "sim_nonfranchise",
           "gap", "gap_no_same_franchise", "gap_z"]].round(4).to_string(index=False))
