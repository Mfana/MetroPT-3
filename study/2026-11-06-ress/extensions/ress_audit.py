"""Preflight for the RESS staging folder. The bundled audit.py checks EAAI rules (anonymity, AI-novelty labels), which do not apply here."""
import hashlib,json,re,subprocess,sys
from pathlib import Path
root=Path(sys.argv[1]);p=[]
tex=(root/"manuscript.tex").read_text();title=(root/"title-page.tex").read_text();bib=(root/"references.bib").read_text()
body=subprocess.run(["pdftotext","-layout",str(root/"manuscript.pdf"),"-"],capture_output=True,text=True).stdout
ab=re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}",tex,re.S).group(1)
words=len(ab.split());words<=200 or p.append(f"Abstract has {words} words, limit 200")
kw=[k for k in re.search(r"\\begin\{keyword\}(.*?)\\end\{keyword\}",tex,re.S).group(1).split(r"\sep") if k.strip()]
1<=len(kw)<=7 or p.append("Keywords must number 1 to 7")
[p.append(f"Keyword uses 'and' or 'of': {k.strip()}") for k in kw if re.search(r"\b(and|of)\b",k)]
hl=[l.strip().removeprefix("- ") for l in (root/"highlights.txt").read_text().splitlines() if l.strip()]
3<=len(hl)<=5 or p.append("Highlights must number 3 to 5")
[p.append(f"Highlight over 85 characters: {h}") for h in hl if len(h)>85]
"highlights" in "highlights.txt" or p.append("Highlights file name")
n=len(body.split());n<=13000 or p.append(f"Compiled text has {n} words, limit 13,000")
pos=[tex.find(x) for x in("Declaration of generative AI","\\section*{Acknowledgements}","\\bibliography{references}")]
(-1 not in pos and pos==sorted(pos)) or p.append("Order must be generative AI declaration, acknowledgements, references")
"Data availability" in tex or p.append("Data statement missing")
"[dataset]" in bib or p.append("Dataset reference not marked [dataset]")
[p.append(f"Unresolved placeholder in {name}: {m}") for name,t in(("manuscript.tex",tex),("title-page.tex",title)) for m in re.findall(r"\[REPLACE[^\]]*\]",t)]
log=(root/"manuscript.log").read_text()
re.search(r"undefined|multiply defined|rerun to get",log,re.I) and p.append("Log reports unresolved references")
cited=set(k for c in re.findall(r"\\cite\{([^}]+)\}",tex) for k in c.split(","))
keys=set(re.findall(r"@\w+\{([^,]+),",bib));[p.append(f"Citation missing from bibliography: {k}") for k in cited-keys]
[p.append(f"Figure not found: {f}") for f in re.findall(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}",tex) if not (root/f).exists()]
[p.append(f"Banned EAAI label: {x}") for x in("AI novelty.","Engineering application.","Engineering Applications of Artificial Intelligence") if x in tex]
ledger=root/"claim-ledger.csv"
ledger.exists() or p.append("Claim ledger missing")
human=(root/"author-signoff.txt")
human.exists() or p.append("Human author sign-off not recorded")
out=dict(status="blocked" if p else "automated_preflight_pass",abstract_words=words,keywords=len(kw),highlights=len(hl),max_highlight=max(map(len,hl)),compiled_words=n,cited=len(cited),issues=p)
print(json.dumps(out,indent=1));(root/"audit-ress.json").write_text(json.dumps(out,indent=1)+"\n")
