import json,sys,glob,datetime
TODAY='2026-06-27'
d=json.load(open('site/data.json'))
kwf=json.load(open('keywords.json')); kmap=kwf['map']
try: alog=json.load(open('attempt_log.json'))
except: alog={}
by_id={c['id']:c for c in d['collections']}
nprz=ncol=0
for f in sorted(glob.glob('results_*.json')):
    r=json.load(open(f))
    for cid,k in r.get('keywords',{}).items(): kmap[cid]=k
    for cid,prizes in r.get('prices',{}).items():
        c=by_id.get(cid)
        if not c: continue
        hit=False
        for p in c['prizes']:
            pz=str(p['pz']).strip()
            key=None
            if pz in prizes: key=pz
            elif pz.upper() in prizes: key=pz.upper()
            elif pz.lower() in ('lo','last one','lastone'):
                for cand in ('LO','Last one','Last One','lastone'):
                    if cand in prizes: key=cand;break
            if key is not None and p.get('jp') is None:
                p['jp']=prizes[key]; nprz+=1; hit=True
        if hit: ncol+=1
    # attempt log
    for cid,note in r.get('attempts',{}).items():
        alog[cid]={'date':TODAY,'result':note}
d['rate']=0.2068; d['updated']=TODAY
json.dump(d,open('site/data.json','w'),ensure_ascii=False,indent=1)
json.dump(kwf,open('keywords.json','w'),ensure_ascii=False,indent=1)
json.dump(alog,open('attempt_log.json','w'),ensure_ascii=False,indent=1)
print('merged: +%d prizes across %d collections | keywords=%d | attempts logged=%d'%(nprz,ncol,len(kmap),len(alog)))
