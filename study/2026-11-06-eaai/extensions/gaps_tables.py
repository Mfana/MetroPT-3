"""Results tables for provenance/registered-plan-addendum-gaps.md. Uses saved outputs only; refits nothing."""
import csv,json,os,statistics as st,subprocess,sys
from pathlib import Path
import numpy as np
from scipy.stats import rankdata
sys.path.insert(0,"extensions")
import rescore
H=[30,60,180,360,720];F=["apr18","may29","jun05","jul15"];LAB=dict(zip(H,("30 min","1 h","3 h","6 h","12 h")));G="runs/gaps"
key=lambda x:(x["fold"],x["h"],x["model"])
def load(p): return json.load(open(f"{p}/run.json"))["results"]
frozen=load("runs/seq-study")
def rows_seq(rs):
    out=[]
    for r in rs:
        if r.get("kind")=="exploratory": continue
        w,u,c,p=r["window"],r["uncalibrated"],r["platt_calibrated"],r["policy"];f=p["failures"]
        cau=[v for v in f.values() if v["caught"]]
        out.append(dict(fold=r["fold"],kind=r["kind"],h=r["h"],model=r["model"],ap=w["average_precision"],auroc=w["auroc"],bss=c.get("brier_skill"),slope=c.get("calibration_slope"),b=r["platt"][1],failures=len(f),caught=len(cau),lead=";".join(str(v["first_lead_minutes"]) for v in cau),chance=max([v["chance_rate_under_circular_shift"] for v in cau],default=None),fa_day=p["false_alarms_per_day"],fa=p["false_alarm_episodes"],occ=p["alarm_occupancy"]))
    return out
def rows_event(path):
    out=[]
    for r in csv.DictReader(open(path)):
        fl=lambda k:(float(r[k]) if r[k] not in("","None") else None)
        ch=[float(x) for x,l in zip(r["chance"].split(";"),r["leads"].split(";")) if l not in("None","") and x not in("None","")]
        out.append(dict(fold=r["fold"],kind=r["kind"],h=int(r["h"]),model=r["model"],ap=fl("ap"),auroc=fl("auroc"),bss=fl("bss_platt"),slope=fl("slope_platt"),b=fl("platt_b"),failures=int(r["failures"]),caught=int(r["caught"]),lead=r["leads"],chance=max(ch,default=None),fa_day=fl("fa_day"),fa=int(r["fa"]),occ=None))
    return out
def get(rows,fold,h,m): return next(r for r in rows if r["fold"]==fold and r["h"]==h and r["model"]==m)
def rules(rows,comp,m,h):
    A=[get(rows,f"A_hold{f}",h,m) for f in F];C=[get(comp,f"A_hold{f}",h,"M1") for f in F]
    D,D1,E=get(rows,"D_forward_jul15",h,m),get(comp,"D_forward_jul15",h,"M1"),get(rows,"E_false_alarm_after_jul16",h,m)
    base=sum(a["bss"]>0 for a in A);state=sum(a["ap"]>c["ap"] and a["bss"]>c["bss"] for a,c in zip(A,C));sD=D["ap"]>D1["ap"] and D["bss"]>D1["bss"]
    slope=sum(a["b"]>0 and a["slope"] is not None and .7<=a["slope"]<=1.3 for a in A)
    caught=[a for a in A if a["caught"]];valid=sum(a["chance"]<.5 for a in caught);fa=st.median(a["fa_day"] for a in A)
    p=dict(pass_base=base==4,pass_state=state>=3 and sD,pass_slope=slope>=3,pass_warning=valid>=3,pass_burden=fa<=1 and E["fa_day"]<=1)
    return dict(model=m,horizon=LAB[h],skill_pos=base,beats_m1=state,beats_m1_forward=sD,slope_in_range=slope,caught=len(caught),caught_valid=valid,fa_median=fa,fa_after_jul16=E["fa_day"],median_auroc=st.median(a["auroc"] for a in A),**p,rules_met=sum(p.values()),defensible=sum(p.values())==5)
P=Path("tables/primary-metrics.csv");base_event=rows_event(P)
S0=rows_seq(frozen)
# The rule code must reproduce the frozen sequence rule table before it is used on new runs.
for o in csv.DictReader(open("tables/seq-rule-outcomes.csv")):
    h=[k for k,v in LAB.items() if v==o["horizon"]][0];n=rules(S0,base_event,o["model"],h)
    assert n["rules_met"]==int(o["rules_met_of_5"]) and n["caught"]==int(o["caught_of_4"]) and n["slope_in_range"]==int(o["slope_in_range_of_4"]) and n["beats_m1"]==int(o["beats_m1_of_4"]),(o,n)
print("rule code reproduces frozen table: yes")
def write(name,rows):
    with open(f"tables/{name}","w",newline="") as x:
        w=csv.DictWriter(x,list(rows[0]));w.writeheader();w.writerows(rows)
