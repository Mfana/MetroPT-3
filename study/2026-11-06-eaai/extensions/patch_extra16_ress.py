"""Write addendum 3 into the RESS manuscript. Run after patch_literature_ress.py and extra16_tables.py."""
from pathlib import Path
p=Path("submission-ress/manuscript.tex");T=p.read_text()
R=[("These are not company reports, and we did not use them.","These are not company reports, so we did not train on them, and we test against them only as a sensitivity analysis."),
("A planned larger setting of M5 and M6, with 64 units and 2,000 steps,",
"\\emph{Further intervals.} After reading Toribio et al.\\ \\cite{toribio2026}, we tested saved scores against their twelve further intervals, under a plan dated before any comparison. Nothing was refitted, so every model had been trained with these intervals as normal time. They were treated like reports. False alarms were recounted with their warning, active and 24-hour recovery periods removed, and the frozen catch rule and shift control were applied in analysis A, with the other analyses as a secondary check. A combination needed catches with chance rates below 0.5 on 75\\% of the reports and intervals together, the share the warning rule sets, and had to meet the burden limit. The other rules were not recomputed, because the calibrators had been fitted under four reports.\n\nA planned larger setting of M5 and M6, with 64 units and 2,000 steps,"),
("M3, M5 and M6 for the registered and timing rows, and M5 and M6 at each seed for the further seeds.","M3, M5 and M6 for the registered and timing rows, M5 and M6 at each seed for the further seeds, and M1 to M6 for the further intervals, on the warning and burden rules only. In that row, failure tests are in analysis A and AUROC is for the warning windows."),
("\\subsection{Further checks}\n",
"\\emph{Further intervals.} Alarms rebuilt from saved scores reproduced every frozen count in all 250 cells. The twelve further intervals did not change the findings. In analysis A, 4 of 354 tests were caught, all by M3 before the 12 April interval, against about 7.1 expected from alarm rates alone. Across all analyses 11 of 685 were caught. None of 30 combinations reached the warning share. False alarms were not concentrated in these periods: the removed time held 5.8\\% of scored time and 2.3\\% of false alarms, or 1.2\\% and 1.6\\% without the recovery period. The same 19 of 20 combinations with an analysis E met the burden limit before and after the recount. During the intervals themselves, alarms fired in 35 of 360 cases. Median AUROC for the active periods at 1 hour was 0.81 for M1 and 0.97 for M5, but 0.32 for M6. Eleven of the twelve intervals coincide with a sustained loaded run, and 11 of the 26 runs away from reports fall on them, as do 3 of the 7 of at least 4 hours. This points to a loaded state, as M1 does, and does not validate the intervals as failures. It also does not show what a model trained on all 16 could do.\n\n\\subsection{Further checks}\n"),
("Report-free periods may contain unreported faults: we counted the twelve further intervals listed by Toribio et al.\\ \\cite{toribio2026} as normal time, in training and in false-alarm counts, so training labels may be noisy and false-alarm rates overstated. We did not test the results against those labels.",
"Report-free periods may contain unreported faults. Our test against the twelve further intervals used models trained with them as normal time, so training labels may be noisy, and a model trained on all 16 might behave differently. Those intervals are not company reports, and we have not verified how they were derived. They cannot lift the calibration gates unless they are confirmed as independent failures."),
("The clearest next step is independent failures.","The clearest next step is independent failures. An engineer's review of the twelve further intervals would settle whether a refit on all 16 is justified."),
]
for a,b in R:
    assert T.count(a)==1,a
    T=T.replace(a,b)
p.write_text(T)
q=Path("submission-ress/table-sensitivity.tex");S=q.read_text()
a="\\bottomrule\\end{tabular}"
assert S.count(a)==1
q.write_text(S.replace(a,"Twelve further intervals, saved scores & 354 & 4 & 0 of 30 & 0.43--0.54 & 0.30--0.53 & 0.58--0.63\\\\\n"+a))
print(len(R)+1,"replacements")
