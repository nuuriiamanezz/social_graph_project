"""Step 13: data for the site's interactive network map -> assets/data/network.json

Per decade: largest connected component, same layout recipe as step 12,
nodes: name n, community c (8 largest, else -1), degree d, x/y, role r (a/d),
f = indices into that decade's film list;
edges with weight. Also prints the headline counts used on the site.
Needs results/communities.tsv (step 8).  Run from project/:
  python3 src/13_export_site_data.py
"""
import itertools, json, os
import numpy as np, pandas as pd, networkx as nx

films = pd.read_csv("data/processed/films.tsv", sep="\t")
fp = pd.read_csv("data/processed/film_people.tsv", sep="\t").merge(films[["tconst", "decade", "title_imdb", "year"]],
                                                                    on="tconst")
comm = pd.read_csv("results/communities.tsv", sep="\t")
close = pd.read_csv("results/network_closure.tsv", sep="\t").set_index("decade")
NC = 8

out = {"decades": {}}
all_edges = set()
for dec, d in fp.groupby("decade"):
    G = nx.Graph()
    for _, g in d.groupby("tconst"):
        ppl = sorted(set(g.nconst))
        G.add_nodes_from(ppl)
        for a, b in itertools.combinations(ppl, 2):
            G.add_edge(a, b, weight=G[a][b]["weight"] + 1 if G.has_edge(a, b) else 1)
    all_edges |= set(G.edges())
    H = G.subgraph(max(nx.connected_components(G), key=len)).copy()
    pos = nx.spring_layout(H, k=1.6 / np.sqrt(len(H)), iterations=300, seed=3, weight="weight")
    xy = np.array(list(pos.values()))
    lo, span = xy.min(0), (xy.max(0) - xy.min(0)).max()
    c = comm[comm.decade == dec].set_index("nconst")
    ft = d.drop_duplicates("tconst").sort_values(["year", "title_imdb"])
    fid = {t: i for i, t in enumerate(ft.tconst)}
    filmlist = d.groupby("nconst").tconst.apply(lambda s: sorted(fid[t] for t in s))
    roles = d.groupby("nconst").role.apply(lambda s: "director" if (s == "director").any() else "actor")
    nodes = list(H)
    idx = {n: i for i, n in enumerate(nodes)}
    credits = d.nconst.value_counts()
    deg = dict(H.degree())
    comms = []  # label each big community by its most-credited member
    for k in range(NC):
        mem = [n for n in nodes if c.community[n] == k]
        top = max(mem, key=lambda n: (credits.get(n, 0), deg[n])) if mem else None
        comms.append({"id": k, "size": int(c.comm_size[mem[0]]) if mem else 0, "label": c.name[top] if top else ""})
    out["decades"][str(dec)] = {
        "people": G.number_of_nodes(), "giant": len(H), "repeat_share": round(float(close.repeat_edges[dec]), 4),
        "communities": comms,
        "films": [f"{t} ({y})" for t, y in zip(ft.title_imdb, ft.year)],
        "nodes": [{"n": c.name[n], "c": int(c.community[n]) if c.community[n] < NC else -1, "d": deg[n],
                   "x": round(float((pos[n][0] - lo[0]) / span), 3), "y": round(float((pos[n][1] - lo[1]) / span), 3),
                   "f": filmlist[n], "r": roles[n][0]}
                  for n in nodes],
        "edges": [[idx[a], idx[b], w] for a, b, w in H.edges(data="weight")],
    }

os.makedirs("assets/data", exist_ok=True)
with open("assets/data/network.json", "w") as f:
    json.dump(out, f, separators=(",", ":"), ensure_ascii=False)
print("films", films.tconst.nunique(), "| people", fp.nconst.nunique(), "| unique collaborations", len(all_edges))
print("network.json", os.path.getsize("assets/data/network.json") // 1024, "KB")