# 1. Held-in
hi=load(f"{G}/heldin");fd={key(r):r.get("prediction_digest") for r in frozen}
same=sum(fd[key(r)]==r["prediction_digest"] for r in hi);print("heldin digests identical",same,"of",len(hi));assert same==len(hi)
t=[]
for r in hi:
    per=[v["auroc"] for v in r["heldin_by_failure"].values() if v["auroc"] is not None]
    t.append(dict(fold=r["fold"],h=r["h"],model=r["model"],train_windows=r["train_windows"],train_positives=r["train_positives"],heldin_auroc=r["heldin_auroc"],heldin_ap=r["heldin_ap"],heldin_min_failure_auroc=min(per),heldout_auroc=r["heldout_auroc"],heldout_ap=r["heldout_ap"]))
write("gaps-heldin.csv",t)
for m in("M5","M6"):
    for h in H:
        s=[x for x in t if x["model"]==m and x["h"]==h];md=st.median(x["heldin_auroc"] for x in s)
        print("heldin",m,LAB[h],"train",round(md,3),"AP",round(st.median(x["heldin_ap"] for x in s),3),"min within failure",round(min(x["heldin_min_failure_auroc"] for x in s),3),"heldout",round(st.median(x["heldout_auroc"] for x in s),3),"verdict",">=.90" if md>=.9 else ("<.80" if md<.8 else "mixed"))
# 2. Rerun
a={key(r):r["prediction_digest"] for r in load(f"{G}/seed1791")};b=load(f"{G}/seed1791-rerun");same=sum(a[key(r)]==r["prediction_digest"] for r in b);print("seed rerun digests identical",same,"of",len(b));assert same==len(b)
# 3. Seeds
SEEDS={791:S0,**{s:rows_seq(load(f"{G}/seed{s}")) for s in(1791,2791,3791,4791)}}
RC=[]
def chance(path,seed,rng):
    idx,marg,_,lab=rescore.read_scores(path);o=np.argsort(idx);lab,marg=lab[o],marg[o];k=lab>=0;y=lab[k]==1;s=marg[k];n,pos=len(y),int(y.sum())
    r=rankdata(s);au=lambda m:(r[m].sum()-pos*(pos+1)/2)/(pos*(n-pos));gap=np.minimum(np.arange(n),n-np.arange(n))
    sim=np.array([au(np.roll(y,int(q))) for q in rng.choice(np.flatnonzero(gap>=pos),1000,replace=False)])
    return au(y),float(np.quantile(sim,.95)),float((sim>=au(y)).mean())
rng=np.random.default_rng(791);met=[];allseed=[];RCrows=[]
for s,rows in SEEDS.items():
    for m in("M5","M6"):
        for h in H:
            o=rules(rows,base_event,m,h);met.append(dict(seed=s,**o))
    for r in rows: allseed.append(dict(seed=s,**r))
    if s!=791:
        for f in F:
            for h in H:
                for m in("M5","M6"):
                    obs,p95,sh=chance(f"{G}/seed{s}/scores/A_hold{f}_h{h}_{m}.csv.gz",s,rng);assert abs(obs-get(rows,f"A_hold{f}",h,m)["auroc"])<1e-5
                    RCrows.append(dict(seed=s,fold=f"A_hold{f}",h=h,model=m,auroc=obs,shift_p95=p95,share_at_least_observed=sh))
write("gaps-seed-metrics.csv",allseed);write("gaps-seed-rules.csv",met);write("gaps-seed-chance.csv",RCrows)
print("seed rules: defensible",sum(x["defensible"] for x in met),"of",len(met),"; rules met distribution",{k:sum(x["rules_met"]==k for x in met) for k in range(6)})
print("max per rule:",{k:sum(x[k] for x in met) for k in("pass_base","pass_state","pass_slope","pass_warning","pass_burden")},"max caught_valid",max(x["caught_valid"] for x in met))
for s,rows in SEEDS.items():
    print("seed",s,"tests",sum(r["failures"] for r in rows if r["kind"] in"ABDE" ),"A caught",sum(r["caught"] for r in rows if r["kind"]=="A"),"of",sum(r["failures"] for r in rows if r["kind"]=="A"),"all-fold caught",sum(r["caught"] for r in rows),"of",sum(r["failures"] for r in rows),"bss>0",sum(r["bss"]>0 for r in rows if r["kind"]=="A"),"slope in range",sum(r["b"]>0 and r["slope"] is not None and .7<=r["slope"]<=1.3 for r in rows if r["kind"]=="A"),"b==0",sum(r["b"]==0 for r in rows if r["kind"]=="A"))
