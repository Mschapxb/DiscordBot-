"""
admin_pages.py — Pages HTML du panneau d'administration de Tenebris.

Trois constantes, extraites de bot.py pour alléger le monolithe (~2 200 lignes de HTML/CSS/JS) :
  • ADMIN_HTML   : le panneau /admin
  • FORUM_HTML   : la copie interne du forum, page /forum
  • SERVEUR_HTML : « ce que Tenebris a compris » du serveur, page /serveur

Ce sont des chaînes brutes servies telles quelles (aucune substitution côté Python) : on peut
les éditer ici sans toucher à la logique du bot.
"""

FORUM_HTML = r"""<!DOCTYPE html>
<html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Forum — copie interne de Tenebris</title>
<style>
:root{--bg:#0e0d13;--panel:#17151f;--panel2:#1e1b28;--line:#2c2838;--txt:#e7e3f0;--dim:#9a93ad;--acc:#b57edc;--acc2:#7c5cbf}
*{box-sizing:border-box}
body{margin:0;font-family:system-ui,Segoe UI,Roboto,sans-serif;background:var(--bg);color:var(--txt);height:100vh;display:flex;flex-direction:column}
header{padding:12px 18px;background:var(--panel);border-bottom:1px solid var(--line);display:flex;align-items:center;gap:14px;flex-wrap:wrap}
header h1{font-size:16px;margin:0;color:var(--acc)}
header .stats{color:var(--dim);font-size:12px}
header a{color:var(--acc);text-decoration:none;font-size:13px}
#search{margin-left:auto;display:flex;gap:6px}
#search input{background:var(--panel2);border:1px solid var(--line);color:var(--txt);border-radius:8px;padding:7px 10px;width:240px}
#search button{background:var(--acc2);border:0;color:#fff;border-radius:8px;padding:7px 12px;cursor:pointer}
main{flex:1;display:flex;min-height:0}
#tree{width:340px;overflow:auto;border-right:1px solid var(--line);background:var(--panel)}
#view{flex:1;overflow:auto;padding:22px 26px}
.sec{border-bottom:1px solid var(--line)}
.sec>.h{padding:10px 14px;cursor:pointer;font-weight:600;display:flex;justify-content:space-between;gap:8px;color:var(--acc)}
.sec>.h:hover{background:var(--panel2)}
.sec .items{display:none}
.sec.open .items{display:block}
.topic{padding:7px 14px 7px 26px;cursor:pointer;font-size:13.5px;color:var(--txt);border-left:3px solid transparent;display:flex;gap:6px;align-items:center}
.topic:hover{background:var(--panel2)}
.topic.active{background:var(--panel2);border-left-color:var(--acc)}
.dot{width:7px;height:7px;border-radius:50%;flex:0 0 auto}
.dot.ok{background:#5fd68a}.dot.no{background:#54506a}
.count{color:var(--dim);font-weight:400;font-size:12px}
#view h2{color:var(--acc);margin:0 0 4px}
#view .path{color:var(--dim);font-size:13px;margin-bottom:2px}
#view .maj{color:var(--dim);font-size:12px;margin-bottom:16px}
#view .kw{background:var(--panel2);border:1px solid var(--line);border-radius:8px;padding:8px 12px;color:var(--dim);font-size:13px;margin-bottom:16px}
#view .liens{background:var(--panel2);border:1px solid var(--line);border-radius:8px;padding:8px 12px;font-size:13px;margin-bottom:16px;line-height:1.8}
#view .liens a{color:var(--acc);text-decoration:none}
#view .liens a:hover{text-decoration:underline}
#view .path.orph{color:#e0a24e}
.tree{border:1px solid var(--line);border-radius:8px;padding:10px 12px;background:var(--panel);margin-bottom:14px}
.tnode{padding:2px 0}
.tnode>a,.tleaf a{color:var(--acc);text-decoration:none}
.tnode>a:hover,.tleaf a:hover{text-decoration:underline}
.tw{cursor:pointer;user-select:none;color:var(--dim);display:inline-block;width:14px}
.tkids{margin-left:16px;border-left:1px solid var(--line);padding-left:10px}
.twrap{position:relative}
.ttype{color:var(--dim);font-size:11px;margin-right:2px}
.tleaf{padding:2px 0 2px 16px;font-size:13px;color:var(--txt)}
.dim{color:var(--dim);font-size:12px}
#view h3{margin:18px 0 8px}
.lk{display:inline-flex;align-items:center;gap:4px;background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:2px 6px 2px 10px;margin:2px 3px}
.lk.man{border-color:var(--acc)}
.lk.men{border-style:dashed}
.lk i{cursor:pointer;color:var(--dim);font-style:normal;font-size:11px;padding:0 3px}
.lk i:hover{color:#e06a6a}
.liens input{background:var(--bg);border:1px solid var(--line);color:var(--txt);border-radius:8px;padding:5px 9px;min-width:230px;margin:0 6px}
.liens .mini,#view .mini{background:var(--acc2);border:0;color:#fff;border-radius:8px;padding:5px 11px;cursor:pointer;font-size:13px}
#svgwrap{background:var(--panel);border:1px solid var(--line);border-radius:12px;margin-top:10px;overflow:hidden}
#schema line.e{stroke:var(--line);stroke-width:1.4}
#schema line.eman{stroke:var(--acc);stroke-width:2}
#schema line.emen{stroke:var(--line);stroke-dasharray:4 3}
#schema circle{cursor:pointer;stroke:var(--bg);stroke-width:2}
#schema circle.c0{fill:var(--acc)}
#schema circle.c1{fill:var(--acc2)}
#schema circle.c2{fill:#4a4460}
#schema text{fill:var(--txt);font-size:11px;text-anchor:middle;pointer-events:none}
.lg{margin-left:10px}
.lg i{display:inline-block;width:9px;height:9px;border-radius:50%;margin:0 4px 0 10px}
.lg i.c0{background:var(--acc)}.lg i.c1{background:var(--acc2)}.lg i.c2{background:#4a4460}
#view .notes{background:var(--panel2);border:1px solid var(--line);border-left:3px solid var(--acc);border-radius:8px;padding:6px 14px;margin-bottom:16px;font-size:13.5px}
#view .notes ul{margin:6px 0;padding-left:20px}
#view .notes li{margin:3px 0}
.synthead{display:flex;justify-content:space-between;align-items:baseline;margin-bottom:6px}
#view pre{white-space:pre-wrap;word-wrap:break-word;line-height:1.55;font-family:inherit;font-size:14.5px;margin:0}
#view a.src{color:var(--acc);font-size:12px;text-decoration:none}
.empty{color:var(--dim);margin-top:40px;text-align:center}
.res{padding:12px 14px;border-bottom:1px solid var(--line);cursor:pointer}
.res:hover{background:var(--panel2)}
.res .t{color:var(--acc);font-weight:600}
.res .x{color:var(--dim);font-size:12.5px;margin-top:3px}
</style></head>
<body>
<header>
  <h1>📚 Forum — copie interne</h1>
  <span class="stats" id="stats">…</span>
  <a href="/admin">← retour admin</a>
  <a href="#" onclick="showGraph();return false" style="margin-left:2px">🌳 vue graphe</a>
  <a href="#" onclick="showSchema('');return false" style="margin-left:2px">🕸️ schéma global</a>
  <div id="search"><input id="q" placeholder="Rechercher dans le forum…" />
    <button onclick="doSearch()">Chercher</button></div>
</header>
<main>
  <div id="tree"></div>
  <div id="view"><div class="empty">Choisis un sujet à gauche, ou lance une recherche.</div></div>
</main>
<script>
const esc = s => (s||"").replace(/[&<>]/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
async function api(params){ const r = await fetch("/admin/api/forum?"+params); if(r.status===401){location.href="/admin";return null;} return r.json(); }
async function load(){
  const d = await api("action=tree"); if(!d) return;
  const s = d.stats||{};
  document.getElementById("stats").textContent =
     `${s.total||0} sujets · ${s.sujets_copies||0} copiés (${Math.round((s.octets||0)/1024)} Ko) · ${d.forum||""}`;
  const tree = d.tree||{}; const box = document.getElementById("tree"); box.innerHTML="";
  for(const [sec, items] of Object.entries(tree)){
    const div = document.createElement("div"); div.className="sec";
    div.innerHTML = `<div class="h">${esc(sec)} <span class="count">${items.length}</span></div><div class="items"></div>`;
    const it = div.querySelector(".items");
    items.forEach(t=>{
      const el=document.createElement("div"); el.className="topic";
      el.innerHTML=`<span class="dot ${t.copie?'ok':'no'}"></span>${esc(t.titre)}`;
      el.onclick=()=>openTopic(t.url, el);
      it.appendChild(el);
    });
    div.querySelector(".h").onclick=()=>div.classList.toggle("open");
    box.appendChild(div);
  }
}
let cur=null;
async function openTopic(url, el){
  if(cur) cur.classList.remove("active"); if(el){el.classList.add("active");cur=el;}
  const d = await api("action=topic&url="+encodeURIComponent(url)); if(!d) return;
  const v=document.getElementById("view");
  if(d.error){v.innerHTML=`<div class="empty">${esc(d.error)}</div>`;return;}
  v.innerHTML = `<h2>${esc(d.titre)}</h2>`
    + (d.chemin?`<div class="path">📍 ${esc(d.chemin)}</div>`:`<div class="path orph">⚠️ sans rubrique</div>`)
    + `<div class="maj">Copié le ${esc(d.maj||"?")} · <a class="src" href="${esc(d.url)}" target="_blank">voir sur le forum ↗</a></div>`
    + (d.resume?`<div class="kw">🔑 ${esc(d.resume)}</div>`:``)
    + ((d.liens&&d.liens.length)?`<div class="liens"><b>🔗 Cite :</b> `
        + d.liens.map(l=>`<span class="lk ${l.type==='manuel'?'man':(l.type==='mention'?'men':'')}" title="${l.type==='manuel'?'ajouté à la main':(l.type==='mention'?'détecté par mention du nom':'lien du forum')}"><a href="#" onclick='openTopic(${JSON.stringify(l.url)});return false'>${esc(l.titre)}</a><i onclick='delLink(${JSON.stringify(d.url)},${JSON.stringify(l.url)})' title="Supprimer ce lien">✕</i></span>`).join(" ")+`</div>`:``)
    + ((d.retroliens&&d.retroliens.length)?`<div class="liens"><b>🔙 Cité par :</b> `
        + d.retroliens.map(l=>`<a href="#" onclick='openTopic(${JSON.stringify(l.url)});return false'>${esc(l.titre)}</a>`).join(" · ")+`</div>`:``)
    + `<div class="liens"><b>➕ Ajouter un lien :</b>
         <input id="lkq" list="lktitres" placeholder="titre de l'article à relier…">
         <datalist id="lktitres"></datalist>
         <button class="mini" onclick='addLink(${JSON.stringify(d.url)})'>Relier</button></div>`
    + `<div style="margin:10px 0;display:flex;gap:8px;flex-wrap:wrap">
         <button class="mini" onclick='showSchema(${JSON.stringify(d.url)})'>🕸️ Schéma des liens</button>
         <button class="mini" onclick='toggleTree(${JSON.stringify(d.url)},${JSON.stringify(d.titre)})'>🌳 Arbre des liens</button></div>`
    + `<div id="tree-mount"></div>`
    + ((d.notes&&d.notes.length)?`<div class="notes"><b>📝 Notes (mémoire de Tenebris) :</b><ul>`+d.notes.map(n=>`<li>${esc(n)}</li>`).join("")+`</ul></div>`:``)
    + (d.synthese
        ? `<div class="synthwrap"><div class="synthead"><b>✍️ Fiche réécrite</b> <a href="#" onclick="toggleRaw();return false" id="rawlink" class="src">voir le brut</a></div><pre id="synth">${esc(d.synthese)}</pre><pre id="rawc" style="display:none">${esc(d.contenu||"")}</pre></div>`
        : (d.contenu?`<pre>${esc(d.contenu)}</pre>`:`<div class="empty">Pas encore de copie de ce sujet. Lance « Copie complète » ou « Réparer » dans l'admin.</div>`));
  v.scrollTop=0;
  fillTitres();
}
async function doSearch(){
  const q=document.getElementById("q").value.trim(); if(!q) return;
  const d=await api("action=search&q="+encodeURIComponent(q)); if(!d) return;
  const v=document.getElementById("view");
  const rs=d.resultats||[];
  if(!rs.length){v.innerHTML=`<div class="empty">Rien trouvé pour « ${esc(q)} ».</div>`;return;}
  v.innerHTML=`<h2>${rs.length} résultat(s) pour « ${esc(q)} »</h2>`+rs.map(r=>
    `<div class="res" onclick='openTopic(${JSON.stringify(r.url)})'>
       <div class="t">${esc(r.titre)}</div>
       <div class="x">${esc(r.chemin)}</div>
       ${r.extrait?`<div class="x">${esc(r.extrait)}</div>`:``}
     </div>`).join("");
}
// --- Édition des liens (corriger ce qui est faux ou manquant) ---
let _titres=null;
async function fillTitres(){
  const dl=document.getElementById("lktitres"); if(!dl) return;
  if(!_titres){ const d=await api("action=titres"); if(!d) return; _titres=d.titres||[]; }
  dl.innerHTML=_titres.map(t=>`<option value="${esc(t.titre)}">`).join("");
}
async function postForum(body){
  const r=await fetch("/admin/api/forum",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)});
  if(r.status===401){location.href="/admin";return null;}
  return r.json();
}
async function addLink(url){
  const inp=document.getElementById("lkq"); const q=(inp.value||"").trim(); if(!q) return;
  if(!_titres){ await fillTitres(); }
  const t=(_titres||[]).find(x=>x.titre.toLowerCase()===q.toLowerCase());
  if(!t){ alert("Article introuvable : choisis un titre dans la liste."); return; }
  const d=await postForum({action:"link_add", url:url, cible:t.url, titre:t.titre});
  if(d && d.ok){ inp.value=""; openTopic(url, cur); } else if(d){ alert(d.message||"Échec."); }
}
async function delLink(url, cible){
  if(!window.confirm("Supprimer ce lien ? Il ne sera pas recréé automatiquement.")) return;
  const d=await postForum({action:"link_remove", url:url, cible:cible});
  if(d && d.ok){ openTopic(url, cur); } else if(d){ alert(d.message||"Échec."); }
}
// --- SCHÉMA : le réseau des liens, dessiné (qui est lié à qui) ---
async function showSchema(url){
  const d=await api("action=schema&depth=2&url="+encodeURIComponent(url||"")); if(!d) return;
  const v=document.getElementById("view");
  const N=d.noeuds||[], E=d.aretes||[];
  if(!N.length){ v.innerHTML=`<div class="empty">Aucun lien à représenter. Lance « Réparer & tisser » dans l'admin.</div>`; return; }
  v.innerHTML=`<h2>🕸️ Schéma des liens</h2>
    <div class="kw">${N.length} article(s), ${E.length} lien(s). Glisse les bulles, clique pour ouvrir la fiche.
    <span class="lg"><i class="c0"></i>départ <i class="c1"></i>voisin direct <i class="c2"></i>plus loin</span></div>
    <div id="svgwrap"></div>`;
  drawSchema(document.getElementById("svgwrap"), N, E, d.depart);
  v.scrollTop=0;
}
function drawSchema(host, N, E, depart){
  const W=host.clientWidth||700, H=Math.max(420, Math.min(760, 180+N.length*16));
  const idx={}; N.forEach((n,i)=>idx[n.url]=i);
  // placement initial : le départ au centre, les autres en anneaux par niveau
  const P=N.map((n,i)=>{
    const lvl=n.niveau||0, r=lvl*Math.min(W,H)*0.22+ (lvl?0:0);
    const a=(i/Math.max(1,N.length))*Math.PI*2;
    return {x:W/2+Math.cos(a)*r+(lvl?0:0.01), y:H/2+Math.sin(a)*r, vx:0, vy:0, n:n};
  });
  const L=E.map(e=>({s:idx[e.de], t:idx[e.vers], type:e.type})).filter(l=>l.s!=null&&l.t!=null);
  // petite simulation de forces (répulsion + ressorts) — pas de bibliothèque externe
  for(let it=0; it<220; it++){
    for(let i=0;i<P.length;i++) for(let j=i+1;j<P.length;j++){
      let dx=P[j].x-P[i].x, dy=P[j].y-P[i].y, d2=dx*dx+dy*dy||1, d=Math.sqrt(d2);
      const f=1800/d2; const fx=dx/d*f, fy=dy/d*f;
      P[i].vx-=fx; P[i].vy-=fy; P[j].vx+=fx; P[j].vy+=fy;
    }
    L.forEach(l=>{
      const a=P[l.s], b=P[l.t];
      let dx=b.x-a.x, dy=b.y-a.y, d=Math.sqrt(dx*dx+dy*dy)||1;
      const f=(d-110)*0.012, fx=dx/d*f, fy=dy/d*f;
      a.vx+=fx; a.vy+=fy; b.vx-=fx; b.vy-=fy;
    });
    P.forEach(p=>{
      if(p.n.niveau===0){ p.x=W/2; p.y=H/2; p.vx=p.vy=0; return; }   // le départ reste au centre
      p.x+=Math.max(-12,Math.min(12,p.vx)); p.y+=Math.max(-12,Math.min(12,p.vy));
      p.vx*=0.82; p.vy*=0.82;
      p.x=Math.max(60,Math.min(W-60,p.x)); p.y=Math.max(28,Math.min(H-28,p.y));
    });
  }
  const ed=L.map(l=>`<line x1="${P[l.s].x}" y1="${P[l.s].y}" x2="${P[l.t].x}" y2="${P[l.t].y}" class="e ${l.type==='manuel'?'eman':(l.type==='mention'?'emen':'')}"/>`).join("");
  const nd=P.map((p,i)=>{
    const t=p.n.titre.length>22?p.n.titre.slice(0,21)+"…":p.n.titre;
    return `<g class="nd" data-i="${i}" transform="translate(${p.x},${p.y})">
      <circle r="${p.n.niveau===0?13:9}" class="c${Math.min(2,p.n.niveau||0)}"><title>${esc(p.n.titre)}${p.n.chemin?" — "+esc(p.n.chemin):""}</title></circle>
      <text y="-16">${esc(t)}</text></g>`;
  }).join("");
  host.innerHTML=`<svg id="schema" viewBox="0 0 ${W} ${H}" width="100%" height="${H}">${ed}${nd}</svg>`;
  // interactions : clic = ouvrir la fiche, glisser = déplacer la bulle
  const svg=document.getElementById("schema");
  let drag=null, moved=false;
  svg.querySelectorAll(".nd").forEach(g=>{
    g.addEventListener("mousedown",e=>{drag={g:g,i:+g.dataset.i};moved=false;e.preventDefault();});
    g.addEventListener("click",()=>{ if(!moved) openTopic(P[+g.dataset.i].n.url); });
  });
  svg.addEventListener("mousemove",e=>{
    if(!drag) return; moved=true;
    const r=svg.getBoundingClientRect();
    const x=(e.clientX-r.left)/r.width*W, y=(e.clientY-r.top)/r.height*H;
    P[drag.i].x=x; P[drag.i].y=y;
    drag.g.setAttribute("transform",`translate(${x},${y})`);
    L.forEach((l,k)=>{ if(l.s===drag.i||l.t===drag.i){
      const ln=svg.querySelectorAll("line")[k];
      ln.setAttribute("x1",P[l.s].x); ln.setAttribute("y1",P[l.s].y);
      ln.setAttribute("x2",P[l.t].x); ln.setAttribute("y2",P[l.t].y);
    }});
  });
  svg.addEventListener("mouseup",()=>{drag=null;});
  svg.addEventListener("mouseleave",()=>{drag=null;});
}
function toggleRaw(){
  const s=document.getElementById("synth"), r=document.getElementById("rawc"), l=document.getElementById("rawlink");
  if(!s||!r) return;
  const rawShown=r.style.display!=="none";
  r.style.display=rawShown?"none":"block"; s.style.display=rawShown?"block":"none";
  l.textContent=rawShown?"voir le brut":"voir la fiche réécrite";
}
document.getElementById("q").addEventListener("keydown",e=>{if(e.key==="Enter")doSearch();});
// --- Arbre des liens : depuis un article, on déplie ses voisins de proche en proche ---
async function toggleTree(url, titre){
  const m=document.getElementById("tree-mount");
  if(m.dataset.open==="1"){ m.innerHTML=""; m.dataset.open="0"; return; }
  m.dataset.open="1"; m.innerHTML='<div class="tree"></div>';
  await growNode(m.querySelector(".tree"), url, titre, new Set([url]));
}
async function growNode(parent, url, titre, seen){
  const node=document.createElement("div"); node.className="tnode";
  node.innerHTML=`<span class="tw">▸</span> <a href="#" onclick='openTopic(${JSON.stringify(url)});return false'>${esc(titre)}</a>`;
  const kids=document.createElement("div"); kids.className="tkids"; kids.style.display="none";
  parent.appendChild(node); parent.appendChild(kids);
  let loaded=false;
  node.querySelector(".tw").onclick=async(ev)=>{
    ev.stopPropagation();
    const open=kids.style.display!=="none";
    kids.style.display=open?"none":"block";
    node.querySelector(".tw").textContent=open?"▸":"▾";
    if(!open&&!loaded){
      loaded=true;
      const d=await api("action=topic&url="+encodeURIComponent(url)); if(!d) return;
      const voisins=[...(d.liens||[]).map(l=>({...l,type:'→'})),...(d.retroliens||[]).map(l=>({...l,type:'←'}))];
      if(!voisins.length){ kids.innerHTML='<div class="tleaf">— aucun lien —</div>'; return; }
      for(const vz of voisins){
        if(seen.has(vz.url)){
          const dupe=document.createElement("div"); dupe.className="tleaf";
          dupe.innerHTML=`${vz.type} <a href="#" onclick='openTopic(${JSON.stringify(vz.url)});return false'>${esc(vz.titre)}</a> <span class="dim">(déjà dans l'arbre)</span>`;
          kids.appendChild(dupe);
        } else {
          const s2=new Set(seen); s2.add(vz.url);
          const wrap=document.createElement("div"); wrap.className="twrap";
          wrap.innerHTML=`<span class="ttype">${vz.type}</span>`;
          kids.appendChild(wrap);
          await growNode(wrap, vz.url, vz.titre, s2);
        }
      }
    }
  };
}
// --- Vue graphe : orphelins (sans rubrique) + articles les plus connectés ---
async function showGraph(){
  const d=await api("action=graph"); if(!d) return;
  if(cur){cur.classList.remove("active");cur=null;}
  const v=document.getElementById("view");
  const orph=d.orphelins||[], top=d.plus_lies||[];
  v.innerHTML=`<h2>🌳 Tissage du forum</h2>`
   +`<div class="kw">${(d.stats&&d.stats.total)||0} sujets · ${(d.stats&&d.stats.liens)||0} liens · <b style="color:${orph.length?'#e0a24e':'#5fd68a'}">${orph.length}</b> sans rubrique</div>`
   +`<h3 style="color:var(--acc)">Articles les plus connectés</h3>`
   + top.map(t=>`<div class="res" onclick='openTopic(${JSON.stringify(t.url)})'><div class="t">${esc(t.titre)} <span class="dim">· ${t.degre} liens</span></div><div class="x">${esc(t.chemin||'⚠️ sans rubrique')}</div></div>`).join("")
   + (orph.length?`<h3 style="color:#e0a24e">Sans rubrique (${orph.length}) — lance « Réparer » dans l'admin</h3>`
      + orph.map(t=>`<div class="res" onclick='openTopic(${JSON.stringify(t.url)})'><div class="t">${esc(t.titre)}</div></div>`).join(""):'');
  v.scrollTop=0;
}
load();
</script>
</body></html>"""

