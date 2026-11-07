"""Sensitivity table and onset figure data for the RESS manuscript, from tables/gaps-* only."""
import csv,statistics as st
from pathlib import Path
OUT=Path("submission-ress");n=float
R=lambda p:list(csv.DictReader(open(f"tables/{p}")))
P=R("primary-metrics.csv");S=R("seq-metrics.csv");SM=[r for r in R("gaps-seed-metrics.csv") if r["seed"]!="791"];SR=[r for r in R("gaps-seed-rules.csv") if r["seed"]!="791"];TM=R("gaps-shift-metrics.csv");TR=R("gaps-shift-rules.csv")
H=["30","60","180","360","720"]
def rng(rows,m):
    v=[st.median(n(r["auroc"]) for r in rows if r["kind"]=="A" and r["model"]==m and r["h"]==h) for h in H];return f"{min(v):.2f}--{max(v):.2f}"
seedrange=lambda m:(lambda v:f"{min(v):.2f}--{max(v):.2f}")([st.median(n(r["auroc"]) for r in SM if r["kind"]=="A" and r["model"]==m and r["h"]==h and r["seed"]==s) for s in("1791","2791","3791","4791") for h in H])
L=[r"\begin{tabular}{lrrrrrr}\toprule Analysis & Failure tests & Caught & Horizons meeting rules & \multicolumn{3}{c}{Median AUROC by horizon, analysis A}\\\cmidrule(lr){5-7} & & & & M3 & M5 & M6\\\midrule"]
L.append(f"Registered & {sum(int(r['failures']) for r in P+S)} & {sum(int(r['caught']) for r in P+S)} & 0 of 15 & {rng(P,'M3')} & {rng(S,'M5')} & {rng(S,'M6')}\\\\")
L.append(f"Four further seeds (M5, M6) & {sum(int(r['failures']) for r in SM)} & {sum(int(r['caught']) for r in SM)} & {sum(r['defensible']=='True' for r in SR)} of {len(SR)} & -- & {seedrange('M5')} & {seedrange('M6')}\\\\")
for d,lab in(("-60","Onsets 60 min earlier"),("60","Onsets 60 min later")):
    t=[r for r in TM if r["shift"]==d];q=[r for r in TR if r["shift"]==d]
    L.append(f"{lab} & {sum(int(r['failures']) for r in t)} & {sum(int(r['caught']) for r in t)} & {sum(r['defensible']=='True' for r in q)} of {len(q)} & {rng(t,'M3')} & {rng(t,'M5')} & {rng(t,'M6')}\\\\")
L.append(r"\bottomrule\end{tabular}");(OUT/"table-sensitivity.tex").write_text("\n".join(L)+"\n");print("\n".join(L))
O=R("gaps-onset-profile.csv")
for f in("apr18","may29","jun05","jul15"):
    with open(OUT/f"figure-data/fig3-{f}.csv","w",newline="") as x:
        w=csv.writer(x);w.writerow(["minutes","load"])
        for r in O:
            if r["failure"]==f and r["COMP"]!="": w.writerow([int(r["bin_start_min"])+7.5,round(1-n(r["COMP"]),4)])
