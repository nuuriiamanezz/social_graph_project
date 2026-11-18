"""Step 15 (Act II checks): does our plot-similarity score measure plot similarity?

Three checks on the TF-IDF score from step 6, without changing step 6:

  python3 src/15_similarity_checks.py methods [--emb]
      Recomputes the Act II gap with a second measure, so the finding does not
      rest on TF-IDF alone:
        keywords   Jaccard overlap of the TMDB keyword lists (written by TMDB
                   editors, a different source than the overview text)
        embedding  sentence embeddings of the same name-free overviews
                   (only with --emb; needs `pip install sentence-transformers`
                   and internet for the first download of all-MiniLM-L6-v2)
      Also gives the franchise-free gap its own shuffle null, since step 6 only
      tests the full gap. -> results/similarity_checks.tsv

  python3 src/15_similarity_checks.py sheets
      Draws 60 film pairs (same decade, never the same franchise) and writes one
      identical label sheet per group member to data/validation/. Stratified by
      TF-IDF score (20 high, 20 middle, 20 low) so the sample is not 60 obviously
      unrelated pairs. The sheets show no scores, so labelling is blind.
      -> data/validation/labels_<name>.xlsx, data/validation/hand_check_pairs.tsv

  python3 src/15_similarity_checks.py score [--emb]
      After everyone has labelled their own sheet without talking to each other:
      agreement between labellers, and how well each measure tracks the human
      labels. -> results/hand_check.tsv

Needs data/interim/overviews_no_names.tsv from step 5.  Run from project/.
pip install openpyxl  (to read and write the .xlsx sheets)
"""
import itertools, os, sys
import numpy as np, pandas as pd, scipy.sparse as sp
from scipy.stats import spearmanr
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import cohen_kappa_score, roc_auc_score
from sklearn.preprocessing import normalize

LABELLERS = ["Nour", "Nuria", "Marah"]
N_PER_STRATUM, NPERM, SEED = 20, 200, 15
VAL = "data/validation"


def load():
    films = pd.read_csv("data/processed/films.tsv", sep="\t")
    txt = pd.read_csv("data/interim/overviews_no_names.tsv", sep="\t").set_index("tconst").text
    films["text"] = txt.reindex(films.tconst).fillna("").values
    return films


def vectors(films, emb=False):
    """Row-normalised vectors per measure; for keywords the pair score is Jaccard."""
    v = {"tfidf": normalize(TfidfVectorizer(stop_words="english", min_df=2).fit_transform(films.text))}
    kw = films.keywords.fillna("").str.lower().str.split("|").apply(lambda k: {w for w in k if w})
    vocab = {w: j for j, w in enumerate(sorted(set().union(*kw)))}
    rows, cols = zip(*[(i, vocab[w]) for i, ks in enumerate(kw) for w in ks])
    v["keywords"] = sp.csr_matrix((np.ones(len(rows)), (rows, cols)), shape=(len(films), len(vocab)))
    if emb:
        from sentence_transformers import SentenceTransformer
        v["embedding"] = SentenceTransformer("all-MiniLM-L6-v2").encode(
            films.text.tolist(), normalize_embeddings=True)
    return v


def sim(name, X, i, j=None):
    """Similarity matrix between films i and j (j=None: i with itself)."""
    A, B = X[i], X[i if j is None else j]
    S = A @ B.T
    S = S.toarray() if sp.issparse(S) else np.asarray(S)
    if name == "keywords":  # Jaccard = shared / (|a| + |b| - shared)
        na = np.asarray(A.sum(1)).ravel()
        nb = np.asarray(B.sum(1)).ravel()
        union = na[:, None] + nb[None, :] - S
        S = np.divide(S, union, out=np.zeros_like(S), where=union > 0)
    return S


def pairmean(S, mask):
    iu = np.triu_indices_from(S, 1)
    v = S[iu][mask[iu]]
    return v.mean() if len(v) else np.nan


def gap(S, sh, keep):
    return pairmean(S, sh & keep) - pairmean(S, ~sh & keep)


