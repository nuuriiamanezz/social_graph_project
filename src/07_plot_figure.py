"""Step 7: figure for Act II from results/plot_similarity.tsv (step 6)."""
import pandas as pd
import matplotlib.pyplot as plt

res = pd.read_csv("results/plot_similarity.tsv", sep="\t")
fig, ax = plt.subplots(1, 2, figsize=(10, 3.8))
for name, r in res.groupby("method"):
    b = r.sim_all.iloc[0]  # methods have different scales -> relative to the 1980s
    ax[0].errorbar(r.decade, r.sim_all / b, yerr=[(r.sim_all - r.sim_all_lo) / b, (r.sim_all_hi - r.sim_all) / b],
                   marker="o", capsize=3, label=f"{name}, all films")
    ax[0].plot(r.decade, r.sim_nonfranchise / r.sim_nonfranchise.iloc[0], "--", marker=".",
               label=f"{name}, no franchise films")
    ax[1].errorbar(r.decade, r.gap, yerr=[r.gap - r.gap_lo, r.gap_hi - r.gap], marker="o", capsize=3, label=name)
    ax[1].fill_between(r.decade, r.gap_null - 2 * r.gap_null_sd, r.gap_null + 2 * r.gap_null_sd, alpha=.15)

ax[0].axhline(1, color="grey", lw=.8)
ax[0].set(xlabel="decade", ylabel="mean plot similarity (1980s = 1)", title="Are plots converging?")
ax[1].axhline(0, color="grey", lw=.8)
ax[1].set(xlabel="decade", ylabel="similarity gap: shared people - none",
          title="Do the same people tell the same stories?")
ax[0].legend(fontsize=8); ax[1].legend(fontsize=8)
fig.text(.01, .01, "error bars: 95% bootstrap over films; shaded: null (plots shuffled), mean ± 2 sd. "
         "2020s = 2020-2024 only.", fontsize=7, color="grey")
fig.tight_layout(rect=(0, .04, 1, 1))
fig.savefig("results/plot_similarity.png", dpi=200)
print("saved results/plot_similarity.png")
