"""Step 11: figure for Act III from step 10's results."""
import numpy as np, pandas as pd
import matplotlib.pyplot as plt

types = pd.read_csv("results/ratings_by_type.tsv", sep="\t")
coefs = pd.read_csv("results/ratings_models.tsv", sep="\t")
dirs = pd.read_csv("results/director_betweenness.tsv", sep="\t").query("films >= 2")
dsum = pd.read_csv("results/director_summary.tsv", sep="\t").set_index("decade")

fig, ax = plt.subplots(1, 3, figsize=(14, 3.9), gridspec_kw=dict(width_ratios=[1.2, 1, 1]))

# a) mean rating per film type and decade
style = {"tight circle": ("C3", -2.5), "other": ("grey", 0), "bridge": ("C0", 2.5)}
for ty, (c, dx) in style.items():
    r = types[types.type == ty]
    ax[0].errorbar(r.decade + dx, r.rating, yerr=[r.rating - r.lo, r.hi - r.rating], fmt="o-", color=c,
                   capsize=3, label=ty)
ax[0].set(title="Ratings by type of film", xlabel="decade", ylabel="mean IMDb rating")
ax[0].legend(fontsize=8)

# b) coefficients with 95% CI, and the shuffled-ratings null (±2 sd around 0)
lab = {"prior_ties": "prior ties\n(0 → 1)", "n_comms": "communities\nspanned (+1)", "franchise": "franchise"}
mods = {"main": ("C0", -.2), "with_votes": ("C1", 0), "non_franchise": ("C2", .2)}
terms = list(lab)
for m, (c, dy) in mods.items():
    r = coefs[coefs.model == m].set_index("term").reindex(terms)
    y = np.arange(len(terms)) + dy
    ax[1].errorbar(r.coef, y, xerr=[r.coef - r.ci_lo, r.ci_hi - r.coef], fmt="o", color=c, capsize=3,
                   label=m.replace("_", " "))
    ax[1].barh(y, 4 * r.null_sd, left=-2 * r.null_sd, height=.15, color=c, alpha=.15)
ax[1].axvline(0, color="grey", lw=.8)
ax[1].set_yticks(range(len(terms)), [lab[t] for t in terms])
ax[1].invert_yaxis()
ax[1].set(title="Effect on rating (controls: decade, genre)", xlabel="change in rating")
ax[1].legend(fontsize=8, loc="lower right")

# c) directors
for dec, g in dirs.groupby("decade"):
    ax[2].scatter(g.betweenness, g.rating, s=8, alpha=.5, label=f"{dec}s  ρ={dsum.loc[str(dec), 'rho']:.2f}")
ax[2].set_xscale("log")
ax[2].set(title=f"Directors with 2+ films: brokerage vs. ratings\n(ρ={dsum.loc['all', 'rho']:.2f}, perm. p={dsum.loc['all', 'p_perm']:.2f})",
          xlabel="betweenness in decade network", ylabel="mean rating of their films")
ax[2].legend(fontsize=7, markerscale=2)

fig.text(.01, .01, "a, b: 95% CI (bootstrap over films / robust OLS). b: shaded = ratings shuffled within decade, "
         "±2 sd (1000 runs). Tight circle = some people pairs had worked together before, ≤2 communities; "
         "bridge = 3+ communities, no prior ties.", fontsize=7, color="grey")
fig.tight_layout(rect=(0, .04, 1, 1))
fig.savefig("results/ratings.png", dpi=200)
print("saved results/ratings.png")
