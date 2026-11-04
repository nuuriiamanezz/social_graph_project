# Hollywood: A Closed Club?

DTU 02805 Social Graphs & Interactions, final project (Fall 2026).

**Question.** Over the last four decades, has Hollywood's collaboration network become more closed (more clustered, more repeat collaboration, more franchise-dominated), have its stories become more alike, and how does that relate to how audiences rate the films?

**Site:** https://nuuriiamanezz.github.io/social_graph_project/

## Data
- **IMDb non-commercial datasets** (`title.basics`, `title.ratings`, `title.principals`, `name.basics`) from https://datasets.imdbws.com/: films, ratings, cast & crew. Download into `data/raw/` (git-ignored).
- **TMDB API**: plot overviews, keywords, origin country (to define "Hollywood" = US origin). Token goes in `.env` as `TMDB_TOKEN=...` (git-ignored, never commit it).

Filter: US feature films, 1980–2024, ≥25k IMDb votes; nodes = director + top-4 billed actors.

## Layout
```
index.html, assets/   project site (GitHub Pages)
data/raw/             IMDb dumps (ignored)
data/processed/       filtered tables we commit (small)
src/                  scripts (filtering, TMDB fetch)
notebooks/            analysis
paper/                PNAS LaTeX export / figures
```

## Team
Nuria Máñez Molina (s234523) · Nour Marak (s234700) · Marah Osama Marak (s182946)
