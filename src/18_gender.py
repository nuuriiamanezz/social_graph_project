"""Step 18 (backup idea): gender on screen.

Gender = IMDb's credit category ("actor" / "actress"). This is IMDb's binary label,
so it cannot represent non-binary performers, and directors have no gender in
IMDb: everything below is about the cast (top-4 billed actors).

Network, per decade (same people network as step 8, directors included as nodes):
  women_credits / women_leads    share of cast credits / first-billed roles held by women
  women_people / women_multi     share of distinct cast members who are women, overall
                                 and among those with 2+ films in the decade
  bet_gap, bet_gap_ctrl          women's minus men's betweenness percentile (among cast),
                                 raw and controlling for number of films; permutation p
                                 from shuffling gender (within film-count groups for ctrl)
  repeat_w / repeat_m            share of a woman's / man's ties that are repeat ties
  next_w / next_m                share of women / men cast who appear again next decade
  ww_obs / ww_null, assort       share of cast-cast ties that are woman-woman vs. shuffled
                                 gender; gender assortativity (0 = mixing at random)
Text, per decade (TMDB overviews):
  she_share                      share of gendered pronouns that are she/her/hers/herself
  she_share_fled                 same, plots of female-led films only
  rating_f / rating_m            mean IMDb rating of female-led / male-led films
Words: log-odds with an informative Dirichlet prior (Monroe et al. 2008) of words
in plots of female-led vs male-led films (character names removed, step 5;
pronouns left out so content words show).
Needs data/interim/overviews_no_names.tsv (step 5). Run from project/:
  python3 src/18_gender.py
"""
import itertools, os, re
import numpy as np, pandas as pd, networkx as nx
import statsmodels.formula.api as smf
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS

NPERM = 500
rng = np.random.default_rng(18)
films = pd.read_csv("data/processed/films.tsv", sep="\t")
fp = pd.read_csv("data/processed/film_people.tsv", sep="\t").merge(films[["tconst", "decade"]], on="tconst")
txt = pd.read_csv("data/interim/overviews_no_names.tsv", sep="\t").set_index("tconst").text
films["text"] = txt.reindex(films.tconst).fillna("").values

cast = fp[fp.category.isin(["actor", "actress"])].copy()
cast["woman"] = (cast.category == "actress").astype(int)
gender = cast.drop_duplicates("nconst").set_index("nconst").woman  # IMDb label is per person
lead = cast.sort_values("ordering").drop_duplicates("tconst").set_index("tconst").woman
films["female_led"] = films.tconst.map(lead)

FEM, MASC = {"she", "her", "hers", "herself"}, {"he", "him", "his", "himself"}
tok = lambda s: re.findall(r"[a-z]+", s.lower())


def pron(texts):
    t = [w for s in texts for w in tok(s)]
    f, m = sum(w in FEM for w in t), sum(w in MASC for w in t)
    return f / (f + m) if f + m else np.nan


