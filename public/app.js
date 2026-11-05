/* Huffman Web Compressor — interfaz */
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const fmt = (n, d = 0) => Number(n).toLocaleString("es-MX", { maximumFractionDigits: d, minimumFractionDigits: d });
const fmtW = (n) => Number(n).toLocaleString("es-MX", { maximumFractionDigits: 2 });
const pct = (x, d = 1) => fmt(x * 100, d) + " %";
function bytes(n) {
  if (n < 1024) return fmt(n) + " B";
  if (n < 1024 * 1024) return fmt(n / 1024, 1) + " KB";
  return fmt(n / 1024 / 1024, 2) + " MB";
}
const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);

/* ---------- tema y pestañas ---------- */
(() => {
  let guardado = null;
  try { guardado = localStorage.getItem("tema"); } catch {}
  if (guardado) document.documentElement.dataset.theme = guardado;
  $("#tema").onclick = () => {
    const oscuro = matchMedia("(prefers-color-scheme: dark)").matches;
    const actual = document.documentElement.dataset.theme || (oscuro ? "dark" : "light");
    const nuevo = actual === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = nuevo;
    try { localStorage.setItem("tema", nuevo); } catch {}
  };
  $$(".tab").forEach((b) => (b.onclick = () => abrirTab(b.dataset.tab)));
})();
function abrirTab(id) {
  $$(".tab").forEach((t) => t.classList.toggle("active", t.dataset.tab === id));
  $$(".panel").forEach((p) => p.classList.toggle("active", p.id === "panel-" + id));
  if (id === "mst" && !mstDatos) generarMST();
}

function estado(el, msg, error = false) {
  el.hidden = !msg;
  el.classList.toggle("error", error);
  el.innerHTML = msg;
}
function zonaArrastre(label, input, alSoltar) {
  ["dragenter", "dragover"].forEach((e) => label.addEventListener(e, (ev) => { ev.preventDefault(); label.classList.add("over"); }));
  ["dragleave", "drop"].forEach((e) => label.addEventListener(e, (ev) => { ev.preventDefault(); label.classList.remove("over"); }));
  label.addEventListener("drop", (ev) => ev.dataTransfer.files[0] && alSoltar(ev.dataTransfer.files[0]));
  input.addEventListener("change", () => input.files[0] && alSoltar(input.files[0]));
}
async function postear(url, cuerpo) {
  const r = await fetch(url, { method: "POST", body: cuerpo });
  let datos;
  try { datos = await r.json(); } catch { throw new Error(`El servidor respondió ${r.status}.`); }
  if (!r.ok) throw new Error(datos.error || `Error ${r.status}`);
  return datos;
}
function b64aBlob(b64, tipo) {
  const bin = atob(b64);
  const arr = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) arr[i] = bin.charCodeAt(i);
  return new Blob([arr], { type: tipo });
}
function descargar(blob, nombre) {
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = nombre;
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 2000);
}

/* ======================================================================
   COMPRIMIR
   ====================================================================== */
let ultimo = null;
const MAX = 4.4 * 1024 * 1024;

zonaArrastre($("#drop"), $("#archivo"), (f) => {
  if (f.size > MAX) return estado($("#estado"), `El archivo pesa ${bytes(f.size)}; el límite es 4.4 MB.`, true);
  const fd = new FormData();
  fd.append("archivo", f);
  comprimir(fd, f.name);
});
$("#btn-texto").onclick = () => {
  const fd = new FormData();
  fd.append("texto", $("#texto").value);
  comprimir(fd, "texto pegado");
};

async function comprimir(fd, nombre) {
  estado($("#estado"), `<span class="spin"></span>Comprimiendo <b>${esc(nombre)}</b>: frecuencias → árbol voraz → códigos → bits…`);
  try {
    const d = await postear("/api/comprimir", fd);
    ultimo = d;
    estado($("#estado"), "");
    pintarResultados(d);
  } catch (e) {
    estado($("#estado"), e.message, true);
  }
}