SERVEUR_HTML = r"""<!DOCTYPE html>
<html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Serveur — ce que Tenebris a compris</title>
<style>
:root{--bg:#0e0d13;--panel:#17151f;--panel2:#1e1b28;--line:#2c2838;--txt:#e7e3f0;--dim:#9a93ad;--acc:#b57edc;--acc2:#7c5cbf}
*{box-sizing:border-box}
body{margin:0;font-family:system-ui,Segoe UI,Roboto,sans-serif;background:var(--bg);color:var(--txt);min-height:100vh}
header{padding:12px 20px;background:var(--panel);border-bottom:1px solid var(--line);display:flex;align-items:center;gap:14px;flex-wrap:wrap;position:sticky;top:0;z-index:5}
header h1{font-size:16px;margin:0;color:var(--acc)}
header a{color:var(--acc);text-decoration:none;font-size:13px}
header button{background:var(--acc2);border:0;color:#fff;border-radius:8px;padding:7px 12px;cursor:pointer;margin-left:auto}
.wrap{max-width:940px;margin:0 auto;padding:22px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:18px 20px;margin-bottom:20px}
.card h2{color:var(--acc);margin:0 0 4px}
.meta{color:var(--dim);font-size:13px;margin-bottom:10px}
.tags{display:flex;gap:8px;flex-wrap:wrap;margin:8px 0}
.tag{background:var(--panel2);border:1px solid var(--line);border-radius:20px;padding:3px 11px;font-size:12.5px;color:var(--dim)}
.summary{font-size:14.5px;line-height:1.55;margin:8px 0}
h3{color:var(--txt);font-size:14px;margin:16px 0 8px;border-bottom:1px solid var(--line);padding-bottom:5px}
.chan{padding:9px 0;border-bottom:1px solid var(--line);font-size:13.5px}
.chan:last-child{border-bottom:0}
.chan .n{color:var(--acc)}
.chan .r{color:var(--dim);margin-top:2px}
.note{padding:5px 0;font-size:13.5px;color:var(--txt)}
.note::before{content:"•";color:var(--acc);margin-right:8px}
.empty{color:var(--dim);text-align:center;padding:40px}
</style></head>
<body>
<header>
  <h1>🛰️ Serveur — ce que Tenebris a compris</h1>
  <a href="/admin">← retour admin</a> <a href="/forum">📚 forum</a>
  <button onclick="analyser(this)">🔍 Analyser à fond</button>
</header>
<div class="wrap" id="wrap"><div class="empty">Chargement…</div></div>
<script>
const esc=s=>(s||"").replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
async function load(){
  const r=await fetch("/admin/api/serveur"); if(r.status===401){location.href="/admin";return;}
  const d=await r.json(); const w=document.getElementById("wrap");
  const S=d.serveurs||[];
  if(!S.length){w.innerHTML='<div class="empty">Aucun serveur analysé pour l\'instant. Clique « Analyser à fond ».</div>';return;}
  w.innerHTML=S.map(g=>{
    const tags=[g.type,g.theme,g.public,g.confiance?('confiance: '+g.confiance):''].filter(Boolean)
      .map(t=>`<span class="tag">${esc(t)}</span>`).join("");
    const acts=(g.activites||[]).map(a=>`<span class="tag">${esc(a)}</span>`).join("");
    const chans=(g.channels||[]).map(c=>`<div class="chan"><div class="n">#${esc(c.name)}</div><div class="r">${esc(c.resume||"—")}</div></div>`).join("");
    const notes=(g.notes||[]).map(n=>`<div class="note">${esc(n)}</div>`).join("");
    return `<div class="card">
      <h2>${esc(g.name)}</h2>
      <div class="meta">${g.members||0} membres · dernière analyse : ${esc(g.last_observed||"jamais")}</div>
      ${g.purpose?`<div class="summary"><b>But :</b> ${esc(g.purpose)}</div>`:``}
      <div class="tags">${tags}${acts}</div>
      ${g.summary?`<div class="summary">${esc(g.summary)}</div>`:``}
      ${chans?`<h3>Salons (${(g.channels||[]).length})</h3>${chans}`:`<h3>Salons</h3><div class="r" style="color:var(--dim)">Pas encore de résumé par salon — lance « Analyser à fond ».</div>`}
      ${notes?`<h3>Ce qu'elle en retient</h3>${notes}`:``}
    </div>`;
  }).join("");
}
async function analyser(btn){
  btn.disabled=true; btn.textContent="Analyse lancée…";
  const r=await fetch("/admin/api/serveur",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({action:"analyser"})});
  if(r.status===401){location.href="/admin";return;}
  btn.textContent="⏳ en cours (reviens dans quelques min)";
  setTimeout(()=>{btn.disabled=false;btn.textContent="🔄 Rafraîchir";btn.onclick=()=>load();},8000);
}
load();
</script>
</body></html>"""

