"""Would counting the minute exactly 5 minutes before a start change any catch? Saved scores only; fits nothing."""
import csv,gzip,json,sys
from pathlib import Path
sys.path.insert(0,"extensions")
import numpy as np,event_study as es
D=es.load_minutes("../../data/raw/MetroPT3(AirCompressor).csv");n,first=len(D["grid"]),D["first"]
b="provenance/event-study-config.json";t="provenance/event-study-config-timing.json";E0="provenance/event-study-events.csv"
S=[("registered","runs/event-study",E0,b),("registered","runs/seq-study",E0,b)]+[(f"seed{s}",f"runs/gaps/seed{s}",E0,b) for s in(1791,2791,3791,4791)]
for g,e in(("minus60","provenance/events-minus60.csv"),("plus60","provenance/events-plus60.csv")):S+=[(g,f"runs/gaps/event-{g}",e,t),(g,f"runs/gaps/shift-{g}",e,t)]
rows=[];tot={}
for name,path,evf,cf in S:
    cfg=json.load(open(cf));ev=es.read_events(evf,cfg);ranges,emb=es.block_ranges(ev,first,n,cfg["embargo_minutes"]);F={f["name"]:f for f in es.folds_for(4,ranges,ev,first)}
    j=json.load(open(path+"/run.json")).get("results") or [json.loads(l) for l in open(path+"/results.jsonl")]
    for r in j:
        if r.get("status")!="done" or r["fold"] not in F or "policy" not in r:continue
        fn=Path(f"{path}/scores/{r['fold']}_h{int(r['h'])}_{r['model']}.csv.gz")
        a=np.loadtxt(gzip.open(fn,"rt"),delimiter=",",skiprows=1,ndmin=2);idx=a[:,0].astype(int);sc=np.full(n,-np.inf);sc[idx]=a[:,1];v=np.zeros(n,bool);v[idx]=True
        al,raw=es.alarm_series(sc,r["policy"]["threshold"],v,cfg);h=int(r["h"]);f=F[r["fold"]]
        if f.get("test_after") is not None:continue
        test=es.block_mask(n,ranges,f["test"],emb)
        if r["model"] in("M5","M6"):test=test&(np.arange(n)>=cfg["lookback_minutes"])
        a0=int(np.flatnonzero(test)[0])
        for e in ev:
            o=e["onset"]-first
            if not test[max(o-1,0)]:continue
            lo,hi=max(o-h,a0),o-cfg["min_response_minutes"]
            tot[name]=tot.get(name,0)+1
            if hi>lo and not raw[lo:hi].any() and hi<n and raw[hi]:
                rows.append(dict(set=name,fold=r["fold"],h=h,model=r["model"],failure=e["id"]))
print("tests",tot);print("catches added by including the exact 5-minute minute:",len(rows),rows)
with open("tables/alarm-boundary.csv","w",newline="") as x:
    w=csv.DictWriter(x,["set","fold","h","model","failure"]);w.writeheader();w.writerows(rows)
