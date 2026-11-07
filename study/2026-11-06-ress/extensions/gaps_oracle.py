"""Addendum 2, section 2: the frozen oracle policy applied to saved M5 and M6 analysis A scores. Upper bound only."""
import csv,json,sys,statistics as st
from datetime import datetime
from pathlib import Path
sys.path.insert(0,"extensions")
import event_study as es,rescore
import numpy as np
base=json.load(open("provenance/event-study-config.json"))
main=json.load(open("runs/event-study/run.json"))
zero=int((datetime.fromisoformat(main["input"]["first"])-datetime(1970,1,1)).total_seconds()//60)
events=main["events"]
# Confirm the function reproduces the frozen M3 oracle table before it is used on new scores.
ref={(r["fold"],r["h"],r["q"]):r for r in csv.DictReader(open("tables/exploratory-oracle-threshold.csv")) if r["model"]=="M3"}
rows=[];worst=0
def one(run,fold,h,model,q):
    index,margin,_,y=rescore.read_scores(f"runs/{run}/scores/{fold}_h{h}_{model}.csv.gz")
    onsets=[(e["id"],e["onset"]-zero) for e in events if index[0]<=e["onset"]-zero<=index[-1]]
    return rescore.oracle_policy(index,margin,y,onsets,h,q,base,base["seed"])
for r in ref.values():
    o=one("event-study",r["fold"],int(r["h"]),"M3",float(r["q"]));worst=max(worst,abs(o["false_alarms_per_day"]-float(r["fa_day"])))
    assert sum(v.get("caught",False) for v in o["failures"].values())==int(r["caught"])
print("frozen M3 oracle reproduced; max FA/day difference",worst);assert worst<1e-9
for fold in ("A_holdapr18","A_holdmay29","A_holdjun05","A_holdjul15"):
  for h in base["horizon_minutes"]:
    for model in ("M5","M6"):
      for q in (.9,.95,.98,.99):
        o=one("seq-study",fold,h,model,q);f=list(o["failures"].values())[0]
        rows.append(dict(fold=fold,h=h,model=model,q=q,caught=int(f.get("caught",False)),lead=f.get("first_lead_minutes"),chance=f.get("chance_rate_under_circular_shift"),fa_day=o["false_alarms_per_day"]))
with open("tables/gaps-oracle-seq.csv","w",newline="") as x:
    w=csv.DictWriter(x,list(rows[0]));w.writeheader();w.writerows(rows)
M3=list(csv.DictReader(open("tables/exploratory-oracle-threshold.csv")))
for m in("M1","M3","M4","M5","M6"):
  for q in (.9,.95,.98,.99):
    s=[r for r in rows if r["model"]==m and r["q"]==q] if m in("M5","M6") else [r for r in M3 if r["model"]==m and float(r["q"])==q]
    c=[r for r in s if int(r["caught"])]
    print(m,q,"caught",len(c),"of",len(s),"chance<.5:",sum(float(str(r["chance"]).split(";")[0])<.5 for r in c),"FA/day median",round(st.median(float(r["fa_day"]) for r in s),2))
print("M5/M6 caught, chance<.5, q>=.95:",[(r["fold"][6:],r["h"],r["model"],r["q"],r["lead"],r["chance"],round(r["fa_day"],2)) for r in rows if r["caught"] and r["chance"]<.5 and r["q"]>=.95])
by={}
for r in rows:
    if r["q"]==.95: by.setdefault((r["model"],r["fold"][6:]),[]).append(r["caught"])
print({k:sum(v) for k,v in by.items()})