def methods(emb):
    rng = np.random.default_rng(SEED)
    films = load()
    fp = pd.read_csv("data/processed/film_people.tsv", sep="\t")
    ppl = {p: k for k, p in enumerate(fp.nconst.unique())}
    row = pd.Series(films.index, index=films.tconst)
    fp = fp[fp.tconst.isin(row.index)]
    M = sp.csr_matrix((np.ones(len(fp)), (row[fp.tconst].values, fp.nconst.map(ppl).values)))

    out = []
    for name, X in vectors(films, emb).items():
        for dec, fd in films.groupby("decade"):
            i = fd.index.values
            S = sim(name, X, i)
            sh = (M[i] @ M[i].T).toarray() > 0
            fr = fd.collection.notna().values
            coll = fd.collection.fillna("").to_numpy(dtype=object)
            other = ~((coll[:, None] == coll[None, :]) & fr[:, None])  # not same franchise
            everything = np.ones_like(sh)
            g, g_nf = gap(S, sh, everything), gap(S, sh, other)
            null, null_nf = [], []  # same network, plots shuffled between films
            for _ in range(NPERM):
                p = rng.permutation(len(i))
                Sp = S[np.ix_(p, p)]
                null.append(gap(Sp, sh, everything))
                null_nf.append(gap(Sp, sh, other))
            null, null_nf = np.array(null), np.array(null_nf)
            out.append(dict(
                method=name, decade=dec, films=len(i),
                sim_all=pairmean(S, everything), sim_nonfranchise=pairmean(S[np.ix_(~fr, ~fr)], np.ones((len(i) - fr.sum(),) * 2, bool)),
                gap=g, gap_ratio=pairmean(S, sh) / pairmean(S, ~sh),
                gap_z=(g - null.mean()) / null.std(), gap_p=(np.sum(null >= g) + 1) / (NPERM + 1),
                gap_no_same_franchise=g_nf,
                gap_nf_ratio=pairmean(S, sh & other) / pairmean(S, ~sh & other),
                gap_nf_z=(g_nf - null_nf.mean()) / null_nf.std(),
                gap_nf_p=(np.sum(null_nf >= g_nf) + 1) / (NPERM + 1)))
    res = pd.DataFrame(out)
    os.makedirs("results", exist_ok=True)
    res.to_csv("results/similarity_checks.tsv", sep="\t", index=False)
    pd.set_option("display.width", 200)
    print(res[["method", "decade", "sim_all", "gap_ratio", "gap_z",
               "gap_nf_ratio", "gap_nf_z", "gap_nf_p"]].round(3).to_string(index=False))
    print("\ngap_ratio: how many times more similar pairs that share a person are than pairs that"
          "\nshare nobody (1 = no difference). gap_nf_*: the same with same-franchise pairs removed.")


def sheets():
    rng = np.random.default_rng(SEED)
    films = load()
    X = vectors(films)["tfidf"]
    pairs = []
    for dec, fd in films.groupby("decade"):
        i = fd.index.values
        S = sim("tfidf", X, i)
        coll = fd.collection.to_numpy(dtype=object)
        a, b = np.triu_indices(len(i), 1)
        ok = ~((coll[a] == coll[b]) & pd.notna(coll[a]))
        ok &= (fd.text.values[a] != "") & (fd.text.values[b] != "")
        pairs.append(pd.DataFrame(dict(decade=dec, a=i[a][ok], b=i[b][ok], tfidf=S[a, b][ok])))
    pairs = pd.concat(pairs, ignore_index=True)
    # by rank, not value: over half of all pairs share no word at all (score 0)
    r = pairs.tfidf.rank(method="first", pct=True)
    strata = {"high": pairs[r > 0.98], "middle": pairs[(r > 0.5) & (r <= 0.98)],
              "low": pairs[r <= 0.5]}
    pick = pd.concat([s.sample(N_PER_STRATUM, random_state=SEED).assign(stratum=k)
                      for k, s in strata.items()])
    pick = pick.sample(frac=1, random_state=SEED).reset_index(drop=True)  # mix the strata
    pick["pair_id"] = np.arange(1, len(pick) + 1)
    f = films.set_index(films.index)
    key = pd.DataFrame(dict(pair_id=pick.pair_id, decade=pick.decade, stratum=pick.stratum,
                            tconst_a=f.tconst[pick.a].values, tconst_b=f.tconst[pick.b].values))
    sheet = pd.DataFrame({
        "pair_id": pick.pair_id,
        "film_a": [f"{t} ({y})" for t, y in zip(f.title_imdb[pick.a], f.year[pick.a])],
        "plot_a": f.overview[pick.a].values,
        "film_b": [f"{t} ({y})" for t, y in zip(f.title_imdb[pick.b], f.year[pick.b])],
        "plot_b": f.overview[pick.b].values,
        "label": "",
    })
    os.makedirs(VAL, exist_ok=True)
    key.to_csv(f"{VAL}/hand_check_pairs.tsv", sep="\t", index=False)
    guide = pd.DataFrame({"How to label": [
        "Read the two plot summaries and put 0, 1 or 2 in the 'label' column:",
        "0 = different stories (different situation, conflict and kind of protagonist)",
        "1 = some shared plot elements (a similar setup OR conflict OR protagonist, not all of it)",
        "2 = very similar stories (you could describe both with the same one-sentence premise)",
        "Judge the STORY only, not genre, tone, actors or how well you know the films.",
        "Label on your own: do not compare answers until all three sheets are done.",
        "Leave other columns as they are. About 20 minutes for 60 pairs.",
    ]})
    for who in LABELLERS:
        path = f"{VAL}/labels_{who}.xlsx"
        with pd.ExcelWriter(path, engine="openpyxl") as xw:
            sheet.to_excel(xw, sheet_name="pairs", index=False)
            guide.to_excel(xw, sheet_name="instructions", index=False)
            ws = xw.sheets["pairs"]
            for col, width in zip("ABCDEF", [8, 28, 70, 28, 70, 8]):
                ws.column_dimensions[col].width = width
            from openpyxl.styles import Alignment
            for r in ws.iter_rows(min_row=2):
                for c in r:
                    c.alignment = Alignment(wrap_text=True, vertical="top")
            ws.freeze_panes = "A2"
            xw.sheets["instructions"].column_dimensions["A"].width = 100
    print(f"wrote {len(sheet)} pairs to {VAL}/labels_<name>.xlsx for {', '.join(LABELLERS)}")
    print(pick.groupby("stratum").tfidf.agg(["min", "max"]).round(3))