function pintarResultados(d) {
  const s = d.stats;
  $("#resultados").hidden = false;
  $("#r-nombre").textContent = d.nombre;
  $("#k-orig").textContent = bytes(s.bytes_original);
  $("#k-orig-sub").textContent = `${fmt(s.caracteres)} caracteres · ${d.encoding.toUpperCase()}`;
  $("#k-huf").textContent = bytes(s.bytes_huf);
  $("#k-huf-sub").textContent = `datos ${bytes(s.bytes_datos)} + cabecera ${bytes(s.bytes_cabecera)}`;
  $("#k-ahorro").textContent = pct(s.ahorro);
  $("#k-razon").textContent = `razón de compresión ${fmt(s.bytes_original / s.bytes_huf, 2)} : 1`;
  $("#k-bpc").textContent = fmt(s.bits_por_simbolo, 3);
  $("#k-entropia").textContent = `entropía H = ${fmt(s.entropia, 3)} · eficiencia ${pct(s.eficiencia)}`;
  $("#k-simb").textContent = fmt(s.simbolos_distintos);
  $("#k-altura").textContent = `código más largo: ${s.altura_arbol} bits`;

  // barras de tamaño
  const filas = [
    ["orig", "Original (8+ bits/car.)", s.bytes_original],
    ["fijo", `Longitud fija (${s.bits_fijo_minimo} bits/car.)`, s.bytes_fijo_minimo],
    ["huf", "Huffman (.huf)", s.bytes_huf],
    ["zlib", "Referencia: ZIP/DEFLATE", s.bytes_zlib],
  ];
  const max = Math.max(...filas.map((f) => f[2]));
  $("#barras-tam").innerHTML = filas.map(([c, n, v]) =>
    `<div class="barra ${c}"><span>${n}</span><div class="pista"><div class="relleno" data-w="${(v / max) * 100}"></div></div><span class="v">${bytes(v)}</span></div>`).join("");
  requestAnimationFrame(() => $$("#barras-tam .relleno").forEach((r) => (r.style.width = r.dataset.w + "%")));
  $("#nota-tam").innerHTML =
    `Huffman usa en promedio <b>${fmt(s.bits_por_simbolo, 3)}</b> bits por carácter contra los 8 de ASCII/UTF-8 ` +
    `y queda a ${fmt(s.bits_por_simbolo - s.entropia, 3)} bits del límite teórico (entropía). ` +
    `ZIP combina Huffman con LZ77 (repeticiones de palabras), por eso comprime más.`;

  // gráfica de frecuencias
  const top = d.tabla.slice(0, 30);
  const fmax = top[0].frecuencia;
  $("#graf-freq").innerHTML = top.map((r) =>
    `<div class="col" title="'${esc(r.simbolo)}' · ${fmt(r.frecuencia)} veces · código ${r.codigo}"><div class="b" data-h="${(r.frecuencia / fmax) * 100}"></div><span class="l">${esc(r.simbolo)}</span></div>`).join("");
  requestAnimationFrame(() => $$("#graf-freq .b").forEach((b) => (b.style.height = b.dataset.h + "%")));

  pintarTabla(d.tabla);
  $("#n-pasos").textContent = `(${fmt(d.pasos.length)} fusiones = n − 1)`;
  $("#pasos tbody").innerHTML = d.pasos.map((p, i) =>
    `<tr><td>${i + 1}</td><td><code>${esc(p.izq)}</code> ${fmt(p.f_izq)}</td><td><code>${esc(p.der)}</code> ${fmt(p.f_der)}</td><td><b>${fmt(p.suma)}</b></td><td class="num">${p.restantes}</td></tr>`).join("");

  $("#chips").innerHTML = d.vista_codificacion.map((x) =>
    `<span class="chip"><span class="c">${esc(x.c)}</span><span class="k">${x.code}</span></span>`).join("");
  $("#bits").innerHTML = d.bits_inicio.replace(/(.{8})/g, "$1 ").replace(/1/g, '<span class="uno">1</span>');

  $("#orig-prev").textContent = d.texto_inicio;
  $("#dec-prev").textContent = d.decodificado_inicio;
  const v = $("#verif");
  v.className = "pill " + (d.identico ? "ok" : "mal");
  v.textContent = d.identico ? "✔ Idéntico byte a byte al original" : "✘ El texto decodificado no coincide";
  $("#tiempos").textContent =
    `Tiempos en el servidor: árbol ${fmt(s.t_arbol_ms, 2)} ms · comprimir ${fmt(s.t_comprimir_ms, 1)} ms · descomprimir ${fmt(s.t_descomprimir_ms, 1)} ms`;

  dibujarArbol(d.arbol);
  $("#resultados").scrollIntoView({ behavior: "smooth", block: "start" });
}

