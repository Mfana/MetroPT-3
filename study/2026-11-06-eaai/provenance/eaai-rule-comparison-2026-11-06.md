# EAAI rule comparison, retrieved 2026-11-06

Source: ScienceDirect, *Engineering Applications of Artificial Intelligence*, "Guide for authors", read in the author's Chrome session via institutional access. Direct fetch and the built-in browser returned HTTP 403. About the first 50,000 of 62,220 characters were read, so the end of the References section, the submission checklist and post-decision sections are NOT verified.

| Rule | Current guide | Package baseline (`references/journal.md`, `audit.py`) | Resolution |
|---|---|---|---|
| Scope | Must report novel aspects of AI for a real-world engineering application, validated on public data | Same intent | **Critical gate**: see novelty gate |
| Desk rejection | Abstract must state AI contribution and engineering application; no undefined acronyms in title or abstract; single-column; metaphor-based metaheuristics rarely accepted | Abstract labels and single column checked | Add: define every acronym in title and abstract. "MetroPT-3" is a dataset name and must be introduced as such |
| Length and size | At most 50 pages; manuscript under 100 MB, or desk rejection | 50 pages; 100,000,000 bytes combined | Keep stricter combined limit |
| Article types | Original Research; Survey/Tutorial; Case Studies/Software Reviews; IFAC EAAI Forum short communications, which include critiques of a claim in the literature | Not considered | **New route** for an evidence-limited paper |
| Review | Double anonymized; title page and anonymized manuscript are separate files | Same | Same |
| Abstract | At most 250 words | Same | Same |
| Keywords | 1 to 6, English, avoid "and"/"of" | 1 to 6 | Add wording check |
| Highlights | Encouraged, 3 to 5, at most 85 characters, editable file with "highlights" in its name | Same | Same |
| Generative AI | Declaration in a new section **at the end of the manuscript, before references**, using the guide's title and wording. Figures: data plots derived reproducibly are allowed; disclose in each caption if AI tools created the image | `audit.py` looks for it on the title page | **Conflict**: guide wins. Put the statement in the manuscript; keep the title-page label only to satisfy the audit, and record this |
| Acknowledgments | Title page only | Title page | Same |
| Competing interests | Declarations tool always completed; Word file uploaded | Title page | Add declarations-tool step for the author |
| Funding | Standard sentence if none | Title page | Author to confirm |
| CRediT | Required from corresponding author | Required | Author to confirm |
| Figures | Separate files; vector EPS/PDF with embedded fonts; caption for each | Vector where suitable | Supply separate PDF figures |
| Tables | Editable, no vertical rules or shading | Editable | Booktabs only |
| Research data | Option C: deposit in a repository and cite, or state why not; data statement required | Apply current policy | Deposit derived outputs; cite UCI DOI |
| Other | SI units; up to 6 Inspec codes; math as editable text; conference-overlap note in cover letter | Not listed | Add Inspec codes at submission |
| References | Any consistent style; every reference must be real; DOIs where available | Verify metadata | Same |
| Graphical abstract | Encouraged, optional | Not listed | Optional |

## Scope consequence

EAAI's scope sentence requires novel aspects of AI. An evaluation protocol or a new split alone does not obviously meet that sentence, and the package's protocol says the same. The IFAC EAAI Forum and Case Studies article types are the plausible routes if the verified contribution is evaluative rather than algorithmic.
