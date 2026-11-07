"""Exploratory: load share before each report and how unusual it is. Fits nothing."""
import csv,json,sys
sys.path.insert(0,"extensions")
import numpy as np,event_study as es
cfg=json.load(open("provenance/event-study-config.json"));ev=es.read_events("provenance/event-study-events.csv",cfg)
d=es.load_minutes("../../data/raw/MetroPT3(AirCompressor).csv");g,first,pres=d["grid"],d["first"],d["present"]
comp=g[:,d["names"].index("COMP")];loaded=1-np.nan_to_num(comp,nan=0)  # Load share as in Figure 3: mean of 1-COMP, so cycling within a minute counts.
ok=pres.copy()
for e in ev: ok[max(e["onset"]-first,0):min(e["release"]-first,len(ok))]=False
W=360;c=np.r_[0,np.cumsum(np.where(pres,loaded,0))];p=np.r_[0,np.cumsum(pres)];co=np.r_[0,np.cumsum(ok)]
# Reference: every 6-hour window with at least 80% present minutes and none in a report period.
idx=np.arange(0,len(ok)-W);full=(co[idx+W]-co[idx])>=.8*W;share=(c[idx+W]-c[idx])/np.maximum(p[idx+W]-p[idx],1);ref=share[full]
rows=[]
for e in ev:
    o=e["onset"]-first
    for lo,hi in ((-360,0),(-240,-15),(-120,-15)):
        n=pres[o+lo:o+hi].sum();s=float(loaded[o+lo:o+hi][pres[o+lo:o+hi]].mean()) if n else float("nan")
        rows.append(dict(failure=e["id"],window_start=lo,window_end=hi,present=int(n),load_share=round(s,4)))
    s6=rows[-3]["load_share"];rows[-3]["reference_share_at_or_above"]=round(float(np.mean(ref>=s6)),4) if s6==s6 else ""
print("reference windows",len(ref),"median",round(float(np.median(ref)),3),"p95",round(float(np.percentile(ref,95)),3))
for r in rows: print(r)
with open("tables/onset-load-share.csv","w",newline="") as x:
    w=csv.DictWriter(x,["failure","window_start","window_end","present","load_share","reference_share_at_or_above"]);w.writeheader();w.writerows(rows)