ADMIN_HTML = r"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Tenebris — Panneau du Maître</title>
<style>
  :root{
    --bg:#0c0a0f; --panel:#151119; --panel2:#1c1622; --line:#2a2130;
    --ink:#e9e2ee; --dim:#9a8ea6; --crimson:#b02a3a; --crimson2:#8e1f2c;
    --gold:#c9a24b; --user:#241a2c; --bot:#2a1519; --ok:#3d7a4e; --warn:#a8642a;
  }
  *{box-sizing:border-box}
  html,body{margin:0;height:100%}
  body{background:var(--bg);color:var(--ink);font:15px/1.5 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif}
  a{color:var(--gold)}
  .hidden{display:none!important}
  ::-webkit-scrollbar{width:9px;height:9px}
  ::-webkit-scrollbar-thumb{background:#2c2233;border-radius:6px}
  /* --- Login --- */
  #login{display:flex;align-items:center;justify-content:center;height:100vh;padding:20px}
  #login .card{background:var(--panel);border:1px solid var(--line);border-radius:16px;padding:32px;max-width:360px;width:100%;text-align:center;box-shadow:0 20px 60px rgba(0,0,0,.5)}
  #login h1{font-family:Georgia,serif;letter-spacing:3px;margin:0 0 4px;color:var(--crimson)}
  #login p{color:var(--dim);margin:0 0 22px;font-size:13px}
  input,textarea,select{font:inherit;color:var(--ink);background:var(--panel2);border:1px solid var(--line);border-radius:10px;padding:11px 13px;width:100%}
  input:focus,textarea:focus{outline:none;border-color:var(--crimson)}
  button{font:inherit;cursor:pointer;border:none;border-radius:10px;padding:11px 16px;color:#fff;background:var(--crimson);font-weight:600}
  button:hover{background:var(--crimson2)}
  button.ghost{background:transparent;border:1px solid var(--line);color:var(--dim)}
  button.ghost:hover{border-color:var(--crimson);color:var(--ink)}
  button.mini{padding:4px 9px;font-size:12px;border-radius:8px;font-weight:500}
  .err{color:#e2647a;font-size:13px;min-height:18px;margin-top:10px}
  /* --- Shell --- */
  #app{display:flex;flex-direction:column;height:100vh}
  #topbar{display:flex;align-items:center;gap:16px;padding:12px 20px;border-bottom:1px solid var(--line);background:var(--panel)}
  #topbar .brand{font-family:Georgia,serif;letter-spacing:2px;color:var(--crimson);font-size:20px}
  #topbar .brand small{display:block;color:var(--dim);font-size:10px;letter-spacing:1px}
  #nav{display:flex;gap:6px;flex:1;flex-wrap:wrap}
  .tab{background:transparent;border:1px solid transparent;color:var(--dim);padding:8px 14px;border-radius:10px;font-weight:600}
  .tab:hover{color:var(--ink);background:var(--panel2)}
  .tab.on{color:var(--ink);background:var(--panel2);border-color:var(--crimson)}
  #views{flex:1;min-height:0;overflow:hidden}
  .view{height:100%;overflow-y:auto;padding:22px}
  .view.conv{padding:0;display:grid;grid-template-columns:320px 1fr;overflow:hidden}
  h2.title{font-family:Georgia,serif;letter-spacing:1px;color:var(--gold);margin:0 0 16px;font-weight:400}
  /* --- Dashboard --- */
  .cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:14px;margin-bottom:26px}
  .card{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:16px}
  .card .n{font-size:30px;font-weight:700;color:var(--ink)}
  .card .l{color:var(--dim);font-size:12px;letter-spacing:.5px;text-transform:uppercase;margin-top:2px}
  .panel{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:18px;margin-bottom:22px}
  .panel h3{margin:0 0 12px;font-size:13px;letter-spacing:1px;text-transform:uppercase;color:var(--gold)}
  .chips{display:flex;flex-wrap:wrap;gap:8px}
  .chip{background:var(--panel2);border:1px solid var(--line);border-radius:20px;padding:4px 12px;font-size:13px;color:var(--ink)}
  .chip b{color:var(--gold);margin-left:6px}
  .chip.cat{color:var(--dim)}
  #graph{width:100%;height:420px;background:var(--panel2);border:1px solid var(--line);border-radius:14px}
  /* --- Liste conversations --- */
  #side{border-right:1px solid var(--line);display:flex;flex-direction:column;background:var(--panel);min-height:0}
  #sideHead{padding:12px 14px;border-bottom:1px solid var(--line);color:var(--dim);font-size:12px;letter-spacing:1px;text-transform:uppercase}
  #list{overflow-y:auto;flex:1;min-height:0}
  .row{padding:12px 16px;border-bottom:1px solid var(--line);cursor:pointer;display:flex;gap:10px;align-items:flex-start}
  .row:hover{background:var(--panel2)}
  .row.active{background:var(--panel2);border-left:3px solid var(--crimson);padding-left:13px}
  .row .nm{font-weight:600;display:flex;align-items:center;gap:6px;flex-wrap:wrap}
  .row .pv{color:var(--dim);font-size:12px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:230px}
  .row .meta{color:var(--dim);font-size:11px;margin-top:2px}
  .dot{width:8px;height:8px;border-radius:50%;background:var(--dim);margin-top:6px;flex:none}
  .dot.p{background:var(--warn)}
  .badge{font-size:10px;padding:1px 7px;border-radius:20px;border:1px solid var(--line);color:var(--dim);letter-spacing:.5px}
  .badge.master{color:var(--gold);border-color:var(--gold)}
  .badge.paused{color:var(--warn);border-color:var(--warn)}
  .badge.off{color:#a05;border-color:#a05}
  /* --- Où parle la personne : message privé, ou salon d'un serveur ? --- */
  .badge.mp{color:#c9a0ff;border-color:#6d4a99;background:rgba(140,90,200,.10)}
  .badge.srv{color:#7ddc9a;border-color:#37714d;background:rgba(70,160,110,.10)}
  .badge.unk{color:var(--dim);border-color:var(--line)}
  .lieu{font-size:11px;margin-top:3px;display:flex;align-items:center;gap:5px;flex-wrap:wrap}
  .lieu .w{color:var(--dim)}
  /* --- Barre de chargement globale (toute requête en vol) --- */
  #bar{position:fixed;top:0;left:0;right:0;height:3px;z-index:60;background:transparent;overflow:hidden;opacity:0;transition:opacity .2s}
  #bar.on{opacity:1}
  #bar i{display:block;height:100%;width:35%;background:linear-gradient(90deg,transparent,var(--crimson),var(--gold),transparent);animation:slide 1.1s linear infinite}
  @keyframes slide{from{transform:translateX(-100%)}to{transform:translateX(320%)}}
  /* --- Spinner de bouton --- */
  .spin{display:inline-block;width:12px;height:12px;border:2px solid rgba(255,255,255,.28);border-top-color:#fff;border-radius:50%;animation:turn .7s linear infinite;vertical-align:-2px;margin-right:6px}
  @keyframes turn{to{transform:rotate(360deg)}}
  button:disabled{opacity:.65;cursor:progress}
  /* --- Overlay des tâches longues (observation, missions) --- */
  #task{position:fixed;inset:0;z-index:70;background:rgba(6,4,9,.72);display:flex;align-items:center;justify-content:center;padding:20px}
  #task .box{background:var(--panel);border:1px solid var(--line);border-radius:16px;padding:24px;width:100%;max-width:430px;box-shadow:0 24px 70px rgba(0,0,0,.6)}
  #task h4{margin:0 0 4px;font-family:Georgia,serif;letter-spacing:1px;color:var(--gold);font-size:16px}
  #task .step{color:var(--dim);font-size:13px;min-height:19px;margin-bottom:14px}
  #task .track{height:9px;border-radius:9px;background:var(--panel2);border:1px solid var(--line);overflow:hidden}
  #task .fill{height:100%;width:0%;border-radius:9px;background:linear-gradient(90deg,var(--crimson),var(--gold));transition:width .45s ease}
  #task .foot{display:flex;justify-content:space-between;align-items:center;margin-top:10px;font-size:12px;color:var(--dim)}
  #task .res{margin-top:14px;font-size:13px;line-height:1.5;white-space:pre-wrap}
  #task .res.ko{color:#e2647a}
  #task .btnrow{margin-top:16px;display:flex;justify-content:flex-end}
  /* --- Notifications discrètes (remplacent les alert()) --- */
  #toasts{position:fixed;right:16px;bottom:16px;z-index:80;display:flex;flex-direction:column;gap:8px;max-width:340px}
  .toast{background:var(--panel2);border:1px solid var(--line);border-left:3px solid var(--ok);border-radius:10px;padding:10px 13px;font-size:13px;box-shadow:0 10px 30px rgba(0,0,0,.5);animation:pop .25s ease}
  .toast.ko{border-left-color:var(--crimson)}
  @keyframes pop{from{transform:translateY(8px);opacity:0}to{transform:translateY(0);opacity:1}}
  /* --- Thread + fiche --- */
  #main{display:flex;flex-direction:column;min-width:0;min-height:0}
  #head{padding:14px 20px;border-bottom:1px solid var(--line);display:flex;align-items:center;gap:14px;background:var(--panel)}
  #head .who{font-weight:700;font-size:17px}
  #head .sub{color:var(--dim);font-size:12px}
  #head .spacer{flex:1}
  .switch{display:flex;align-items:center;gap:8px;font-size:13px;color:var(--dim)}
  .toggle{position:relative;width:46px;height:26px;background:var(--line);border-radius:20px;transition:.2s;cursor:pointer;flex:none}
  .toggle.on{background:var(--warn)}
  .toggle b{position:absolute;top:3px;left:3px;width:20px;height:20px;background:#fff;border-radius:50%;transition:.2s}
  .toggle.on b{left:23px}
  #stream{flex:1;overflow-y:auto;padding:22px;min-height:0;display:flex;flex-direction:column;gap:12px}
  .empty{margin:auto;color:var(--dim);text-align:center;max-width:340px}
  .empty .big{font-family:Georgia,serif;font-size:26px;color:var(--crimson);letter-spacing:2px;margin-bottom:8px}
  .fiche{background:var(--panel2);border:1px solid var(--line);border-radius:14px;padding:16px;margin-bottom:4px}
  .fiche .frow{display:flex;gap:8px;margin:6px 0;font-size:13px}
  .fiche .fk{color:var(--gold);min-width:120px;text-transform:uppercase;font-size:11px;letter-spacing:.5px;padding-top:2px}
  .fiche .fv{color:var(--ink);flex:1}
  .noteitem{display:flex;gap:8px;align-items:flex-start;padding:6px 0;border-top:1px dashed var(--line)}
  .noteitem .nt{flex:1;font-size:13px}
  .noteitem .nd{color:var(--dim);font-size:11px}
  .sum{background:var(--panel2);border:1px dashed var(--line);border-radius:12px;padding:12px 14px;color:var(--dim);font-size:13px}
  .sum b{color:var(--gold);letter-spacing:1px;font-size:11px;text-transform:uppercase}
  .msg{max-width:78%;padding:10px 14px;border-radius:14px;white-space:pre-wrap;word-wrap:break-word}
  .msg .lbl{font-size:11px;color:var(--dim);margin-bottom:3px;letter-spacing:.5px}
  .msg.u{align-self:flex-start;background:var(--user);border:1px solid var(--line);border-top-left-radius:4px}
  .msg.a{align-self:flex-end;background:var(--bot);border:1px solid #3a1c22;border-top-right-radius:4px}
  #compose{border-top:1px solid var(--line);padding:14px 18px;background:var(--panel);display:flex;gap:10px;align-items:flex-end}
  #compose textarea{resize:none;height:46px;max-height:160px}
  #compose .send{height:46px;padding:0 20px}
  .note{color:var(--dim);font-size:11px;padding:0 18px 10px;background:var(--panel)}
  /* --- Recherche --- */
  .searchbar{display:flex;gap:10px;margin-bottom:18px}
  .result{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:12px 14px;margin-bottom:10px;cursor:pointer}
  .result:hover{border-color:var(--crimson)}
  .result .k{font-size:11px;letter-spacing:.5px;text-transform:uppercase;color:var(--gold)}
  .result .w{color:var(--dim);font-size:12px}
  /* --- Mémoire --- */
  .memrow{display:flex;gap:10px;align-items:flex-start;background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:11px 14px;margin-bottom:9px}
  .memrow .mt{flex:1;font-size:14px}
  .memrow .mc{font-size:10px;letter-spacing:.5px;text-transform:uppercase;color:var(--dim);border:1px solid var(--line);border-radius:20px;padding:1px 8px;white-space:nowrap}
  .memrow .mc.dir{color:var(--gold);border-color:var(--gold)}
  @media(max-width:760px){
    .view.conv{grid-template-columns:1fr}
    body.viewthread #side{display:none}
    body:not(.viewthread) #main{display:none}
    .fiche .frow{flex-direction:column;gap:2px}
    .fiche .fk{min-width:0}
  }
  /* Console admin */
  .form{display:flex;flex-direction:column;gap:5px;max-width:640px}
  .form>label{color:var(--dim);font-size:13px;margin-top:8px}
  .form .inp{width:100%}
  .adm-sec{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:18px;margin-bottom:18px}
  .adm-sec h3{margin:0 0 14px;font-size:13px;letter-spacing:1px;text-transform:uppercase;color:var(--gold)}
  .frm{display:grid;grid-template-columns:240px 1fr;gap:12px 16px;align-items:center;max-width:660px}
  .frm label{color:var(--dim);font-size:13px}
  .frm select,.frm input[type=number]{width:auto;min-width:130px}
  .chk{width:20px;height:20px;accent-color:var(--crimson);cursor:pointer}
  .btnrow{display:flex;gap:10px;flex-wrap:wrap;align-items:center}
  .adm-sec .btnrow{margin-top:14px}
  .danger{background:#7a1f1f}.danger:hover{background:#611717}
  .admuser{display:flex;align-items:center;gap:10px;padding:9px 12px;border:1px solid var(--line);border-radius:10px;margin-bottom:8px}
  .admuser .an{flex:1}
  .auditrow{display:flex;gap:12px;font-size:12px;padding:7px 0;border-bottom:1px dashed var(--line)}
  .auditrow .at{color:var(--dim);white-space:nowrap}
  .auditrow .aa{color:var(--gold);white-space:nowrap}
  .imp{font-size:10px;padding:1px 7px;border-radius:20px;border:1px solid var(--line);color:var(--dim)}
  .imp.haute{color:#e2647a;border-color:#e2647a}
</style>
</head>
<body>

<div id="bar"><i></i></div>
<div id="toasts"></div>
<div id="task" class="hidden">
  <div class="box">
    <h4 id="tk_label">Tâche en cours</h4>
    <div class="step" id="tk_step">Démarrage…</div>
    <div class="track"><div class="fill" id="tk_fill"></div></div>
    <div class="foot"><span id="tk_pct">0 %</span><span id="tk_time">0 s</span></div>
    <div class="res hidden" id="tk_res"></div>
    <div class="btnrow"><button class="mini ghost hidden" id="tk_close" onclick="taskClose()">Fermer</button></div>
  </div>
</div>

<div id="login">
  <div class="card">
    <h1>TENEBRIS</h1>
    <p>Accès réservé au Maître</p>
    <input id="pw" type="password" placeholder="Mot de passe" autocomplete="current-password">
    <div style="height:12px"></div>
    <button id="loginBtn" style="width:100%">Entrer</button>
    <div class="err" id="loginErr"></div>
  </div>
</div>

<div id="app" class="hidden">
  <div id="topbar">
    <div class="brand">TENEBRIS<small>PANNEAU DU MAÎTRE</small></div>
    <div id="nav">
      <button class="tab on" data-v="dash">Tableau de bord</button>
      <button class="tab" data-v="conv">Conversations</button>
      <button class="tab" data-v="search">Recherche</button>
      <button class="tab" data-v="mem">Mémoire</button>
      <button class="tab" data-v="guilds">Serveurs</button>
      <button class="tab" data-v="persona">Personnalité</button>
      <button class="tab" data-v="agenda">Rappels & Missions</button>
      <button class="tab" data-v="admin">Console</button>
    </div>
    <div id="guildBox" style="display:flex;align-items:center;gap:8px;margin-left:auto">
      <span style="font-size:11px;color:var(--dim);letter-spacing:.04em">SERVEUR</span>
      <select id="guildSel" onchange="onGuildChange()" title="Filtre la mémoire par serveur"
              style="background:var(--card,#1a1a1f);color:inherit;border:1px solid var(--line,#333);border-radius:8px;padding:5px 8px;font-size:12px;max-width:220px"></select>
      <label id="orbisTog" style="display:none;align-items:center;gap:5px;font-size:11px;color:var(--dim);cursor:pointer">
        <input type="checkbox" id="orbisChk" onchange="toggleOrbis()"> Forum&nbsp;Orbis
      </label>
    </div>
    <button class="ghost" id="logoutBtn" style="padding:6px 12px;font-size:12px">Quitter</button>
  </div>

  <div id="views">
    <!-- Tableau de bord -->
    <div class="view" id="v-dash">
      <h2 class="title">Vue d'ensemble</h2>
      <div class="cards" id="statCards"></div>
      <div class="panel"><h3>Tags les plus fréquents</h3><div class="chips" id="topTags"></div></div>
      <div class="panel"><h3>Mémoire commune par catégorie</h3><div class="chips" id="cats"></div></div>
      <div class="panel"><h3>Relations entre les personnes</h3><svg id="graph"></svg>
        <div class="w" style="color:var(--dim);font-size:12px;margin-top:8px">Les liens se construisent automatiquement à partir des conversations.</div>
      </div>
    </div>

    <!-- Conversations -->
    <div class="view conv" id="v-conv">
      <aside id="side">
        <div id="sideHead">Conversations</div>
        <div id="list"></div>
      </aside>
      <section id="main">
        <div id="head" class="hidden">
          <button class="ghost mini backBtn" style="display:none">◀</button>
          <div>
            <div class="who" id="hWho">—</div>
            <div class="sub" id="hSub"></div>
          </div>
          <div class="spacer"></div>
          <div class="switch">
            <span id="pauseLbl">IA active</span>
            <div class="toggle" id="pauseTgl"><b></b></div>
          </div>
        </div>
        <div id="stream">
          <div class="empty">
            <div class="big">👁</div>
            <div>Choisis une conversation à gauche pour lire les échanges, consulter la fiche, mettre l'IA en pause ou répondre toi-même.</div>
          </div>
        </div>
        <div class="note hidden" id="composeNote"></div>
        <div id="compose" class="hidden">
          <textarea id="msg" placeholder="Écrire à cette personne à travers le bot…"></textarea>
          <button class="send" id="sendBtn">Envoyer</button>
        </div>
      </section>
    </div>

    <!-- Recherche -->
    <div class="view" id="v-search">
      <h2 class="title">Recherche globale</h2>
      <div class="searchbar">
        <input id="q" placeholder="Chercher dans les souvenirs, les notes, les fiches…">
        <button id="qBtn" style="white-space:nowrap">Chercher</button>
      </div>
      <div id="results"></div>
    </div>

    <!-- Mémoire -->
    <div class="view" id="v-mem">
      <h2 class="title">Mémoire commune</h2>
      <div class="searchbar">
        <input id="newMem" placeholder="Ajouter un souvenir…">
        <button id="addMemBtn" style="white-space:nowrap">Ajouter</button>
      </div>
      <div id="memList"></div>
    </div>

    <!-- Serveurs -->
    <div class="view" id="v-guilds">
      <h2 class="title">Serveurs</h2>
      <div style="color:var(--dim);font-size:13px;margin-bottom:16px">
        Ce que Tenebris observe et retient des serveurs où elle se trouve — mis à jour automatiquement, pas seulement à son arrivée.
      </div>
      <div id="guildList"></div>
    </div>

    <!-- Personnalité -->
    <div class="view" id="v-persona">
      <h2 class="title">Personnalité</h2>
      <div style="color:var(--dim);font-size:13px;margin-bottom:16px">
        Le <b>noyau</b> est son cap : il s'applique à toutes ses réponses et seul toi le modifies.
        Les <b>adaptations</b> sont ce qu'elle apprend des membres avec le temps — elles nuancent le noyau, jamais ne le contredisent.
      </div>
      <div class="adm-sec">
        <h3>Noyau</h3>
        <div class="form">
          <label>Nom</label><input id="p_nom" class="inp">
          <label>Essence (qui elle est)</label><textarea id="p_essence" class="inp" rows="3"></textarea>
          <label>Ton (comment elle parle)</label><textarea id="p_ton" class="inp" rows="3"></textarea>
          <label>Caractère (une ligne par trait)</label><textarea id="p_caractere" class="inp" rows="5"></textarea>
          <label>Jamais (interdits, une ligne chacun)</label><textarea id="p_interdits" class="inp" rows="4"></textarea>
        </div>
        <div class="btnrow">
          <button class="mini" onclick="savePersona()">Enregistrer le noyau</button>
          <button class="mini ghost" onclick="resetPersona()">Réinitialiser</button>
        </div>
      </div>
      <div class="adm-sec">
        <h3>Adaptations apprises</h3>
        <div id="adaptList"></div>
        <div class="btnrow">
          <button class="mini ghost" onclick="addAdaptation()">+ Ajouter</button>
          <button class="mini" onclick="evolvePersona()">🎭 Apprendre des membres maintenant</button>
        </div>
      </div>
      <div class="adm-sec">
        <h3>Son emoji</h3>
        <div style="display:flex;gap:16px;align-items:flex-start;flex-wrap:wrap">
          <div style="text-align:center">
            <img id="emoImg" alt="emoji" style="width:96px;height:96px;image-rendering:auto;
                 background:rgba(255,255,255,.04);border-radius:12px;padding:6px">
            <div id="emoOrig" style="color:var(--dim);font-size:11px;margin-top:4px"></div>
          </div>
          <div style="flex:1;min-width:260px">
            <div style="color:var(--dim);font-size:13px;margin-bottom:8px">
              Elle l'utilise comme signature dans ses messages. L'image est redimensionnée en 128×128 automatiquement.
            </div>
            <input type="file" id="emoFile" accept="image/*" class="inp" style="padding:8px">
            <div class="btnrow">
              <button class="mini" onclick="uploadEmoji()">Changer l'image</button>
              <button class="mini ghost" onclick="resetEmojiImage()">Image d'origine</button>
              <button class="mini ghost" onclick="createAllEmoji()">Créer sur tous les serveurs</button>
            </div>
          </div>
        </div>
        <div id="emoServers" style="margin-top:14px"></div>
      </div>
    </div>

    <!-- Rappels & Missions -->
    <div class="view" id="v-agenda">
      <h2 class="title">Rappels &amp; Missions</h2>

      <div class="adm-sec">
        <h3>Rappels programmés</h3>
        <div style="color:var(--dim);font-size:13px;margin-bottom:10px">
          Chaque rappel indique sa destination : un salon du serveur, ou un message privé au destinataire.
        </div>
        <div id="remList"></div>
        <div class="form" style="margin-top:12px">
          <label>Échéance</label>
          <input id="rm_quand" class="inp" placeholder="demain 9h · +3j · 2026-08-01 14:00">
          <label>Message</label>
          <textarea id="rm_msg" class="inp" rows="2"></textarea>
          <label style="display:flex;align-items:center;gap:8px">
            <input type="checkbox" id="rm_prive"> Envoyer en message privé (au lieu d'un salon)
          </label>
          <label>Serveur</label>
          <select id="rm_gid" class="inp" onchange="fillRemChannels()"></select>
          <label id="rm_lab_salon">Salon</label>
          <select id="rm_salon" class="inp"></select>
          <label>Destinataire (pour un MP, ou à mentionner)</label>
          <input id="rm_uid" class="inp" placeholder="ID Discord de la personne">
        </div>
        <div class="btnrow"><button class="mini" onclick="createReminder()">Programmer</button></div>
      </div>

      <div class="adm-sec">
        <h3>Missions</h3>
        <div style="color:var(--dim);font-size:13px;margin-bottom:10px">
          Trois formes de mission, toutes exécutées en fond, chacune à son rythme :<br>
          <b>Veille de forum</b> — elle surveille un forum et publie ses <b>nouveaux sujets</b>
          (au premier passage elle note l'existant sans rien annoncer).<br>
          <b>Rappel récurrent</b> — elle répète un message toutes les X minutes <b>jusqu'à une date
          et une heure</b>, puis s'arrête d'elle-même.<br>
          <b>Consigne récurrente</b> — elle exécute une consigne (calculs, jets de dés réels,
          synthèse) à intervalle régulier jusqu'à l'échéance, et publie le résultat.
        </div>
        <div id="misList"></div>

        <div class="form" style="margin-top:14px">
          <label>Type de mission</label>
          <select id="ms_type" class="inp" onchange="switchMisType()">
            <option value="rappel">Rappel récurrent (jusqu'à une date)</option>
            <option value="meme">Mèmes réguliers (thème au choix)</option>
            <option value="consigne">Consigne récurrente (calculs, dés…)</option>
            <option value="forum">Veille de forum</option>
          </select>

          <label>Nom de la mission</label>
          <input id="ms_nom" class="inp" placeholder="Relance du raid · Veille Orbis Naturae…">

          <div id="ms_f_forum" class="hidden">
            <label>Adresse du forum (ou d'une rubrique précise)</label>
            <input id="ms_url" class="inp" value="https://orbis-naturae.forumactif.com/" placeholder="https://orbis-naturae.forumactif.com/">
            <div style="color:var(--dim);font-size:12px;margin-top:4px">Forum officiel du projet — laisse tel quel sauf pour surveiller un autre site.</div>
          </div>

          <div id="ms_f_rappel">
            <label>Message répété</label>
            <textarea id="ms_msg" class="inp" rows="2" placeholder="N'oubliez pas de poster vos actions du tour."></textarea>
          </div>

          <div id="ms_f_meme" class="hidden">
            <label>Thème des mèmes</label>
            <input id="ms_theme" class="inp" placeholder="programmation · jeux vidéo · fantasy · chat · sombre · absurde…">
            <div style="color:var(--dim);font-size:12px;margin-top:4px">
              Thèmes connus : général, programmation, jeux vidéo, sombre, fantasy, chat, chien,
              science, histoire, animé, français, absurde. Tu peux aussi donner un nom de subreddit.
              Elle ne resert jamais deux fois le même mème.
            </div>
          </div>

          <div id="ms_f_consigne" class="hidden">
            <label>Consigne à exécuter à chaque passage</label>
            <textarea id="ms_consigne" class="inp" rows="4" placeholder="Lance 14 attaques de 1d100, objectif 70, et publie le total des dégâts."></textarea>
            <div style="color:var(--dim);font-size:12px;margin-top:4px">
              Elle garde ses outils : les dés qu'elle lance ici sont de <b>vrais</b> tirages.
            </div>
          </div>

          <label style="display:flex;align-items:center;gap:8px;margin-top:8px">
            <input type="checkbox" id="ms_prive" onchange="switchMisType()"> Envoyer en message privé (au lieu d'un salon)
          </label>

          <label>Serveur</label>
          <select id="ms_gid" class="inp" onchange="fillMisChannels()"></select>
          <div id="ms_f_salon">
            <label>Salon où publier</label>
            <select id="ms_salon" class="inp"></select>
          </div>
          <label id="ms_lab_uid">Personne à mentionner (facultatif — ID Discord)</label>
          <input id="ms_uid" class="inp" placeholder="194346572400558081">

          <label>Toutes les (minutes)</label>
          <input id="ms_freq" class="inp" type="number" value="60" min="1">
          <div id="ms_f_fin">
            <label>Jusqu'au (date et heure de fin)</label>
            <input id="ms_fin" class="inp" placeholder="2026-08-01 14:00 · +3j · dans 6h">
          </div>
          <label style="display:flex;align-items:center;gap:8px;margin-top:8px">
            <input type="checkbox" id="ms_now"> Lancer un premier passage immédiatement
          </label>
        </div>
        <div class="btnrow"><button class="mini" id="ms_btn" onclick="createMission()">Confier la mission</button></div>
      </div>
    </div>

    <!-- Console d'administration -->
    <div class="view" id="v-admin">
      <h2 class="title">Console d'administration</h2>

      <div class="adm-sec">
        <h3>Nettoyage & optimisation de la mémoire</h3>
        <div style="color:var(--dim);font-size:13px;margin-bottom:12px">
          Fait le ménage dans les notes de tout le monde et dans la mémoire commune :
          supprime les <b>doublons</b> (même info répétée), <b>fusionne</b> les notes qui se
          recoupent en une seule plus riche, retire les <b>contradictions</b> (on garde la plus
          récente), range les <b>consignes qui se superposent</b>, et applique la
          <b>limite de 10 notes par personne</b>. Les notes écrites à la main ne sont jamais touchées.
        </div>
        <div class="btnrow" style="display:flex;gap:8px;flex-wrap:wrap;align-items:center">
          <button class="mini" id="clean_go" onclick="cleanMemory({merge:true, llm:true}, this)">🔀 Optimiser tout (doublons + fusion + contradictions + plafond 10)</button>
          <button class="mini ghost" onclick="cleanMemory({merge:false, llm:true}, this)">🧹 Nettoyer (doublons + contradictions)</button>
          <button class="mini ghost" onclick="cleanMemory({merge:false, llm:false}, this)">⚡ Doublons + plafond (rapide, local)</button>
        </div>
        <div style="color:var(--dim);font-size:12px;margin-top:8px">La fusion et les contradictions utilisent le modèle (Mistral) : un peu plus lentes, mais elles comprennent le sens. Le mode rapide reste 100&nbsp;% local.</div>
      </div>

      <div class="adm-sec">
        <h3>Observation du serveur</h3>
        <div style="color:var(--dim);font-size:13px;margin-bottom:12px">
          Tenebris analyse le serveur À FOND (tous les salons accessibles, depuis le début) : elle
          résume <b>chaque salon</b>, cerne le but et l'ambiance, et prend des notes utiles — le tout
          consultable dans une page dédiée (comme /forum, mais pour le serveur).
          <a href="/serveur" target="_blank" style="color:var(--acc);margin-left:6px">🛰️ Ouvrir /serveur ↗</a>
        </div>
        <div class="btnrow" style="flex-wrap:wrap;gap:8px">
          <button class="mini" onclick="analyserServeur(this)">🔍 Analyser le serveur à fond</button>
        </div>
        <div style="color:var(--dim);font-size:12px;margin-top:8px">Ça lit beaucoup de messages et fait un résumé par salon (Mistral) : quelques minutes selon la taille du serveur. Tourne en fond.</div>
      </div>

      <div class="adm-sec">
        <h3>Bibliothèque du forum</h3>
        <div style="color:var(--dim);font-size:13px;margin-bottom:12px">
          Tenebris tient une <b>copie interne du forum</b> : pour chaque sujet, le chemin, un court
          résumé, et — depuis la <b>copie complète</b> — le <b>contenu intégral</b> du sujet, relisible
          hors ligne. Elle remplit la carte toute seule en fond ; la copie complète, elle, se lance à
          la demande. Le forum de référence est <b id="lib_forum">—</b>.
          <a href="/forum" target="_blank" style="color:var(--acc);margin-left:6px">📚 Ouvrir /forum ↗</a>
        </div>
        <div id="lib_stats" style="font-size:13px;margin-bottom:12px;color:var(--dim)">Chargement…</div>
        <div class="btnrow" style="flex-wrap:wrap;gap:8px">
          <button class="mini" id="lib_copy" onclick="libAction('copie', this)">📚 Copie complète (contenu)</button>
          <button class="mini" id="lib_fix" onclick="libAction('reparer', this)">🔧 Réparer & tisser (rubriques + liens)</button>
          <button class="mini" id="lib_rw" onclick="libAction('reecrire', this)">✍️ Réécrire (fiches propres + notes)</button>
          <button class="mini ghost" id="lib_map" onclick="libAction('carte', this)">🗺️ Cartographier</button>
          <button class="mini ghost" id="lib_sum" onclick="libAction('resumer', this)">📖 Indexer maintenant</button>
          <label style="display:flex;align-items:center;gap:6px;font-size:13px;margin-left:auto">
            <input type="checkbox" id="lib_toggle" onchange="libToggle()"> Remplissage automatique
          </label>
          <button class="mini ghost" onclick="libAction('vider', this)">🗑️ Vider</button>
        </div>
      </div>

      <div class="adm-sec">
        <h3>Salons écoutés <button class="mini ghost" style="float:right;font-size:12px" onclick="loadListen()">🔄 Rafraîchir</button></h3>
        <div style="color:var(--dim);font-size:13px;margin-bottom:10px">
          Dans un salon écouté, Tenebris suit la discussion <b>sans être mentionnée</b> :
          elle apprend des gens (notes automatiques) et s'invite parfois dans la conversation,
          selon le niveau de <b>bavardage</b> réglé plus bas. Elle répond toujours si on l'appelle par son nom.
          <br><b>Écouter n'est pas parler</b> : tant que le bavardage est sur « jamais », elle se contente d'apprendre.
        </div>
        <div class="frm" style="margin-bottom:14px">
          <label>Mode d'écoute</label>
          <select id="s_ecoute" onchange="setListenMode()">
            <option value="tous">Tous les salons (défaut) — sourdine au cas par cas</option>
            <option value="selection">Sélection — seulement ceux que j'ouvre</option>
            <option value="aucune">Aucune — elle est sourde</option>
          </select>
        </div>
        <div id="listenBox"></div>
      </div>

      <div class="adm-sec">
        <h3>Paramètres de l'IA</h3>
        <div class="frm">
          <label>Niveau d'autonomie</label>
          <select id="s_autonomy"><option value="discret">Discret</option><option value="normal">Normal</option><option value="proactif">Proactif</option></select>
          <label>Prise de notes autonome</label><input type="checkbox" class="chk" id="s_autonote">
          <label>Actions autonomes (envois)</label><input type="checkbox" class="chk" id="s_autoact">
          <label>Conseil intérieur (2 agents)</label><input type="checkbox" class="chk" id="s_delib">
          <label>Partage mémoire entre membres</label><input type="checkbox" class="chk" id="s_share">
          <label>Extraction tous les N messages</label><input type="number" id="s_extract" min="2" max="50">
          <label>Rétention (jours, 0 = jamais)</label><input type="number" id="s_reten" min="0" max="3650">
          <label>Seuil d'importance des notes</label>
          <select id="s_thresh"><option value="faible">Faible</option><option value="normale">Normale</option><option value="haute">Haute</option></select>
          <label>Mode roleplay (modèles peu censurés)</label>
          <select id="s_rp"><option value="intelligent">Intelligent (comprend seule)</option><option value="auto">Auto (indices only)</option><option value="toujours">Toujours</option><option value="jamais">Jamais</option></select>
          <label>Bavardage (interventions spontanées)</label>
          <select id="s_bavard">
            <option value="jamais">Jamais — elle écoute et apprend, sans jamais couper</option>
            <option value="discret">Discret — une remarque de temps en temps</option>
            <option value="normal">Normal — elle se mêle à la conversation</option>
            <option value="bavard">Bavard — elle a toujours quelque chose à dire</option>
          </select>
        </div>
        <div class="btnrow"><button id="saveSettings">Enregistrer les paramètres</button></div>
      </div>

      <div class="adm-sec">
        <h3>Joueurs &amp; utilisateurs</h3>
        <div style="color:var(--dim);font-size:13px;margin-bottom:8px">Clique un utilisateur pour voir sa fiche complète et la mémoire liée à lui.</div>
        <div id="admUsers"></div>
        <div id="userDetail" style="display:none"></div>
      </div>

      <div class="adm-sec">
        <h3>Données mémoire</h3>
        <div class="btnrow">
          <button id="btnExport">Exporter (JSON)</button>
          <button id="btnImport" class="ghost">Importer…</button>
          <input type="file" id="fileImport" accept="application/json" class="hidden">
          <button id="btnRestore" class="ghost">Restaurer la sauvegarde</button>
        </div>
        <div class="btnrow" style="margin-top:12px">
          <select id="resetScope" style="width:auto">
            <option value="all">Tout</option><option value="memories">Souvenirs seulement</option>
            <option value="users">Fiches seulement</option><option value="audit">Journal seulement</option>
          </select>
          <button id="btnReset" class="danger">Réinitialiser</button>
        </div>
      </div>

      <div class="adm-sec">
        <h3>Actions exécutées</h3>
        <div style="color:var(--dim);font-size:13px;margin-bottom:8px">
          Tout ce qu'elle a réellement fait — outil appelé, paramètres, résultat.
          Si une action n'apparaît pas ici, <b>elle n'a pas eu lieu</b>.
        </div>
        <div id="actList"></div>
      </div>

      <div class="adm-sec">
        <h3>Journal d'audit</h3>
        <div id="auditList"></div>
      </div>
    </div>
  </div>
</div>

<script>
const $ = s => document.querySelector(s);
const $$ = s => Array.from(document.querySelectorAll(s));
let current = null, curMeta = null, stateTimer = null, threadTimer = null, channelTimer = null, view = 'dash';

function esc(t){ const d=document.createElement('div'); d.textContent=(t==null?'':t); return d.innerHTML; }

/* ---------- Chargement : plus jamais d'attente muette ---------- */
let _pending = 0;
function loadStart(){ _pending++; $('#bar').classList.add('on'); }
function loadEnd(){ _pending = Math.max(0, _pending-1); if(!_pending) $('#bar').classList.remove('on'); }

async function jget(url){
  loadStart();
  try{
    const r = await fetch(url);
    return {status:r.status, body: await r.json().catch(()=>({}))};
  }catch(e){ return {status:0, body:{error:'Réseau injoignable.'}}; }
  finally{ loadEnd(); }
}
async function jpost(url,obj){
  loadStart();
  try{
    const r = await fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(obj||{})});
    return {status:r.status, body: await r.json().catch(()=>({}))};
  }catch(e){ return {status:0, body:{error:'Réseau injoignable.'}}; }
  finally{ loadEnd(); }
}

/* ---------- Sélecteur de SERVEUR (mémoire multi-serveur) ---------- */
let GUILD = localStorage.getItem('tnbGuild') || '';   // '' = tous serveurs
let GUILDS = [];                                       // options connues
let HOME_GUILD = '';
/* Ajoute ?guild=… (ou &guild=…) à une URL d'API quand un serveur est sélectionné. */
function gq(url){
  if(!GUILD) return url;
  return url + (url.includes('?') ? '&' : '?') + 'guild=' + encodeURIComponent(GUILD);
}
function renderGuildSel(guilds, home){
  if(guilds){ GUILDS = guilds; }
  if(home !== undefined){ HOME_GUILD = home || ''; }
  const sel = $('#guildSel'); if(!sel) return;
  let html = '<option value="">Tous les serveurs</option>';
  for(const g of GUILDS){
    const tags = (g.home?' ⌂':'') + (g.forum_orbis?' 🌐':'') + (g.present?'':' (absent)');
    html += '<option value="'+g.gid+'"'+(String(g.gid)===String(GUILD)?' selected':'')+'>'+esc(g.name)+tags+'</option>';
  }
  sel.innerHTML = html;
  if(GUILD && !GUILDS.some(g=>String(g.gid)===String(GUILD))){ GUILD=''; localStorage.removeItem('tnbGuild'); }
  sel.value = GUILD;
  updateOrbisToggle();
}
function updateOrbisToggle(){
  const tog = $('#orbisTog'), chk = $('#orbisChk');
  if(!tog || !chk) return;
  const g = GUILDS.find(x=>String(x.gid)===String(GUILD));
  if(!GUILD || !g){ tog.style.display='none'; return; }
  tog.style.display='flex';
  chk.checked = !!g.forum_orbis;
}
async function onGuildChange(){
  GUILD = $('#guildSel').value || '';
  if(GUILD) localStorage.setItem('tnbGuild', GUILD); else localStorage.removeItem('tnbGuild');
  updateOrbisToggle();
  reloadCurrentView();
}
async function toggleOrbis(){
  if(!GUILD) return;
  const val = $('#orbisChk').checked;
  const {status, body} = await jpost('/admin/api/guild_settings', {gid:GUILD, key:'forum_orbis', value:val});
  if(status!==200){ alert(body.error||'Échec'); $('#orbisChk').checked=!val; return; }
  const g = GUILDS.find(x=>String(x.gid)===String(GUILD)); if(g) g.forum_orbis = val;
  if(body.home_guild!==undefined){ HOME_GUILD = body.home_guild||''; }
  renderGuildSel();
}
/* Recharge la vue active après un changement de serveur. */
function reloadCurrentView(){
  if(view==='dash') loadDash();
  else if(view==='conv'){ refreshState(); if(current) refreshThread(); }
  else if(view==='mem') loadMemories();
  else if(view==='search'){ const q=$('#q'); if(q && q.value) doSearch(); }
}

/* Bouton occupé : il se désactive et tourne pendant que la requête vit. */
async function busy(el, fn, texte){
  const b = (typeof el === 'string') ? $(el) : el;
  if(!b) return await fn();
  const old = b.innerHTML;
  b.disabled = true;
  b.innerHTML = '<span class="spin"></span>' + (texte || 'Patiente…');
  try{ return await fn(); }
  finally{ b.disabled = false; b.innerHTML = old; }
}
/* Version pour les boutons créés à la volée (onclick="…") : on récupère l'élément cliqué. */
function ev(){ return (window.event && window.event.currentTarget) || null; }

/* ---------- Notifications ---------- */
function toast(msg, ko){
  const d = document.createElement('div');
  d.className = 'toast' + (ko ? ' ko' : '');
  d.textContent = msg;
  $('#toasts').appendChild(d);
  setTimeout(()=>{ d.style.opacity='0'; d.style.transition='opacity .35s'; setTimeout(()=>d.remove(), 400); }, ko ? 6000 : 3800);
}

/* ---------- Tâches longues : vraie barre de progression ---------- */
let _tkTimer = null, _tkStart = 0, _tkDone = null;
function taskOpen(label){
  _tkStart = Date.now();
  $('#tk_label').textContent = label || 'Tâche en cours';
  $('#tk_step').textContent = 'Démarrage…';
  $('#tk_fill').style.width = '2%';
  $('#tk_pct').textContent = '0 %';
  $('#tk_time').textContent = '0 s';
  $('#tk_res').classList.add('hidden');
  $('#tk_res').classList.remove('ko');
  $('#tk_close').classList.add('hidden');
  $('#task').classList.remove('hidden');
}
function taskClose(){
  $('#task').classList.add('hidden');
  clearInterval(_tkTimer); _tkTimer = null;
  if(_tkDone){ const f=_tkDone; _tkDone=null; f(); }
}
/* Suit une tâche côté serveur jusqu'à sa fin. `apres` = ce qu'on rafraîchit ensuite. */
function taskFollow(id, label, apres){
  taskOpen(label);
  _tkDone = apres || null;
  clearInterval(_tkTimer);
  _tkTimer = setInterval(async () => {
    $('#tk_time').textContent = Math.round((Date.now()-_tkStart)/1000) + ' s';
    const {status, body} = await jget('/admin/api/task?id='+encodeURIComponent(id));
    if(status === 401){ clearInterval(_tkTimer); taskClose(); showLogin(); return; }
    if(status !== 200) return;                       // tâche pas encore visible : on repasse
    const t = body.tache || {};
    $('#tk_fill').style.width = Math.max(2, t.pct||0) + '%';
    $('#tk_pct').textContent = (t.pct||0) + ' %';
    if(t.etape) $('#tk_step').textContent = t.etape;
    if(t.fini){
      clearInterval(_tkTimer); _tkTimer = null;
      const r = $('#tk_res');
      r.textContent = t.resultat || (t.ok ? 'Terminé.' : 'Échec.');
      r.classList.remove('hidden');
      r.classList.toggle('ko', !t.ok);
      $('#tk_close').classList.remove('hidden');
      if(apres) apres();                             // on rafraîchit tout de suite
      _tkDone = null;
    }
  }, 700);
}

/* ---------- Auth ---------- */
async function populateGuilds(){
  const {status, body} = await jget('/admin/api/state');   /* sans filtre : liste complète */
  if(status===200) renderGuildSel(body.guilds, body.home_guild);
}
async function tryEnter(){
  const {status} = await jget('/admin/api/state');
  if(status===200){ showApp(); await populateGuilds(); switchView('dash'); startTimers(); }
  else showLogin();
}
function showLogin(){ $('#login').classList.remove('hidden'); $('#app').classList.add('hidden'); stopTimers(); }
function showApp(){ $('#login').classList.add('hidden'); $('#app').classList.remove('hidden'); }
$('#loginBtn').onclick = async () => {
  const pw = $('#pw').value;
  const {status, body} = await jpost('/admin/api/login', {password: pw});
  if(status===200){ $('#pw').value=''; $('#loginErr').textContent=''; tryEnter(); }
  else $('#loginErr').textContent = body.error || 'Échec.';
};
$('#pw').addEventListener('keydown', e => { if(e.key==='Enter') $('#loginBtn').click(); });
$('#logoutBtn').onclick = async () => { await jpost('/admin/api/logout',{}); showLogin(); };

/* ---------- Navigation ---------- */
function switchView(v){
  view = v;
  $$('.tab').forEach(t => t.classList.toggle('on', t.dataset.v===v));
  $$('.view').forEach(el => el.classList.add('hidden'));
  $('#v-'+v).classList.remove('hidden');
  if(v==='dash') loadDash();
  if(v==='conv') refreshState();
  if(v==='mem') loadMemories();
  if(v==='guilds') loadGuilds();
  if(v==='persona'){ loadPersona(); loadEmoji(); }
  if(v==='agenda') loadAgenda();
  if(v==='admin') loadAdmin();
}
$$('.tab').forEach(t => t.onclick = () => switchView(t.dataset.v));

/* ---------- Tableau de bord ---------- */
async function loadDash(){
  const {status, body} = await jget(gq('/admin/api/overview'));
  if(status!==200){ if(status===401) showLogin(); return; }
  const cards = [
    ['Personnes', body.users], ['Serveurs', body.guilds], ['Souvenirs', body.memories],
    ['Notes', body.notes], ['Notes serveur', body.guild_notes],
    ['Messages', body.messages], ['Actifs (7j)', body.active_7d],
    ['Relations', body.relations], ['En pause', body.paused],
  ];
  $('#statCards').innerHTML = cards.map(c =>
    '<div class="card"><div class="n">'+c[1]+'</div><div class="l">'+c[0]+'</div></div>').join('');
  $('#topTags').innerHTML = (body.top_tags||[]).length
    ? body.top_tags.map(t => '<span class="chip">'+esc(t.tag)+'<b>'+t.n+'</b></span>').join('')
    : '<span class="w" style="color:var(--dim)">Aucun tag encore.</span>';
  $('#cats').innerHTML = (body.categories||[]).map(c =>
    '<span class="chip cat">'+esc(c.cat)+'<b>'+c.n+'</b></span>').join('') || '<span style="color:var(--dim)">Vide.</span>';
  loadGraph();
}

async function loadGraph(){
  const {status, body} = await jget(gq('/admin/api/graph'));
  const svg = $('#graph');
  if(status!==200){ svg.innerHTML=''; return; }
  const W = svg.clientWidth || 800, H = 420, cx = W/2, cy = H/2;
  const nodes = body.nodes||[], edges = body.edges||[];
  if(!nodes.length){ svg.innerHTML = '<text x="'+cx+'" y="'+cy+'" fill="#9a8ea6" text-anchor="middle" font-size="14">Pas encore de personnes à relier.</text>'; return; }
  const master = nodes.find(n=>n.master);
  const ring = nodes.filter(n=>!n.master);
  const pos = {};
  if(master) pos[master.id] = [cx, cy];
  const R = Math.min(W,H)/2 - 70;
  ring.forEach((n,i) => {
    const a = (2*Math.PI*i)/Math.max(ring.length,1) - Math.PI/2;
    pos[n.id] = [cx + R*Math.cos(a), cy + R*Math.sin(a)];
  });
  let s = '';
  edges.forEach(e => {
    const p = pos[e.a], q = pos[e.b];
    if(p&&q) s += '<line x1="'+p[0]+'" y1="'+p[1]+'" x2="'+q[0]+'" y2="'+q[1]+'" stroke="#3a2c44" stroke-width="1.5"/>';
  });
  nodes.forEach(n => {
    const p = pos[n.id]; if(!p) return;
    const r = n.master ? 22 : Math.max(9, Math.min(18, 8 + (n.weight||0)));
    const fill = n.master ? '#c9a24b' : '#b02a3a';
    s += '<g style="cursor:pointer" onclick="fromGraph(\''+n.id+'\')">';
    s += '<circle cx="'+p[0]+'" cy="'+p[1]+'" r="'+r+'" fill="'+fill+'" opacity="0.9"/>';
    s += '<text x="'+p[0]+'" y="'+(p[1]+r+14)+'" fill="#e9e2ee" text-anchor="middle" font-size="12">'+esc(n.name)+'</text></g>';
  });
  svg.setAttribute('viewBox','0 0 '+W+' '+H);
  svg.innerHTML = s;
}
function fromGraph(uid){ switchView('conv'); openThread(uid); }

/* ---------- Liste conversations ---------- */
async function refreshState(){
  const {status, body} = await jget(gq('/admin/api/state'));
  if(status!==200){ if(status===401) showLogin(); return; }
  renderGuildSel(body.guilds, body.home_guild);
  renderList(body.users);
}
/* Où parle la personne ? Message privé, ou salon d'un serveur ? */
function lieuHTML(u){
  const t = u.lieu_type || 'inconnu';
  if(t === 'mp')
    return '<span class="badge mp">✉ MP</span><span class="w">conversation privée</span>'+
           (u.lieu_vivant ? '' : '<span class="w">· hors ligne</span>');
  if(t === 'serveur')
    return '<span class="badge srv">💬 SERVEUR</span><span class="w">'+esc(u.lieu_salon||'')+
           (u.lieu_serveur ? ' · '+esc(u.lieu_serveur) : '')+'</span>';
  return '<span class="badge unk">? lieu inconnu</span>';
}

function renderList(users){
  const list = $('#list');
  list.innerHTML = '';
  if(!users || !users.length){ list.innerHTML='<div style="padding:20px;color:var(--dim);font-size:13px">Aucune conversation encore.</div>'; return; }
  for(const u of users){
    const row = document.createElement('div');
    row.className = 'row' + (String(u.uid)===String(current) ? ' active':'');
    row.onclick = () => openThread(u.uid);
    let badges = '';
    if(u.is_master) badges += '<span class="badge master">MAÎTRE</span>';
    if(u.paused) badges += '<span class="badge paused">EN PAUSE</span>';
    if(!u.reachable && u.lieu_type==='inconnu') badges += '<span class="badge off">hors portée</span>';
    row.innerHTML =
      '<div class="dot'+(u.paused?' p':'')+'"></div>'+
      '<div style="min-width:0;flex:1">'+
        '<div class="nm">'+esc(u.username || u.name)+' '+badges+'</div>'+
        (u.name && u.username && u.name!==u.username ? '<div class="meta">'+esc(u.name)+'</div>' : '')+
        '<div class="lieu">'+lieuHTML(u)+'</div>'+
        '<div class="pv">'+esc(u.preview||'—')+'</div>'+
        '<div class="meta">'+u.messages+' msg · vu '+esc(u.last_seen||'?')+'</div>'+
      '</div>';
    list.appendChild(row);
  }
}

/* ---------- Fil + fiche ---------- */
async function openThread(uid){
  current = String(uid);
  document.body.classList.add('viewthread');
  if(view!=='conv') switchView('conv');
  await refreshThread();
}
function backToList(){ document.body.classList.remove('viewthread'); current=null; }

function ficheHTML(b){
  const p = b.profile || {};
  let rows = '';
  const line = (k,v) => v ? '<div class="frow"><div class="fk">'+k+'</div><div class="fv">'+v+'</div></div>' : '';
  rows += line('Résumé', esc(p.summary));
  rows += line('Intérêts', (p.interests||[]).map(esc).join(', '));
  rows += line('Aime', (p.liked_topics||[]).map(esc).join(', '));
  rows += line('Sensible', (p.sensitive_topics||[]).map(esc).join(', '));
  rows += line('Humeur', esc(p.mood));
  rows += line('Style', esc(p.style));
  const tags = (b.tags||[]).map(t=>'<span class="chip">'+esc(t)+'</span>').join(' ');
  rows += tags ? '<div class="frow"><div class="fk">Tags</div><div class="fv chips">'+tags+'</div></div>' : '';
  const rels = b.relations||{};
  const relTxt = Object.keys(rels).map(k=>esc(k)+' — '+esc(rels[k])).join('<br>');
  rows += relTxt ? '<div class="frow"><div class="fk">Liens</div><div class="fv">'+relTxt+'</div></div>' : '';
  // Notes éditables avec métadonnées
  let notes = '';
  (b.notes||[]).forEach(n => {
    const imp = n.importance||'normale';
    const meta = esc(n.category||'observation')+' · '+esc(n.author||'IA')+' · '+esc(n.date)+(n.modified?(' · modifié '+esc(n.modified)):'');
    notes += '<div class="noteitem"><div class="nt">'+
      '<span class="imp '+imp+'">'+imp+'</span> '+esc(n.text)+
      '<div class="nd">'+meta+'</div></div>'+
      '<button class="mini ghost" onclick="editNote('+n.i+')">Éditer</button>'+
      '<button class="mini ghost" onclick="delNote('+n.i+')">🗑</button></div>';
  });
  const addBtn = '<button class="mini ghost" onclick="addNote()" style="margin-top:6px">+ Ajouter une note</button>';
  const notesBlock = '<div class="frow"><div class="fk">Notes ('+((b.notes||[]).length)+')</div><div class="fv">'+
    (notes || '<span style="color:var(--dim)">Aucune note.</span>')+addBtn+'</div></div>';
  const hasFiche = rows.trim().length > 0;
  return '<div class="fiche"><h3 style="margin:0 0 6px;color:var(--gold);font-size:12px;letter-spacing:1px;text-transform:uppercase">Fiche</h3>'+
    (hasFiche ? rows : '<div style="color:var(--dim);font-size:13px">Fiche encore vide — elle se remplit au fil des conversations.</div>')+
    notesBlock + '</div>';
}

async function refreshThread(){
  if(!current) return;
  const {status, body} = await jget(gq('/admin/api/thread?uid='+current));
  if(status!==200){ if(status===401) showLogin(); return; }
  curMeta = body;
  $('#head').classList.remove('hidden');
  $('#compose').classList.remove('hidden');
  $('#composeNote').classList.remove('hidden');
  $('#hWho').textContent = body.username || body.name;
  const lieu = (body.lieu_type==='mp') ? '✉ message privé'
             : (body.lieu_type==='serveur') ? ('💬 '+(body.lieu_salon||'')+(body.lieu_serveur?(' · '+body.lieu_serveur):''))
             : '? lieu inconnu';
  $('#hSub').innerHTML = esc((body.name && body.name!==body.username ? body.name+' · ' : '')+'id '+body.uid+' · '+(body.interactions||0)+' interactions')+
    ' · <span class="badge '+(body.lieu_type==='mp'?'mp':(body.lieu_type==='serveur'?'srv':'unk'))+'">'+esc(lieu)+'</span>'+
    (body.lieu_vivant ? '' : ' <span style="color:var(--dim)">(dernier lieu connu)</span>');
  setPauseUI(body.paused);
  $('#composeNote').textContent = body.paused
    ? "IA en pause : Tenebris ne répond plus à cette personne. Tes messages partent en ton nom, via le bot."
    : "IA active : tes messages partent quand même via le bot, en plus des réponses automatiques.";

  const s = $('#stream');
  const atBottom = (s.scrollHeight - s.scrollTop - s.clientHeight) < 60;
  s.innerHTML = '';
  s.insertAdjacentHTML('beforeend', ficheHTML(body));
  if(body.summary){
    const d = document.createElement('div'); d.className='sum';
    d.innerHTML = '<b>Résumé des échanges plus anciens</b><br>'+esc(body.summary);
    s.appendChild(d);
  }
  if(!body.messages || !body.messages.length){
    const e = document.createElement('div'); e.style.color='var(--dim)'; e.style.fontSize='13px';
    e.textContent='Pas de messages en mémoire vive pour cette personne.';
    s.appendChild(e);
  } else {
    for(const m of body.messages){
      const div = document.createElement('div');
      const mine = (m.role === 'assistant');
      div.className = 'msg ' + (mine?'a':'u');
      div.innerHTML = '<div class="lbl">'+(mine?'Tenebris':esc(body.username || body.name))+'</div>'+esc(m.content);
      s.appendChild(div);
    }
  }
  if(atBottom) s.scrollTop = s.scrollHeight;
}

async function editNote(i){
  if(!current || !curMeta) return;
  const cur = (curMeta.notes.find(n=>n.i===i)||{}).text || '';
  const txt = window.prompt('Modifier la note :', cur);
  if(txt===null) return;
  const t = txt.trim();
  if(!t){ return delNote(i); }
  const {status} = await jpost('/admin/api/note', {uid: current, index: i, text: t});
  if(status===200) refreshThread();
}
async function addNote(){
  if(!current) return;
  const txt = window.prompt('Nouvelle note sur cette personne :');
  if(txt===null) return;
  const t = txt.trim(); if(!t) return;
  let imp = (window.prompt('Importance ? faible / normale / haute', 'normale')||'normale').trim().toLowerCase();
  if(['faible','normale','haute'].indexOf(imp)<0) imp='normale';
  const {status} = await jpost('/admin/api/note', {uid: current, text: t, importance: imp, category: 'note admin', guild: GUILD});
  if(status===200) refreshThread();
}
async function delNote(i){
  if(!current) return;
  if(!window.confirm('Supprimer cette note ?')) return;
  const {status} = await jpost('/admin/api/note', {uid: current, index: i, delete: true});
  if(status===200) refreshThread();
}

function setPauseUI(paused){
  $('#pauseTgl').classList.toggle('on', !!paused);
  $('#pauseLbl').textContent = paused ? 'IA en pause' : 'IA active';
}
$('#pauseTgl').onclick = async () => {
  if(!current || !curMeta) return;
  const next = !curMeta.paused;
  setPauseUI(next);
  const {status} = await jpost('/admin/api/pause', {uid: current, paused: next});
  if(status===401) showLogin();
  await refreshThread(); await refreshState();
};

/* ---------- Envoi manuel ---------- */
async function doSend(){
  const ta = $('#msg'); const text = ta.value.trim();
  if(!text || !current) return;
  $('#sendBtn').disabled = true;
  const {status, body} = await jpost('/admin/api/send', {uid: current, text});
  $('#sendBtn').disabled = false;
  if(status===200){ ta.value=''; refreshThread(); toast('Message envoyé via le bot.'); }
  else if(status===401) showLogin();
  else toast(body.error || 'Échec de l\'envoi.', true);
}
$('#sendBtn').onclick = doSend;
$('#msg').addEventListener('keydown', e => { if(e.key==='Enter' && (e.ctrlKey||e.metaKey)){ e.preventDefault(); doSend(); } });
$$('.backBtn').forEach(b => b.onclick = backToList);

/* ---------- Recherche ---------- */
async function doSearch(){
  const q = $('#q').value.trim();
  const box = $('#results');
  if(!q){ box.innerHTML=''; return; }
  const {status, body} = await jget('/admin/api/search?q='+encodeURIComponent(q));
  if(status!==200){ if(status===401) showLogin(); return; }
  if(!body.results.length){ box.innerHTML='<div style="color:var(--dim)">Rien trouvé pour « '+esc(q)+' ».</div>'; return; }
  box.innerHTML = body.results.map(r => {
    const nav = r.uid ? ' onclick="fromGraph(\''+r.uid+'\')" style="cursor:pointer"' : '';
    return '<div class="result"'+nav+'><div class="k">'+esc(r.kind)+' · '+esc(r.who)+'</div>'+
      '<div>'+esc(r.text)+'</div><div class="w">'+esc(r.date||'')+'</div></div>';
  }).join('');
}
$('#qBtn').onclick = doSearch;
$('#q').addEventListener('keydown', e => { if(e.key==='Enter') doSearch(); });

/* ---------- Mémoire ---------- */
async function loadMemories(){
  const {status, body} = await jget(gq('/admin/api/memories'));
  const box = $('#memList');
  if(status!==200){ if(status===401) showLogin(); return; }
  if(!body.memories.length){ box.innerHTML='<div style="color:var(--dim)">Mémoire vide'+(GUILD?' pour ce serveur':'')+'.</div>'; return; }
  box.innerHTML = body.memories.map(m =>
    '<div class="memrow"><span class="mc'+(m.directive?' dir':'')+'">'+esc(m.category)+'</span>'+
    '<div class="mt">'+esc(m.text)+'<div class="nd" style="color:var(--dim);font-size:11px">'+esc(m.date)+guildTag(m.guild)+'</div></div>'+
    '<button class="mini ghost" onclick="editMem('+m.i+')">Éditer</button>'+
    '<button class="mini ghost" onclick="delMem('+m.i+')">🗑</button></div>').join('');
}
/* Étiquette du serveur d'origine (affichée surtout en vue « tous serveurs »). */
function guildName(gid){
  if(!gid) return '';
  const g = GUILDS.find(x=>String(x.gid)===String(gid));
  return g ? g.name : gid;
}
function guildTag(gid){
  if(GUILD) return '';                 /* déjà filtré sur un serveur : inutile */
  const nm = gid ? guildName(gid) : (HOME_GUILD ? 'hérité › '+guildName(HOME_GUILD) : 'hérité');
  return ' · <span style="color:var(--accent,#8a7bff)">🌐 '+esc(nm)+'</span>';
}
async function addMem(){
  const inp = $('#newMem'); const t = inp.value.trim();
  if(!t) return;
  const {status} = await jpost('/admin/api/memory', {text: t, guild: GUILD});
  if(status===200){ inp.value=''; loadMemories(); }
  else if(status===401) showLogin();
}
async function editMem(i){
  const txt = window.prompt('Modifier le souvenir :');
  if(txt===null) return;
  const t = txt.trim(); if(!t) return;
  const {status} = await jpost('/admin/api/memory', {index: i, text: t});
  if(status===200) loadMemories();
}
async function delMem(i){
  if(!window.confirm('Supprimer ce souvenir ?')) return;
  const {status} = await jpost('/admin/api/memory', {index: i, delete: true});
  if(status===200) loadMemories();
}
$('#addMemBtn').onclick = addMem;
$('#newMem').addEventListener('keydown', e => { if(e.key==='Enter') addMem(); });

/* ---------- Serveurs ---------- */
async function loadGuilds(){
  const {status, body} = await jget('/admin/api/guilds');
  const box = $('#guildList');
  if(status!==200){ if(status===401) showLogin(); return; }
  if(!body.guilds || !body.guilds.length){ box.innerHTML='<div style="color:var(--dim)">Aucun serveur connu.</div>'; return; }
  box.innerHTML = body.guilds.map(g => {
    const notes = (g.notes||[]).map(n =>
      '<div class="noteitem"><div class="nt"><span class="imp '+(n.importance||'normale')+'">'+esc(n.importance||'normale')+'</span> '+
      esc(n.text)+'<div class="nd">'+esc(n.category||'observation')+' · '+esc(n.author||'IA')+' · '+esc(n.date)+
      (n.modified?(' · modifié '+esc(n.modified)):'')+'</div></div>'+
      '<button class="mini ghost" onclick="editGuildNote(\''+g.gid+'\','+n.i+')">Éditer</button>'+
      '<button class="mini ghost" onclick="delGuildNote(\''+g.gid+'\','+n.i+')">🗑</button></div>').join('')
      || '<div style="color:var(--dim);font-size:13px">Aucune note pour l\'instant.</div>';
    return '<div class="adm-sec">'+
      '<h3>'+esc(g.name)+(g.present?'':' <span class="badge off">absente</span>')+'</h3>'+
      '<div style="color:var(--dim);font-size:12px;margin-bottom:10px">'+
        g.members+' membres · rejoint '+esc(g.joined||'?')+' · dernière observation : '+esc(g.last_observed||'jamais')+'</div>'+
      (g.purpose ? '<div class="fiche" style="margin-bottom:12px">'+
        '<div class="frow"><div class="fk">But</div><div class="fv">'+esc(g.purpose)+'</div></div>'+
        (g.type ? '<div class="frow"><div class="fk">Type</div><div class="fv">'+esc(g.type)+'</div></div>' : '')+
        (g.theme ? '<div class="frow"><div class="fk">Thème</div><div class="fv">'+esc(g.theme)+'</div></div>' : '')+
        (g.public ? '<div class="frow"><div class="fk">Public</div><div class="fv">'+esc(g.public)+'</div></div>' : '')+
        ((g.activites&&g.activites.length) ? '<div class="frow"><div class="fk">Activités</div><div class="fv chips">'+
            g.activites.map(a=>'<span class="chip">'+esc(a)+'</span>').join(' ')+'</div></div>' : '')+
        (g.confiance ? '<div class="frow"><div class="fk">Confiance</div><div class="fv">'+esc(g.confiance)+'</div></div>' : '')+
      '</div>' : '<div style="color:var(--dim);font-size:13px;margin-bottom:12px">But non encore déterminé — lance une observation.</div>')+
      (g.summary ? '<div class="sum" style="margin-bottom:12px"><b>Résumé</b><br>'+esc(g.summary)+'</div>' : '')+
      '<div class="fk" style="margin-bottom:6px">Notes ('+((g.notes||[]).length)+')</div>'+notes+
      '<div class="btnrow">'+
        '<button class="mini ghost" onclick="addGuildNote(\''+g.gid+'\')">+ Ajouter une note</button>'+
        (g.present ? '<button class="mini" onclick="observeGuild(\''+g.gid+'\',\''+esc(g.name).replace(/'/g,"\\'")+'\')">👁 Observer maintenant</button>' : '')+
      '</div></div>';
  }).join('');
}
async function addGuildNote(gid){
  const txt = window.prompt('Nouvelle note sur ce serveur :');
  if(txt===null) return;
  const t = txt.trim(); if(!t) return;
  const {status} = await jpost('/admin/api/guild_note', {gid, text: t, importance: 'normale'});
  if(status===200) loadGuilds(); else if(status===401) showLogin();
}
async function editGuildNote(gid, i){
  const txt = window.prompt('Modifier la note :');
  if(txt===null) return;
  const t = txt.trim(); if(!t) return delGuildNote(gid, i);
  const {status} = await jpost('/admin/api/guild_note', {gid, index: i, text: t});
  if(status===200) loadGuilds();
}
async function delGuildNote(gid, i){
  if(!window.confirm('Supprimer cette note de serveur ?')) return;
  const {status} = await jpost('/admin/api/guild_note', {gid, index: i, delete: true});
  if(status===200) loadGuilds();
}
async function observeGuild(gid, nom){
  const {status, body} = await jpost('/admin/api/observe', {gid});
  if(status!==200){ toast((body && body.error) || 'Échec.', true); return; }
  taskFollow(body.task, 'Observation — ' + (nom || 'serveur'), loadGuilds);
}

/* ---------- Personnalité ---------- */
function renderPersona(p){
  $('#p_nom').value = p.nom||'';
  $('#p_essence').value = p.essence||'';
  $('#p_ton').value = p.ton||'';
  $('#p_caractere').value = (p.caractere||[]).join('\n');
  $('#p_interdits').value = (p.interdits||[]).join('\n');
  const box = $('#adaptList');
  const a = p.adaptations||[];
  box.innerHTML = a.length ? a.map((x,i) =>
    '<div class="noteitem"><div class="nt">'+esc(x.texte)+
    '<div class="nd">'+esc(x.auteur||'IA')+' · '+esc(x.date||'')+(x.raison?(' · '+esc(x.raison)):'')+'</div></div>'+
    '<button class="mini ghost" onclick="delAdaptation('+i+')">🗑</button></div>').join('')
    : '<div style="color:var(--dim);font-size:13px">Aucune adaptation pour l\'instant — elle apprendra en observant.</div>';
}
async function loadPersona(){
  const {status, body} = await jget('/admin/api/persona');
  if(status!==200){ if(status===401) showLogin(); return; }
  renderPersona(body.persona);
}
async function savePersona(){
  const payload = {
    action:'save',
    nom: $('#p_nom').value.trim(),
    essence: $('#p_essence').value.trim(),
    ton: $('#p_ton').value.trim(),
    caractere: $('#p_caractere').value.split('\n').map(s=>s.trim()).filter(Boolean),
    interdits: $('#p_interdits').value.split('\n').map(s=>s.trim()).filter(Boolean),
  };
  const {status, body} = await jpost('/admin/api/persona', payload);
  if(status===200){ renderPersona(body.persona); alert('Personnalité enregistrée. Elle s\'applique dès le prochain message.'); }
  else alert((body&&body.error)||'Échec.');
}
async function resetPersona(){
  if(!window.confirm('Rétablir la personnalité d\'origine ? Les adaptations apprises seront perdues.')) return;
  const {status, body} = await jpost('/admin/api/persona', {action:'reset'});
  if(status===200) renderPersona(body.persona);
}
async function addAdaptation(){
  const t = window.prompt('Nouvelle adaptation :');
  if(t===null || !t.trim()) return;
  const {status, body} = await jpost('/admin/api/persona', {action:'add_adaptation', texte:t.trim()});
  if(status===200) renderPersona(body.persona);
}
async function delAdaptation(i){
  if(!window.confirm('Supprimer cette adaptation ?')) return;
  const {status, body} = await jpost('/admin/api/persona', {action:'del_adaptation', index:i});
  if(status===200) renderPersona(body.persona);
}
async function evolvePersona(){
  const {status, body} = await jpost('/admin/api/persona', {action:'evolve'});
  if(status===200){
    renderPersona(body.persona);
    alert(body.added ? (body.added+' adaptation(s) apprise(s) des membres.') : 'Rien de neuf à retenir pour l\'instant.');
  } else alert((body&&body.error)||'Échec.');
}

/* ---------- Emoji ---------- */
function renderEmoji(b){
  $('#emoImg').src = b.image;
  $('#emoOrig').textContent = b.personnalisee ? 'image personnalisée' : "image d'origine";
  const s = b.serveurs||[];
  $('#emoServers').innerHTML = s.length ? s.map(g => {
    let etat, actions;
    if(g.a_lemoji){
      etat = '<span style="color:var(--ok,#7ddc9a)">✓ '+esc(g.code)+'</span>';
      actions = '<button class="mini ghost" onclick="emojiAction(\''+g.gid+'\',\'recreate\')">Réappliquer l\'image</button>'+
                '<button class="mini ghost" onclick="emojiAction(\''+g.gid+'\',\'delete\')">🗑</button>';
    } else if(!g.peut_creer){
      etat = '<span style="color:var(--dim)">permission « Gérer les expressions » manquante</span>';
      actions = '';
    } else if(g.place<=0){
      etat = '<span style="color:var(--dim)">plus de place pour un emoji</span>';
      actions = '';
    } else {
      etat = '<span style="color:var(--dim)">pas encore créé</span>';
      actions = '<button class="mini" onclick="emojiAction(\''+g.gid+'\',\'create\')">Créer</button>';
    }
    return '<div class="noteitem"><div class="nt"><b>'+esc(g.name)+'</b><div class="nd">'+etat+'</div></div>'+actions+'</div>';
  }).join('') : '<div style="color:var(--dim);font-size:13px">Aucun serveur.</div>';
}
async function loadEmoji(){
  const {status, body} = await jget('/admin/api/emoji');
  if(status!==200){ if(status===401) showLogin(); return; }
  renderEmoji(body);
}
async function emojiAction(gid, action){
  if(action==='delete' && !window.confirm('Supprimer son emoji sur ce serveur ?')) return;
  const {status, body} = await jpost('/admin/api/emoji', {action, gid});
  if(status===200) loadEmoji(); else alert((body&&body.error)||'Échec.');
}
async function createAllEmoji(){
  const {status, body} = await jpost('/admin/api/emoji', {action:'create_all'});
  if(status===200){ alert('Emoji créé sur '+body.faits+' serveur(s).'); loadEmoji(); }
}
async function resetEmojiImage(){
  const {status, body} = await jpost('/admin/api/emoji', {action:'reset_image'});
  if(status===200){ renderEmoji({image:body.image, personnalisee:false, serveurs:[]}); loadEmoji();
    alert("Image d'origine rétablie. Utilise « Réappliquer l'image » sur chaque serveur."); }
}
/* Le redimensionnement se fait ICI, dans le navigateur : pas de dépendance image côté serveur. */
function resizeToPng(file, side){
  return new Promise((resolve, reject) => {
    const fr = new FileReader();
    fr.onerror = () => reject(new Error('lecture impossible'));
    fr.onload = () => {
      const img = new Image();
      img.onerror = () => reject(new Error('image invalide'));
      img.onload = () => {
        const c = document.createElement('canvas');
        c.width = side; c.height = side;
        const ctx = c.getContext('2d');
        ctx.clearRect(0,0,side,side);                  // fond transparent
        const r = Math.min(side/img.width, side/img.height);
        const w = img.width*r, h = img.height*r;
        ctx.drawImage(img, (side-w)/2, (side-h)/2, w, h);
        resolve(c.toDataURL('image/png'));
      };
      img.src = fr.result;
    };
    fr.readAsDataURL(file);
  });
}
async function uploadEmoji(){
  const f = $('#emoFile').files[0];
  if(!f){ alert('Choisis une image.'); return; }
  let dataUrl;
  try { dataUrl = await resizeToPng(f, 128); }
  catch(e){ alert('Image illisible.'); return; }
  const octets = Math.round((dataUrl.length - dataUrl.indexOf(',') - 1) * 3/4);
  if(octets > 240000){ alert('Image trop lourde après conversion ('+Math.round(octets/1024)+' Ko).'); return; }
  const {status, body} = await jpost('/admin/api/emoji', {action:'set_image', image:dataUrl});
  if(status===200){
    renderEmoji({image:body.image, personnalisee:true, serveurs:[]});
    loadEmoji();
    alert("Image enregistrée. Clique « Réappliquer l'image » sur chaque serveur pour la mettre en place.");
  } else alert((body&&body.error)||'Échec.');
}

/* ---------- Rappels & Missions ---------- */
let _cibles = [];
function renderReminders(rs){
  const box = $('#remList');
  box.innerHTML = rs.length ? rs.map(r => {
    const badge = r.mode === 'mp'
      ? '<span style="color:#c9a0ff">✉ ' + esc(r.destination) + '</span>'
      : '<span style="color:#7ddc9a">💬 ' + esc(r.destination) + (r.serveur ? ' · ' + esc(r.serveur) : '') + '</span>';
    return '<div class="noteitem"><div class="nt">' + esc(r.texte) +
      '<div class="nd">' + badge + ' · ' + esc(r.quand) + ' (' + esc(r.restant) + ')' +
      (r.source && r.source !== 'manuel' ? ' · ' + esc(r.source) : '') + '</div></div>' +
      '<button class="mini ghost" onclick="cancelReminder(\'' + r.id + '\')">🗑</button></div>';
  }).join('') : '<div style="color:var(--dim);font-size:13px">Aucun rappel programmé.</div>';
}
async function loadAgenda(){
  const a = await jget('/admin/api/reminders');
  if(a.status === 401){ showLogin(); return; }
  if(a.status === 200) renderReminders(a.body.rappels||[]);
  const b = await jget('/admin/api/missions');
  if(b.status === 200){
    _cibles = b.body.cibles || [];
    fillGuildSelects();
    renderMissions(b.body.missions||[]);
    switchMisType();
  }
}
function fillGuildSelects(){
  ['#rm_gid','#ms_gid'].forEach(sel => {
    const el = $(sel);
    el.innerHTML = _cibles.map(g => '<option value="'+g.gid+'">'+esc(g.name)+'</option>').join('');
  });
  fillRemChannels(); fillMisChannels();
}
function _chans(gid){
  const g = _cibles.find(x => x.gid === gid);
  return g ? g.salons : [];
}
function fillRemChannels(){
  $('#rm_salon').innerHTML = _chans($('#rm_gid').value)
    .map(c => '<option value="'+c.id+'">#'+esc(c.name)+'</option>').join('');
}
function fillMisChannels(){
  $('#ms_salon').innerHTML = _chans($('#ms_gid').value)
    .map(c => '<option value="'+c.id+'">#'+esc(c.name)+'</option>').join('');
}
/* Le bouton « Programmer » du formulaire de rappel simple. */
async function createReminder(){
  const payload = {
    action:'create',
    quand: $('#rm_quand').value.trim(),
    message: $('#rm_msg').value.trim(),
    en_prive: $('#rm_prive').checked,
    gid: $('#rm_gid').value,
    salon_id: $('#rm_salon').value,
    personne_id: $('#rm_uid').value.trim(),
  };
  const btn = ev();
  const {status, body} = await busy(btn, () => jpost('/admin/api/reminders', payload), 'Je programme…');
  if(status === 200){
    renderReminders(body.rappels); $('#rm_msg').value=''; $('#rm_quand').value='';
    toast('Rappel programmé.');
  }
  else toast((body&&body.error)||'Échec.', true);
}
async function cancelReminder(id){
  if(!window.confirm('Annuler ce rappel ?')) return;
  const {status, body} = await jpost('/admin/api/reminders', {action:'cancel', id});
  if(status === 200){ renderReminders(body.rappels); toast('Rappel annulé.'); }
  else toast((body&&body.error)||'Échec.', true);
}
function switchMisType(){
  const t = $('#ms_type').value;
  const prive = $('#ms_prive').checked && (t === 'rappel' || t === 'consigne');
  $('#ms_f_forum').classList.toggle('hidden', t !== 'forum');
  $('#ms_f_rappel').classList.toggle('hidden', t !== 'rappel');
  $('#ms_f_consigne').classList.toggle('hidden', t !== 'consigne');
  $('#ms_f_meme').classList.toggle('hidden', t !== 'meme');
  $('#ms_f_fin').classList.toggle('hidden', t === 'forum');
  $('#ms_prive').parentElement.classList.toggle('hidden', t === 'forum' || t === 'meme');
  $('#ms_f_salon').classList.toggle('hidden', prive);
  $('#ms_lab_uid').textContent = prive
    ? 'Destinataire du MP (ID Discord — obligatoire)'
    : 'Personne à mentionner (facultatif — ID Discord)';
  const mini = (t==='rappel') ? 5 : (t==='consigne' ? 10 : 15);
  $('#ms_freq').min = mini;
  if(parseInt($('#ms_freq').value||'0',10) < mini) $('#ms_freq').value = (t==='rappel' ? 30 : (t==='meme' ? 240 : 60));
  $('#ms_btn').textContent = (t==='forum') ? 'Confier la veille'
                           : (t==='rappel') ? 'Programmer le rappel récurrent'
                           : (t==='meme') ? 'Lancer les mèmes'
                           : 'Confier la consigne';
}

function misTypeBadge(t){
  if(t==='rappel')   return '<span class="badge srv">⏰ RAPPEL</span>';
  if(t==='consigne') return '<span class="badge master">🎲 CONSIGNE</span>';
  if(t==='meme')     return '<span class="badge mp">😹 MÈMES</span>';
  return '<span class="badge unk">📰 VEILLE</span>';
}

function renderMissions(ms){
  const box = $('#misList');
  if(!ms || !ms.length){
    box.innerHTML = '<div style="color:var(--dim);font-size:13px">Aucune mission.</div>';
    return;
  }
  box.innerHTML = ms.map(m => {
    const etat = m.termine ? '<span style="color:var(--dim)">terminée (échéance atteinte)</span>'
               : m.actif   ? '<span style="color:#7ddc9a">active</span>'
                           : '<span style="color:var(--dim)">en pause</span>';
    const dest = (m.mode === 'mp')
      ? '<span style="color:#c9a0ff">✉ ' + esc(m.destination) + '</span>'
      : '<span style="color:#7ddc9a">💬 ' + esc(m.destination) + (m.serveur ? ' · ' + esc(m.serveur) : '') + '</span>';
    const quoi = (m.type === 'forum') ? esc(m.url || '')
               : (m.type === 'rappel') ? esc((m.message || '').slice(0,140))
               : (m.type === 'meme') ? ('thème : <b>' + esc(m.message || 'général') + '</b>')
               : esc((m.consigne || '').slice(0,140));
    const err = m.erreurs > 0 ? ' · <span style="color:#e88">' + m.erreurs + ' échec(s)</span>' : '';
    const fin = m.fin ? ' · jusqu\'au <b>' + esc(m.fin) + '</b>' : ' · sans échéance';
    const nxt = (m.prochain && m.actif && !m.termine) ? ' · prochain passage ' + esc(m.prochain) : '';
    const env = m.envois ? ' · ' + m.envois + ' envoi(s)' : '';
    const con = (m.type === 'forum') ? ' · ' + m.connus + ' sujets connus'
                + (m.amorcee ? '' : ' · <span style="color:var(--dim)">pas encore amorcée</span>')
              : (m.type === 'meme') ? ' · ' + m.connus + ' déjà servis' : '';
    return '<div class="noteitem"><div class="nt">' +
      misTypeBadge(m.type) + ' <b>' + esc(m.nom) + '</b> → ' + dest +
      '<div class="nd">' + quoi + '</div>' +
      '<div class="nd">' + etat + ' · toutes les ' + m.interval_min + ' min' + fin + nxt + env + con + err + '</div></div>' +
      '<button class="mini ghost" onclick="misAction(\'' + m.id + '\',\'check\',\'' + esc(m.nom).replace(/'/g,"\\'") + '\')">Exécuter</button>' +
      (m.termine ? '<button class="mini ghost" onclick="misProlonger(\'' + m.id + '\')">Prolonger</button>'
                 : '<button class="mini ghost" onclick="misAction(\'' + m.id + '\',\'toggle\')">' + (m.actif ? 'Pause' : 'Activer') + '</button>') +
      '<button class="mini ghost" onclick="misAction(\'' + m.id + '\',\'delete\')">🗑</button></div>';
  }).join('');
}

async function createMission(){
  const t = $('#ms_type').value;
  const payload = {
    action: 'create',
    type: t,
    nom: $('#ms_nom').value.trim(),
    url: $('#ms_url').value.trim(),
    message: (t === 'meme') ? ($('#ms_theme').value.trim() || 'général') : $('#ms_msg').value.trim(),
    consigne: $('#ms_consigne').value.trim(),
    gid: $('#ms_gid').value,
    salon_id: $('#ms_salon').value,
    personne_id: $('#ms_uid').value.trim(),
    en_prive: $('#ms_prive').checked && (t === 'rappel' || t === 'consigne'),
    frequence_min: parseInt($('#ms_freq').value || '60', 10),
    fin: $('#ms_fin').value.trim(),
    demarrer_maintenant: $('#ms_now').checked,
  };
  const {status, body} = await busy('#ms_btn', () => jpost('/admin/api/missions', payload), 'Je m\'en charge…');
  if(status === 200){
    renderMissions(body.missions);
    $('#ms_url').value=''; $('#ms_nom').value=''; $('#ms_msg').value=''; $('#ms_consigne').value='';
    toast(t === 'forum'
      ? "Veille confiée. J'ai noté les sujets existants ; j'annoncerai les nouveaux."
      : t === 'meme'
      ? "Mission de mèmes lancée. Elle ne servira jamais deux fois le même."
      : "Mission confiée. Elle tournera jusqu'à l'échéance, puis s'arrêtera seule.");
  } else toast((body && body.error) || 'Échec.', true);
}

async function misAction(id, action, nom){
  if(action === 'delete' && !window.confirm('Supprimer cette mission ?')) return;
  const btn = ev();
  const {status, body} = await busy(btn, () => jpost('/admin/api/missions', {action, id}), '…');
  if(status !== 200){ toast((body && body.error) || 'Échec.', true); return; }
  if(body.missions) renderMissions(body.missions);
  if(action === 'check' && body.task){
    taskFollow(body.task, (nom || 'Mission') + ' — exécution', loadAgenda);
  }
}

async function misProlonger(id){
  const fin = window.prompt("Nouvelle échéance (ex : 2026-08-01 14:00, +3j, dans 6h) :");
  if(fin === null) return;
  const {status, body} = await jpost('/admin/api/missions', {action:'prolonger', id, fin: fin.trim()});
  if(status === 200){ renderMissions(body.missions); toast('Mission prolongée et réactivée.'); }
  else toast((body && body.error) || 'Échec.', true);
}

async function loadActions(){
  const {status, body} = await jget('/admin/api/actions');
  if(status !== 200) return;
  const a = body.actions || [];
  $('#actList').innerHTML = a.length ? a.map(x => {
    const icone = x.ok ? '<span style="color:#7ddc9a">✔</span>' : '<span style="color:#e88">✖</span>';
    return '<div class="noteitem"><div class="nt">' + icone + ' <b>' + esc(x.outil) + '</b> ' +
      '<span style="color:var(--dim)">' + esc(x.params) + '</span>' +
      '<div class="nd">' + esc(x.resultat) + '</div>' +
      '<div class="nd">' + esc(x.acteur) + ' · ' + esc(x.ts) + '</div></div></div>';
  }).join('') : '<div style="color:var(--dim);font-size:13px">Aucune action exécutée pour l\'instant.</div>';
}

/* ---------- Console d'administration ---------- */
async function loadAdmin(){ await loadSettings(); await loadLibrary(); await loadListen(); await loadAdminUsers(); await loadActions(); await loadAudit(); }

function renderLibrary(d){
  const s = d.stats||{}; 
  $('#lib_forum').textContent = d.forum||'—';
  $('#lib_toggle').checked = !!d.actif;
  const pct = s.total ? Math.round(100*s.resumes/s.total) : 0;
  if(!s.total){
    $('#lib_stats').innerHTML = 'Bibliothèque vide. Clique <b>Cartographier le forum</b> pour la construire.';
    return;
  }
  $('#lib_stats').innerHTML =
    '<b style="color:var(--txt)">'+s.total+'</b> sujets cartographiés · '+
    '<b style="color:#7ddc9a">'+s.resumes+'</b> résumés à jour ('+pct+' %) · '+
    ((d.copie&&d.copie.sujets_copies)? ('<b style="color:var(--acc)">'+d.copie.sujets_copies+'</b> copiés intégralement ('+Math.round((d.copie.octets||0)/1024)+' Ko) · ') : '')+
    ((d.copie&&d.copie.liens)? ('<b>'+d.copie.liens+'</b> liens · ') : '')+
    ((d.copie&&d.copie.sans_rubrique)? ('<b style="color:#e0a24e">'+d.copie.sans_rubrique+'</b> sans rubrique · ') : '')+
    (s.a_faire? ('<b>'+s.a_faire+'</b> en attente · ') : '')+
    'dernière carte : '+(s.derniere_carte||'jamais');
}
async function loadLibrary(){
  const {status, body} = await jget('/admin/api/library');
  if(status===401){ showLogin(); return; }
  if(status===200) renderLibrary(body);
}
async function libToggle(){
  const {status, body} = await jpost('/admin/api/library', {action:'toggle', actif: $('#lib_toggle').checked});
  if(status===200){ renderLibrary(body); toast(body.actif?'Remplissage automatique activé.':'Remplissage automatique coupé.'); }
}
async function analyserServeur(btn){
  if(!window.confirm("Lancer une analyse À FOND du serveur (tous les salons, résumé par salon) ? Ça peut prendre quelques minutes et consomme du quota.")) return;
  const {status, body} = await busy(btn, ()=>jpost('/admin/api/serveur', {action:'analyser'}), '…');
  if(status!==200){ toast((body&&body.error)||'Échec.', true); return; }
  if(body.task){ taskFollow(body.task, 'Analyse complète du serveur', null); }
}
async function libAction(action, btn){
  if(action==='vider' && !window.confirm('Vider toute la bibliothèque du forum ?')) return;
  const {status, body} = await busy(btn, ()=>jpost('/admin/api/library', {action}), '…');
  if(status!==200){ toast((body&&body.error)||'Échec.', true); return; }
  if(body.task){
    const lbl = action==='carte'?'Cartographie du forum':(action==='copie'?'Copie complète du forum':(action==='reparer'?'Réparation & tissage':(action==='reecrire'?'Réécriture des articles':'Résumés du forum')));
    taskFollow(body.task, lbl, loadLibrary);
  } else {
    renderLibrary(body);
    if(action==='vider') toast('Bibliothèque vidée.');
  }
}

async function cleanMemory(opts, btn){
  opts = opts || {};
  const merge = !!opts.merge, llm = opts.llm !== false;
  const msg = merge
    ? 'Optimiser toute la mémoire (doublons + fusion des notes proches + contradictions + consignes) et appliquer la limite de 10 notes par personne ? Les notes écrites à la main sont préservées.'
    : (llm
        ? 'Nettoyer la mémoire (doublons + contradictions) et appliquer la limite de 10 notes par personne ?'
        : 'Retirer les doublons (local) et appliquer la limite de 10 notes par personne ?');
  if(!window.confirm(msg)) return;
  const {status, body} = await busy(btn, ()=>jpost('/admin/api/clean_memory', {contradictions: llm, merge: merge}), '…');
  if(status!==200){ toast((body&&body.error)||'Échec.', true); return; }
  if(body.task){
    taskFollow(body.task, 'Nettoyage de la mémoire', ()=>{ if(window._curUser) openUser(window._curUser); });
  }
}

function renderListen(body){
  const box = $('#listenBox');
  $('#s_ecoute').value = body.mode || 'tous';
  const srv = body.serveurs||[];
  if(!srv.length){ box.innerHTML='<div style="color:var(--dim)">Aucun serveur.</div>'; return; }
  if(body.mode === 'aucune'){
    box.innerHTML = '<div style="color:var(--dim);font-size:13px">Elle est sourde : elle n\'entend aucun salon, et n\'apprend plus rien passivement.</div>';
    return;
  }
  const aide = (body.mode === 'tous')
    ? 'Elle écoute tout. Clique un salon pour le mettre <b>en sourdine</b>.'
    : 'Elle n\'écoute que ce que tu ouvres. Clique un salon pour <b>l\'ouvrir</b>.';
  box.innerHTML = '<div style="color:var(--dim);font-size:12px;margin-bottom:8px">'+aide+'</div>' +
    srv.map(g =>
      '<div style="margin-bottom:12px"><div class="fk" style="margin-bottom:6px">'+esc(g.name)+'</div>'+
      '<div class="chips">'+ g.salons.map(c =>
        '<span class="chip" style="cursor:pointer;'+(c.ouvert?'border-color:#7ddc9a;color:#7ddc9a':'opacity:.55')+'" '+
        'onclick="toggleListen(\''+c.id+'\','+(c.ouvert?'false':'true')+')">'+
        (c.ouvert?'👂 ':'🔇 ')+'#'+esc(c.name)+'</span>').join(' ')+
      '</div></div>').join('') +
    '<div style="color:var(--dim);font-size:12px;margin-top:6px">'+
      body.ouverts+' salon(s) écouté(s) sur '+body.total+
      (body.muets ? ' · '+body.muets+' en sourdine' : '')+
      ' · bavardage : <b>'+esc(body.niveau)+'</b></div>';
}
async function loadListen(){
  const {status, body} = await jget('/admin/api/listen');
  if(status!==200){ if(status===401) showLogin(); return; }
  renderListen(body);
}
async function setListenMode(){
  const {status, body} = await jpost('/admin/api/listen', {mode: $('#s_ecoute').value});
  if(status!==200){ toast((body&&body.error)||'Échec.', true); return; }
  renderListen(body);
  toast('Mode d\'écoute mis à jour.');
}
async function toggleListen(cid, ouvert){
  const on = (ouvert===true||ouvert==='true');
  const {status, body} = await jpost('/admin/api/listen', {salon_id: cid, ouvert: on});
  if(status!==200){ toast((body&&body.error)||'Échec.', true); return; }
  renderListen(body);
  toast(on ? 'Salon ouvert à son écoute.' : 'Salon mis en sourdine.');
}

async function loadSettings(){
  const {status, body} = await jget('/admin/api/settings');
  if(status!==200){ if(status===401) showLogin(); return; }
  const s = body.settings||{};
  $('#s_autonomy').value = s.autonomy_level||'normal';
  $('#s_autonote').checked = !!s.auto_note;
  $('#s_autoact').checked = !!s.auto_actions;
  $('#s_delib').checked = !!s.deliberation;
  $('#s_share').checked = !!s.share_between_users;
  $('#s_extract').value = (s.extract_every!=null)?s.extract_every:6;
  $('#s_reten').value = (s.retention_days!=null)?s.retention_days:0;
  $('#s_thresh').value = s.note_threshold||'normale';
  $('#s_rp').value = s.rp_mode||'intelligent';
  $('#s_bavard').value = s.bavardage||'jamais';
}
$('#saveSettings').onclick = async () => {
  const patch = {
    autonomy_level: $('#s_autonomy').value,
    auto_note: $('#s_autonote').checked,
    auto_actions: $('#s_autoact').checked,
    deliberation: $('#s_delib').checked,
    share_between_users: $('#s_share').checked,
    extract_every: parseInt($('#s_extract').value||'6',10),
    retention_days: parseInt($('#s_reten').value||'0',10),
    note_threshold: $('#s_thresh').value,
    rp_mode: $('#s_rp').value,
    bavardage: $('#s_bavard').value,
  };
  const {status} = await jpost('/admin/api/settings', {settings: patch});
  if(status===200){ const b=$('#saveSettings'); b.textContent='Enregistré ✓'; setTimeout(()=>b.textContent='Enregistrer les paramètres',1500); }
  else if(status===401) showLogin();
};

async function loadAdminUsers(){
  const {status, body} = await jget('/admin/api/state');
  if(status!==200){ if(status===401) showLogin(); return; }
  const box = $('#admUsers');
  box.innerHTML = (body.users||[]).map(u => {
    const badges = (u.is_master?'<span class="badge master">MAÎTRE</span>':'')
      + (u.is_admin && !u.is_master?'<span class="badge">admin</span>':'')
      + (u.paused?'<span class="badge" style="background:#7a3a3a">en pause</span>':'');
    return '<div class="admuser" style="cursor:pointer" onclick="openUser(\''+u.uid+'\')">'+
      '<div class="an">'+esc(u.username || u.name)+' '+badges+
        '<div style="color:var(--dim);font-size:12px;margin-top:2px">'+
        (u.messages||0)+' msg · vu '+(esc(u.last_seen)||'?')+'</div></div>'+
      '<div style="color:var(--dim);font-size:18px">›</div></div>';
  }).join('') || '<div style="color:var(--dim)">Aucun joueur connu.</div>';
}

async function openUser(uid){
  const {status, body} = await jget(gq('/admin/api/user?uid='+encodeURIComponent(uid)));
  if(status!==200){ toast((body&&body.error)||'Introuvable.', true); return; }
  const impColor = {faible:'#888', normale:'#c9a227', haute:'#c96a27'};
  const notesHtml = (body.notes||[]).map(n =>
    '<div style="border:1px solid var(--line);border-radius:8px;padding:8px 10px;margin-bottom:6px">'+
      '<div style="display:flex;justify-content:space-between;gap:8px">'+
        '<span>'+esc(n.text)+'</span>'+
        '<button class="mini ghost" style="flex-shrink:0" onclick="delNote(\''+body.uid+'\','+n.index+')">✕</button>'+
      '</div>'+
      '<div style="color:var(--dim);font-size:11px;margin-top:4px">'+
        '<span style="color:'+(impColor[n.importance]||'#888')+'">●</span> '+esc(n.importance)+
        ' · '+n.age_jours+'j'+
        (n.confidence && n.confidence!=='normale'?' · fiabilité '+esc(n.confidence):'')+
        (n.reviews?' · revue '+n.reviews+'×':'')+
        (n.author && n.author!=='IA'?' · ✍ '+esc(n.author):'')+
        (n.category?' · '+esc(n.category):'')+
      '</div>'+
      (n.context?'<div style="color:var(--dim);font-size:11px;margin-top:2px;font-style:italic">↳ '+esc(n.context)+'</div>':'')+
      '</div>').join('') || '<div style="color:var(--dim)">Aucune note sur cette personne.</div>';

  const badges = (body.is_master?'<span class="badge master">MAÎTRE</span>':'')
    + (body.is_admin && !body.is_master?'<span class="badge">admin</span>':'')
    + (body.paused?'<span class="badge" style="background:#7a3a3a">en pause</span>':'');
  const lieu = body.lieu_type==='mp' ? '✉ Messages privés'
    : (body.lieu_salon ? '💬 #'+esc(body.lieu_salon)+(body.lieu_serveur?' ('+esc(body.lieu_serveur)+')':'') : 'inconnu');

  $('#userDetail').innerHTML =
    '<button class="mini ghost" onclick="closeUser()">‹ Retour à la liste</button>'+
    '<h3 style="margin:10px 0 4px">'+esc(body.name)+' '+badges+'</h3>'+
    '<div style="color:var(--dim);font-size:13px;margin-bottom:12px">'+
      (body.username?'@'+esc(body.username)+' · ':'')+'id '+esc(body.uid)+'<br>'+
      (body.interactions||0)+' interactions · '+(body.messages||0)+' messages · dernier lieu : '+lieu+'<br>'+
      'vu '+(esc(body.last_seen)||'?')+
      (body.titre?' · titre : '+esc(body.titre):'')+
    '</div>'+
    '<div style="display:flex;gap:8px;margin-bottom:12px;flex-wrap:wrap">'+
      '<input id="newNote" class="inp" style="flex:1;min-width:180px" placeholder="Ajouter une note (permanente)…">'+
      '<button class="mini" onclick="addNote(\''+body.uid+'\')">+ Note</button>'+
      (body.notes_total?'<button class="mini ghost" onclick="clearNotes(\''+body.uid+'\')">🗑️ Tout effacer</button>':'')+
    '</div>'+
    '<div style="display:flex;gap:8px;margin-bottom:12px;flex-wrap:wrap">'+
      (body.is_master?'':'<button class="mini ghost" onclick="toggleAdmin(\''+body.uid+'\','+(!body.is_admin)+')">'+
        (body.is_admin?'Retirer admin':'Rendre admin')+'</button>')+
      '<button class="mini ghost" onclick="togglePause(\''+body.uid+'\','+(!body.paused)+')">'+
        (body.paused?'▶️ Réactiver l’IA':'⏸️ Mettre en pause')+'</button>'+
    '</div>'+
    '<div style="color:var(--dim);font-size:12px;margin-bottom:6px">'+body.notes_total+' note(s) — ce que Tenebris sait de cette personne :</div>'+
    notesHtml;
  $('#admUsers').style.display='none';
  $('#userDetail').style.display='block';
  window._curUser = body.uid;
}
function closeUser(){
  $('#userDetail').style.display='none';
  $('#admUsers').style.display='block';
  loadAdminUsers();
}
async function delNote(uid, index){
  const {status} = await jpost('/admin/api/user', {uid, action:'delete_note', index});
  if(status===200){ openUser(uid); toast('Note effacée.'); }
}
async function clearNotes(uid){
  if(!window.confirm('Effacer TOUTES les notes de cette personne ?')) return;
  const {status, body} = await jpost('/admin/api/user', {uid, action:'clear_notes'});
  if(status===200){ openUser(uid); toast((body.supprimees||0)+' note(s) effacée(s).'); }
}
async function addNote(uid){
  const t = $('#newNote').value.trim();
  if(!t) return;
  const {status} = await jpost('/admin/api/user', {uid, action:'add_note', texte:t, importance:'haute', guild: GUILD});
  if(status===200){ openUser(uid); toast('Note ajoutée (permanente).'); }
}
async function toggleAdmin(uid, val){
  const {status, body} = await jpost('/admin/api/set_admin', {uid, is_admin: val});
  if(status===401){ showLogin(); return; }
  if(status!==200){ toast(body.error||'Refusé.', true); return; }
  openUser(uid); toast(val?'Admin accordé.':'Admin retiré.');
}
async function togglePause(uid, val){
  const {status, body} = await jpost('/admin/api/pause', {uid, paused: val});
  if(status!==200){ toast((body&&body.error)||'Refusé.', true); return; }
  openUser(uid); toast(val?'IA mise en pause pour cette personne.':'IA réactivée.');
}

async function loadAudit(){
  const {status, body} = await jget('/admin/api/audit');
  if(status!==200) return;
  $('#auditList').innerHTML = (body.audit||[]).map(a =>
    '<div class="auditrow"><span class="at">'+esc(a.ts)+'</span><span class="aa">'+esc(a.action)+'</span>'+
    '<span style="flex:1">'+esc(a.detail)+'</span><span style="color:var(--dim)">'+esc(a.actor)+'</span></div>').join('')
    || '<div style="color:var(--dim)">Aucune action journalisée.</div>';
}

/* Données mémoire */
$('#btnExport').onclick = () => { window.location = '/admin/api/export'; };
$('#btnImport').onclick = () => $('#fileImport').click();
$('#fileImport').onchange = async (e) => {
  const f = e.target.files[0]; if(!f) return;
  if(!window.confirm('Importer remplacera TOUTE la mémoire actuelle (une sauvegarde sera créée). Continuer ?')){ e.target.value=''; return; }
  try{
    const data = JSON.parse(await f.text());
    const {status, body} = await jpost('/admin/api/import', {data});
    if(status===200){ alert('Import réussi : '+body.users+' fiches, '+body.memories+' souvenirs.'); loadAdmin(); }
    else alert(body.error||'Import refusé.');
  }catch(err){ alert('Fichier JSON invalide.'); }
  e.target.value='';
};
$('#btnRestore').onclick = async () => {
  if(!window.confirm('Restaurer la dernière sauvegarde automatique ?')) return;
  const {status, body} = await jpost('/admin/api/restore', {});
  if(status===200){ alert('Sauvegarde restaurée.'); loadAdmin(); }
  else alert(body.error||'Aucune sauvegarde disponible.');
};
$('#btnReset').onclick = async () => {
  const scope = $('#resetScope').value;
  if(!window.confirm('Réinitialiser ('+scope+') ? Une sauvegarde sera créée pour pouvoir annuler.')) return;
  const {status} = await jpost('/admin/api/reset', {scope});
  if(status===200){ alert('Réinitialisé. (Restaure la sauvegarde pour annuler.)'); loadAdmin(); }
  else if(status===401) showLogin();
};

/* ---------- Timers ---------- */
function startTimers(){
  stopTimers();
  stateTimer = setInterval(() => { if(view==='conv') refreshState(); }, 5000);
  threadTimer = setInterval(() => { if(view==='conv' && current) refreshThread(); }, 3500);
  // Onglet admin : on rafraîchit la liste des salons écoutés pour voir arriver les
  // nouveaux salons sans recharger la page (toutes les 15 s, seulement si visible).
  channelTimer = setInterval(() => { if(view==='admin') loadListen(); }, 15000);
}
function stopTimers(){ clearInterval(stateTimer); clearInterval(threadTimer); clearInterval(channelTimer); }

tryEnter();
</script>
</body>
</html>"""
