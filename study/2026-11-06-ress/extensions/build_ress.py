"""Tables and figure data for the RESS manuscript, from frozen outputs only."""
import csv,statistics as st
from pathlib import Path
OUT=Path("submission-ress")
P=list(csv.DictReader(open("tables/primary-metrics.csv")));S=list(csv.DictReader(open("tables/seq-metrics.csv")))
RC=list(csv.DictReader(open("tables/exploratory-rank-chance.csv")));RO=list(csv.DictReader(open("tables/rule-outcomes.csv")));SR=list(csv.DictReader(open("tables/seq-rule-outcomes.csv")))
ALL=P+S
H=["30","60","180","360","720"];LAB=dict(zip(H,("30 min","1 h","3 h","6 h","12 h")));F=["apr18","may29","jun05","jul15"];FN=dict(zip(F,("18 Apr","29 May","5 Jun","15 Jul")))
n=float
def c(fold,h,m): return next(r for r in ALL if r["fold"]==fold and r["h"]==h and r["model"]==m)
def ch(fold,h,m): return next(r for r in RC if r["fold"]==fold and r["h"]==h and r["model"]==m)
# Slope rule for M3 counted the same way as M5 and M6.
m3slope={h:sum(n(c(f"A_hold{f}",h,"M3")["platt_b"])>0 and c(f"A_hold{f}",h,"M3")["slope_platt"] not in("","None") and .7<=n(c(f"A_hold{f}",h,"M3")["slope_platt"])<=1.3 for f in F) for h in H};print("M3 slope in range",m3slope)
print("Max Platt b, A:",{m:round(max(n(r["platt_b"]) for r in ALL if r["kind"]=="A" and r["model"]==m),4) for m in("M1","M2","M3","M4","M5","M6")})
print("max bss_platt A",{m:round(max(n(r["bss_platt"]) for r in ALL if r["kind"]=="A" and r["model"]==m),5) for m in("M1","M2","M3","M4","M5","M6")})
L=[r"\begin{tabular}{llrrrrrrr}\toprule Model & Horizon & Skill $>0$ & Beats M1 & Slope in range & Caught & FA/day, median & FA/day, after 16 Jul & Rules met\\\midrule"]
for lab,r in zip(LAB.values(),RO):
    met=sum(r[k]=="True" for k in("pass_base","pass_state","pass_slope","pass_warning","pass_burden","pass_explain"))
    h=[k for k,v in LAB.items() if v==lab][0]
    L.append(f"{'M3' if h=='30' else ''} & {lab} & {r['platt_bss_positive_of_4']}/4 & {r['m3_beats_m1_of_4']}/4 & {m3slope[h]}/4 & {r['caught_of_4']}/4 & {n(r['fa_median']):.2f} & {n(r['fa_after_jul16']):.2f} & {met}/6\\\\")
L.append(r"\midrule")
for r in SR:
    L.append(f"{r['model'] if r['horizon']=='30 min' else ''} & {r['horizon']} & {r['bss_platt_pos_of_4']}/4 & {r['beats_m1_of_4']}/4 & {r['slope_in_range_of_4']}/4 & {r['caught_of_4']}/4 & {n(r['fa_median']):.2f} & {n(r['fa_after_jul16']):.2f} & {r['rules_met_of_5']}/5\\\\")
    if r["model"]=="M5" and r["horizon"]=="12 h": L.append(r"\midrule")
L.append(r"\bottomrule\end{tabular}");(OUT/"table-rules.tex").write_text("\n".join(L)+"\n")
L=[r"\begin{tabular}{l*{12}{r}}\toprule & \multicolumn{4}{c}{M3, gradient boosting} & \multicolumn{4}{c}{M5, LSTM} & \multicolumn{4}{c}{M6, TCN}\\\cmidrule(lr){2-5}\cmidrule(lr){6-9}\cmidrule(lr){10-13} Horizon"+" & 18 Apr & 29 May & 5 Jun & 15 Jul"*3+r"\\\midrule"]
for h in H:
    L.append(LAB[h]+"".join(f" & {n(c(f'A_hold{f}',h,m)['auroc']):.2f}" for m in("M3","M5","M6") for f in F)+r"\\")
