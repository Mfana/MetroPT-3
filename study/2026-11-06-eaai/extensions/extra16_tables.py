"""Addendum 3 summaries from tables/extra16-*.csv, applying the rules fixed in the addendum."""
import csv, statistics as st
C = list(csv.DictReader(open("tables/extra16-cells.csv")))
E = list(csv.DictReader(open("tables/extra16-intervals.csv")))
R = list(csv.DictReader(open("tables/extra16-rank.csv")))
n = float
MODELS = ["M1", "M2", "M3", "M4", "M5", "M6"]; H = ["30", "60", "180", "360", "720"]
A = [r for r in C if r["kind"] == "A"]; K = [r for r in C if r["kind"] == "E"]
print("== 1. False alarms, analysis A, pooled per model")
for m in MODELS:
    x = [r for r in A if r["model"] == m]
    f4, d4, f16, d16, fn, dn = (sum(n(r[k]) for r in x) for k in ("fa4", "days4", "fa16", "days16", "fa16_norec", "days16_norec"))
    print(m, "FA", int(f4), "->", int(f16), "(no rec", int(fn), ") days %.0f -> %.0f (%.0f)" % (d4, d16, dn),
          "rate %.3f -> %.3f (%.3f)" % (f4 / d4, f16 / d16, fn / dn),
          "| in removed time: %d FA in %.0f days, %.3f/day; remaining %.3f/day" % (f4 - f16, d4 - d16, (f4 - f16) / (d4 - d16), f16 / d16),
          "| median cell %.3f -> %.3f" % (st.median(n(r["fa_day4"]) for r in x), st.median(n(r["fa_day16"]) for r in x)))
print("== Burden rule (A median <=1 and E <=1), per model and horizon")
rows = []
for m in MODELS:
    for h in H:
        a = [r for r in A if r["model"] == m and r["h"] == h]
        e = [r for r in K if r["model"] == m and r["h"] == h]
        if not a or not e:
            continue
        d = {}
        for tag, col in (("4", "fa_day4"), ("16", "fa_day16"), ("16n", "fa_day16_norec")):
            d["a" + tag] = st.median(n(r[col]) for r in a); d["e" + tag] = n(e[0][col]); d["pass" + tag] = d["a" + tag] <= 1 and d["e" + tag] <= 1
        # Section 3: warning across reports and intervals.
        rep_tests = sum(int(r["rep_tests"]) for r in a); rep_valid = sum(int(r["rep_valid"]) for r in a)
        x_tests = sum(int(r["x_tests"]) for r in a); x_valid = sum(int(r["x_valid"]) for r in a); x_caught = sum(int(r["x_caught"]) for r in a); xb = sum(int(r["x_valid_before_run"]) for r in a)
        share = (rep_valid + x_valid) / (rep_tests + x_tests) if rep_tests + x_tests else 0
        rows.append(dict(model=m, h=h, fa_A_4=round(d["a4"], 3), fa_E_4=round(d["e4"], 3), burden_4=d["pass4"], fa_A_16=round(d["a16"], 3), fa_E_16=round(d["e16"], 3), burden_16=d["pass16"], fa_A_16n=round(d["a16n"], 3), fa_E_16n=round(d["e16n"], 3), burden_16n=d["pass16n"],
                         rep_tests=rep_tests, rep_valid=rep_valid, x_tests=x_tests, x_caught=x_caught, x_valid=x_valid, x_valid_before_run=xb, warn_share=round(share, 3), warn_75=share >= .75, both=share >= .75 and d["pass16"]))
for r in rows:
    print(r["model"], r["h"], "A/E 4: %s/%s %s | 16: %s/%s %s | no rec: %s/%s %s | rep %d/%d x caught %d valid %d before-run %d of %d share %.2f %s" % (r["fa_A_4"], r["fa_E_4"], r["burden_4"], r["fa_A_16"], r["fa_E_16"], r["burden_16"], r["fa_A_16n"], r["fa_E_16n"], r["burden_16n"], r["rep_valid"], r["rep_tests"], r["x_caught"], r["x_valid"], r["x_valid_before_run"], r["x_tests"], r["warn_share"], "WARN75" if r["warn_75"] else ""))
