"""Step 17: figure for the robustness checks (results/robustness.tsv, step 16)."""
import pandas as pd
import matplotlib.pyplot as plt

r = pd.read_csv("results/robustness.tsv", sep="\t")
r["mid"] = r.period + r.span / 2
style = {"base_400": ("400 / decade (main)", "C0", "-", 2.6), "n_300": ("300 / decade", "C0", "--", 1.3),
         "n_200": ("200 / decade", "C0", ":", 1.3), "top3_actors": ("top-3 actors", "C2", "-", 1.3),
         "no_franchise": ("no franchise films (200)", "C3", "-", 1.8), "all_25k": ("all films ≥25k votes", "C7", "-", 1.3),
         "half_150": ("150 per 5 years", "C1", "-", 1.8)}
panels = [("repeat_edges", "Repeat collaborations", "share of ties on 2+ films", True),
          ("clust_excess", "Clustering above chance", "clustering − null", False),
          ("modularity_excess", "Community structure above chance", "modularity − null", False),
          ("returning_prev", "People from the previous period", "share of credits", True)]
fig, ax = plt.subplots(1, 4, figsize=(16, 4))
for a, (k, title, yl, pc) in zip(ax, panels):
    for v, (lab, c, ls, lw) in style.items():
        d = r[r.variant == v]
        a.plot(d.mid, d[k], ls, color=c, lw=lw, marker="o" if v in ("base_400", "half_150", "no_franchise") else None,
               ms=4, label=lab)
    a.set(title=title, ylabel=yl, xticks=[1980, 1990, 2000, 2010, 2020])
    if pc:
        a.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f"{y:.0%}"))
    a.axhline(0, color="grey", lw=.6)
ax[0].legend(fontsize=7.5, loc="upper left")
fig.text(.01, .01, "Each point = one period, plotted at its midpoint (decades, or 5-year windows for '150 per 5 years'). "
         "Null = people shuffled across films, 20 runs. 5-year windows give fewer chances to repeat, so compare that line with itself.",
         fontsize=7.5, color="grey")
fig.tight_layout(rect=(0, .04, 1, 1))
fig.savefig("results/robustness.png", dpi=200)
print("saved results/robustness.png")
