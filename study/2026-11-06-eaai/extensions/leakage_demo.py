"""Exploratory: M3 under a row-random split versus the registered whole-failure hold-out."""
import csv,json,sys
import numpy as np
sys.path.insert(0,"extensions")
import event_study as es, rescore
cfg=json.load(open("provenance/event-study-config.json"))
events=es.read_events("provenance/event-study-events.csv",cfg)
data=es.load_minutes("../../data/raw/MetroPT3(AirCompressor).csv")
views,ok=es.features(data,cfg);y,ep,_=es.build_labels(data,events,cfg)
X=views["M3"][0];n=len(X)
with open("tables/exploratory-random-split.csv","w",newline="") as s:
    w=csv.writer(s);w.writerow(["h","test_windows","positives","prevalence","ap","ap_over_prevalence","auroc"])
    for h in cfg["horizon_minutes"]:
        rng=np.random.default_rng(cfg["seed"]+h)
        valid=ok&(y[h]>=0)
        train=valid&(rng.random(n)<.6)
        test=valid&~train
        idx,wt=es.training_sample(train,y[h],cfg,rng)
        m=es.GBDT(cfg,cfg["seed"]).fit(X[idx],y[h][idx].astype(float),wt)
        t=(y[h][test]==1).astype(float)
        ap,auc=rescore.tie_metrics(m.margin(X[test]),t)
        w.writerow([h,int(test.sum()),int(t.sum()),t.mean(),ap,ap/t.mean(),auc]);print(h,round(ap,3),round(auc,3),flush=True)