with open("tables/extra16-rules.csv", "w", newline="") as x:
    w = csv.DictWriter(x, list(rows[0])); w.writeheader(); w.writerows(rows)
print("burden pass 4:", sum(r["burden_4"] for r in rows), "16:", sum(r["burden_16"] for r in rows), "16 no rec:", sum(r["burden_16n"] for r in rows), "of", len(rows))
print("newly passing:", [(r["model"], r["h"]) for r in rows if r["burden_16"] and not r["burden_4"]], "no rec:", [(r["model"], r["h"]) for r in rows if r["burden_16n"] and not r["burden_4"]])
print("meet warn75:", sum(r["warn_75"] for r in rows), "both:", sum(r["both"] for r in rows))
print("== 2. Warning on intervals, analysis A")
EA = [r for r in E if r["kind"] == "A"]; T = [r for r in EA if r["scorable"] == "1"]; Ca = [r for r in T if r["caught"] == "1"]
V = [r for r in Ca if n(r["chance"]) < .5]; B = [r for r in V if r["before_run"] == "1"]
print("rows", len(EA), "scorable", len(T), "caught", len(Ca), "valid", len(V), "valid before run", len(B), "share %.3f" % (len(B) / len(T)))
for m in MODELS:
    x = [r for r in T if r["model"] == m]; print(" ", m, "tests", len(x), "caught", sum(r["caught"] == "1" for r in x), "valid", sum(r in V for r in x), "before run", sum(r in B for r in x), "median chance %.3f" % st.median(n(r["chance"]) for r in x))
for h in H:
    x = [r for r in T if r["h"] == h]; print(" h", h, "tests", len(x), "caught", sum(r["caught"] == "1" for r in x), "valid", sum(r in V for r in x), "before run", sum(r in B for r in x))
for iv in sorted({r["interval"] for r in EA}, key=lambda s: int(s[1:])):
    x = [r for r in T if r["interval"] == iv]; print(" ", iv, "tests", len(x), "caught", sum(r["caught"] == "1" for r in x), "valid", sum(r in V for r in x), "before run", sum(r in B for r in x), "| active alarm", sum(r["active_alarm"] == "1" for r in EA if r["interval"] == iv), "of", sum(r["interval"] == iv for r in EA))
print("expected from chance, sum of chance rates %.1f; observed caught %d" % (sum(n(r["chance"]) for r in T), len(Ca)))
print("caught detail", [(r["fold"], r["h"], r["model"], r["interval"], r["lead"], round(n(r["chance"]), 3), r["before_run"]) for r in Ca][:60])
print("== all registered cells")
Tall = [r for r in E if r["scorable"] == "1"]; Call = [r for r in Tall if r["caught"] == "1"]; Vall = [r for r in Call if n(r["chance"]) < .5]
print("tests", len(Tall), "caught", len(Call), "valid", len(Vall), "before run", sum(r["before_run"] == "1" for r in Vall))
print("== 4. Rank")
for t in ("warning", "active"):
    for m in MODELS:
        x = [r for r in R if r["target"] == t and r["model"] == m and r["auroc"]]
        print(t, m, " ".join("%s:%.2f" % (h, st.median(n(r["auroc"]) for r in x if r["h"] == h)) for h in H), "| cells auroc>0.5 & share<.05:", sum(n(r["auroc"]) > .5 and n(r["share_at_least_observed"]) < .05 for r in x), "of", len(x))
print("active alarm: analysis A", sum(r["active_alarm"] == "1" for r in EA), "of", len(EA), {m: sum(r["active_alarm"] == "1" for r in EA if r["model"] == m) for m in MODELS})
