"""Build rule outcomes, stability summary, figure data and LaTeX tables from frozen outputs."""
import csv,json,re,statistics as st
from pathlib import Path
R=list(csv.DictReader(open("tables/primary-metrics.csv")))
run=json.load(open("runs/event-study/run.json"))
num=lambda v:float(v) if v not in("",None,"None") else None
H=["30","60","180","360","720"];LAB={"30":"30 min","60":"1 h","180":"3 h","360":"6 h","720":"12 h"}
F=["apr18","may29","jun05","jul15"];FOLD={f:f"A_hold{f}" for f in F}
def cell(f,h,m,k="A"):
    return next(r for r in R if r["fold"]==f and r["h"]==h and r["model"]==m)
s=run["stability"]
seed_j=sorted(e["top_k_jaccard"] for e in s["across_seeds"]);p10=seed_j[int(.1*len(seed_j))]
out=[]
for h in H:
    A=[cell(FOLD[f],h,"M3") for f in F];M1=[cell(FOLD[f],h,"M1") for f in F]
    D3,D1=cell("D_forward_jul15",h,"M3"),cell("D_forward_jul15",h,"M1")
    E=cell("E_false_alarm_after_jul16",h,"M3")
    base=sum(num(a["bss_platt"])>0 for a in A)
    state=sum(num(a["ap"])>num(b["ap"]) and num(a["bss_platt"])>num(b["bss_platt"]) for a,b in zip(A,M1))
    stateD=num(D3["ap"])>num(D1["ap"]) and num(D3["bss_platt"])>num(D1["bss_platt"])
    defined=[a for a in A if num(a["platt_b"])>0]
    caught=sum(int(a["caught"]) for a in A)
    fa=st.median(num(a["fa_day"]) for a in A);fae=num(E["fa_day"])
    hor=[e["top_k_jaccard"] for e in s["across_horizons"] if int(h) in e["pair"]]
    fail=[e["top_k_jaccard"] for e in s["across_failures"] if e["h"]==int(h)]
    row={"horizon":LAB[h],"platt_bss_positive_of_4":base,"m3_beats_m1_of_4":state,"m3_beats_m1_forward":stateD,"platt_nonzero_slope_of_4":len(defined),"caught_of_4":caught,"fa_median":fa,"fa_after_jul16":fae,"horizon_jaccard_median":st.median(hor),"failure_jaccard_median":st.median(fail),"seed_jaccard_p10":p10}
    row["pass_base"]=base==4;row["pass_state"]=state>=3 and stateD;row["pass_slope"]=False;row["pass_warning"]=caught>=3;row["pass_burden"]=fa<=1 and fae<=1;row["pass_explain"]=st.median(hor)>=p10 and st.median(fail)>=p10
    row["defensible"]=all(row[k] for k in("pass_base","pass_state","pass_slope","pass_warning","pass_burden","pass_explain"))
    out.append(row)
with open("tables/rule-outcomes.csv","w",newline="") as x:
    w=csv.DictWriter(x,fieldnames=list(out[0]));w.writeheader();w.writerows(out)
for o in out: print(o)
for key in s:
    for m in("spearman","top_k_jaccard","sign_agreement","cosine"):
        v=[e[m] for e in s[key] if e[m] is not None];print(key,m,round(st.median(v),3),round(min(v),3),round(max(v),3))
# Figure data
rand={r["h"]:r for r in csv.DictReader(open("tables/exploratory-random-split.csv"))}
with open("figures/fig1.csv","w",newline="") as x:
    w=csv.writer(x);w.writerow(["pos","apr18","may29","jun05","jul15","m4median","random"])
    for i,h in enumerate(H):
        w.writerow([i,*[cell(FOLD[f],h,"M3")["auroc"] for f in F],st.median(num(cell(FOLD[f],h,"M4")["auroc"]) for f in F),rand[h]["auroc"]])
rows=[]
for line in open("logs/sanity.txt"):
    m=re.match(r"\s+(\w+) h=(\d+) load AUROC ([\d.]+) oil AUROC ([\d.]+) mean load pre ([\d.]+) other ([\d.]+)",line)
    if m: rows.append(m.groups())
with open("tables/exploratory-single-feature.csv","w",newline="") as x:
    w=csv.writer(x);w.writerow(["failure","h","load_auroc","oil_auroc","load_pre","load_other"]);w.writerows(rows)
tick=lambda b:"Yes" if b else "No"
L=[]
L.append(r"\begin{tabular}{lrrrrrr}\toprule Horizon & Calibrated skill $>0$ & M3 beats M1 & Non-zero Platt slope & Failures caught & False alarms/day & Rules met\\\midrule")
for o in out:
    met=sum(o[k] for k in("pass_base","pass_state","pass_slope","pass_warning","pass_burden","pass_explain"))
    L.append(f"{o['horizon']} & {o['platt_bss_positive_of_4']}/4 & {o['m3_beats_m1_of_4']}/4 & {o['platt_nonzero_slope_of_4']}/4 & {o['caught_of_4']}/4 & {o['fa_median']:.2f} & {met}/6\\\\")
