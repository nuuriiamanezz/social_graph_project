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
  const search = document.getElementById("ex-search"), names = document.getElementById("ex-names");
  const repeatBox = document.getElementById("ex-repeat");
  const legend = root.querySelector(".ex-legend"), decBar = root.querySelector(".ex-dec");

  const svg = d3.select(stage).append("svg").attr("role", "img").attr("aria-label", "Collaboration network");
  const g = svg.append("g"), gE = g.append("g"), gN = g.append("g"), gL = g.append("g"), gS = g.append("g");
  let data, D, dec = "2010", sel = null, selName = null, comm = null, hoverComm = null, adj = [], k = 1;

  const zoom = d3.zoom().scaleExtent([0.6, 14]).on("zoom", (e) => {
    k = e.transform.k;
    g.attr("transform", e.transform);
    gN.selectAll("circle").attr("r", (n) => n.rad / Math.sqrt(k));
    gE.selectAll("line").attr("stroke-width", (e) => (e[2] > 1 ? 1.4 : 0.5) / Math.sqrt(k));
    gL.selectAll("text").attr("font-size", 12 / k).attr("stroke-width", 3 / k);
    gS.selectAll("text").attr("font-size", 13 / k).attr("stroke-width", 3 / k).attr("x", (n) => n.px + 8 / k).attr("y", (n) => n.py + 4 / k);
  });
  svg.call(zoom).on("click", (e) => { if (e.target === svg.node()) { setSel(null); } });

  const color = (n) => (n.c >= 0 ? PAL[n.c] : OTHER);
  const fmt = d3.format(",");

  function draw() {
    D = data.decades[dec];
    const W = stage.clientWidth, H = stage.clientHeight, s = Math.min(W, H) - 50;
    const ox = (W - s) / 2, oy = (H - s) / 2;
    D.nodes.forEach((n, i) => { n.i = i; n.px = ox + n.x * s; n.py = oy + (1 - n.y) * s; n.rad = 2 + Math.sqrt(n.d) * 0.9; });
    adj = D.nodes.map(() => new Set());
    D.edges.forEach(([a, b]) => { adj[a].add(b); adj[b].add(a); });

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

    // community labels at each community's most-credited member
    const lab = D.communities.filter((c) => c.label).map((c) => {
      const n = D.nodes.find((m) => m.n === c.label && m.c === c.id);
      return n ? { t: c.label, x: n.px, y: n.py, c: c.id } : null;
    }).filter(Boolean);
    lab.forEach((l) => { l.w = l.t.length * 7; l.ly = l.y - 6; });
    for (let it = 0; it < 60; it++) {  // push overlapping labels apart vertically
      let moved = false;
      lab.forEach((a) => lab.forEach((b) => {
        if (a === b || Math.abs(a.x - b.x) > (a.x < b.x ? a.w : b.w) || Math.abs(a.ly - b.ly) >= 15) return;
        const d = (15 - Math.abs(a.ly - b.ly)) / 2 + 0.5, up = a.ly <= b.ly ? a : b, dn = up === a ? b : a;
        up.ly -= d; dn.ly += d; moved = true;
      }));
      if (!moved) break;
    }
    gL.selectAll("text").data(lab, (l) => l.t).join("text")
      .attr("x", (l) => l.x + 6).attr("y", (l) => l.ly).text((l) => l.t)
      .attr("fill", (l) => PAL[l.c]).attr("font-family", "Inter, sans-serif").attr("font-weight", 600)
      .attr("font-size", 12 / k).attr("paint-order", "stroke").attr("stroke", "#0c0b0a").attr("stroke-width", 3 / k)
      .style("pointer-events", "none");

    info.innerHTML = `<b>${dec}s</b><br>${fmt(D.giant)} people in the largest group · repeat ties ${(D.repeat_share * 100).toFixed(1)}%`;
    names.innerHTML = D.nodes.map((n) => `<option value="${n.n.replace(/"/g, "&quot;")}">`).join("");
    buildLegend();
    // keep the selected person across decades if they are in this one
    const again = selName ? D.nodes.find((n) => n.n === selName) : null;
    sel = again ? again.i : null;
    if (selName && !again) info.innerHTML += `<br><span style="color:#d9a94a">${selName} is not in this decade's largest group</span>`;
    update();
  }

  function buildLegend() {
    legend.innerHTML = "";
    D.communities.forEach((c) => {
      if (!c.label) return;
      const b = document.createElement("button");
      b.innerHTML = `<i style="background:${PAL[c.id]}"></i>${c.label}'s circle · ${c.size}`;
      b.className = comm === c.id ? "on" : "";
      b.onmouseenter = () => { hoverComm = c.id; update(); };
      b.onmouseleave = () => { hoverComm = null; update(); };
      b.onclick = () => { comm = comm === c.id ? null : c.id; sel = null; selName = null; search.value = ""; buildLegend(); update(); };
      legend.appendChild(b);
    });
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
    if (i === null) search.value = "";
    update();
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
        dec = d; comm = null;
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