function pintarTabla(filas) {
  $("#tabla tbody").innerHTML = filas.map((r) =>
    `<tr><td class="sym" title="${r.codepoint}">${esc(r.simbolo)}</td><td class="num">${fmt(r.frecuencia)}</td><td class="num">${fmt(r.probabilidad * 100, 3)}%</td><td class="code">${r.codigo}</td><td class="num">${r.longitud}</td><td class="num">${fmt(r.bits_totales)}</td></tr>`).join("");
}
$("#filtro").oninput = (e) => {
  if (!ultimo) return;
  const q = e.target.value.trim().toLowerCase();
  pintarTabla(q ? ultimo.tabla.filter((r) => r.simbolo.toLowerCase().includes(q) || r.codigo.startsWith(q) || r.codepoint.toLowerCase().includes(q)) : ultimo.tabla);
};

$("#btn-descargar-huf").onclick = () => {
  if (!ultimo) return;
  descargar(b64aBlob(ultimo.huf_b64, "application/octet-stream"), ultimo.nombre.replace(/\.[^.]*$/, "") + ".huf");
};
$("#btn-roundtrip").onclick = () => {
  if (!ultimo) return;
  const f = new File([b64aBlob(ultimo.huf_b64)], ultimo.nombre.replace(/\.[^.]*$/, "") + ".huf");
  abrirTab("descomprimir");
  descomprimir(f);
};

/* ---------- árbol con D3 ---------- */
let arbolZoom, arbolSvg, arbolRaiz, arbolG, arbolActualizar;
function dibujarArbol(datos) {
  const cont = $("#arbol");
  cont.innerHTML = "";
  if (!window.d3) { cont.textContent = "No se pudo cargar D3."; return; }
  const W = cont.clientWidth, H = cont.clientHeight;
  arbolSvg = d3.select(cont).append("svg").attr("viewBox", [0, 0, W, H]);
  arbolG = arbolSvg.append("g");
  arbolZoom = d3.zoom().scaleExtent([0.05, 4]).on("zoom", (e) => arbolG.attr("transform", e.transform));
  arbolSvg.call(arbolZoom);

  arbolRaiz = d3.hierarchy(datos);
  arbolRaiz.descendants().forEach((d, i) => { d.id = i; d._children = d.children; });
  // d3.cluster alinea todas las hojas en la misma columna (dendrograma):
  // así las etiquetas de los caracteres nunca se enciman con nodos internos.
  const DX = 22, DY = 70;
  const tree = d3.cluster().nodeSize([DX, DY]).separation(() => 1);
  const gLinks = arbolG.append("g");
  const gNodos = arbolG.append("g");

  arbolActualizar = (fuente, ajustar = false) => {
    tree(arbolRaiz);
    const nodos = arbolRaiz.descendants(), links = arbolRaiz.links();
    const t = arbolSvg.transition().duration(350);
    const anim = (sel) => (ajustar ? sel : sel.transition(t));

    const link = gLinks.selectAll("g.lk").data(links, (d) => d.target.id);
    const lEnter = link.enter().append("g").attr("class", "lk");
    lEnter.append("path").attr("class", "link");
    lEnter.append("text").attr("class", "bit").attr("text-anchor", "middle");
    link.exit().remove();
    const lAll = lEnter.merge(link);
    anim(lAll.select("path")).attr("d", (d) => `M${d.source.y},${d.source.x}C${(d.source.y + d.target.y) / 2},${d.source.x} ${(d.source.y + d.target.y) / 2},${d.target.x} ${d.target.y},${d.target.x}`);
    lAll.select("text").text((d) => d.target.data.code.slice(-1));
    anim(lAll.select("text")).attr("x", (d) => (d.source.y + d.target.y) / 2).attr("y", (d) => (d.source.x + d.target.x) / 2 - 3);

    const nodo = gNodos.selectAll("g.nd").data(nodos, (d) => d.id);
    const nEnter = nodo.enter().append("g").attr("class", (d) => "nd " + (d.data.leaf ? "n-hoja" : "n-int"))
      .attr("transform", () => `translate(${fuente.y0 ?? 0},${fuente.x0 ?? 0})`)
      .on("click", (e, d) => {
        if (d.data.leaf) return;
        d.children = d.children ? null : d._children;
        arbolActualizar(d);
      });
    nEnter.filter((d) => !d.data.leaf).append("circle").attr("r", 5.5);
    nEnter.filter((d) => !d.data.leaf).append("text").attr("class", "fq").attr("x", -8).attr("y", -7).attr("text-anchor", "end").text((d) => fmt(d.data.freq));
    const hoja = nEnter.filter((d) => d.data.leaf);
    hoja.append("rect").attr("x", -2).attr("y", -9).attr("rx", 4).attr("height", 18).attr("width", (d) => 12 + d.data.name.length * 7);
    hoja.append("text").attr("class", "sym").attr("x", 4).attr("dy", "0.35em").text((d) => d.data.name);
    hoja.append("text").attr("class", "code").attr("x", (d) => 16 + d.data.name.length * 7).attr("dy", "0.35em").text((d) => `${d.data.code}  ·  ${fmt(d.data.freq)}`);
    nodo.exit().remove();
    anim(nEnter.merge(nodo).classed("plegado", (d) => !d.children && d._children))
      .attr("transform", (d) => `translate(${d.y},${d.x})`);
    nodos.forEach((d) => { d.x0 = d.x; d.y0 = d.y; });
    if (ajustar) ajustarArbol();
  };
  arbolActualizar(arbolRaiz, true);
}
function ajustarArbol() {
  if (!arbolG) return;
  const cont = $("#arbol");
  const W = cont.clientWidth, H = cont.clientHeight;
  const b = arbolG.node().getBBox();
  const k = Math.min(W / (b.width + 60), H / (b.height + 40), 1.4);
  const tr = d3.zoomIdentity.translate(W / 2 - k * (b.x + b.width / 2), H / 2 - k * (b.y + b.height / 2)).scale(k);
  arbolSvg.transition().duration(400).call(arbolZoom.transform, tr);
}
$("#arbol-ajustar").onclick = ajustarArbol;
$("#arbol-expandir").onclick = () => {
  if (!arbolRaiz) return;
  arbolRaiz.descendants().forEach((d) => (d.children = d._children));
  arbolActualizar(arbolRaiz);
  setTimeout(ajustarArbol, 380);
};

