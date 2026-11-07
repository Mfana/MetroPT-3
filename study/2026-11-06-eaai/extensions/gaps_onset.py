"""Exploratory, added after seeing the +60 result: do alarms under a later onset come before the reported start,
and when do sensors change relative to it? Saved outputs and raw telemetry only; nothing is fitted."""
import csv,json,sys
sys.path.insert(0,"extensions")
import numpy as np,event_study as es
M=list(csv.DictReader(open("tables/gaps-shift-metrics.csv")))
rows=[];
for r in M:
    if int(r["caught"]) and r["kind"] in "AD":
        for l in str(r["lead"]).split(";"):
            if l not in("None",""):
                rows.append(dict(shift=int(r["shift"]),fold=r["fold"],kind=r["kind"],h=int(r["h"]),model=r["model"],lead_from_moved_onset=int(l),minutes_after_reported_start=int(r["shift"])-int(l)*1 if False else 60-int(l),chance=r["chance"],fa_day=r["fa_day"],auroc=r["auroc"]))
with open("tables/gaps-shift-plus60-alarm-timing.csv","w",newline="") as x:
    w=csv.DictWriter(x,list(rows[0]));w.writeheader();w.writerows(rows)
a=[r["minutes_after_reported_start"] for r in rows]
print("caught under +60:",len(a),"cells; alarm minutes after reported start: min",min(a),"median",np.median(a),"max",max(a),"; before reported start:",sum(v<0 for v in a))
print("by failure",{f:sum(f in r["fold"] for r in rows) for f in("apr18","may29","jun05","jul15")},"by model",{m:sum(r["model"]==m for r in rows) for m in("M1","M2","M3","M4","M5","M6")},"horizon",{h:sum(r["h"]==h for r in rows) for h in(30,60,180,360,720)})
print("before-start cells",[r for r in rows if r["minutes_after_reported_start"]<0])
print("M folds with kinds",set(r["kind"] for r in M if int(r["caught"])),"total caught",sum(int(r["caught"]) for r in M),"E FA max",max(float(r["fa_day"]) for r in M if r["kind"]=="E"))
base=json.load(open("provenance/event-study-config.json"));ev=es.read_events("provenance/event-study-events.csv",base);d=es.load_minutes("../../data/raw/MetroPT3(AirCompressor).csv")
g,names,first,pres=d["grid"],d["names"],d["first"],d["present"]
out=[]
sig=["COMP","TP2","TP3","Reservoirs","Oil_temperature","Motor_current","MPG","H1","DV_pressure"]
sig=[s for s in sig if s in names]
print("names",names)
for e in ev:
    o=e["onset"]-first
    ref=np.arange(o-1440*3,o-180);ref=ref[(ref>=0)&pres[ref]]
    print(e["id"],"present share -180..0",round(pres[o-180:o].mean(),2),"0..+60",round(pres[o:o+60].mean(),2))
    for lo in range(-240,120,15):
        seg=np.arange(o+lo,o+lo+15);
        rec=dict(failure=e["id"],bin_start_min=lo,present=int(pres[seg].sum()))
        for s in sig:
            j=names.index(s);v=g[seg,j];rec[s]=float(np.nanmean(v)) if np.isfinite(v).any() else ""
        out.append(rec)
    print(" ",e["id"],"3-day ref mean:",{s:round(float(np.nanmean(g[ref,names.index(s)])),2) for s in sig})
    for rec in out[-24:]:
        if rec["bin_start_min"]>=-60: print("  ",rec["bin_start_min"],rec["present"],{s:(round(rec[s],2) if rec[s]!="" else None) for s in sig})
with open("tables/gaps-onset-profile.csv","w",newline="") as x:
    w=csv.DictWriter(x,list(out[0]));w.writeheader();w.writerows(out)
# Minute-level start of the sustained loaded run, and how often such runs occur away from reports.
comp=g[:,names.index("COMP")];loaded=(comp<.5)&pres
d_=np.diff(np.r_[0,loaded.astype(int),0]);st_=np.flatnonzero(d_==1);en=np.flatnonzero(d_==-1);runs=np.c_[st_,en-st_]
on=[e["onset"]-first for e in ev];end=[e["end"]-first for e in ev]
near=lambda s:any(o-120<=s<=b for o,b in zip(on,end))
T=[]
for e,o in zip(ev,on):
    r=[(int(s-o),int(l)) for s,l in runs if o-120<=s<=o+60 and l>=30]
    print("sustained run >=30 min starting within -120..+60 of",e["id"],":(start rel. to reported, length)",r)
    T.append(dict(failure=e["id"],runs=";".join(f"{a}|{b}" for a,b in r)))
for L in(30,60,120,240):
    away=[(s,l) for s,l in runs if l>=L and not near(s)];print("runs >=",L,"min away from reports:",len(away),"of total",int(sum(l>=L for s,l in runs)),"longest away",max((int(l) for s,l in away),default=0))
print("days covered",round(pres.sum()/1440,1))
with open("tables/gaps-onset-runs.csv","w",newline="") as x:
    w=csv.DictWriter(x,["failure","runs"]);w.writeheader();w.writerows(T)
