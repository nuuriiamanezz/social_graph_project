"""Step 12: network pictures for the paper / site.

network_maps.png   1980s vs 2010s collaboration networks (largest component),
                   nodes coloured by their Act I community (8 largest, rest grey),
                   size by degree, repeat ties (2+ films together) drawn dark.
                   Each big community is labelled with its most-credited person.
clustering.png     a) degree distribution (CCDF) per decade
                   b) tie strength: share of ties with >= w films together, per decade
                   (C(k) vs degree was tried: identical to the null, since it is
                   fixed by the 5-person casts, so it is left out)
Needs results/communities.tsv from step 8.  Run from project/:
  python3 src/12_network_maps.py
"""
import itertools
import numpy as np, pandas as pd, networkx as nx
import matplotlib.pyplot as plt

rng = np.random.default_rng(42)
films = pd.read_csv("data/processed/films.tsv", sep="\t")
fp = pd.read_csv("data/processed/film_people.tsv", sep="\t").merge(films[["tconst", "decade"]], on="tconst")
comm = pd.read_csv("results/communities.tsv", sep="\t")
PAL = ["#e6194b", "#3cb44b", "#4363d8", "#f58231", "#911eb4", "#42d4f4", "#f032e6", "#9a6324"]


def project(t, p):
    G = nx.Graph()
    for _, g in pd.DataFrame({"t": t, "p": p}).groupby("t"):
        ppl = sorted(set(g.p))
        G.add_nodes_from(ppl)
        for a, b in itertools.combinations(ppl, 2):
            G.add_edge(a, b, weight=G[a][b]["weight"] + 1 if G.has_edge(a, b) else 1)
    return G


def shuffle(t, p):  # same null as step 8
    p = rng.permutation(p)
    for _ in range(1000):
        dup = pd.DataFrame({"t": t, "p": p}).duplicated().to_numpy().nonzero()[0]
        if not len(dup):
            break
        for i in dup:
            j = rng.integers(len(p))
            p[i], p[j] = p[j], p[i]
    return p


graphs = {dec: project(d.tconst.to_numpy(), d.nconst.to_numpy()) for dec, d in fp.groupby("decade")}

# --- network maps ---------------------------------------------------------------
fig, axes = plt.subplots(1, 2, figsize=(14, 7))
for ax, dec in zip(axes, [1980, 2010]):
    G = graphs[dec].subgraph(max(nx.connected_components(graphs[dec]), key=len)).copy()
    c = comm[comm.decade == dec].set_index("nconst")
    pos = nx.spring_layout(G, k=1.6 / np.sqrt(len(G)), iterations=300, seed=3, weight="weight")
    col = {n: PAL[c.community[n]] if c.community[n] < len(PAL) else "#cccccc" for n in G}
    rep = [(a, b) for a, b, w in G.edges(data="weight") if w > 1]
    one = [(a, b) for a, b, w in G.edges(data="weight") if w == 1]
    nx.draw_networkx_edges(G, pos, edgelist=one, ax=ax, width=.2, alpha=.15, edge_color="grey")
    nx.draw_networkx_edges(G, pos, edgelist=rep, ax=ax, width=1.1, alpha=.8, edge_color="black")
    deg = dict(G.degree())
    nx.draw_networkx_nodes(G, pos, ax=ax, node_size=[3 + deg[n] * 1.2 for n in G],
                           node_color=[col[n] for n in G], linewidths=0)
    credits = fp[fp.decade == dec].nconst.value_counts()
    for k in range(len(PAL)):  # label each big community by its most-credited member
        mem = [n for n in G if c.community[n] == k]
        if not mem:
            continue
        top = max(mem, key=lambda n: (credits.get(n, 0), deg[n]))
        x, y = pos[top]
        ax.annotate(c.name[top], (x, y), fontsize=8, weight="bold", color=PAL[k],
                    xytext=(4, 4), textcoords="offset points",
                    bbox=dict(boxstyle="round,pad=.15", fc="white", ec="none", alpha=.7))
    share = len(rep) / G.number_of_edges()
    ax.set_title(f"{dec}s · {len(G)} people · repeat ties (black) = {share:.1%}", fontsize=11)
    ax.axis("off")
fig.suptitle("Who works with whom: the 400 most-voted US films of each decade", fontsize=13)
fig.text(.01, .01, "Largest connected component. Colour = Louvain community (8 largest; grey = others), "
         "size = degree, labels = most-credited person in each community.", fontsize=8, color="grey")
fig.tight_layout(rect=(0, .03, 1, .96))
fig.savefig("results/network_maps.png", dpi=200)
print("saved results/network_maps.png")

# --- degree distribution + clustering spectrum ------------------------------------
fig, ax = plt.subplots(1, 2, figsize=(11, 4))
bins = np.unique(np.round(np.logspace(np.log10(4), np.log10(80), 12)))
for k, (dec, G) in enumerate(graphs.items()):
    deg = np.array([d for _, d in G.degree()])
    xs = np.sort(np.unique(deg))
    ax[0].loglog(xs, [(deg >= x).mean() for x in xs], "-", color=f"C{k}", label=f"{dec}s")

    w = np.array([x for *_, x in G.edges(data="weight")])
    ws = np.arange(1, w.max() + 1)
    ax[1].semilogy(ws, [(w >= x).mean() for x in ws], "o-", color=f"C{k}", label=f"{dec}s")
ax[0].set(title="Degree distribution", xlabel="degree k (collaborators)", ylabel="P(K ≥ k)")
ax[1].set(title="Tie strength: how often pairs work together", xlabel="films made together (w)",
          ylabel="share of ties with ≥ w films", xticks=range(1, 8))
ax[0].legend(fontsize=8); ax[1].legend(fontsize=8)
fig.text(.01, .01, "Degree 4 = one film only (a single 5-person cast). 2020s = 2020-2024 only. "
         "(Clustering-by-degree C(k) was tried but equals the null: it is set by the 5-person casts.)",
         fontsize=7, color="grey")
fig.tight_layout(rect=(0, .04, 1, 1))
fig.savefig("results/clustering.png", dpi=200)
print("saved results/clustering.png")
