#!/usr/bin/env bash
# Step 0: stream the big IMDb dumps down to films 1980-2024 with >=10k votes
# (+ their actors/directors). Run from project/. Takes ~30 s.
set -e
mkdir -p data/interim
zcat < data/raw/title.ratings.tsv.gz | awk -F'\t' 'NR==1 || $3>=10000' > data/interim/ratings_10k.tsv
zcat < data/raw/title.basics.tsv.gz | awk -F'\t' 'NR==FNR{if(FNR>1) r[$1]=1; next} FNR==1 || (($1 in r) && $2=="movie" && $6>=1980 && $6<=2024)' data/interim/ratings_10k.tsv - > data/interim/basics_10k.tsv
zcat < data/raw/title.principals.tsv.gz | awk -F'\t' 'NR==FNR{if(FNR>1) m[$1]=1; next} FNR==1 || (($1 in m) && ($4=="actor"||$4=="actress"||$4=="director"))' data/interim/basics_10k.tsv - > data/interim/principals_10k.tsv
wc -l data/interim/*.tsv
