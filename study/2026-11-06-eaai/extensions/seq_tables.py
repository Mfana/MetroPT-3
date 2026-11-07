"""Sequence-model metrics and frozen rule outcomes from runs/seq-study; digests checked against the rerun."""
import csv,json,statistics as st
from pathlib import Path
run=json.load(open("runs/seq-study/run.json"));re=json.load(open("runs/seq-rerun-holdjul15/run.json"))
key=lambda x:(x["fold"],x["h"],x["model"])
d={key(x):x.get("prediction_digest") for x in run["results"]}
same=sum(d[key(x)]==x["prediction_digest"] for x in re["results"]);print("rerun digests identical",same,"of",len(re["results"]))
assert same==len(re["results"])
cols=["fold","kind","h","model","windows","positives","distinct_scores","ap","auroc","bss_uncal","bss_platt","ece10_uncal","ece10_platt","slope_uncal","slope_platt","platt_a","platt_b","threshold","failures","caught","first_lead","chance_max","fa","unscorable","scored_days","fa_day","occupancy","digest"]
rows=[];rand=[]
for r in run["results"]:
    w=r["window"]
    if r["kind"]=="exploratory":
        rand.append({"h":r["h"],"model":r["model"],**{k:w[k] for k in("windows","positives","prevalence","average_precision","auroc")}});continue
    u,c,p=r["uncalibrated"],r["platt_calibrated"],r["policy"];f=p["failures"]
    leads=[v["first_lead_minutes"] for v in f.values() if v["caught"]]
    rows.append(dict(fold=r["fold"],kind=r["kind"],h=r["h"],model=r["model"],windows=w["windows"],positives=w["positives"],distinct_scores=w["distinct_scores"],ap=w["average_precision"],auroc=w["auroc"],bss_uncal=u["brier_skill"],bss_platt=c["brier_skill"],ece10_uncal=u["ece_10"],ece10_platt=c["ece_10"],slope_uncal=u.get("calibration_slope"),slope_platt=c.get("calibration_slope"),platt_a=r["platt"][0],platt_b=r["platt"][1],threshold=p["threshold"],failures=len(f),caught=sum(v["caught"] for v in f.values()),first_lead=min(leads) if leads else "",chance_max=max([v["chance_rate_under_circular_shift"] for v in f.values() if v["caught"]],default=""),fa=p["false_alarm_episodes"],unscorable=p["unscorable_alarm_episodes"],scored_days=p["scored_days"],fa_day=p["false_alarms_per_day"],occupancy=p["alarm_occupancy"],digest=r["prediction_digest"]))
with open("tables/seq-metrics.csv","w",newline="") as x:
    w=csv.DictWriter(x,cols);w.writeheader();w.writerows(rows)
with open("tables/exploratory-seq-random-split.csv","w",newline="") as x:
    w=csv.DictWriter(x,list(rand[0]));w.writeheader();w.writerows(rand)
