"""Step 4: first decade-by-decade comparison (network + text). Run from project/."""
import itertools, random, numpy as np, pandas as pd, networkx as nx
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
U="data/processed/"  # run from project/
films=pd.read_csv(U+"films.tsv",sep="\t"); fp=pd.read_csv(U+"film_people.tsv",sep="\t")
random.seed(1); rows=[]
for dec,fd in films.groupby("decade"):
    G=nx.Graph()
    for t,g in fp[fp.tconst.isin(fd.tconst)].groupby("tconst"):
        ppl=sorted(set(g.nconst)); G.add_nodes_from(ppl)
        for a,b in itertools.combinations(ppl,2):
            w=G[a][b]["weight"]+1 if G.has_edge(a,b) else 1; G.add_edge(a,b,weight=w)
    deg=np.array([d for _,d in G.degree()])
    gc=max(nx.connected_components(G),key=len)
    C=nx.average_clustering(G)
    Cn=[]
    for s in range(5):
        R=nx.Graph(G); nx.double_edge_swap(R,nswap=3*R.number_of_edges(),max_tries=10**6,seed=s); Cn.append(nx.average_clustering(R))
    comms=nx.community.louvain_communities(G,seed=1)
    # people appearing in >=3 films this decade
    cnt=fp[fp.tconst.isin(fd.tconst)].nconst.value_counts()
    tf=TfidfVectorizer(stop_words="english",min_df=2).fit_transform(fd.overview.fillna(""))
    S=cosine_similarity(tf); sim=S[np.triu_indices_from(S,1)].mean()
    kw=TfidfVectorizer(token_pattern=r"[^|]+").fit_transform(fd.keywords.fillna(""))
    K=cosine_similarity(kw); ksim=K[np.triu_indices_from(K,1)].mean()
    rows.append(dict(decade=dec,people=G.number_of_nodes(),edges=G.number_of_edges(),
        mean_deg=deg.mean().round(2),giant=round(len(gc)/len(G),2),
        repeat_edges=round(np.mean([d["weight"]>1 for *_,d in G.edges(data=True)]),3),
        people_3plus=int((cnt>=3).sum()),
        clust=round(C,3),clust_null=round(np.mean(Cn),3),
        modularity=round(nx.community.modularity(G,comms),3),
        franchise=round(fd.collection.notna().mean(),2),
        plot_sim=round(sim,4),kw_sim=round(ksim,4),rating=round(fd.rating.mean(),2)))
print(pd.DataFrame(rows).to_string(index=False))
