"""Step 5: remove character names from the TMDB overviews (spaCy NER).

Otherwise "Tony Stark" alone makes every Iron Man film look alike.
spaCy often finds "Marty McFly" once but misses the later "Marty", so every
name word it finds is removed everywhere in that overview.
Run from project/:  python3 src/05_clean_overviews.py
(pip install spacy && python -m spacy download en_core_web_sm)
"""
import os, re
import pandas as pd
import spacy

films = pd.read_csv("data/processed/films.tsv", sep="\t")
nlp = spacy.load("en_core_web_sm", disable=["parser", "lemmatizer"])

out = []
for doc in nlp.pipe(films.overview.fillna(""), batch_size=64):
    names = {w for e in doc.ents if e.label_ == "PERSON"
             for w in e.text.split() if w[:1].isupper() and len(w) > 1}
    txt = doc.text
    for w in sorted(names, key=len, reverse=True):
        txt = re.sub(r"\b" + re.escape(w) + r"('s)?\b", "", txt)
    out.append(" ".join(txt.split()))

films["text"] = out
os.makedirs("data/interim", exist_ok=True)
films[["tconst", "text"]].to_csv("data/interim/overviews_no_names.tsv", sep="\t", index=False)
changed = (films.text != films.overview.fillna("").str.split().str.join(" ")).sum()
print(f"names removed in {changed} of {len(films)} overviews")
print(films.loc[films.title_imdb == "Iron Man", ["overview", "text"]].T.to_string(header=False))