L.append(r"\bottomrule\end{tabular}")
Path("tables/table-rules.tex").write_text("\n".join(L)+"\n")
L=[r"\begin{tabular}{lrrrrrrrr}\toprule & \multicolumn{4}{c}{M3 AUROC, held out} & \multicolumn{4}{c}{M3 uncalibrated Brier skill}\\\cmidrule(lr){2-5}\cmidrule(lr){6-9} Horizon & Apr 18 & May 29 & Jun 5 & Jul 15 & Apr 18 & May 29 & Jun 5 & Jul 15\\\midrule"]
for h in H:
    c=[cell(FOLD[f],h,"M3") for f in F]
    L.append(LAB[h]+" & "+" & ".join(f"{num(a['auroc']):.2f}" for a in c)+" & "+" & ".join(f"{num(a['bss_uncal']):.2f}" for a in c)+r"\\")
L.append(r"\bottomrule\end{tabular}")
Path("tables/table-m3.tex").write_text("\n".join(L)+"\n")
L=[r"\begin{tabular}{llrrrr}\toprule Failure & Signal & 30 min & 6 h & 12 h & Load share before / elsewhere (6 h)\\\midrule"]
by={(r[0],r[1]):r for r in rows}
for f,n in zip(F,("Apr 18","May 29","Jun 5","Jul 15")):
    L.append(f"{n} & Load share & {by[(f,'30')][2]} & {by[(f,'360')][2]} & {by[(f,'720')][2]} & {by[(f,'360')][4]} / {by[(f,'360')][5]}\\\\")
    L.append(f" & Oil temperature & {by[(f,'30')][3]} & {by[(f,'360')][3]} & {by[(f,'720')][3]} & \\\\")
L.append(r"\bottomrule\end{tabular}")
Path("tables/table-direction.tex").write_text("\n".join(L)+"\n")
# Numbers for text
print("random",{k:(round(float(v["auroc"]),3),round(float(v["ap"]),3)) for k,v in rand.items()})
for h in H:
    print(h,"M3 med AUROC",round(st.median(num(cell(FOLD[f],h,"M3")["auroc"]) for f in F),3),"M1",round(st.median(num(cell(FOLD[f],h,"M1")["auroc"]) for f in F),3),"M4",round(st.median(num(cell(FOLD[f],h,"M4")["auroc"]) for f in F),3),"M2",round(st.median(num(cell(FOLD[f],h,"M2")["auroc"]) for f in F),3))
allc=[r for r in R if r["kind"]=="A"]
print("A cells",len(allc),"caught total",sum(int(r["caught"]) for r in allc),"Platt b=0:",sum(num(r["platt_b"])==0 for r in allc),"of",len(allc))
print("All folds caught:",sum(int(r["caught"]) for r in R),"cells with failures",sum(int(r["failures"])>0 for r in R),"failure-tests",sum(int(r["failures"]) for r in R))
print("uncal BSS>0 A:",sum(num(r["bss_uncal"])>0 for r in allc),"M3 uncal range",min(num(r["bss_uncal"]) for r in allc if r["model"]=="M3"),max(num(r["bss_uncal"]) for r in allc if r["model"]=="M3"))
print("max AUROC cell M3 A",max((num(r["auroc"]),r["fold"],r["h"]) for r in allc if r["model"]=="M3"),"best M4",max((num(r["auroc"]),r["fold"],r["h"]) for r in allc if r["model"]=="M4"))
print("forward M3 D",[(r["h"],r["auroc"][:5],r["distinct_scores"]) for r in R if r["kind"]=="D" and r["model"]=="M3"])
print("forward M3 C",[(r["h"],r["auroc"][:5],r["distinct_scores"]) for r in R if r["kind"]=="C" and r["model"]=="M3"])
print("E M3 FA/day",[(r["h"],r["fa_day"][:5],r["fa"]) for r in R if r["kind"]=="E" and r["model"]=="M3"])
X=list(csv.DictReader(open("tables/exploratory-oracle-threshold.csv")))
for q in(".95","0.95","0.99"):
    s3=[x for x in X if x["q"]==q and x["model"]=="M3"]
    if s3: print("oracle q",q,"M3 caught",sum(int(x["caught"]) for x in s3),"/",len(s3),"chance of caught",[ (x["fold"][6:],x["h"],x["chance"]) for x in s3 if int(x["caught"])], "FA med",st.median(float(x["fa_day"]) for x in s3))
