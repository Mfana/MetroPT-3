"""Build the Data-Centric Engineering version from the RESS manuscript. Results and numbers are unchanged.
Run from the study folder: python extensions/build_dce.py"""
import re, shutil
from pathlib import Path

SRC, OUT = Path("submission-ress"), Path("submission-dce")
OUT.mkdir(exist_ok=True)
for f in ["references.bib", "Figure_1.pdf", "Figure_2.pdf", "Figure_3.pdf"] + [p.name for p in SRC.glob("table-*.tex")]:
    shutil.copy(SRC / f, OUT / f)
t = (SRC / "manuscript.tex").read_text()

title = re.search(r"\\title\{(.*?)\}\n", t).group(1)
abstract = t[t.index("\\begin{abstract}") + len("\\begin{abstract}"):t.index("\\end{abstract}")].strip()
body = t[t.index("\\section{Introduction}"):t.index("\\section*{CRediT")]
data = re.search(r"\\section\*\{Data availability\}\n(.*?)\n\n", t, re.S).group(1).strip()
data = re.sub(r"commit [0-9a-f]{7}", "commit "+__import__("os").environ.get("DCE_COMMIT","7fd871e"), data)
thanks = re.search(r"\\section\*\{Acknowledgements\}\n(.*?)\n\n", t, re.S).group(1).strip()

IMPACT = ("Machine-learning models for predictive maintenance often look highly accurate on public benchmarks, but that accuracy can "
          "come from how the data are split rather than from any ability to warn of a new failure. On a public metro compressor "
          "dataset with only four reported failures, we held out each failure in turn. No model gave a timely alarm before any of the four failures, although the "
          "same models scored almost perfectly on a random split and once labels reached into the failure. The study gives "
          "engineers and data scientists a test for such claims: hold out whole failures, compare against operating "
          "state and chance, count the alerts a maintainer would receive, and state how many independent failures support the result.")
KEYWORDS = "predictive maintenance; model validation; early warning; probability calibration; rare failures"

# Opening paragraph aimed at data-science readers; the rest of the introduction is unchanged.
OPEN = ("Data-driven condition monitoring now supplies much of the evidence for predictive maintenance, and the value of that "
        "evidence depends on how models are evaluated as much as on how they are built. A benchmark with millions of records "
        "can still hold only a handful of independent failures, and an evaluation that ignores this can report skill that does "
        "not exist. This paper examines that problem on a widely used public dataset and offers a set of checks that any "
        "data-centric study of rare failures can apply.\n\n")
body = body.replace("\\section{Introduction}\n", "\\section{Introduction}\n" + OPEN, 1)

# Define abbreviations at first use in the main text.
for a, b in [("M5 is an LSTM \\cite{hochreiter1997}", "M5 is a long short-term memory (LSTM) network \\cite{hochreiter1997}"),
             ("and M6 is a temporal convolutional network \\cite{bai2018}", "and M6 is a temporal convolutional network (TCN) \\cite{bai2018}"),
             ("\\subsection{Implications for reliability evaluation}", "\\subsection{Implications for evaluating condition-monitoring models}")]:
    assert body.count(a) == 1, a
    body = body.replace(a, b)
first_auroc = body.index("AUROC")
defn = body.index("(AUROC)")
assert defn <= first_auroc + 10, "AUROC is used before it is defined"

# AI use: data and code use in Methods, text use in Acknowledgements, as the journal asks.
AI_METHODS = (" The analysis code used to run the experiments was developed with Claude Opus 5.5 (Anthropic). The author reviewed "
              "the code and outputs, and every reported number was recomputed from saved outputs by a script that checks it against the text.")
anchor = "A tie-handling error in rank metrics was found after results were first viewed and corrected from saved scores, without changing any score, threshold or alarm."
assert body.count(anchor) == 1
body = body.replace(anchor, anchor + AI_METHODS)
AI_TEXT = ("During the preparation of this work the author used Claude Opus 5.5 (Anthropic) to develop the analysis code that was "
           "used to run the experiments, and draft the manuscript. After using this tool, the author reviewed and edited the content "
           "as needed and takes full responsibility for the content of the published article.")

ABBREV = [("AP", "average precision"), ("AUROC", "area under the receiver operating characteristic curve"), ("BSS", "Brier skill score"),
          ("FA", "false alarms"), ("LSTM", "long short-term memory"), ("M0 to M6", "the seven models compared (Table 2)"),
          ("TCN", "temporal convolutional network"), ("UCI", "University of California, Irvine (Machine Learning Repository)")]

head = r"""\documentclass[11pt]{article}
\usepackage[a4paper,margin=2.5cm]{geometry}
\usepackage{amsmath,booktabs,graphicx,lineno}
\usepackage[T1]{fontenc}
\usepackage[numbers,sort&compress]{natbib}
\usepackage{xurl}
\usepackage[hidelinks]{hyperref}
\linenumbers
\begin{document}
\begin{center}
{\Large\bfseries TITLE\par}
\vspace{1em}
Mfanasibili Ngwenya\textsuperscript{*}\par
\vspace{0.5em}
{\small Graduate School of Business Leadership, University of South Africa, Cnr Janadel and Alexandra Ave, Midrand, 1686, South Africa\par
\textsuperscript{*}Corresponding author. Email: \href{mailto:engwenm@unisa.ac.za}{engwenm@unisa.ac.za}\par}
\end{center}
\begin{abstract}
ABSTRACT
\end{abstract}
\noindent\textbf{Impact Statement}\par\noindent IMPACT\par
\medskip\noindent\textbf{Keywords:} KEYWORDS
"""
head = head.replace("TITLE", title).replace("ABSTRACT", abstract).replace("IMPACT", IMPACT).replace("KEYWORDS", KEYWORDS)
tail = ("\\section*{Abbreviations}\n\\begin{tabular}{@{}lp{0.75\\linewidth}@{}}\n" + "".join(f"{a} & {b}\\\\\n" for a, b in ABBREV) + "\\end{tabular}\n\n"
        "\\section*{Acknowledgements}\n" + thanks + " " + AI_TEXT + "\n\n"
        "\\section*{Funding statement}\nThis work received no specific grant from any funding agency, commercial or not-for-profit sectors.\n\n"
        "\\section*{Competing interests}\nThe author declares none.\n\n"
        "\\section*{Data availability statement}\n" + data + "\n\n"
        "\\bibliographystyle{elsarticle-num}\n\\bibliography{references}\n\\end{document}\n")
(OUT / "manuscript.tex").write_text(head + body + tail)

n = lambda s: len(re.findall(r"[A-Za-z0-9][A-Za-z0-9'\-–,.%]*", re.sub(r"\\[a-zA-Z]+\{|[{}]|\\~", "", s)))
print("abstract words", n(abstract), "impact words", n(IMPACT), "keywords", len(KEYWORDS.split(";")))
