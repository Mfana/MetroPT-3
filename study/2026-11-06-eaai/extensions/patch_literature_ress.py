"""Apply the full-text reading of Guha, Teng and Toribio (2026-11-07) to the RESS manuscript. Run after build_gaps_ress.py."""
from pathlib import Path
p=Path("submission-ress/manuscript.tex");T=p.read_text()
R=[("Their headline figures are computed on the first 2,000 holdout windows, and they also report longer streams and note that precision falls as the stream grows.",
"Their headline figures are computed on the first 2,000 holdout windows, about 36\\% of which are warning windows. They state that the holdout has one failure, so recall stays fixed as the stream lengthens while precision falls, from 0.89 to 0.70 at 30,000 windows."),
("which is a different question from warning before onset. Toribio et al.\\ \\cite{toribio2026} forecast at 1, 3 and 6 hours and then apply anomaly detectors.",
"which is a different question from warning before onset. Their Transformer-style detector found all four reports in all five seeds, with median first-hit delays of at most 4.1 minutes. Toribio et al.\\ \\cite{toribio2026} forecast the signals at 1, 3 and 6 hours and apply anomaly detectors to the forecasts, scoring timestamps rather than events. Their best detector, XGBOD, reaches an F1 of 0.86 at 6 hours, and the other eleven stay below 0.35 at that horizon. They evaluate against 16 intervals: the four company reports and twelve they attribute to Davari et al.\\ \\cite{davari2021}."),
("as far as stated in the portions read.}","as far as each paper states.}"),
("Teng and Gao \\cite{teng2026} & Normal-only detection & First month to fit & All later & None & Thresholds only\\\\\n",
"Teng and Gao \\cite{teng2026} & Normal-only detection & First month to fit & 4 & None & Thresholds only\\\\\nToribio et al.\\ \\cite{toribio2026} & Forecast, then detection & Sequential, 60/40 detectors & Not stated (16 labelled) & 1, 3, 6 h & None\\\\\n"),
("where each failure is a single independent event and four are all that exist,","where each reported failure is a single event and the operator reports only four,"),
("The operator reports four air leaks, on 18 April, 29 May, 5 June and 15 July.","The operator reports four air leaks, on 18 April, 29 May, 5 June and 15 July. Toribio et al.\\ \\cite{toribio2026} list twelve further air-leak intervals, which they attribute to Davari et al.\\ \\cite{davari2021}. These are not company reports, and we did not use them."),
("A positive label that reaches into the failure therefore measures detection, however it is described.","A positive label that reaches into the failure therefore measures detection, however it is described. The delays of about four minutes reported by Teng and Gao \\cite{teng2026} point the same way."),
("Report-free periods may contain unreported faults.","Report-free periods may contain unreported faults: we counted the twelve further intervals listed by Toribio et al.\\ \\cite{toribio2026} as normal time, in training and in false-alarm counts, so training labels may be noisy and false-alarm rates overstated. We did not test the results against those labels."),
]
for a,b in R:
    assert T.count(a)==1,a
    T=T.replace(a,b)
p.write_text(T);print(len(R),"replacements")