/* ======================================================================
   DESCOMPRIMIR
   ====================================================================== */
let ultimoTxt = null;
zonaArrastre($("#drop-huf"), $("#archivo-huf"), descomprimir);
async function descomprimir(f) {
  estado($("#estado-huf"), `<span class="spin"></span>Reconstruyendo el árbol y decodificando <b>${esc(f.name)}</b>…`);
  const fd = new FormData();
  fd.append("archivo", f);
  try {
    const d = await postear("/api/descomprimir", fd);
    ultimoTxt = d;
    estado($("#estado-huf"), "");
    $("#res-huf").hidden = false;
    $("#h-nombre").textContent = d.nombre;
    $("#h-huf").textContent = bytes(d.bytes_huf);
    $("#h-txt").textContent = bytes(d.bytes_texto);
    $("#h-chars").textContent = fmt(d.caracteres);
    $("#h-t").textContent = fmt(d.t_ms, 1) + " ms";
    $("#h-prev").textContent = d.texto_inicio + (d.caracteres > 3000 ? "\n\n[…]" : "");
  } catch (e) {
    estado($("#estado-huf"), e.message, true);
  }
}
$("#btn-descargar-txt").onclick = () => ultimoTxt && descargar(b64aBlob(ultimoTxt.texto_b64, "text/plain"), ultimoTxt.nombre);

/* ======================================================================
   ÁRBOL DE EXPANSIÓN MÍNIMA
   ====================================================================== */
let mstDatos = null, mstPaso = 0, mstTimer = null;
const NS = "http://www.w3.org/2000/svg";

