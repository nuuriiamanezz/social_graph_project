"""Step 13: data for the site's interactive network map -> assets/data/network.json

Per decade: largest connected component, same layout recipe as step 12,
communities: label = most-credited member, name = genre/franchise name (see genre_names);
nodes: name n, community c (8 largest, else -1), degree d, x/y, role r (a/d),
f = indices into that decade's film list (titles in films, IMDb ratings in ratings);
edges with weight. Also prints the headline counts used on the site.
Needs results/communities.tsv (step 8).  Run from project/, then step 15 for the layout the site uses:
  python3 src/13_export_site_data.py && node src/15_layout_network.mjs
"""
import itertools, json, os
import numpy as np, pandas as pd, networkx as nx

films = pd.read_csv("data/processed/films.tsv", sep="\t")
fp = pd.read_csv("data/processed/film_people.tsv", sep="\t").merge(films[["tconst", "decade", "title_imdb", "year", "rating"]],
                                                                    on="tconst")
comm = pd.read_csv("results/communities.tsv", sep="\t")
close = pd.read_csv("results/network_closure.tsv", sep="\t").set_index("decade")
NC = 8

fnet = pd.read_csv("results/film_network.tsv", sep="\t")[["tconst", "community"]]
fg = films.merge(fnet, on="tconst")
fg["g"] = fg.genres.str.split(",")


def genre_names(dec, labels):
    """Name each big community by what its films have in common.
    Films of a community = films where most of the cast/director belong to it (step 8).
    Name = the two genres most over-represented vs. the whole decade (lift), among
    genres in at least 30% of its films. Its biggest franchise (2+ films in one TMDB
    collection) is kept separately. Clashes get the most-credited person added."""
    dd = fg[fg.decade == dec]
    base = dd.explode("g").g.value_counts(normalize=True)
    res = {}
    for k in range(NC):
        cf = dd[dd.community == k]
        if not len(cf):
            res[k] = dict(name=labels[k], nfilms=0)
            continue
        gs = cf.explode("g").g.value_counts()
        share, lift = gs / len(cf), (gs / gs.sum()) / base.reindex(gs.index)
        cand = lift[share >= 0.3].sort_values(ascending=False)
        if not len(cand):
            cand = lift.sort_values(ascending=False)
        g1 = cand.index[0]
        coll = cf.collection.dropna().value_counts()
        fr = coll.index[0].replace(" Collection", "").replace(" (Reboot)", "") if len(coll) else None
        frn = int(coll.iloc[0]) if len(coll) else 0
        name = f"{g1} & {cand.index[1]}" if len(cand) > 1 else g1
        res[k] = dict(name=name, genre=g1, gshare=round(float(share[g1]), 2), glift=round(float(lift[g1]), 1),
                      franchise=fr if frn >= 2 else None, franchise_n=frn, nfilms=int(len(cf)))
    key = lambda n: frozenset(n.split(" & "))  # "Action & Crime" clashes with "Crime & Action"
    names = [key(r["name"]) for r in res.values()]
    for k, r in res.items():
        if names.count(key(r["name"])) > 1:
            r["name"] = f"{r['name']} ({labels[k]})"
    return res


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
    gn = genre_names(dec, [x["label"] for x in comms])
    for x in comms:
        x.update(gn[x["id"]])
    small = c.loc[[n for n in nodes if c.community[n] >= NC]]  # grey on the site
    out["decades"][str(dec)] = {
        "people": G.number_of_nodes(), "giant": len(H), "repeat_share": round(float(close.repeat_edges[dec]), 4),
        "small": {"people": len(small), "groups": int(small.community.nunique()),
                  "median_size": int(small.drop_duplicates("community").comm_size.median())},
        "communities": comms,
        "films": [f"{t} ({y})" for t, y in zip(ft.title_imdb, ft.year)],
        "ratings": [round(float(r), 1) for r in ft.rating],
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
