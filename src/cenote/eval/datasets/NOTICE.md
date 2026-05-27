# Dataset Attributions

## MIRACL subsamples (`miracl_es_subset.jsonl`, `miracl_en_subset.jsonl`)

These files contain up to ~5000 passages each, subsampled from the MIRACL corpus,
plus up to ~200 development queries with relevance judgments.

- **Source corpus**: <https://github.com/project-miracl/miracl>
- **Code license**: Apache 2.0 (we used `miracl/miracl-corpus` and `miracl/miracl` HF datasets)
- **Content license**: passages are Wikipedia-derived and are distributed
  under **CC-BY-SA 3.0** (<https://creativecommons.org/licenses/by-sa/3.0/>).
- **Citation**:

```text
@article{miracl,
    author = {Xinyu Zhang and Nandan Thakur and Odunayo Ogundepo and Ehsan Kamalloo and David Alfonso-Hermelo and Xiaoguang Li and Qun Liu and Mehdi Rezagholizadeh and Jimmy Lin},
    title = {{MIRACL}: A Multilingual Retrieval Dataset Covering 18 Diverse Languages},
    journal = {Transactions of the Association for Computational Linguistics},
    year = {2023}
}
```

By including these files, this distribution complies with CC-BY-SA 3.0
attribution requirements. Redistribution must preserve this NOTICE.

## `cenote_mini_es.jsonl`

Original content authored by the cenote-core maintainers. Released under
Apache 2.0 along with the rest of the codebase.
