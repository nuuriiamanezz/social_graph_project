"""Step 9: figure for Act I from results/network_closure.tsv (step 8)."""
import pandas as pd
import matplotlib.pyplot as plt

r = pd.read_csv("results/network_closure.tsv", sep="\t")
x = r.decade
fig, ax = plt.subplots(1, 4, figsize=(14, 3.6))

for a, k, title in [(ax[0], "clust", "Clustering above chance"),
                    (ax[1], "repeat_edges", "Repeat collaborations"),
                    (ax[2], "modularity", "Community structure")]:
    a.plot(x, r[k], "o-", label="observed")
    a.plot(x, r[f"{k}_null"], "s--", color="grey", label="null (bipartite shuffle)")
    a.fill_between(x, r[f"{k}_null"] - 2 * r[f"{k}_null_sd"], r[f"{k}_null"] + 2 * r[f"{k}_null_sd"],
                   color="grey", alpha=.2)
    a.set(title=title, xlabel="decade")
ax[0].set_ylabel("average clustering")
ax[1].set_ylabel("share of ties on 2+ films")
ax[2].set_ylabel("Louvain modularity")
ax[0].legend(fontsize=8)

ax[3].plot(x, r.returning_prev, "o-", label="people from previous decade")
ax[3].plot(x, r.hub_share, "o-", label="top 5% people")
ax[3].plot(x, r.franchise, "o-", label="franchise films")
ax[3].set(title="Who gets the work", xlabel="decade", ylabel="share of credits / films", ylim=(0, .7))
ax[3].legend(fontsize=8)

fig.text(.01, .01, "400 most-voted US films per decade; nodes = director + top-4 actors. "
         "Shaded: null mean ± 2 sd (50 runs). 2020s = 2020-2024 only, so fewer chances to repeat.",
         fontsize=7, color="grey")
fig.tight_layout(rect=(0, .04, 1, 1))
fig.savefig("results/network_closure.png", dpi=200)
print("saved results/network_closure.png")
