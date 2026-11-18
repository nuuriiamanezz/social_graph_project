"""Step 19: figure for gender on screen (results/gender.tsv, gender_words.tsv from step 18)."""
import numpy as np, pandas as pd
import matplotlib.pyplot as plt

r = pd.read_csv("results/gender.tsv", sep="\t")
w = pd.read_csv("results/gender_words.tsv", sep="\t")
x = r.decade
pct = plt.FuncFormatter(lambda y, _: f"{y:.0%}")
fig, ax = plt.subplots(1, 4, figsize=(17, 4.2), gridspec_kw=dict(width_ratios=[1, 1, 1, 1.15]))

# a) how much of the screen
a = ax[0]
a.plot(x, r.women_credits, "o-", color="C3", label="cast credits held by women")
a.plot(x, r.women_leads, "o-", color="C1", label="lead roles (first-billed)")
a.plot(x, r.she_share, "s--", color="C4", label="she/her among plot pronouns")
a.plot(x, r.she_share_mled, "s:", color="C4", alpha=.7, label="… in plots of male-led films")
a.axhline(.5, color="grey", lw=.7, ls="--")
a.set(title="Women on screen", xlabel="decade", ylim=(0, .6))
a.yaxis.set_major_formatter(pct); a.legend(fontsize=7.5, loc="upper left")

# b) in the closed club?
a = ax[1]
a.plot(x, r.repeat_m, "o-", color="C0", label="men: ties that repeat")
a.plot(x, r.repeat_w, "o--", color="C3", label="women: ties that repeat")
a2 = a.twinx()
a2.plot(x, r.next_m, "s-", color="C0", alpha=.45, label="men: back next decade")
a2.plot(x, r.next_w, "s--", color="C3", alpha=.45, label="women: back next decade")
a.set(title="Inside the closed club?", xlabel="decade", ylabel="share of their ties on 2+ films")
a2.set_ylabel("share in the next decade too", color="grey")
a.yaxis.set_major_formatter(pct); a2.yaxis.set_major_formatter(pct)
h1, l1 = a.get_legend_handles_labels(); h2, l2 = a2.get_legend_handles_labels()
a.legend(h1 + h2, l1 + l2, fontsize=7.5, loc="upper left")

# c) centrality gap
a = ax[2]
for k, c, lab in [("bet_gap", "C3", "raw"), ("bet_gap_ctrl", "C2", "same number of films")]:
    a.fill_between(x, -2 * r[k + "_null_sd"], 2 * r[k + "_null_sd"], color=c, alpha=.12)
    a.plot(x, r[k], "o-", color=c, label=lab)
    for xi, yi, p in zip(x, r[k], r[k + "_p"]):
        if p < 0.05:
            a.annotate("*", (xi, yi), xytext=(4, -10), textcoords="offset points", color=c, fontsize=13)
a.axhline(0, color="grey", lw=.8)
a.set(title="Are women less central?", xlabel="decade", ylabel="women − men, betweenness percentile")
a.legend(fontsize=7.5, title="comparison", title_fontsize=7.5)

# d) distinctive words
a = ax[3]
n = 12
top = pd.concat([w.head(n), w.tail(n)])
cols = ["C0" if z < 0 else "C3" for z in top.z]
a.barh(range(len(top)), top.z, color=cols)
a.set_yticks(range(len(top)), top.word, fontsize=8)
a.axvline(0, color="grey", lw=.8)
a.set(title="Words in plots: male-led ◀ ▶ female-led", xlabel="log-odds z-score")

fig.text(.01, .01, "Gender = IMDb's actor/actress label (cast only; binary, directors not covered). "
         "c: shaded = gender shuffled, ± 2 sd (500 runs); * = permutation p < 0.05. d: character names removed, pronouns left out. "
         "2020s = 2020-2024.", fontsize=7.5, color="grey")
fig.tight_layout(rect=(0, .04, 1, 1))
fig.savefig("results/gender.png", dpi=200)
print("saved results/gender.png")
