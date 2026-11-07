"""Exploratory, added after viewing results: how often does a circularly shifted label block reach the observed AUROC?
Uses saved scores only. Positive labels are rotated around the held-out decision sequence, keeping their run structure."""
import csv,glob,gzip,os,re
import numpy as np
from scipy.stats import rankdata
rng=np.random.default_rng(791)
SHIFTS=1000
paths=sorted(glob.glob("runs/event-study/scores/*_M[13].csv.gz"))+sorted(glob.glob("runs/seq-study/scores/*_M[56].csv.gz"))
paths=[p for p in paths if re.match(r"(A_hold|B_hold_may29_jun05)",os.path.basename(p))]
rows=[]
for p in paths:
    m=re.match(r"(.+)_h(\d+)_(M\d)\.csv\.gz",os.path.basename(p));fold,h,model=m.groups()
    with gzip.open(p,"rt") as s:
        data=list(csv.DictReader(s))
    data.sort(key=lambda r:int(r["minute_index"]))
    data=[r for r in data if int(r["label"])>=0]  # -1 marks censored or excluded decisions.
    y=np.array([int(r["label"]) for r in data])==1;score=np.array([float(r["margin"]) for r in data])
    n,pos=len(y),int(y.sum())
    if pos==0: continue
    r=rankdata(score);au=lambda mask:(r[mask].sum()-pos*(pos+1)/2)/(pos*(n-pos))
    obs=au(y)
    gap=np.minimum(np.arange(n),n-np.arange(n))
    ok=np.flatnonzero(gap>=pos)  # A shift must move the labels clear of their own position.
    picks=rng.choice(ok,SHIFTS,replace=False)
    sim=np.array([au(np.roll(y,int(k))) for k in picks])
    rows.append(dict(fold=fold,h=int(h),model=model,windows=n,positives=pos,auroc=obs,shift_median=float(np.median(sim)),shift_p05=float(np.quantile(sim,.05)),shift_p95=float(np.quantile(sim,.95)),share_at_least_observed=float((sim>=obs).mean())))
# The observed value must reproduce the frozen tables before the control is trusted.
ref={}
for r in csv.DictReader(open("tables/primary-metrics.csv")):
    if r["auroc"]: ref[(r["fold"],int(r["h"]),r["model"])]=float(r["auroc"])
for r in csv.DictReader(open("tables/seq-metrics.csv")):
    if r["auroc"]: ref[(r["fold"],int(r["h"]),r["model"])]=float(r["auroc"])
worst=max(abs(ref[(r["fold"],r["h"],r["model"])]-r["auroc"]) for r in rows);print("max difference from frozen tables",worst);assert worst<1e-5  # Saved margins are rounded to 6 decimals.
with open("tables/exploratory-rank-chance.csv","w",newline="") as x:
    w=csv.DictWriter(x,list(rows[0]));w.writeheader();w.writerows(rows)
print(len(rows))
for r in rows:
    if r["model"] in("M5","M6") and r["auroc"]>.7: print(r["fold"],r["h"],r["model"],round(r["auroc"],3),"share",r["share_at_least_observed"],"p95",round(r["shift_p95"],3),"med",round(r["shift_median"],3))
for m in("M1","M3","M5","M6"):
    s=[r for r in rows if r["model"]==m and r["fold"].startswith("A_")]
    print(m,"A cells",len(s),"share<.05:",sum(r["share_at_least_observed"]<.05 for r in s),"median share",round(float(np.median([r["share_at_least_observed"] for r in s])),3))
print("all seq above .7 in A with share<.05:",[(r["fold"][6:],r["h"],r["model"]) for r in rows if r["fold"].startswith("A_") and r["model"] in("M5","M6") and r["share_at_least_observed"]<.05 and r["auroc"]>.5])
print("B may29_jun05 best",sorted([(round(r["auroc"],3),r["h"],r["model"],r["share_at_least_observed"]) for r in rows if r["fold"].startswith("B_")],reverse=True)[:6])
print("cells with auroc>.5 and share<.05 by failure",{f:sum(r["fold"]=="A_hold"+f and r["auroc"]>.5 and r["share_at_least_observed"]<.05 for r in rows) for f in("apr18","may29","jun05","jul15")},"of",len([r for r in rows if r["fold"].startswith("A_")]))
print("below-chance mirror: auroc<.5 and share>.95",sum(r["fold"].startswith("A_") and r["share_at_least_observed"]>.95 for r in rows))
