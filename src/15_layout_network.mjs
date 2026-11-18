// Step 15: community-aware layout for the site's network explorer.
// Adds lx/ly (positions, 1000 x 560 frame) to every node in assets/data/network.json,
// so the browser does not have to run the simulation (about 2 s per decade).
// The 8 big communities each get an anchor on an ellipse (ordered as in the spring
// layout of step 13, so neighbouring communities stay neighbours); links inside a
// community are short and strong, links between communities long and weak; a weak
// pull to the centre keeps chains of one-film casts from sprawling.
// Run from project/ after step 13:  npm i d3-force d3-array && node src/15_layout_network.mjs
import fs from "fs";
import { forceSimulation, forceLink, forceManyBody, forceX, forceY, forceCollide } from "d3-force";
import { mean } from "d3-array";

const F = "assets/data/network.json", data = JSON.parse(fs.readFileSync(F, "utf8"));
const LW = 1000, LH = 560;
for (const [dec, D] of Object.entries(data.decades)) {
  const cs = D.communities.filter((c) => c.label).map((c) => {
    const m = D.nodes.filter((n) => n.c === c.id);
    return { id: c.id, a: Math.atan2(mean(m, (n) => n.y) - 0.5, mean(m, (n) => n.x) - 0.5) };
  }).sort((a, b) => a.a - b.a);
  const ctr = {};
  cs.forEach((c, i) => { const t = (2 * Math.PI * i) / cs.length - Math.PI / 2; ctr[c.id] = [LW / 2 + Math.cos(t) * LW * 0.34, LH / 2 + Math.sin(t) * LH * 0.32]; });
  const nodes = D.nodes.map((n, i) => ({ i, c: n.c, r: 2 + Math.sqrt(n.d) * 0.9,
    x: n.c >= 0 ? ctr[n.c][0] + (n.x - 0.5) * 60 : n.x * LW, y: n.c >= 0 ? ctr[n.c][1] + (0.5 - n.y) * 60 : (1 - n.y) * LH }));
  const same = (l) => nodes[l.a].c >= 0 && nodes[l.a].c === nodes[l.b].c;
  const links = D.edges.map(([a, b, w]) => ({ source: a, target: b, a, b, w }));
  forceSimulation(nodes)
    .force("link", forceLink(links).distance((l) => (same(l) ? 10 : 34)).strength((l) => (same(l) ? 0.35 : 0.03)))
    .force("charge", forceManyBody().strength(-10).distanceMax(120))
    .force("x", forceX((n) => (n.c >= 0 ? ctr[n.c][0] : LW / 2)).strength((n) => (n.c >= 0 ? 0.07 : 0.025)))
    .force("y", forceY((n) => (n.c >= 0 ? ctr[n.c][1] : LH / 2)).strength((n) => (n.c >= 0 ? 0.1 : 0.04)))
    .force("collide", forceCollide((n) => n.r + 0.6).iterations(2))
    .stop().tick(320);
  nodes.forEach((n) => { D.nodes[n.i].lx = Math.round(n.x * 10) / 10; D.nodes[n.i].ly = Math.round(n.y * 10) / 10; });
  console.log(dec, "laid out");
}
fs.writeFileSync(F, JSON.stringify(data));
console.log(F, Math.round(fs.statSync(F).size / 1024), "KB");