async function pedirMST(cuerpo) {
  pararMST();
  try {
    const r = await fetch("/api/mst", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(cuerpo) });
    const d = await r.json();
    if (!r.ok) throw new Error(d.error);
    mstDatos = d;
    mstPaso = 0;
    $("#m-pk").textContent = fmtW(d.kruskal.peso_total);
    $("#m-pp").textContent = fmtW(d.prim.peso_total);
    $("#m-e").textContent = d.grafo.aristas.length;
    $("#m-em").textContent = d.kruskal.aristas.length + (d.kruskal.conexo ? "" : " (no conexo)");
    pintarMST();
  } catch (e) {
    alert("Error: " + e.message);
  }
}
function generarMST() { pedirMST({ modo: "aleatorio", n: +$("#m-n").value, semilla: $("#m-semilla").value }); }
$("#m-generar").onclick = generarMST;
$("#m-manual").onclick = () => pedirMST({ modo: "manual", texto: $("#m-texto").value });
$("#m-alg").onchange = () => { pararMST(); mstPaso = 0; pintarMST(); };
const pasosMST = () => (mstDatos ? mstDatos[$("#m-alg").value].pasos : []);
$("#m-inicio").onclick = () => { pararMST(); mstPaso = 0; pintarMST(); };
$("#m-prev").onclick = () => { pararMST(); mstPaso = Math.max(0, mstPaso - 1); pintarMST(); };
$("#m-next").onclick = () => { pararMST(); mstPaso = Math.min(pasosMST().length, mstPaso + 1); pintarMST(); };
$("#m-fin").onclick = () => { pararMST(); mstPaso = pasosMST().length; pintarMST(); };
$("#m-play").onclick = () => {
  if (mstTimer) return pararMST();
  if (mstPaso >= pasosMST().length) mstPaso = 0;
  $("#m-play").textContent = "⏸";
  mstTimer = setInterval(() => {
    if (mstPaso >= pasosMST().length) return pararMST();
    mstPaso++;
    pintarMST();
  }, 700);
};
function pararMST() { clearInterval(mstTimer); mstTimer = null; $("#m-play").textContent = "▶"; }

function pintarMST() {
  const svg = $("#m-svg");
  svg.innerHTML = "";
  if (!mstDatos) return;
  const { grafo } = mstDatos;
  const alg = $("#m-alg").value;
  const pasos = pasosMST();
  const P = grafo.posiciones;
  const clave = (u, v) => [u, v].sort().join("|");
  const estadoArista = {};
  const enArbol = new Set();
  if (alg === "prim") enArbol.add(mstDatos.prim.inicio);
  pasos.slice(0, mstPaso).forEach((p, i) => {
    estadoArista[clave(p.u, p.v)] = i === mstPaso - 1 ? (p.aceptada ? "mst act" : "rech act") : p.aceptada ? "mst" : "rech";
    if (p.aceptada) { enArbol.add(p.u); enArbol.add(p.v); }
  });
  for (const [u, v, w] of grafo.aristas) {
    const [x1, y1] = P[u], [x2, y2] = P[v];
    const l = document.createElementNS(NS, "line");
    Object.entries({ x1, y1, x2, y2 }).forEach(([k, val]) => l.setAttribute(k, val));
    const st = estadoArista[clave(u, v)] || "";
    l.setAttribute("class", "e " + (st.includes("act") ? "act" : st));
    svg.appendChild(l);
    const t = document.createElementNS(NS, "text");
    t.setAttribute("class", "w");
    t.setAttribute("x", (x1 + x2) / 2);
    t.setAttribute("y", (y1 + y2) / 2 - 4);
    t.setAttribute("text-anchor", "middle");
    t.textContent = w;
    svg.appendChild(t);
  }
  for (const n of grafo.nodos) {
    const g = document.createElementNS(NS, "g");
    g.setAttribute("class", "v" + (enArbol.has(n) ? " en" : ""));
    g.setAttribute("transform", `translate(${P[n][0]},${P[n][1]})`);
    g.innerHTML = `<circle r="15"></circle><text>${esc(n)}</text>`;
    svg.appendChild(g);
  }
  $("#m-contador").textContent = `Paso ${mstPaso} de ${pasos.length}` +
    (mstPaso === pasos.length ? ` · peso total ${fmtW(mstDatos[alg].peso_total)}` : "");
  $("#m-log").innerHTML = pasos.map((p, i) =>
    `<li class="${i < mstPaso ? (p.aceptada ? "ok" : "no") : ""} ${i === mstPaso - 1 ? "actual" : ""}">` +
    `${esc(p.u)}–${esc(p.v)} (${p.w}) <b>${i < mstPaso ? (p.aceptada ? "✔ se agrega" : "✘ " + p.motivo) : ""}</b></li>`).join("");
  const act = $("#m-log li.actual");
  if (act) act.scrollIntoView({ block: "nearest" });
}
