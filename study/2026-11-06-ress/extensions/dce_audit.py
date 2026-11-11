"""Check the Data-Centric Engineering submission against the journal's stated requirements (read 2026-11-11)."""
import json, re, sys
from pathlib import Path

d = Path(sys.argv[1] if len(sys.argv) > 1 else "submission-dce")
t = (d / "manuscript.tex").read_text()
words = lambda s: len(re.sub(r"\\[a-zA-Z]+\{|[{}]|\\~", "", s).split())
abstract = t[t.index("\\begin{abstract}") + 16:t.index("\\end{abstract}")]
impact = re.search(r"Impact Statement\}\\par\\noindent (.*?)\\par", t, re.S).group(1)
keywords = re.search(r"\\textbf\{Keywords:\} (.*)", t).group(1).split(";")
issues = []
if words(abstract) > 250: issues.append("Abstract over 250 words")
if words(impact) != 120: issues.append(f"Impact Statement is {words(impact)} words, not 120")
if len(keywords) > 5: issues.append("More than five keywords")
for s in ("Abbreviations", "Funding statement", "Competing interests", "Data availability statement", "Acknowledgements"):
    if f"\\section*{{{s}}}" not in t: issues.append(f"Missing section: {s}")
for bad in ("CRediT", "REPLACE", "Reliability Engineering \\& System Safety", "Highlights"):
    if bad in t: issues.append(f"Leftover: {bad}")
if "Claude Code" not in t[:t.index("\\section*{Abbreviations}")]: issues.append("AI use not declared in Methods")
if "Claude Opus 5.5" not in t[t.index("\\section*{Acknowledgements}"):]: issues.append("AI text use not declared in Acknowledgements")
for f in ("Figure_1.pdf", "Figure_2.pdf", "Figure_3.pdf", "alt-text.txt", "cover-letter.txt", "manuscript.pdf"):
    if not (d / f).exists(): issues.append(f"Missing file: {f}")
alt = (d / "alt-text.txt").read_text() if (d / "alt-text.txt").exists() else ""
for k in ("Figure 1", "Figure 2", "Figure 3"):
    if k not in alt: issues.append(f"No alt text for {k}")
if not (d / "author-signoff.txt").exists(): issues.append("Human author sign-off not recorded")
out = {"abstract_words": words(abstract), "impact_words": words(impact), "keywords": len(keywords), "issues": issues,
       "status": "ready" if not issues else "blocked"}
(d / "audit-dce.json").write_text(json.dumps(out, indent=1))
print(json.dumps(out, indent=1))