P=list(csv.DictReader(open("tables/primary-metrics.csv")))
n=lambda v:float(v)
H=[30,60,180,360,720];F=["apr18","may29","jun05","jul15"];LAB={30:"30 min",60:"1 h",180:"3 h",360:"6 h",720:"12 h"}
def S(fold,h,m): return next(r for r in rows if r["fold"]==fold and r["h"]==h and r["model"]==m)
def B(fold,h,m): return next(r for r in P if r["fold"]==fold and int(r["h"])==h and r["model"]==m)
out=[]
for m in("M5","M6"):
  for h in H:
    A=[S(f"A_hold{f}",h,m) for f in F];M1=[B(f"A_hold{f}",h,"M1") for f in F];M3=[B(f"A_hold{f}",h,"M3") for f in F]
    D,D1=S("D_forward_jul15",h,m),B("D_forward_jul15",h,"M1");E=S("E_false_alarm_after_jul16",h,m)
    base=sum(a["bss_platt"]>0 for a in A)
    state=sum(a["ap"]>n(b["ap"]) and a["bss_platt"]>n(b["bss_platt"]) for a,b in zip(A,M1))
    stateD=D["ap"]>n(D1["ap"]) and D["bss_platt"]>n(D1["bss_platt"])
    slope=sum(a["slope_platt"] is not None and .7<=a["slope_platt"]<=1.3 for a in A)
    caught=[a for a in A if a["caught"]];valid=sum(a["chance_max"]<.5 for a in caught)
    fa=st.median(a["fa_day"] for a in A)
    o=dict(model=m,horizon=LAB[h],bss_platt_pos_of_4=base,beats_m1_of_4=state,beats_m1_forward=stateD,slope_in_range_of_4=slope,caught_of_4=len(caught),caught_below_chance_limit=valid,fa_median=fa,fa_after_jul16=E["fa_day"],
      median_auroc=st.median(a["auroc"] for a in A),median_auroc_m1=st.median(n(b["auroc"]) for b in M1),median_auroc_m3=st.median(n(b["auroc"]) for b in M3),
      median_ap=st.median(a["ap"] for a in A),median_ap_m1=st.median(n(b["ap"]) for b in M1),median_ap_m3=st.median(n(b["ap"]) for b in M3),
      auroc_above_m3_of_4=sum(a["auroc"]>n(b["auroc"]) for a,b in zip(A,M3)),ap_above_m3_of_4=sum(a["ap"]>n(b["ap"]) for a,b in zip(A,M3)),ap_above_m1_of_4=sum(a["ap"]>n(b["ap"]) for a,b in zip(A,M1)))
    o.update(pass_base=base==4,pass_state=state>=3 and stateD,pass_slope=slope>=3,pass_warning=valid>=3,pass_burden=fa<=1 and E["fa_day"]<=1)
    o["rules_met_of_5"]=sum(o[k] for k in("pass_base","pass_state","pass_slope","pass_warning","pass_burden"));o["defensible"]=o["rules_met_of_5"]==5
    out.append(o)
with open("tables/seq-rule-outcomes.csv","w",newline="") as x:
    w=csv.DictWriter(x,list(out[0]));w.writeheader();w.writerows(out)
f=lambda v:round(v,3) if isinstance(v,float) else v
for o in out: print({k:f(v) for k,v in o.items()})
print("random",[(r["h"],round(r["auroc"],3),round(r["average_precision"],3),r["positives"]) for r in rand])
tests=sum(r["failures"] for r in rows);print("failure tests",tests,"caught",sum(r["caught"] for r in rows))
print("caught cells",[(r["fold"],r["h"],r["model"],r["first_lead"],r["chance_max"],r["fa"]) for r in rows if r["caught"]])
for k in "ABCD":
    s=[r for r in rows if r["kind"]==k];print(k,len(s),"auroc med",round(st.median(r["auroc"] for r in s),3),"range",round(min(r["auroc"] for r in s),3),round(max(r["auroc"] for r in s),3),"bss_platt>0",sum(r["bss_platt"]>0 for r in s),"bss_uncal>0",sum(r["bss_uncal"]>0 for r in s),"platt_b==0",sum(r["platt_b"]==0 for r in s),"fa total",sum(r["fa"] for r in s),"fa_day max",round(max(r["fa_day"] for r in s),3))
print("slopes A",[(None if r["slope_platt"] is None else round(r["slope_platt"],3)) for r in rows if r["kind"]=="A"][:40])
print("Platt b A",[round(r["platt_b"],3) for r in rows if r["kind"]=="A"][:40])
print("per failure AUROC")
for m in("M5","M6"):
  for f_ in F: print(m,f_,[round(S(f"A_hold{f_}",h,m)["auroc"],2) for h in H],"AP/prev",[round(S(f"A_hold{f_}",h,m)["ap"]/(S(f"A_hold{f_}",h,m)["positives"]/S(f"A_hold{f_}",h,m)["windows"]),2) for h in H])
print("E",[(r["model"],r["h"],r["fa"],r["fa_day"]) for r in rows if r["kind"]=="E"])
print("D",[(r["model"],r["h"],round(r["auroc"],2),r["caught"],r["failures"]) for r in rows if r["kind"]=="D"])
print("C",[(r["model"],r["h"],round(r["auroc"],2),r["caught"],r["failures"]) for r in rows if r["kind"]=="C"])
