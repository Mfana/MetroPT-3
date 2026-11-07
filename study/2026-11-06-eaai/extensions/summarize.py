import json,sys,statistics as st,csv
from pathlib import Path
R=Path(sys.argv[1]);d=json.load(open(R/"run.json"));r2=json.load(open(Path(sys.argv[2])/"run.json"))
a={(x["fold"],x["h"],x["model"]):x.get("prediction_digest") for x in d["results"]}
b={(x["fold"],x["h"],x["model"]):x.get("prediction_digest") for x in r2["results"]}
print("rerun digests identical:",a==b,len(a),"status",d["status"]);print("not done:",[ (x["fold"],x["h"],x["model"],x["status"]) for x in d["results"] if x["status"]!="done"])
print("grid",d["grid_minutes"],"present",d["present_minutes"],"valid",d["valid_decisions"]);print(json.dumps(d["label_counts"]))
print("\nA: fold h model | prev AP AUROC | BSS_unc BSS_platt slope_platt ece10 topgap | caught lead chance FA/day occ")
rows=[]
for x in d["results"]:
    if x["status"]!="done": continue
    w,u,p,po=x["window"],x["uncalibrated"],x["platt_calibrated"],x["policy"]
    f=po["failures"]
    row={"fold":x["fold"],"kind":x["kind"],"h":x["h"],"model":x["model"],"windows":w["windows"],"positives":w["positives"],"prevalence":w["prevalence"],"ap":w.get("average_precision"),"auroc":w.get("auroc"),"bss_uncal":u.get("brier_skill"),"bss_platt":p.get("brier_skill"),"slope_uncal":u.get("calibration_slope"),"slope_platt":p.get("calibration_slope"),"intercept_platt":p.get("calibration_intercept"),"ece10_platt":p.get("ece_10"),"ece5_platt":p.get("ece_5"),"ece15_platt":p.get("ece_15"),"topgap_platt":p.get("top_decile_gap"),"logloss_platt":p.get("log_loss"),"mean_pred_platt":p.get("mean_predicted"),"brier_platt":p.get("brier"),"caught":sum(v.get("caught",False) for v in f.values()),"failures":len(f),"leads":";".join(str(v.get("first_lead_minutes")) for v in f.values()),"chance":";".join(str(v.get("chance_rate_under_circular_shift")) for v in f.values()),"fa_day":po["false_alarms_per_day"],"fa":po["false_alarm_episodes"],"unscorable":po["unscorable_alarm_episodes"],"days":po["scored_days"],"occ":po["alarm_occupancy"],"oof_pos":x["oof_positive"]}
    rows.append(row)
with open(R/"summary.csv","w",newline="") as s:
    w=csv.DictWriter(s,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
g=lambda v,n=3:"  -  " if v is None else f"{v:.{n}f}"
for k in "ABCDE":
    print("\n==",k)
    for x in rows:
        if x["kind"]==k: print(f'{x["fold"][:22]:22} {x["h"]:4} {x["model"]} prev {x["prevalence"]:.4f} AP {g(x["ap"])} ROC {g(x["auroc"])} BSSu {g(x["bss_uncal"])} BSSp {g(x["bss_platt"])} sl {g(x["slope_platt"],2)} ece {g(x["ece10_platt"],4)} top {g(x["topgap_platt"],3)} caught {x["caught"]}/{x["failures"]} lead {x["leads"]} chance {x["chance"]} FA/d {g(x["fa_day"],2)} unsc {x["unscorable"]}')
s=d["stability"]
for key in s:
    for m in ("spearman","top_k_jaccard","sign_agreement","cosine"):
        v=[e[m] for e in s[key] if e[m] is not None]
        if v: print(key,m,"n",len(v),"median",round(st.median(v),3),"min",round(min(v),3),"p10",round(sorted(v)[int(.1*len(v))],3),"max",round(max(v),3))
fam={}
for x in d["results"]:
    if x.get("shap"):
        v=x["shap"]["0"] if "0" in x["shap"] else x["shap"][0]
        import numpy as np
        m=np.abs(np.array(v["values"])).mean(0);o=np.argsort(-m)[:5]
        print(x["fold"],x["h"],[v["families"][i] for i in o])
