// Interactive collaboration network (data: assets/data/network.json, made by src/13_export_site_data.py)
(function () {
  const root = document.getElementById("explorer");
  if (!root) return;
  const stage = root.querySelector(".ex-stage");
  const fallback = () => {
    stage.innerHTML = '<img class="fallback" src="assets/img/network_maps.png" alt="1980s vs 2010s collaboration networks">';
    root.querySelector(".ex-bar").style.display = "none";
  };
  if (typeof d3 === "undefined") return fallback();

  const PAL = ["#ff5a5f", "#4fd18b", "#5b8cff", "#ffa24c", "#c77dff", "#4dd9f0", "#ff6fd8", "#e8c46a"];
  const OTHER = "#4a443b";
  const info = stage.querySelector(".ex-info"), tip = stage.querySelector(".ex-tip");
  // person / community card lives at the top of the side panel, above the colour key
  const side = root.querySelector(".ex-side");
  const card = document.createElement("div"); card.className = "ex-card";
  (side || stage).insertBefore(card, (side || stage).firstChild);
  const search = document.getElementById("ex-search"), names = document.getElementById("ex-names");
  const repeatBox = document.getElementById("ex-repeat");
  const legend = root.querySelector(".ex-legend"), decBar = root.querySelector(".ex-dec");

  const svg = d3.select(stage).append("svg").attr("role", "img").attr("aria-label", "Collaboration network");
  const g = svg.append("g"), gE = g.append("g"), gN = g.append("g"), gL = g.append("g"), gS = g.append("g");
  let data, D, dec = "2010", sel = null, selName = null, comm = null, hoverComm = null, adj = [], adjW = [], k = 1;

  const zoom = d3.zoom().scaleExtent([0.6, 14]).on("zoom", (e) => {
    k = e.transform.k;
    g.attr("transform", e.transform);
    gN.selectAll("circle").attr("r", (n) => n.rad / Math.sqrt(k));
    gE.selectAll("line").attr("stroke-width", (e) => (e[2] > 1 ? 1.4 : 0.5) / Math.sqrt(k));
    gL.selectAll("text").attr("font-size", 13.5 / k).attr("stroke-width", 4 / k);
    gS.selectAll("text").attr("font-size", 13 / k).attr("stroke-width", 3 / k).attr("x", (n) => n.px + 8 / k).attr("y", (n) => n.py + 4 / k);
  });
  svg.call(zoom).on("click", (e) => { if (e.target === svg.node()) { setSel(null); if (comm !== null) pickComm(comm); } });

  const color = (n) => (n.c >= 0 ? PAL[n.c] : OTHER);
  const fmt = d3.format(",");

  // Positions come precomputed from src/15_layout_network.mjs (community-aware force layout).
  const layout = (dec) => data.decades[dec].nodes.map((n) => [n.lx, n.ly]);

  function draw() {
    D = data.decades[dec];
    const P = layout(dec), W = stage.clientWidth, H = stage.clientHeight, pad = 34;
    const [x0, x1] = d3.extent(P, (p) => p[0]), [y0, y1] = d3.extent(P, (p) => p[1]);
    const s = Math.min((W - 2 * pad) / (x1 - x0), (H - 2 * pad - 30) / (y1 - y0));
    const ox = (W - s * (x1 - x0)) / 2 - s * x0, oy = (H - s * (y1 - y0)) / 2 - s * y0 + 12;
    D.nodes.forEach((n, i) => { n.i = i; n.px = ox + s * P[i][0]; n.py = oy + s * P[i][1]; n.rad = 2 + Math.sqrt(n.d) * 0.9; });
    adj = D.nodes.map(() => new Set()); adjW = D.nodes.map(() => []);
    D.edges.forEach(([a, b, w]) => { adj[a].add(b); adj[b].add(a); adjW[a].push([b, w]); adjW[b].push([a, w]); });

    gE.selectAll("line").data(D.edges, (e) => e[0] + "-" + e[1]).join("line")
      .attr("x1", (e) => D.nodes[e[0]].px).attr("y1", (e) => D.nodes[e[0]].py)
      .attr("x2", (e) => D.nodes[e[1]].px).attr("y2", (e) => D.nodes[e[1]].py)
      .attr("stroke", (e) => (e[2] > 1 ? "#f1d38a" : "#8a8070"))
      .attr("stroke-width", (e) => (e[2] > 1 ? 1.4 : 0.5) / Math.sqrt(k));

    gN.selectAll("circle").data(D.nodes, (n) => n.n).join("circle")
      .attr("cx", (n) => n.px).attr("cy", (n) => n.py).attr("r", (n) => n.rad / Math.sqrt(k))
      .attr("fill", color).attr("stroke", "#0c0b0a").attr("stroke-width", 0.4)
      .style("cursor", "pointer")
      .on("mouseenter", (e, n) => showTip(e, n))
      .on("mousemove", (e) => moveTip(e))
      .on("mouseleave", () => { tip.style.opacity = 0; })
      .on("click", (e, n) => { e.stopPropagation(); setSel(sel === n.i ? null : n.i); });

    // community labels at each community's centre, named after its most-credited member
    const lab = D.communities.filter((c) => c.label).map((c) => {
      const m = D.nodes.filter((n) => n.c === c.id);
      return { t: c.label, x: d3.median(m, (n) => n.px), y: d3.median(m, (n) => n.py), c: c.id };
    });
    lab.forEach((l) => { l.w = l.t.length * 8; l.ly = l.y; l.x -= l.w / 2; });
    for (let it = 0; it < 60; it++) {  // push overlapping labels apart vertically
      let moved = false;
      lab.forEach((a) => lab.forEach((b) => {
        if (a === b || Math.abs(a.x - b.x) > (a.x < b.x ? a.w : b.w) || Math.abs(a.ly - b.ly) >= 17) return;
        const d = (17 - Math.abs(a.ly - b.ly)) / 2 + 0.5, up = a.ly <= b.ly ? a : b, dn = up === a ? b : a;
        up.ly -= d; dn.ly += d; moved = true;
      }));
      if (!moved) break;
    }
    gL.selectAll("text").data(lab, (l) => l.t).join("text")
      .attr("x", (l) => l.x).attr("y", (l) => l.ly).text((l) => l.t)
      .attr("fill", (l) => PAL[l.c]).attr("font-family", "Inter, sans-serif").attr("font-weight", 700)
      .attr("font-size", 13.5 / k).attr("paint-order", "stroke").attr("stroke", "#0c0b0a").attr("stroke-width", 4 / k)
      .style("cursor", "pointer")
      .on("click", (e, l) => { e.stopPropagation(); pickComm(l.c); });

    info.innerHTML = `<b>${dec}s</b><br>${fmt(D.giant)} people in the largest group · repeat ties ${(D.repeat_share * 100).toFixed(1)}%`;
    names.innerHTML = D.nodes.map((n) => `<option value="${n.n.replace(/"/g, "&quot;")}">`).join("");
    buildLegend();
    // keep the selected person across decades if they are in this one
    const again = selName ? D.nodes.find((n) => n.n === selName) : null;
    sel = again ? again.i : null;
    if (comm !== null) showCard();
    if (sel !== null) showPerson(sel);
    if (selName && !again) info.innerHTML += `<br><span style="color:#d9a94a">${selName} is not in this decade's largest group</span>`;
    update();
  }

  function buildLegend() {
    legend.innerHTML = "";
    const row = (id, color, html) => {
      const b = document.createElement("button");
      b.innerHTML = `<i style="background:${color}"></i><span>${html}</span>`;
      b.className = comm === id ? "on" : "";
      b.onmouseenter = () => { hoverComm = id; update(); };
      b.onmouseleave = () => { hoverComm = null; update(); };
      b.onclick = () => pickComm(id);
      legend.appendChild(b);
    };
    D.communities.forEach((c) => { if (c.label) row(c.id, PAL[c.id], `${c.label}'s circle <em>${c.size}</em>`); });
    const sm = D.small;
    row(-1, OTHER, `Smaller communities <em>${sm.people}</em><small>${sm.groups} more groups, typically ${sm.median_size} people each. Too many to colour, so they share grey and sit in the middle, between the circles they connect to.</small>`);
  }

  function pickComm(id) {
    comm = comm === id ? null : id; sel = null; selName = null; search.value = "";
    buildLegend(); update(); showCard();
  }

  // stats for the selected community: how closed is it?
  function showCard() {
    if (comm === null || comm < 0) { card.style.display = "none"; return; }
    const c = D.communities[comm], mem = D.nodes.filter((n) => n.c === comm), ids = new Set(mem.map((n) => n.i));
    let inside = 0, out = 0, rep = 0;
    D.edges.forEach(([a, b, w]) => {
      const ia = ids.has(a), ib = ids.has(b);
      if (ia && ib) { inside++; if (w > 1) rep++; } else if (ia || ib) out++;
    });
    const films = new Set(mem.flatMap((n) => n.f));
    const top = mem.slice().sort((a, b) => b.f.length - a.f.length || b.d - a.d).slice(0, 6);
    card.innerHTML = `<button class="x" aria-label="Close">×</button>
      <div class="k">COMMUNITY</div><h4 style="color:${PAL[comm]}">${c.label}'s circle</h4>
      <div class="cs"><div><b>${mem.length}</b>people</div><div><b>${films.size}</b>films</div>
      <div><b>${Math.round((100 * inside) / (inside + out))}%</b>ties inside</div><div><b>${(100 * rep / Math.max(1, inside)).toFixed(1)}%</b>repeat ties</div></div>
      <div class="k" style="margin-top:8px">MOST ACTIVE</div>
      <ul>${top.map((n) => `<li data-i="${n.i}">${n.n} <span>${n.f.length} films</span></li>`).join("")}</ul>
      <div class="note">Decade average: ${(D.repeat_share * 100).toFixed(1)}% repeat ties.</div>`;
    card.style.display = "block";
    if (side) side.scrollTop = 0;
    card.querySelector(".x").onclick = () => pickComm(comm);
    card.querySelectorAll("li").forEach((li) => (li.onclick = () => { const i = +li.dataset.i; comm = null; buildLegend(); setSel(i); }));
  }

  function update() {
    const cc = hoverComm !== null ? hoverComm : comm;
    let on = null; // set of active node indices, or null = all
    if (hoverComm === null && sel !== null) on = new Set([sel, ...adj[sel]]);
    else if (cc !== null) on = new Set(D.nodes.filter((n) => n.c === cc).map((n) => n.i));
    const rep = repeatBox.checked;
    gN.selectAll("circle")
      .attr("opacity", (n) => (!on || on.has(n.i) ? 1 : 0.1))
      .attr("stroke", (n) => (n.i === sel ? "#fff" : "#0c0b0a"))
      .attr("stroke-width", (n) => (n.i === sel ? 2 / Math.sqrt(k) : 0.4));
    gE.selectAll("line").attr("opacity", (e) => {
      if (rep && e[2] < 2) return 0;
      if (hoverComm === null && sel !== null) return e[0] === sel || e[1] === sel ? 0.9 : 0.03;
      if (on) return on.has(e[0]) && on.has(e[1]) ? 0.6 : 0.03;
      return e[2] > 1 ? 0.75 : 0.16;
    });
    gL.selectAll("text").attr("opacity", (l) => (!on || (sel === null || hoverComm !== null) && cc === l.c ? 1 : 0.15));
    gS.selectAll("text").data(sel !== null ? [D.nodes[sel]] : [], (n) => n.n).join("text")
      .attr("x", (n) => n.px + 8 / k).attr("y", (n) => n.py + 4 / k).text((n) => n.n)
      .attr("fill", "#fff").attr("font-family", "Playfair Display, Georgia, serif").attr("font-weight", 700)
      .attr("font-size", 13 / k).attr("paint-order", "stroke").attr("stroke", "#0c0b0a").attr("stroke-width", 3 / k)
      .style("pointer-events", "none");
  }

  function setSel(i) {
    sel = i;
    selName = i === null ? null : D.nodes[i].n;
    if (i === null) { search.value = ""; if (comm === null) card.style.display = "none"; }
    else showPerson(i);
    update();
  }

  // card for one person: films, repeat partners, career across decades
  function showPerson(i) {
    const n = D.nodes[i], esc = (t) => t.replace(/&/g, "&amp;").replace(/</g, "&lt;");
    const films = n.f.map((j) => [D.films[j], D.ratings ? D.ratings[j] : null]);
    const mr = D.ratings ? d3.mean(films, (f) => f[1]) : null;
    const reps = adjW[i].filter(([, w]) => w > 1).sort((a, b) => b[1] - a[1] || D.nodes[b[0]].d - D.nodes[a[0]].d);
    const decs = Object.keys(data.decades);
    const career = decs.map((d) => {
      const m = data.decades[d].nodes.find((x) => x.n === n.n);
      return { d, m, lab: m && m.c >= 0 ? data.decades[d].communities[m.c].label + "'s circle" : m ? "a smaller community" : "not in the largest group" };
    });
    const inN = career.filter((x) => x.m).length;
    const cl = n.c >= 0 ? `${D.communities[n.c].label}'s circle` : "a smaller community";
    card.innerHTML = `<button class="x" aria-label="Close">×</button>
      <div class="k">${n.r === "d" ? "DIRECTOR" : "ACTOR"} · ${dec}s</div><h4>${esc(n.n)}</h4>
      <div class="pc"><i style="background:${color(n)}"></i>${esc(cl)}</div>
      <div class="cs"><div><b>${n.f.length}</b>films</div><div><b>${n.d}</b>collaborators</div>
      <div><b>${reps.length}</b>worked with again</div><div><b>${mr == null ? "–" : mr.toFixed(1)}</b>avg IMDb rating</div></div>
      <div class="k" style="margin-top:9px">FILMS THIS DECADE</div>
      <ul class="fl">${films.map(([t, r]) => `<li>${esc(t)}${r == null ? "" : `<span>★ ${r.toFixed(1)}</span>`}</li>`).join("")}</ul>
      <div class="k" style="margin-top:9px">WORKED WITH AGAIN</div>
      ${reps.length ? `<ul class="rp">${reps.slice(0, 8).map(([j, w]) => `<li data-i="${j}"><i style="background:${color(D.nodes[j])}"></i>${esc(D.nodes[j].n)}<span>${w} films</span></li>`).join("")}</ul>`
        : `<div class="note" style="margin-top:3px">Nobody this decade: every collaborator was a one-off.</div>`}
      <div class="k" style="margin-top:9px">ACROSS DECADES</div>
      <div class="cr">${career.map((x) => `<button data-d="${x.d}" class="${x.d === dec ? "on" : ""}" ${x.m ? "" : "disabled"} title="${x.d}s: ${esc(x.lab)}">
        <i style="background:${x.m ? (x.m.c >= 0 ? PAL[x.m.c] : OTHER) : "transparent"}"></i>${x.d.slice(2)}s</button>`).join("")}</div>
      <div class="note">In the largest group in ${inN} of ${decs.length} decades. Colour = their circle that decade; click to jump there.</div>`;
    card.style.display = "block";
    if (side) side.scrollTop = 0;
    card.querySelector(".x").onclick = () => setSel(null);
    card.querySelectorAll(".rp li").forEach((li) => (li.onclick = () => setSel(+li.dataset.i)));
    card.querySelectorAll(".cr button:not([disabled])").forEach((b) => (b.onclick = () => {
      if (b.dataset.d !== dec) decBar.querySelectorAll("button").forEach((x) => { if (x.textContent === b.dataset.d + "s") x.click(); });
    }));
  }

  function showTip(e, n) {
    const films = n.f.map((j) => D.films[j]);
    const c = n.c >= 0 ? `${D.communities[n.c].label}'s circle` : "a smaller community";
    tip.innerHTML = `<h4>${n.n}</h4><div class="m">${n.r === "d" ? "Director" : "Actor"} · ${n.d} collaborators · ${c}</div>
      <ul>${films.slice(0, 6).map((f) => `<li>${f}</li>`).join("")}${films.length > 6 ? `<li>+${films.length - 6} more</li>` : ""}</ul>`;
    tip.style.opacity = 1;
    moveTip(e);
  }
  function moveTip(e) {
    const r = stage.getBoundingClientRect();
    let x = e.clientX - r.left + 14, y = e.clientY - r.top + 14;
    if (x + 290 > r.width) x -= 310;
    if (y + tip.offsetHeight > r.height) y = r.height - tip.offsetHeight - 6;
    tip.style.left = x + "px"; tip.style.top = y + "px";
  }

  search.addEventListener("change", () => {
    const n = D.nodes.find((m) => m.n.toLowerCase() === search.value.trim().toLowerCase());
    if (!n) return;
    comm = null; buildLegend(); setSel(n.i);
    const W = stage.clientWidth, H = stage.clientHeight, s = 3;
    svg.transition().duration(700).call(zoom.transform, d3.zoomIdentity.translate(W / 2 - s * n.px, H / 2 - s * n.py).scale(s));
  });
  repeatBox.addEventListener("change", update);

  let rt;
  window.addEventListener("resize", () => { clearTimeout(rt); rt = setTimeout(() => data && draw(), 200); });

  fetch("assets/data/network.json").then((r) => { if (!r.ok) throw new Error(r.status); return r.json(); }).then((j) => {
    data = j;
    Object.keys(data.decades).forEach((d) => {
      const b = document.createElement("button");
      b.textContent = d + "s";
      b.onclick = () => {
        dec = d; comm = null; if (sel === null) card.style.display = "none";
        decBar.querySelectorAll("button").forEach((x) => x.classList.toggle("on", x === b));
        svg.call(zoom.transform, d3.zoomIdentity);
        draw();
      };
      if (d === dec) b.className = "on";
      decBar.appendChild(b);
    });
    draw();
  }).catch(fallback);
})();
