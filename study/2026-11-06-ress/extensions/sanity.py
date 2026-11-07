"""Three independent checks on the surprising below-chance ranks."""
import csv,gzip,json,sys
from pathlib import Path
import numpy as np
from scipy.stats import rankdata
sys.path.insert(0,"extensions")
import event_study as es
cfg=json.load(open("provenance/event-study-config.json"))
events=es.read_events("provenance/event-study-events.csv",cfg)
data=es.load_minutes("../../data/raw/MetroPT3(AirCompressor).csv")
views,ok=es.features(data,cfg)
y,ep,_=es.build_labels(data,events,cfg)
n=len(data["grid"]);ranges,_=es.block_ranges(events,data["first"],n,780)
def auc(s,t):
    r=rankdata(s);P=t.sum();N=len(t)-P
    return (r[t==1].sum()-P*(P+1)/2)/(P*N)
print("1) training-set AUROC, hold out jul15, trained on blocks 1-3")
tr=es.block_mask(n,ranges,[0,1,2],780)&ok
for h in (30,360):
    for m in("M1","M3"):
        idx,w=es.training_sample(tr,y[h],cfg,np.random.default_rng(1))
        mod=es.make_model(m,cfg,1).fit(views[m][0][idx],y[h][idx].astype(float),w)
        mask=tr&(y[h]>=0)
        te=es.block_mask(n,ranges,[3],780)&ok&(y[h]>=0)
        print(f"  h={h} {m} train {auc(mod.margin(views[m][0][mask]),(y[h][mask]==1).astype(float)):.3f} heldout {auc(mod.margin(views[m][0][te]),(y[h][te]==1).astype(float)):.3f}")
print("2) one feature, no model: AUROC of 60-minute load share (1-COMP mean), per failure, within its block")
X,labels=views["M3"]
load=1-X[:,labels.index("COMP|mean")]
oil=X[:,labels.index("Oil_temperature|mean")]
for k,e in enumerate(events):
    for h in (30,360,720):
        b=es.block_mask(n,ranges,[k],780)&ok&(y[h]>=0)
        t=(y[h][b]==1).astype(float)
        print(f"  {e['id']} h={h} load AUROC {auc(load[b],t):.3f} oil AUROC {auc(oil[b],t):.3f} mean load pre {load[b][t==1].mean():.2f} other {load[b][t==0].mean():.2f}")
print("3) independent recomputation of primary metrics with scipy.rankdata")
rows=list(csv.DictReader(open("tables/primary-metrics.csv")))
worst=0
for r in rows:
    if r["kind"]=="E": continue
    with gzip.open(f"runs/event-study/scores/{r['fold']}_h{r['h']}_{r['model']}.csv.gz","rt") as s:
        next(s);a=np.array([l.split(",") for l in s],dtype=float)
    m=a[:,3]>=0
    worst=max(worst,abs(auc(a[m,1],(a[m,3]==1).astype(float))-float(r["auroc"])))
print("  max abs AUROC difference vs primary-metrics.csv:",worst, "over",sum(r["kind"]!="E" for r in rows),"cells")