print("ALL caught cells (any seed, same folds):",[(s,r["fold"],r["h"],r["model"],r["lead"],r["chance"],round(r["fa_day"],2),round(r["auroc"],3)) for s,rows in SEEDS.items() for r in rows if r["caught"]])
same_folds=lambda r:r["kind"] in"ADE" or r["fold"]=="B_hold_may29_jun05"
print("extra-seed tests",sum(r["failures"] for s,rows in SEEDS.items() if s!=791 for r in rows),"caught",sum(r["caught"] for s,rows in SEEDS.items() if s!=791 for r in rows))
print("frozen same-fold tests",sum(r["failures"] for r in S0 if same_folds(r)))
sp=[];
for f in F:
    for h in H:
        for m in("M5","M6"):
            v=[get(SEEDS[s],f"A_hold{f}",h,m)["auroc"] for s in SEEDS];sp.append(dict(failure=f,h=h,model=m,min=min(v),median=st.median(v),max=max(v),range=max(v)-min(v),above_half=sum(x>.5 for x in v),**{f"s{s}":x for s,x in zip(SEEDS,v)}))
write("gaps-seed-auroc-range.csv",sp)
print("AUROC range across seeds per cell: median",round(st.median(x["range"] for x in sp),3),"max",round(max(x["range"] for x in sp),3))
for m in("M5","M6"):
    for f in F: print(m,f,[f"{LAB[h]}: {get_[0]:.2f}-{get_[1]:.2f} med {get_[2]:.2f}" for h in H for get_ in [(lambda x:(x['min'],x['max'],x['median']))(next(y for y in sp if y['failure']==f and y['h']==h and y['model']==m))]])
for m in("M5","M6"):
    print("median of per-horizon medians by seed",m,[(s,[round(st.median(get(SEEDS[s],f"A_hold{f}",h,m)["auroc"] for f in F),2) for h in H]) for s in SEEDS])
    print("May29+Jun5 by seed",m,[(s,[round(get(SEEDS[s],"B_hold_may29_jun05",h,m)["auroc"],2) for h in H]) for s in SEEDS])
print("chance: cells",len(RCrows),"auroc>.5 & share<.05",sum(r["auroc"]>.5 and r["share_at_least_observed"]<.05 for r in RCrows),"by failure",{f:sum(r["fold"]==f"A_hold{f}" and r["auroc"]>.5 and r["share_at_least_observed"]<.05 for r in RCrows) for f in F},"cells:",[(r["seed"],r["fold"][6:],r["h"],r["model"],round(r["auroc"],2),r["share_at_least_observed"]) for r in RCrows if r["auroc"]>.5 and r["share_at_least_observed"]<.05])
print("low tail share>.95",sum(r["share_at_least_observed"]>.95 for r in RCrows),"p95 median",round(st.median(r["shift_p95"] for r in RCrows),2))
# 4. Timing
tm=[];mm=[]
for tag,d in(("minus60",-60),("plus60",60)):
    subprocess.run([sys.executable,"-B","-W","ignore","extensions/rescore.py",f"{G}/event-{tag}",f"tables/gaps-shift-event-{tag}.csv",f"tables/gaps-shift-event-oracle-{tag}.csv"],check=True)
    ev=rows_event(f"tables/gaps-shift-event-{tag}.csv");sq=rows_seq(load(f"{G}/shift-{tag}"));rows=ev+sq
    for m in("M3","M5","M6"):
        for h in H: tm.append(dict(shift=d,**rules(rows,ev,m,h)))
    for r in rows: mm.append(dict(shift=d,**r))
    print("shift",d,"tests",sum(r["failures"] for r in rows),"caught",sum(r["caught"] for r in rows),"cells:",[(r["fold"],r["h"],r["model"],r["lead"],r["chance"],round(r["fa_day"],2),round(r["auroc"],3)) for r in rows if r["caught"]])
    for m in("M1","M2","M3","M4","M5","M6"):
        s=[r for r in rows if r["kind"]=="A" and r["model"]==m]
        print(" ",m,"med AUROC",[round(st.median(r["auroc"] for r in s if r["h"]==h),2) for h in H],"caught A",sum(r["caught"] for r in s),"bss>0",sum(r["bss"]>0 for r in s),"b==0",sum(r["b"]==0 for r in s),"slope ok",sum(r["b"]>0 and r["slope"] is not None and .7<=r["slope"]<=1.3 for r in s))
    for m in("M5","M6"): print("  may29",m,[round(get(rows,"A_holdmay29",h,m)["auroc"],2) for h in H])
    print("  burden/ rules",[(x["model"],x["horizon"],x["rules_met"],round(x["fa_median"],2),round(x["fa_after_jul16"],2)) for x in tm if x["shift"]==d])
write("gaps-shift-rules.csv",tm);write("gaps-shift-metrics.csv",mm)
print("shift defensible",sum(x["defensible"] for x in tm),"of",len(tm),"max rule counts",{k:sum(x[k] for x in tm) for k in("pass_base","pass_state","pass_slope","pass_warning","pass_burden")})