def score(emb):
    key = pd.read_csv(f"{VAL}/hand_check_pairs.tsv", sep="\t")
    labels = {}
    for who in LABELLERS:
        s = pd.read_excel(f"{VAL}/labels_{who}.xlsx", sheet_name="pairs").set_index("pair_id").label
        s = pd.to_numeric(s, errors="coerce")
        missing = s.isna() | ~s.isin([0, 1, 2])
        if missing.any():
            sys.exit(f"{who}: pairs {list(s.index[missing])} have no valid label (0, 1 or 2)")
        labels[who] = s.reindex(key.pair_id).astype(int).values
    L = pd.DataFrame(labels)

    rows = []
    for a, b in itertools.combinations(LABELLERS, 2):
        rows.append(dict(check="agreement", what=f"{a} vs {b}",
                         value=cohen_kappa_score(L[a], L[b], weights="quadratic"),
                         exact=(L[a] == L[b]).mean()))
    kap = [r["value"] for r in rows]
    rows.append(dict(check="agreement", what="mean weighted kappa", value=np.mean(kap),
                     exact=np.mean([r["exact"] for r in rows])))

    films = load()
    idx = pd.Series(films.index, index=films.tconst)
    ia, ib = idx[key.tconst_a].values, idx[key.tconst_b].values
    human = L.mean(axis=1).values
    similar = (L.median(axis=1) >= 1).values  # majority says at least "some shared plot"
    for name, X in vectors(films, emb).items():
        s = np.array([sim(name, X, [x], [y])[0, 0] for x, y in zip(ia, ib)])
        rho, p = spearmanr(s, human)
        rows.append(dict(check="measure vs humans", what=f"{name}: Spearman rho with mean label",
                         value=rho, p=p))
        if 0 < similar.sum() < len(similar):
            rows.append(dict(check="measure vs humans",
                             what=f"{name}: AUC, majority-similar vs not ({similar.sum()} vs {(~similar).sum()})",
                             value=roc_auc_score(similar, s)))
    res = pd.DataFrame(rows)
    res.to_csv("results/hand_check.tsv", sep="\t", index=False)
    print(res.round(3).to_string(index=False))
    print("\nweighted kappa: 1 = perfect agreement, 0 = chance; above ~0.6 is usually called substantial."
          "\nSpearman rho: does a higher score go with a higher human label? AUC: chance that a pair the"
          "\nmajority called similar scores higher than one they did not (0.5 = coin flip, 1 = perfect).")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    emb = "--emb" in sys.argv
    if cmd == "methods":
        methods(emb)
    elif cmd == "sheets":
        sheets()
    elif cmd == "score":
        score(emb)
    else:
        sys.exit(__doc__)
