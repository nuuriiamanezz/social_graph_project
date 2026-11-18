"""Step 8 (Act I): is the collaboration network closing?

One network per decade: people (director + top-4 actors) linked when they share
a film, weight = number of shared films.

Per decade:
  clust             average clustering
  repeat_edges      share of ties that repeat (worked together on 2+ films)
  modularity        Louvain modularity (weighted), n_comms = communities with 5+ people
  hub_share         share of all credits held by the top 5% most active people
  returning         share of credits by people already in any earlier decade
                    (grows partly by construction: later decades have more past)
  returning_prev    same, but only the previous decade (fair across decades)
  franchise         share of films in a TMDB collection

Null (main): bipartite shuffle. Each person keeps their number of films and
each film keeps its cast size, but who works with whom is random. This is the
right null for a film -> people projection: every film is a 5-clique, so a
plain degree-preserving swap on the projection destroys those cliques and
makes any projection look "clustered". Reported as mean, sd and z.
For reference, clust_swap = clustering after a degree-preserving edge swap.

Also writes, for Act II/III:
  results/communities.tsv     decade, nconst, name, community, comm_size
  results/film_network.tsv    per film: majority community, share of its people
                              in it, number of communities spanned, and
                              prior_ties = share of its people pairs that also
                              worked together on another film that decade
Run from project/:  python3 src/08_network_closure.py
"""
import itertools, os
import numpy as np, pandas as pd, networkx as nx

NNULL, NSWAP = 50, 10
rng = np.random.default_rng(42)
films = pd.read_csv("data/processed/films.tsv", sep="\t")
fp = pd.read_csv("data/processed/film_people.tsv", sep="\t")
names = pd.read_csv("data/processed/people.tsv", sep="\t", usecols=[0, 1]).set_index("nconst").primaryName
fp = fp.merge(films[["tconst", "decade"]], on="tconst")


def project(t, p):
    """film/person columns -> weighted person-person graph."""
    G = nx.Graph()
    for _, g in pd.DataFrame({"t": t, "p": p}).groupby("t"):
        ppl = sorted(set(g.p))
        G.add_nodes_from(ppl)
        for a, b in itertools.combinations(ppl, 2):
            G.add_edge(a, b, weight=G[a][b]["weight"] + 1 if G.has_edge(a, b) else 1)
    return G


def shuffle(t, p):
    """Permute people across film slots; then fix a person landing twice in one film."""
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
                modularity=nx.community.modularity(G, comms, weight="weight")), comms


rows, comm_rows, film_rows, seen, prev = [], [], [], set(), set()
for dec, d in fp.groupby("decade"):
    t, p = d.tconst.to_numpy(), d.nconst.to_numpy()
    G = project(t, p)
    obs, comms = stats(G)

    null = pd.DataFrame([stats(project(t, shuffle(t, p)))[0] for _ in range(NNULL)])
    swap = []
    for s in range(NSWAP):
        R = nx.Graph(G)
        nx.double_edge_swap(R, nswap=3 * R.number_of_edges(), max_tries=10**7, seed=s)
        swap.append(nx.average_clustering(R))

    credits = d.nconst.value_counts()
    top = credits.iloc[: max(1, int(round(.05 * len(credits))))]
    r = dict(decade=dec, films=d.tconst.nunique(), people=G.number_of_nodes(), edges=G.number_of_edges(),
             mean_deg=2 * G.number_of_edges() / G.number_of_nodes(),
             giant=len(max(nx.connected_components(G), key=len)) / G.number_of_nodes(),
             n_comms=sum(len(c) >= 5 for c in comms),
             hub_share=top.sum() / credits.sum(),
             returning=d.nconst.isin(seen).mean() if seen else np.nan,
             returning_prev=d.nconst.isin(prev).mean() if prev else np.nan,
             franchise=films[films.decade == dec].collection.notna().mean(),
             clust_swap=np.mean(swap))
    for k, v in obs.items():
        r.update({k: v, f"{k}_null": null[k].mean(), f"{k}_null_sd": null[k].std(),
                  f"{k}_z": (v - null[k].mean()) / null[k].std()})
    rows.append(r)
    seen |= set(p); prev = set(p)

    # communities, numbered by size within the decade
    comms = sorted(comms, key=len, reverse=True)
    cid = {n: k for k, c in enumerate(comms) for n in c}
    comm_rows += [dict(decade=dec, nconst=n, name=names.get(n, ""), community=cid[n], comm_size=len(comms[cid[n]]))
                  for n in G]
    for f, g in d.groupby("tconst"):
        ppl = sorted(set(g.nconst))
        c = pd.Series([cid[n] for n in ppl]).value_counts()
        pairs = list(itertools.combinations(ppl, 2))
        film_rows.append(dict(tconst=f, decade=dec, people=len(ppl), community=c.index[0],
                              comm_share=c.iloc[0] / len(ppl), n_comms=len(c),
                              prior_ties=np.mean([G[a][b]["weight"] > 1 for a, b in pairs]) if pairs else np.nan))
    print(f"{dec}s done", flush=True)

os.makedirs("results", exist_ok=True)
res = pd.DataFrame(rows)
res.to_csv("results/network_closure.tsv", sep="\t", index=False)
pd.DataFrame(comm_rows).to_csv("results/communities.tsv", sep="\t", index=False)
pd.DataFrame(film_rows).to_csv("results/film_network.tsv", sep="\t", index=False)
print(res[["decade", "people", "edges", "giant", "clust", "clust_null", "clust_z", "clust_swap",
           "repeat_edges", "repeat_edges_null", "repeat_edges_z", "modularity", "modularity_null",
           "modularity_z", "n_comms", "hub_share", "returning", "returning_prev", "franchise"]].round(3).to_string(index=False))