rows, nxt = [], {}
decs = sorted(films.decade.unique())
people_by_dec = {d: set(cast[cast.decade == d].nconst) for d in decs}
for dec in decs:
    d = fp[fp.decade == dec]
    G = nx.Graph()
    for _, g in d.groupby("tconst"):
        ppl = sorted(set(g.nconst))
        G.add_nodes_from(ppl)
        for a, b in itertools.combinations(ppl, 2):
            G.add_edge(a, b, weight=G[a][b]["weight"] + 1 if G.has_edge(a, b) else 1)
    c = cast[cast.decade == dec]
    nf = c.groupby("nconst").tconst.nunique()
    P = pd.DataFrame({"films": nf, "woman": gender.reindex(nf.index)})
    bet = nx.betweenness_centrality(G)
    P["bet_pct"] = pd.Series({n: bet[n] for n in P.index}).rank(pct=True)
    P["fgrp"] = P.films.clip(upper=4)

    def gaps(w):
        raw = P.bet_pct[w == 1].mean() - P.bet_pct[w == 0].mean()
        ctrl = smf.ols("bet_pct ~ w + C(fgrp)", P.assign(w=w)).fit().params["w"]
        return raw, ctrl
    raw, ctrl = gaps(P.woman.values)
    null_raw, null_ctrl = [], []
    for _ in range(NPERM):
        null_raw.append(gaps(rng.permutation(P.woman.values))[0])
        w = P.woman.copy()
        for _, idx in P.groupby("fgrp").groups.items():  # shuffle within film-count groups
            w[idx] = rng.permutation(w[idx].values)
        null_ctrl.append(gaps(w.values)[1])
    null_raw, null_ctrl = np.array(null_raw), np.array(null_ctrl)

    # repeat ties and homophily among cast-cast ties
    E = [(a, b, w) for a, b, w in G.edges(data="weight") if a in gender.index and b in gender.index
         and a in P.index and b in P.index]
    ga = np.array([gender[a] for a, _, _ in E]); gb = np.array([gender[b] for _, b, _ in E])
    rep = np.array([w > 1 for *_, w in E])
    inc_w = np.r_[rep[ga == 1], rep[gb == 1]]; inc_m = np.r_[rep[ga == 0], rep[gb == 0]]
    ww = ((ga == 1) & (gb == 1)).mean()
    lab = {n: int(gender[n]) for n in P.index}
    ww_null = []
    for _ in range(200):
        perm = dict(zip(lab, rng.permutation(list(lab.values()))))
        ww_null.append(np.mean([perm[a] == 1 and perm[b] == 1 for a, b, _ in E]))
    H = G.subgraph(P.index).copy()
    nx.set_node_attributes(H, lab, "g")

    fd = films[films.decade == dec]
    later = set().union(*[people_by_dec[x] for x in decs if x > dec]) if dec != decs[-1] else None
    nexts = people_by_dec.get(dec + 10)
    rows.append(dict(
        decade=dec, cast_people=len(P),
        women_credits=c.woman.mean(), women_leads=fd.female_led.mean(), women_people=P.woman.mean(),
        women_multi=P.woman[P.films >= 2].mean(),
        bet_gap=raw, bet_gap_p=(np.abs(null_raw) >= abs(raw)).mean(), bet_gap_null_sd=null_raw.std(),
        bet_gap_ctrl=ctrl, bet_gap_ctrl_p=(np.abs(null_ctrl) >= abs(ctrl)).mean(), bet_gap_ctrl_null_sd=null_ctrl.std(),
        repeat_w=inc_w.mean(), repeat_m=inc_m.mean(),
        next_w=np.mean([n in nexts for n in P.index[P.woman == 1]]) if nexts else np.nan,
        next_m=np.mean([n in nexts for n in P.index[P.woman == 0]]) if nexts else np.nan,
        ww_obs=ww, ww_null=np.mean(ww_null), ww_null_sd=np.std(ww_null),
        assort=nx.attribute_assortativity_coefficient(H, "g"),
        she_share=pron(fd.overview.fillna("")), she_share_fled=pron(fd[fd.female_led == 1].overview.fillna("")),
        she_share_mled=pron(fd[fd.female_led == 0].overview.fillna("")),
        rating_f=fd.rating[fd.female_led == 1].mean(), rating_m=fd.rating[fd.female_led == 0].mean(),
        n_fled=int((fd.female_led == 1).sum())))
    print(dec, "done", flush=True)

# --- distinctive words: female-led vs male-led plots ---------------------------
STOP = ENGLISH_STOP_WORDS | FEM | MASC | {"s", "film", "movie", "story", "new", "life", "year", "years"}
cnt = lambda texts: pd.Series([w for s in texts for w in tok(s) if w not in STOP and len(w) > 2]).value_counts()
cf, cm = cnt(films.text[films.female_led == 1]), cnt(films.text[films.female_led == 0])
V = cf.index.union(cm.index)
cf, cm = cf.reindex(V, fill_value=0), cm.reindex(V, fill_value=0)
prior = (cf + cm) * 0.01 + 0.01  # informative Dirichlet prior from the pooled counts
a0, nF, nM = prior.sum(), cf.sum(), cm.sum()
delta = (np.log((cf + prior) / (nF + a0 - cf - prior)) - np.log((cm + prior) / (nM + a0 - cm - prior)))
z = delta / np.sqrt(1 / (cf + prior) + 1 / (cm + prior))
words = pd.DataFrame({"word": V, "n_female_led": cf.values, "n_male_led": cm.values, "z": z.values})
words = words[(words.n_female_led + words.n_male_led) >= 8].sort_values("z")

os.makedirs("results", exist_ok=True)
res = pd.DataFrame(rows)
res.to_csv("results/gender.tsv", sep="\t", index=False)
words.to_csv("results/gender_words.tsv", sep="\t", index=False)
pd.set_option("display.width", 250)
print(res[["decade", "women_credits", "women_leads", "women_people", "women_multi", "bet_gap", "bet_gap_p",
           "bet_gap_ctrl", "bet_gap_ctrl_p", "repeat_w", "repeat_m", "next_w", "next_m"]].round(3).to_string(index=False))
print(res[["decade", "ww_obs", "ww_null", "assort", "she_share", "she_share_fled", "she_share_mled",
           "rating_f", "rating_m", "n_fled"]].round(3).to_string(index=False))
print("\nmost female-led words:", ", ".join(words.word.iloc[::-1][:25]))
print("most male-led words:  ", ", ".join(words.word[:25]))
print(f"female-led films: {int(films.female_led.sum())} of {films.female_led.notna().sum()}")
