// Interactive figures (data: assets/data/charts.json, made by src/14_export_chart_data.py).
// Each <div class="chart" data-chart="..." data-fallback="png"> becomes a set of linked D3 panels.
(function () {
  const holders = [...document.querySelectorAll(".chart[data-chart]")];
  if (!holders.length) return;
  const fallback = () => holders.forEach((h) => {
    h.innerHTML = `<img src="${h.dataset.fallback}" alt="" style="width:100%;display:block;background:#f7f3ea;border-radius:4px">`;
  });
  if (typeof d3 === "undefined") return fallback();

  const C = { grid: "rgba(217,169,74,.13)", axis: "#a69a85", text: "#f3ead8", gold: "#e8c46a", null: "#8a8070",
              blue: "#5b8cff", red: "#ff5a5f", green: "#4fd18b", cyan: "#4dd9f0", pink: "#ff6fd8" };
  const DECS = [1980, 1990, 2000, 2010, 2020];
  const DCOL = { 1980: "#5b8cff", 1990: "#4dd9f0", 2000: "#4fd18b", 2010: "#e8c46a", 2020: "#ff6fd8" };
  const pct = d3.format(".1%"), f3 = d3.format(".3f"), f2 = d3.format(".2f");
  const H = 250, M = { t: 10, r: 14, b: 38, l: 52 };

  // ---------- helpers ----------
  function shell(el, n, cls = "") {
    el.innerHTML = "";
    el.classList.add("ready");
    const ctl = d3.select(el).append("div").attr("class", "ch-ctl");
    const grid = d3.select(el).append("div").attr("class", "ch-grid " + cls).style("--n", n);
    const tip = d3.select(el).append("div").attr("class", "ch-tip");
    return { ctl, grid, tip, el };
  }
  function panel(S, title) {
    const box = S.grid.append("div").attr("class", "ch-panel");
    box.append("h4").text(title);
    const W = Math.max(220, box.node().clientWidth);
    const svg = box.append("svg").attr("width", W).attr("height", H);
    const g = svg.append("g").attr("transform", `translate(${M.l},${M.t})`);
    return { box, svg, g, w: W - M.l - M.r, h: H - M.t - M.b };
  }
  function axes(P, x, y, { xl = "", yl = "", xf = null, yf = null, xt = null, yt = 5, yv = null } = {}) {
    const gl = d3.axisLeft(y).ticks(yt).tickSize(-P.w).tickFormat(""); if (yv) gl.tickValues(yv);
    P.g.append("g").attr("class", "ch-gridl").call(gl);
    const ax = d3.axisBottom(x); if (xf) ax.tickFormat(xf); if (xt) ax.tickValues(xt);
    P.g.append("g").attr("class", "ch-ax").attr("transform", `translate(0,${P.h})`).call(ax);
    const ay = d3.axisLeft(y).ticks(yt); if (yf) ay.tickFormat(yf); if (yv) ay.tickValues(yv);
    P.g.append("g").attr("class", "ch-ax").call(ay);
    P.g.append("text").attr("class", "ch-lab").attr("x", P.w / 2).attr("y", P.h + 32).attr("text-anchor", "middle").text(xl);
    P.g.append("text").attr("class", "ch-lab").attr("transform", "rotate(-90)").attr("x", -P.h / 2).attr("y", -40)
      .attr("text-anchor", "middle").text(yl);
  }
  const decX = (P) => d3.scalePoint().domain(DECS).range([0, P.w]).padding(0.35);
  function showTip(S, html, ev) {
    S.tip.html(html).style("opacity", 1);
    const r = S.el.getBoundingClientRect(), t = S.tip.node();
    let x = ev.clientX - r.left + 14, y = ev.clientY - r.top + 12;
    if (x + t.offsetWidth > r.width - 4) x = ev.clientX - r.left - t.offsetWidth - 14;
    S.tip.style("left", x + "px").style("top", Math.max(0, y) + "px");
  }
  const hideTip = (S) => S.tip.style("opacity", 0);
  function buttons(S, label, opts, cur, on) {
    const g = S.ctl.append("div").attr("class", "ch-btns");
    if (label) g.append("span").text(label);
    g.selectAll("button").data(opts).join("button").text((d) => d[1]).classed("on", (d) => d[0] === cur)
      .on("click", function (e, d) { g.selectAll("button").classed("on", (x) => x === d); on(d[0]); });
  }
  function chips(S, items, onToggle, onHover) {  // items: [key,label,color]
    const off = new Set();
    const g = S.ctl.append("div").attr("class", "ch-chips");
    g.selectAll("button").data(items).join("button")
      .html((d) => `<i style="background:${d[2]}"></i>${d[1]}`)
      .on("click", function (e, d) { off.has(d[0]) ? off.delete(d[0]) : off.add(d[0]); d3.select(this).classed("off", off.has(d[0])); onToggle(off); })
      .on("mouseenter", (e, d) => onHover && onHover(d[0])).on("mouseleave", () => onHover && onHover(null));
    return off;
  }
  // a column per decade that triggers a linked hover over all panels of one chart
  function decHover(S, panels, onDec) {
    panels.forEach((P) => {
      const x = P.x;
      P.guide = P.g.append("line").attr("class", "ch-guide").attr("y1", 0).attr("y2", P.h).style("opacity", 0);
      P.g.append("g").selectAll("rect").data(DECS).join("rect")
        .attr("x", (d) => x(d) - x.step() / 2).attr("width", x.step()).attr("y", 0).attr("height", P.h)
        .attr("fill", "transparent")
        .on("mousemove", (e, d) => { panels.forEach((Q) => Q.guide.attr("x1", Q.x(d)).attr("x2", Q.x(d)).style("opacity", 1)); showTip(S, onDec(d, P), e); })
        .on("mouseleave", () => { panels.forEach((Q) => Q.guide.style("opacity", 0)); hideTip(S); });
    });
  }
  const SUP = { "-": "⁻", 0: "⁰", 1: "¹", 2: "²", 3: "³", 4: "⁴", 5: "⁵", 6: "⁶", 7: "⁷", 8: "⁸", 9: "⁹" };
  const pow10 = (v) => "10" + String(Math.round(Math.log10(v))).split("").map((c) => SUP[c]).join("");
  const zs = (z) => `z = ${d3.format(".0f")(z)}`;

  // ---------- Act I: closure vs null ----------
  function closure(el, D) {
    const S = shell(el, 4), rows = D.closure;
    const by = new Map(rows.map((r) => [r.decade, r]));
    const spec = [
      ["clust", "Clustering above chance", "average clustering", f3],
      ["repeat_edges", "Repeat collaborations", "share of ties on 2+ films", pct],
      ["modularity", "Community structure", "Louvain modularity", f3]];
    const panels = spec.map(([k, title, yl, fmt]) => {
      const P = panel(S, title); P.x = decX(P); P.k = k; P.fmt = fmt;
      const lo = d3.min(rows, (r) => Math.min(r[k], r[k + "_null"] - 2 * r[k + "_null_sd"]));
      const hi = d3.max(rows, (r) => Math.max(r[k], r[k + "_null"] + 2 * r[k + "_null_sd"]));
      const y = d3.scaleLinear().domain([lo - (hi - lo) * 0.08, hi + (hi - lo) * 0.08]).range([P.h, 0]);
      axes(P, P.x, y, { yl, yf: k === "repeat_edges" ? d3.format(".0%") : d3.format(".2f"), xf: (d) => d + "s" });
      P.g.append("path").datum(rows).attr("class", "ch-band")
        .attr("d", d3.area().x((r) => P.x(r.decade)).y0((r) => y(r[k + "_null"] - 2 * r[k + "_null_sd"])).y1((r) => y(r[k + "_null"] + 2 * r[k + "_null_sd"])));
      P.g.append("path").datum(rows).attr("class", "ch-line dash").attr("stroke", C.null).attr("d", d3.line().x((r) => P.x(r.decade)).y((r) => y(r[k + "_null"])));
      P.g.append("path").datum(rows).attr("class", "ch-line").attr("stroke", C.gold).attr("d", d3.line().x((r) => P.x(r.decade)).y((r) => y(r[k])));
      P.g.selectAll(".pt").data(rows).join("circle").attr("class", "pt").attr("r", 4).attr("fill", C.gold).attr("cx", (r) => P.x(r.decade)).attr("cy", (r) => y(r[k]));
      // gap arrows: observed minus null
      P.g.selectAll(".gap").data(rows).join("line").attr("class", "gap").attr("stroke", C.gold).attr("stroke-opacity", .35)
        .attr("x1", (r) => P.x(r.decade)).attr("x2", (r) => P.x(r.decade)).attr("y1", (r) => y(r[k + "_null"])).attr("y2", (r) => y(r[k]));
      return P;
    });
    // who gets the work
    const P = panel(S, "Who gets the work"); P.x = decX(P);
    const lines = [["returning_prev", "people from previous decade", C.cyan], ["franchise", "franchise films", C.green], ["hub_share", "credits of top 5% people", C.pink]];
    const y = d3.scaleLinear().domain([0, 0.65]).range([P.h, 0]);
    axes(P, P.x, y, { yl: "share", yf: d3.format(".0%"), xf: (d) => d + "s" });
    lines.forEach(([k, , c]) => {
      const rr = rows.filter((r) => r[k] != null);
      P.g.append("path").datum(rr).attr("class", "ch-line w-" + k).attr("stroke", c).attr("d", d3.line().x((r) => P.x(r.decade)).y((r) => y(r[k])));
      P.g.selectAll(".p-" + k).data(rr).join("circle").attr("class", "w-" + k).attr("r", 3.5).attr("fill", c).attr("cx", (r) => P.x(r.decade)).attr("cy", (r) => y(r[k]));
    });
    panels.push(P);
    S.ctl.append("div").attr("class", "ch-key").html(
      `<span><i style="background:${C.gold}"></i>observed</span><span><i class="dash"></i>null: people shuffled across films (± 2 sd, 50 runs)</span>` +
      lines.map(([, l, c]) => `<span><i style="background:${c}"></i>${l}</span>`).join(""));
    decHover(S, panels, (d, Q) => {
      const r = by.get(d);
      if (!Q.k) return `<b>${d}s</b><br>from previous decade: ${r.returning_prev == null ? "—" : pct(r.returning_prev)}<br>franchise films: ${pct(r.franchise)}<br>top 5% people: ${pct(r.hub_share)} of credits<br><span class="m">${r.people} people · ${r.films} films</span>`;
      const k = Q.k;
      return `<b>${d}s · ${Q.box.select("h4").text()}</b><br>observed: ${Q.fmt(r[k])}<br>null: ${Q.fmt(r[k + "_null"])} ± ${Q.fmt(2 * r[k + "_null_sd"])}<br><span class="m">${zs(r[k + "_z"])} vs. the null</span>`;
    });
  }

  // ---------- degree + tie strength ----------
  function dists(el, D) {
    const S = shell(el, 2);
    let off = new Set();
    const mk = (title, data, xs, ys, xl, yl, xf, yf, row) => {
      const P = panel(S, title);
      const all = DECS.flatMap((d) => data[d]);
      const x = (xs === "log" ? d3.scaleLog() : d3.scaleLinear()).domain(d3.extent(all, (p) => p[0])).range([0, P.w]);
      const y = d3.scaleLog().domain([d3.min(all, (p) => p[1]) * 0.7, 1.05]).range([P.h, 0]);
      axes(P, x, y, { xl, yl, xf, yf, yv: [1, 0.1, 0.01, 0.001, 0.0001].filter((v) => v >= y.domain()[0]), xt: xs === "log" ? [1, 2, 5, 10, 20, 50].filter((v) => v <= x.domain()[1]) : d3.range(1, d3.max(all, (p) => p[0]) + 1) });
      const line = d3.line().x((p) => x(p[0])).y((p) => y(p[1])).curve(xs === "log" ? d3.curveStepAfter : d3.curveLinear);
      P.lines = P.g.selectAll(".dl").data(DECS).join("path").attr("class", "ch-line dl").attr("stroke", (d) => DCOL[d]).attr("d", (d) => line(data[d]));
      if (xs !== "log") P.dots = P.g.selectAll(".dd").data(DECS.flatMap((d) => data[d].map((p) => [d, ...p]))).join("circle")
        .attr("class", "dd").attr("r", 3.5).attr("fill", (p) => DCOL[p[0]]).attr("cx", (p) => x(p[1])).attr("cy", (p) => y(p[2]));
      P.guide = P.g.append("line").attr("class", "ch-guide").attr("y1", 0).attr("y2", P.h).style("opacity", 0);
      P.g.append("rect").attr("width", P.w).attr("height", P.h).attr("fill", "transparent")
        .on("mousemove", (e) => {
          let v = x.invert(d3.pointer(e)[0]); v = Math.max(1, Math.round(v));
          P.guide.attr("x1", x(v)).attr("x2", x(v)).style("opacity", 1);
          const lines = DECS.filter((d) => !off.has(d)).map((d) => {
            const pts = data[d].filter((p) => p[0] <= v), p = pts[pts.length - 1];
            return `<span style="color:${DCOL[d]}">●</span> ${d}s: ${p ? row(p, v) : "—"}`;
          });
          showTip(S, `<b>${xl.split(" (")[0]} ≥ ${v}</b><br>` + lines.join("<br>"), e);
        })
        .on("mouseleave", () => { P.guide.style("opacity", 0); hideTip(S); });
      return P;
    };
    const A = mk("Degree distribution", D.degree, "log", "log", "degree k (collaborators)", "P(K ≥ k)", d3.format("d"), (v) => (v >= .01 ? d3.format(".0%")(v) : d3.format(".1%")(v)),
      (p) => `${pct(p[1])} of people`);
    const B = mk("Tie strength: how often pairs work together", D.ties, "lin", "log", "films made together (w)", "share of ties with ≥ w films", d3.format("d"), (v) => (v >= .01 ? d3.format(".0%")(v) : d3.format(".1%")(v)),
      (p, v) => p[0] === v ? `${d3.format(".2%")(p[1])} (${p[2]} pairs)` : "none");
    const refresh = (hl) => [A, B].forEach((P) => {
      P.lines.style("opacity", (d) => (off.has(d) ? 0 : hl && hl !== d ? 0.15 : 1)).attr("stroke-width", (d) => (hl === d ? 3.2 : 2));
      if (P.dots) P.dots.style("opacity", (p) => (off.has(p[0]) ? 0 : hl && hl !== p[0] ? 0.15 : 1));
    });
    off = chips(S, DECS.map((d) => [d, d + "s", DCOL[d]]), (o) => { off = o; refresh(); }, refresh);
    S.ctl.append("div").attr("class", "ch-hint").text("Click a decade to hide it, hover to highlight.");
  }

  // ---------- Act II: plot similarity ----------
  function plots(el, D) {
    const S = shell(el, 2);
    const methods = [...new Set(D.plots.map((r) => r.method))];
    let method = methods[0], noSame = false;
    const draw = () => {
      S.grid.html("");
      const rows = D.plots.filter((r) => r.method === method), b = rows[0].sim_all, bn = rows[0].sim_nonfranchise;
      const by = new Map(rows.map((r) => [r.decade, r]));
      // A: relative similarity
      const A = panel(S, "Are plots converging?"); A.x = decX(A);
      const ya = d3.scaleLinear().domain([0.88, d3.max(rows, (r) => r.sim_all_hi / b) * 1.03]).range([A.h, 0]);
      axes(A, A.x, ya, { yl: "mean plot similarity (1980s = 1)", yf: d3.format(".2f"), xf: (d) => d + "s" });
      A.g.append("line").attr("class", "ch-ref").attr("x1", 0).attr("x2", A.w).attr("y1", ya(1)).attr("y2", ya(1));
      A.g.append("path").datum(rows).attr("class", "ch-band gold").attr("d", d3.area().x((r) => A.x(r.decade)).y0((r) => ya(r.sim_all_lo / b)).y1((r) => ya(r.sim_all_hi / b)));
      A.g.append("path").datum(rows).attr("class", "ch-line").attr("stroke", C.gold).attr("d", d3.line().x((r) => A.x(r.decade)).y((r) => ya(r.sim_all / b)));
      A.g.append("path").datum(rows).attr("class", "ch-line dash").attr("stroke", C.cyan).attr("d", d3.line().x((r) => A.x(r.decade)).y((r) => ya(r.sim_nonfranchise / bn)));
      A.g.selectAll(".pa").data(rows).join("circle").attr("r", 4).attr("fill", C.gold).attr("cx", (r) => A.x(r.decade)).attr("cy", (r) => ya(r.sim_all / b));
      A.g.selectAll(".pb").data(rows).join("circle").attr("r", 3).attr("fill", C.cyan).attr("cx", (r) => A.x(r.decade)).attr("cy", (r) => ya(r.sim_nonfranchise / bn));
      // B: gap
      const P = panel(S, "Do the same people tell the same stories?"); P.x = decX(P);
      const key = noSame ? "gap_no_same_franchise" : "gap";
      const yb = d3.scaleLinear().domain([Math.min(-0.0018, d3.min(rows, (r) => r.gap_null - 2 * r.gap_null_sd)), d3.max(rows, (r) => r.gap_hi) * 1.05]).range([P.h, 0]);
      axes(P, P.x, yb, { yl: "similarity gap: shared people − none", yf: d3.format(".3f"), xf: (d) => d + "s" });
      P.g.append("path").datum(rows).attr("class", "ch-band").attr("d", d3.area().x((r) => P.x(r.decade)).y0((r) => yb(r.gap_null - 2 * r.gap_null_sd)).y1((r) => yb(r.gap_null + 2 * r.gap_null_sd)));
      P.g.append("line").attr("class", "ch-ref").attr("x1", 0).attr("x2", P.w).attr("y1", yb(0)).attr("y2", yb(0));
      P.g.selectAll(".eb").data(rows).join("line").attr("class", "eb").attr("stroke", C.gold).attr("stroke-width", 1.4)
        .attr("x1", (r) => P.x(r.decade)).attr("x2", (r) => P.x(r.decade)).attr("y1", (r) => yb(r.gap_lo)).attr("y2", (r) => yb(r.gap_hi))
        .style("opacity", noSame ? 0.15 : 0.8);
      // ghost of the full gap when same-franchise pairs are removed
      if (noSame) P.g.append("path").datum(rows).attr("class", "ch-line").attr("stroke", C.gold).style("opacity", .25).attr("d", d3.line().x((r) => P.x(r.decade)).y((r) => yb(r.gap)));
      const ln = P.g.append("path").datum(rows).attr("class", "ch-line").attr("stroke", noSame ? C.red : C.gold)
        .attr("d", d3.line().x((r) => P.x(r.decade)).y((r) => yb(r.gap)));
      const pts = P.g.selectAll(".pg").data(rows).join("circle").attr("r", 4.5).attr("fill", noSame ? C.red : C.gold)
        .attr("cx", (r) => P.x(r.decade)).attr("cy", (r) => yb(r.gap));
      if (noSame) {
        ln.transition().duration(900).attr("d", d3.line().x((r) => P.x(r.decade)).y((r) => yb(r[key])));
        pts.transition().duration(900).attr("cy", (r) => yb(r[key]));
      }
      decHover(S, [A, P], (d, Q) => {
        const r = by.get(d);
        if (Q === A) return `<b>${d}s</b><br>all films: ${f2(r.sim_all / b)} × the 1980s<br><span class="m">95% CI ${f2(r.sim_all_lo / b)}–${f2(r.sim_all_hi / b)}</span><br>no franchise films: ${f2(r.sim_nonfranchise / bn)} ×`;
        return `<b>${d}s</b><br>gap: ${d3.format(".4f")(r.gap)} <span class="m">(${zs(r.gap_z)} vs. shuffled plots)</span><br>without same-franchise pairs: ${d3.format(".4f")(r.gap_no_same_franchise)}<br><span class="m">${r.pairs_shared} film pairs share a person</span>`;
      });
    };
    if (methods.length > 1) buttons(S, "Method", methods.map((m) => [m, m]), method, (m) => { method = m; draw(); });
    buttons(S, "Film pairs", [[false, "All pairs"], [true, "Leave out same-franchise pairs"]], false, (v) => { noSame = v; draw(); });
    S.ctl.append("div").attr("class", "ch-key").html(
      `<span><i style="background:${C.gold}"></i>all films</span><span><i style="background:${C.cyan}" class="dashc"></i>no franchise films</span><span><i class="dash"></i>plots shuffled across films (± 2 sd)</span>`);
    draw();
  }

  // ---------- Act III: ratings ----------
  function ratings(el, D) {
    const S = shell(el, 3, "r3");
    const TY = [["tight circle", C.red, -0.22], ["other", C.null, 0], ["bridge", C.blue, 0.22]];
    let offT = new Set(), model = "main", offD = new Set();
    // A: ratings by type
    const A = panel(S, "Ratings by type of film"); A.x = decX(A);
    const ya = d3.scaleLinear().domain([d3.min(D.types, (r) => r.lo) - .05, d3.max(D.types, (r) => r.hi) + .05]).range([A.h, 0]);
    axes(A, A.x, ya, { yl: "mean IMDb rating", yf: d3.format(".1f"), xf: (d) => d + "s" });
    const gT = TY.map(([t, c, dx]) => {
      const rr = D.types.filter((r) => r.type === t), xo = (r) => A.x(r.decade) + dx * A.x.step() * 0.5;
      const g = A.g.append("g");
      g.selectAll("line").data(rr).join("line").attr("stroke", c).attr("stroke-width", 1.3).attr("x1", xo).attr("x2", xo).attr("y1", (r) => ya(r.lo)).attr("y2", (r) => ya(r.hi));
      g.append("path").datum(rr).attr("class", "ch-line").attr("stroke", c).attr("d", d3.line().x(xo).y((r) => ya(r.rating)));
      g.selectAll("circle").data(rr).join("circle").attr("r", 4).attr("fill", c).attr("cx", xo).attr("cy", (r) => ya(r.rating));
      return [t, g];
    });
    // B: coefficients
    const B = panel(S, "Effect on rating");
    const terms = [["prior_ties", "prior ties (0 → 1)"], ["n_comms", "+1 community"], ["franchise", "franchise film"]];
    const xb = d3.scaleLinear().domain([d3.min(D.models, (r) => Math.min(r.ci_lo, -2 * r.null_sd)) - .03, d3.max(D.models, (r) => Math.max(r.ci_hi, 2 * r.null_sd)) + .03]).range([0, B.w]);
    const yb = d3.scaleBand().domain(terms.map((t) => t[0])).range([0, B.h]).padding(0.35);
    B.g.append("g").attr("class", "ch-gridl").attr("transform", `translate(0,${B.h})`).call(d3.axisBottom(xb).ticks(5).tickSize(-B.h).tickFormat(""));
    B.g.append("g").attr("class", "ch-ax").attr("transform", `translate(0,${B.h})`).call(d3.axisBottom(xb).ticks(5).tickFormat(d3.format("+.1f")));
    B.g.append("text").attr("class", "ch-lab").attr("x", B.w / 2).attr("y", B.h + 32).attr("text-anchor", "middle").text("change in rating (points)");
    B.g.append("line").attr("class", "ch-ref").attr("x1", xb(0)).attr("x2", xb(0)).attr("y1", 0).attr("y2", B.h);
    const tl = B.g.selectAll(".tl").data(terms).join("text").attr("class", "ch-lab tl").attr("x", 4).attr("y", (t) => yb(t[0]) - 4).text((t) => t[1]);
    const gB = B.g.append("g");
    const drawB = () => {
      const rr = terms.map(([t]) => D.models.find((r) => r.model === model && r.term === t) || { term: t, missing: true });
      gB.selectAll(".nb").data(rr).join("rect").attr("class", "nb").attr("fill", C.null).attr("opacity", .25).attr("y", (r) => yb(r.term)).attr("height", yb.bandwidth())
        .transition().duration(500).attr("x", (r) => (r.missing ? xb(0) : xb(-2 * r.null_sd))).attr("width", (r) => (r.missing ? 0 : xb(2 * r.null_sd) - xb(-2 * r.null_sd)));
      gB.selectAll(".ci").data(rr).join("line").attr("class", "ci").attr("stroke", C.gold).attr("stroke-width", 2)
        .attr("y1", (r) => yb(r.term) + yb.bandwidth() / 2).attr("y2", (r) => yb(r.term) + yb.bandwidth() / 2)
        .transition().duration(500).attr("x1", (r) => xb(r.missing ? 0 : r.ci_lo)).attr("x2", (r) => xb(r.missing ? 0 : r.ci_hi)).style("opacity", (r) => (r.missing ? 0 : 1));
      gB.selectAll(".cp").data(rr).join("circle").attr("class", "cp").attr("r", 6).attr("stroke", "#0c0b0a").attr("stroke-width", 1.5)
        .attr("cy", (r) => yb(r.term) + yb.bandwidth() / 2)
        .on("mousemove", (e, r) => !r.missing && showTip(S, `<b>${terms.find((t) => t[0] === r.term)[1]}</b><br>${d3.format("+.3f")(r.coef)} points <span class="m">(95% CI ${d3.format("+.2f")(r.ci_lo)} to ${d3.format("+.2f")(r.ci_hi)})</span><br>permutation p = ${f3(r.p_perm)}<br><span class="m">${r.n} films · model: ${model.replace("_", " ")}</span>`, e))
        .on("mouseleave", () => hideTip(S))
        .transition().duration(500).attr("cx", (r) => xb(r.missing ? 0 : r.coef)).attr("fill", (r) => (r.p_perm < 0.05 ? C.red : C.gold)).style("opacity", (r) => (r.missing ? 0 : 1));
    };
    drawB();
    // C: directors
    const ds = new Map(D.dsum.map((r) => [String(r.decade), r]));
    const DIR = D.directors.filter((r) => r.b > 0), nZero = D.directors.length - DIR.length;
    const Cp = panel(S, "Directors: brokerage vs. rating");
    Cp.box.insert("div", "svg").attr("class", "ch-sub").text(`2+ films in the decade · ρ = ${f2(ds.get("all").rho)}, permutation p = ${f2(ds.get("all").p_perm)}`);
    B.box.insert("div", "svg").attr("class", "ch-sub").text("controls: decade and genre");
    A.box.insert("div", "svg").attr("class", "ch-sub").text("mean ± 95% bootstrap CI");
    const xc = d3.scaleLog().domain([d3.min(DIR, (r) => r.b) * 0.8, d3.max(DIR, (r) => r.b) * 1.2]).range([0, Cp.w]);
    const yc = d3.scaleLinear().domain(d3.extent(DIR, (r) => r.r)).nice().range([Cp.h, 0]);
    axes(Cp, xc, yc, { xl: "betweenness in decade network", yl: "mean rating of their films", xf: pow10, xt: d3.range(-6, 0).map((e) => 10 ** e).filter((v) => v >= xc.domain()[0] && v <= xc.domain()[1]), yf: d3.format(".1f") });
    const dots = Cp.g.selectAll(".dr").data(DIR).join("circle").attr("class", "dr").attr("r", (r) => 2.5 + r.f * 0.6)
      .attr("fill", (r) => DCOL[r.dec]).attr("fill-opacity", .65).attr("stroke", "#0c0b0a").attr("stroke-width", .5)
      .attr("cx", (r) => xc(r.b)).attr("cy", (r) => yc(r.r))
      .on("mousemove", function (e, r) { d3.select(this).attr("stroke", "#fff").attr("stroke-width", 1.5).raise(); showTip(S, `<b>${r.n}</b><br>${r.dec}s · ${r.f} films · mean rating ${r.r}<br><span class="m">betweenness ${d3.format(".2e")(r.b)}</span>`, e); })
      .on("mouseleave", function () { d3.select(this).attr("stroke", "#0c0b0a").attr("stroke-width", .5); hideTip(S); });
    // linked hover for panel A
    decHover(S, [A], (d) => `<b>${d}s</b><br>` + TY.filter(([t]) => !offT.has(t)).map(([t, c]) => {
      const r = D.types.find((x) => x.decade === d && x.type === t);
      return `<span style="color:${c}">●</span> ${t}: ${f2(r.rating)} <span class="m">(${r.films} films, CI ${f2(r.lo)}–${f2(r.hi)})</span>`;
    }).join("<br>"));
    // controls
    const row1 = S.ctl.append("div").attr("class", "ch-row");
    const S1 = { ctl: row1 };
    chips(S1, TY.map(([t, c]) => [t, t, c]), (o) => { offT = o; gT.forEach(([t, g]) => g.style("opacity", offT.has(t) ? 0 : 1)); },
      (h) => gT.forEach(([t, g]) => g.style("opacity", offT.has(t) ? 0 : h && h !== t ? 0.15 : 1)));
    buttons(S1, "Model", [["main", "main"], ["with_votes", "+ votes"], ["non_franchise", "non-franchise films"]], model, (m) => { model = m; drawB(); });
    chips(S1, DECS.map((d) => [d, d + "s", DCOL[d]]), (o) => { offD = o; dots.style("display", (r) => (offD.has(r.dec) ? "none" : null)); },
      (h) => dots.attr("fill-opacity", (r) => (h && h !== r.dec ? 0.08 : 0.65)));
    S.ctl.append("div").attr("class", "ch-hint").html("Left: click a film type to hide it. Middle: switch the model; red = permutation p &lt; 0.05, grey bar = shuffled ratings ± 2 sd. Right: hover a director; click a decade to hide it" + (nZero ? ` (${nZero} directors with betweenness 0 cannot be shown on the log axis)` : "") + ".");
  }

  const CH = { closure, dists, plots, ratings };
  let DATA;
  const render = () => holders.forEach((h) => { try { CH[h.dataset.chart](h, DATA); } catch (err) { console.error(err); h.innerHTML = `<img src="${h.dataset.fallback}" alt="" style="width:100%">`; } });
  fetch("assets/data/charts.json").then((r) => { if (!r.ok) throw new Error(r.status); return r.json(); })
    .then((j) => { DATA = j; render(); let t; window.addEventListener("resize", () => { clearTimeout(t); t = setTimeout(render, 250); }); })
    .catch(fallback);
})();
