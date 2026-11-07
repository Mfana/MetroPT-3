"""Tighten the Vieira and Basora citations after reading them on ScienceDirect. Run after patch_fulltext_ress.py."""
from pathlib import Path
p=Path("submission-ress/manuscript.tex");T=p.read_text()
R=[("Vieira et al.\\ \\cite{vieira2026} show that splitting bearing data by bearing rather than by record changes the conclusions, and Basora et al.\\ \\cite{basora2025} benchmark uncertainty quantification for deep prognostics on data rich enough to support it.",
"Vieira et al.\\ \\cite{vieira2026} keep a trained model fixed and show that test signals from bearings seen in training inflate its scores, and that the number of distinct training bearings is decisive. Basora et al.\\ \\cite{basora2025} benchmark uncertainty quantification for deep prognostics on 54 simulated turbofan units, enough to assess calibration, and still find no method strongly robust out of distribution."),
("as Basora et al.\\ \\cite{basora2025} do for prognostics at scale.","as Basora et al.\\ \\cite{basora2025} do on simulated engines."),
]
for a,b in R:
    assert T.count(a)==1,a
    T=T.replace(a,b)
p.write_text(T);print(len(R),"replacements")