L.append(r"\bottomrule\end{tabular}");(OUT/"table-auroc.tex").write_text("\n".join(L)+"\n")
L=[r"\begin{tabular}{l*{4}{r}*{4}{r}}\toprule & \multicolumn{4}{c}{M5, LSTM} & \multicolumn{4}{c}{M6, TCN}\\\cmidrule(lr){2-5}\cmidrule(lr){6-9} Horizon"+r" & 29 May alone & 95th pct.\ shifted & Share $\geq$ observed & 29 May + 5 Jun"*2+r"\\\midrule"]
for h in H:
    row=LAB[h]
    for m in("M5","M6"):
        a=ch("A_holdmay29",h,m);b=ch("B_hold_may29_jun05",h,m)
        row+=f" & {n(a['auroc']):.2f} & {n(a['shift_p95']):.2f} & {n(a['share_at_least_observed']):.2f} & {n(b['auroc']):.2f}"
    L.append(row+r"\\")
L.append(r"\bottomrule\end{tabular}");(OUT/"table-may29.tex").write_text("\n".join(L)+"\n")
(OUT/"table-direction.tex").write_text(Path("tables/table-direction.tex").read_text())
# Figure 1: same split contrast for M3 and M5.
rand3={r["h"]:r for r in csv.DictReader(open("tables/exploratory-random-split.csv"))}
rand5={r["h"]:r for r in csv.DictReader(open("tables/exploratory-seq-random-split.csv"))}
fd=OUT/"figure-data";fd.mkdir(exist_ok=True)
for m,rand in(("M3",rand3),("M5",rand5)):
    with open(fd/f"fig1-{m}.csv","w",newline="") as x:
        w=csv.writer(x);w.writerow(["pos",*F,"random"])
        for i,h in enumerate(H): w.writerow([i,*[c(f"A_hold{f}",h,m)["auroc"] for f in F],rand[h]["auroc"]])
for m in("M5","M6"):
    for f in F:
        with open(fd/f"fig2-{m}-{f}.csv","w",newline="") as x:
            w=csv.writer(x);w.writerow(["pos","auroc","p05","p95"])
            for i,h in enumerate(H):
                r=ch(f"A_hold{f}",h,m);w.writerow([i,r["auroc"],r["shift_p05"],r["shift_p95"]])
A=[r for r in RC if r["fold"].startswith("A_")]
print("A cells",len(A),"p95 range",min(n(r["shift_p95"]) for r in A),max(n(r["shift_p95"]) for r in A),"median p95",st.median(n(r["shift_p95"]) for r in A))
print("auroc>.5 & share<.05",[(r["fold"],r["h"],r["model"]) for r in A if n(r["auroc"])>.5 and n(r["share_at_least_observed"])<.05]," share>.95:",sum(n(r["share_at_least_observed"])>.95 for r in A),"by model",{m:sum(r["model"]==m and n(r["share_at_least_observed"])>.95 for r in A) for m in("M1","M3","M5","M6")},"share<.05 total",sum(n(r["share_at_least_observed"])<.05 for r in A))
print("A with auroc>=.9",[(r["fold"],r["h"],r["model"],round(n(r["auroc"]),2),r["share_at_least_observed"]) for r in A if n(r["auroc"])>=.9])
print("M1 A",[round(n(c(f"A_hold{f}",h,"M1")["auroc"]),2) for f in F for h in H])
print("seq D",[(r["model"],r["h"],r["auroc"][:4]) for r in S if r["kind"]=="D"])
print("median windows/pos",[ (r["fold"],r["h"],r["windows"],r["positives"]) for r in S if r["kind"]=="A" and r["model"]=="M5" and r["h"] in("30","720")])
print("total scored A M5 h30 windows",sum(int(r["windows"]) for r in S if r["kind"]=="A" and r["model"]=="M5" and r["h"]=="30"))
print("random M5",[(r["h"],round(n(r["auroc"]),3),round(n(r["average_precision"]),3)) for r in rand5.values()])
