#!/usr/bin/env python3
"""Generate index/dashboard.html -- a zero-dependency, offline-openable dashboard:
  - Interactive provenance graph (force-directed, colored by type; clicking a node highlights its upstream/downstream)
  - Searchable / type-filterable record table (click an ID to jump to the corresponding .md)
Data comes from index/graph.json (run python tools/index.py first).
Usage: python tools/index.py && python tools/dashboard.py  then double-click index/dashboard.html
"""
import os, json, sys, datetime
sys.path.insert(0, os.path.dirname(__file__))
import fm
import registry as R

ROOT = R.ROOT
g = json.load(open(os.path.join(ROOT, "index", "graph.json")))
colors = ["#e6194B","#3cb44b","#4363d8","#f58231","#911eb4","#42d4f4","#f032e6",
          "#bfef45","#fabed4","#469990","#dcbeff","#9A6324","#800000","#808000",
          "#000075","#a9a9a9","#e6beff","#aaffc3","#ffd8b1","#000000"]
types = sorted({n["type"] for n in g["nodes"]})
tcolor = {t: colors[i % len(colors)] for i, t in enumerate(types)}
label = {t: R.TYPES.get(t, {}).get("label", t) for t in types}

# ---- Raw data for the three tabs ----
today = datetime.date.today()
week_ago = (today - datetime.timedelta(days=7)).isoformat()

# This week (read records.csv / or take created_date from nodes; for simplicity just scan md files)
def _load_all_records():
    out = []
    for dp, _, fs in os.walk(ROOT):
        if any(s in dp for s in (".git", "/index", "/templates", "/tools", "/wiki", "/raw", "/docs", "/references", "/inbox", "/reports")):
            continue
        for fn in fs:
            if not fn.endswith(".md"):
                continue
            p = os.path.join(dp, fn)
            meta, _ = fm.parse(p)
            rid = meta.get("id")
            if not rid or "XXXX" in rid:
                continue
            out.append({
                "id": rid,
                "type": meta.get("type", "?"),
                "title": meta.get("title") or meta.get("name") or "",
                "created": str(meta.get("created", ""))[:10],
                "path": os.path.relpath(p, ROOT),
                "wiki_link": meta.get("wiki_link", ""),
                "expiry": str(meta.get("expiry") or meta.get("expiration") or "")[:10],
                "status": meta.get("status", ""),
                "journal": meta.get("journal", ""),
            })
    return out

_all = _load_all_records()
this_week = sorted(
    [r for r in _all if r["created"] and r["created"] >= week_ago],
    key=lambda r: (r["created"], r["id"]),
    reverse=True,
)
unread_lit = sorted(
    [{"id": r["id"], "title": r["title"], "journal": r["journal"], "path": r["path"]}
     for r in _all if r["type"] == "literature" and not r["wiki_link"]],
    key=lambda r: r["id"],
)
_limit = (today + datetime.timedelta(days=30)).isoformat()
expiring = sorted(
    [{"id": r["id"], "title": r["title"], "expiry": r["expiry"], "path": r["path"]}
     for r in _all if r["expiry"] and r["expiry"] <= _limit],
    key=lambda r: r["expiry"],
)

data = {
    "nodes": g["nodes"],
    "edges": g["edges"],
    "tcolor": tcolor,
    "label": label,
    "tabs": {
        "week_since": week_ago,
        "this_week": this_week,
        "unread_lit": unread_lit,
        "expiring": expiring,
    },
}

html = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>ELN Dashboard</title><style>
*{box-sizing:border-box} body{margin:0;font:14px/1.5 -apple-system,Segoe UI,Roboto,sans-serif;color:#1a1a1a}
header{padding:10px 16px;border-bottom:1px solid #e5e5e5;display:flex;gap:12px;align-items:center;flex-wrap:wrap}
header h1{font-size:16px;margin:0}
#legend span{display:inline-flex;align-items:center;gap:4px;margin-right:8px;font-size:12px;cursor:pointer;opacity:.9}
#legend i{width:11px;height:11px;border-radius:50%;display:inline-block}
.wrap{display:flex;height:calc(100vh - 52px)}
#graph{flex:1;border-right:1px solid #eee;background:#fafafa}
aside{width:460px;overflow:auto;padding:0}
.tabs{display:flex;border-bottom:1px solid #e5e5e5;background:#f7f7f7;position:sticky;top:0;z-index:2}
.tabs button{flex:1;padding:9px 6px;background:transparent;border:none;border-bottom:2px solid transparent;
  cursor:pointer;font-size:12.5px;color:#555;font-family:inherit}
.tabs button.active{color:#111;border-bottom-color:#2555d6;background:#fff;font-weight:600}
.tabs button .badge{display:inline-block;min-width:18px;padding:0 5px;margin-left:4px;
  background:#e5e5e5;border-radius:9px;font-size:11px;color:#333}
.tabs button.active .badge{background:#2555d6;color:#fff}
.panel{padding:12px;display:none} .panel.active{display:block}
input{width:100%;padding:7px 9px;border:1px solid #ccc;border-radius:6px;margin-bottom:8px}
table{width:100%;border-collapse:collapse;font-size:12.5px}
th,td{text-align:left;padding:5px 7px;border-bottom:1px solid #f0f0f0;vertical-align:top}
th{position:sticky;top:0;background:#fff;cursor:pointer}
a{color:#2555d6;text-decoration:none} a:hover{text-decoration:underline}
.chip{font-size:11px;padding:1px 6px;border-radius:10px;color:#fff}
text{pointer-events:none;font-size:10px;fill:#333}
.muted{color:#999}
.card{padding:8px 10px;border:1px solid #eee;border-radius:8px;margin-bottom:6px;background:#fff}
.card .tag{font-size:11px;color:#888;margin-right:6px}
.empty{color:#999;padding:24px 8px;text-align:center;font-size:13px}
h3{margin:0 0 10px 0;font-size:13px;color:#444;font-weight:600}
</style></head><body>
<header><h1>🧬 ELN Dashboard</h1><span class=muted id=stat></span><div id=legend></div></header>
<div class=wrap><svg id=graph></svg>
<aside>
  <div class=tabs>
    <button data-tab=records class=active>Records</button>
    <button data-tab=week>This week <span class=badge id=b-week></span></button>
    <button data-tab=unread>To read <span class=badge id=b-unread></span></button>
    <button data-tab=expire>Expiring <span class=badge id=b-expire></span></button>
  </div>
  <div id=p-records class="panel active">
    <input id=q placeholder="Search id / name / type ...">
    <table><thead><tr><th data-k=id>ID</th><th data-k=type>Type</th><th data-k=name>Name</th>
    <th data-k=status>Status</th><th data-k=project>Project</th></tr></thead><tbody id=rows></tbody></table>
  </div>
  <div id=p-week class=panel><h3 id=h-week></h3><div id=list-week></div></div>
  <div id=p-unread class=panel><h3>LIT with empty wiki_link -- awaiting detailed reading</h3><div id=list-unread></div></div>
  <div id=p-expire class=panel><h3>Resources expiring within 30 days</h3><div id=list-expire></div></div>
</aside></div>
<script>
const D=__DATA__;
const NODES=D.nodes.map(n=>({...n,x:Math.random()*800+100,y:Math.random()*600+80,vx:0,vy:0}));
const IDX=Object.fromEntries(NODES.map(n=>[n.id,n]));
const EDGES=D.edges.filter(e=>IDX[e.src]&&IDX[e.dst]);
const svg=document.getElementById('graph');
let W=svg.clientWidth,H=svg.clientHeight,sel=null,hidden={};
function size(){W=svg.clientWidth;H=svg.clientHeight}window.addEventListener('resize',size);size();
// legend
const lg=document.getElementById('legend');
Object.keys(D.tcolor).forEach(t=>{const s=document.createElement('span');
 s.innerHTML='<i style="background:'+D.tcolor[t]+'"></i>'+(D.label[t]||t);
 s.onclick=()=>{hidden[t]=!hidden[t];s.style.opacity=hidden[t]?.3:.9;draw()};lg.appendChild(s)});
document.getElementById('stat').textContent=NODES.length+' records · '+EDGES.length+' relations';
// force sim
function tick(){
 for(const n of NODES){n.vx*=.85;n.vy*=.85}
 for(let i=0;i<NODES.length;i++)for(let j=i+1;j<NODES.length;j++){
  const a=NODES[i],b=NODES[j];let dx=a.x-b.x,dy=a.y-b.y,d=Math.hypot(dx,dy)||1;
  const f=1200/(d*d);a.vx+=dx/d*f;a.vy+=dy/d*f;b.vx-=dx/d*f;b.vy-=dy/d*f}
 for(const e of EDGES){const a=IDX[e.src],b=IDX[e.dst];let dx=b.x-a.x,dy=b.y-a.y,d=Math.hypot(dx,dy)||1;
  const f=(d-90)*.01;a.vx+=dx/d*f;a.vy+=dy/d*f;b.vx-=dx/d*f;b.vy-=dy/d*f}
 for(const n of NODES){n.x+=n.vx;n.y+=n.vy;n.x=Math.max(30,Math.min(W-30,n.x));n.y=Math.max(30,Math.min(H-30,n.y))}
}
const neigh=id=>{const s=new Set([id]);EDGES.forEach(e=>{if(e.src==id)s.add(e.dst);if(e.dst==id)s.add(e.src)});return s};
function draw(){
 let vis=new Set(NODES.filter(n=>!hidden[n.type]).map(n=>n.id));
 let hl=sel?neigh(sel):null;
 let s='';
 for(const e of EDGES){if(!vis.has(e.src)||!vis.has(e.dst))continue;const a=IDX[e.src],b=IDX[e.dst];
  const on=hl&&hl.has(e.src)&&hl.has(e.dst);
  s+='<line x1='+a.x+' y1='+a.y+' x2='+b.x+' y2='+b.y+' stroke="'+(on?'#333':'#ccc')+'" stroke-width="'+(on?1.6:.7)+'"/>'}
 for(const n of NODES){if(!vis.has(n.id))continue;const dim=hl&&!hl.has(n.id);
  s+='<circle cx='+n.x+' cy='+n.y+' r='+(n.id==sel?9:6)+' fill="'+D.tcolor[n.type]+'" opacity="'+(dim?.15:1)+'" stroke="#fff" stroke-width=1.5 style="cursor:pointer" onclick="pick(\\''+n.id+'\\')"><title>'+n.id+' '+(n.name||'')+'</title></circle>';
  if(n.id==sel||(hl&&hl.has(n.id)))s+='<text x='+(n.x+9)+' y='+(n.y+3)+'>'+n.id+'</text>'}
 svg.innerHTML=s;
}
window.pick=id=>{sel=(sel==id?null:id);draw();document.getElementById('q').value=sel||'';render()};
(function loop(){for(let i=0;i<2;i++)tick();draw();requestAnimationFrame(loop)})();
// table
const rows=document.getElementById('rows'),q=document.getElementById('q');let sortk='id';
function render(){
 const f=q.value.toLowerCase();
 let ns=NODES.filter(n=>!f||[n.id,n.type,n.name,n.status,n.project].join(' ').toLowerCase().includes(f));
 ns.sort((a,b)=>(a[sortk]||'').localeCompare(b[sortk]||''));
 rows.innerHTML=ns.map(n=>'<tr><td><a href="../'+n.path+'">'+n.id+'</a></td>'+
  '<td><span class=chip style="background:'+D.tcolor[n.type]+'">'+(D.label[n.type]||n.type)+'</span></td>'+
  '<td>'+(n.name||'')+'</td><td>'+(n.status||'')+'</td><td>'+(n.project||'')+'</td></tr>').join('');
}
q.oninput=render;document.querySelectorAll('th').forEach(th=>th.onclick=()=>{sortk=th.dataset.k;render()});
render();
// ---- tabs ----
const T=D.tabs;
const bWeek=document.getElementById('b-week'),bUnread=document.getElementById('b-unread'),bExpire=document.getElementById('b-expire');
bWeek.textContent=T.this_week.length;bUnread.textContent=T.unread_lit.length;bExpire.textContent=T.expiring.length;
document.getElementById('h-week').textContent='New records since '+T.week_since;
function esc(s){return (s||'').replace(/[&<>\"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
function link(path){return '../'+path}
function chipFor(t){return '<span class=chip style="background:'+(D.tcolor[t]||'#888')+'">'+(D.label[t]||t)+'</span>'}
function renderWeek(){
  const el=document.getElementById('list-week');
  if(!T.this_week.length){el.innerHTML='<div class=empty>No new records in window</div>';return}
  el.innerHTML=T.this_week.map(r=>
    '<div class=card>'+chipFor(r.type)+' <a href="'+link(r.path)+'">'+r.id+'</a> '+
    '<span class=tag>'+r.created+'</span><br>'+esc(r.title||'(untitled)')+'</div>').join('');
}
function renderUnread(){
  const el=document.getElementById('list-unread');
  if(!T.unread_lit.length){el.innerHTML='<div class=empty>🎉 All LIT closed out</div>';return}
  el.innerHTML=T.unread_lit.map(r=>
    '<div class=card><a href="'+link(r.path)+'">'+r.id+'</a> '+
    (r.journal?'<span class=tag>'+esc(r.journal)+'</span>':'')+
    '<br><b>'+esc(r.title||'(untitled)')+'</b></div>').join('');
}
function renderExpire(){
  const el=document.getElementById('list-expire');
  if(!T.expiring.length){el.innerHTML='<div class=empty>No expiring resources</div>';return}
  el.innerHTML=T.expiring.map(r=>
    '<div class=card><a href="'+link(r.path)+'">'+r.id+'</a> '+
    '<span class=tag>'+r.expiry+'</span><br>'+esc(r.title||'(unnamed)')+'</div>').join('');
}
renderWeek();renderUnread();renderExpire();
document.querySelectorAll('.tabs button').forEach(b=>{
  b.onclick=()=>{
    document.querySelectorAll('.tabs button').forEach(x=>x.classList.remove('active'));
    document.querySelectorAll('.panel').forEach(x=>x.classList.remove('active'));
    b.classList.add('active');
    document.getElementById('p-'+b.dataset.tab).classList.add('active');
  };
});
</script></body></html>"""

out = os.path.join(ROOT, "index", "dashboard.html")
open(out, "w", encoding="utf-8").write(html.replace("__DATA__", json.dumps(data, ensure_ascii=False)))
print("→ index/dashboard.html  (double-click to open in browser)")
