"""
Árbol de expansión mínima (MST) — otros dos algoritmos voraces clásicos.

* Kruskal: ordena todas las aristas por peso y, de forma voraz, toma la más
  ligera que no forme ciclo (se detecta con Union-Find).   O(E log E)
* Prim: crece un solo árbol desde un vértice inicial; en cada paso toma, de
  forma voraz, la arista más ligera que conecta el árbol con un vértice
  nuevo (cola de prioridad).                               O(E log V)

Ambos registran sus pasos para poder animarlos en la interfaz.
"""

from __future__ import annotations

import heapq
import math
import random


class UnionFind:
    def __init__(self, nodos):
        self.padre = {n: n for n in nodos}
        self.rango = {n: 0 for n in nodos}

    def encontrar(self, x):
        while self.padre[x] != x:
            self.padre[x] = self.padre[self.padre[x]]   # compresión de camino
            x = self.padre[x]
        return x

    def unir(self, a, b) -> bool:
        ra, rb = self.encontrar(a), self.encontrar(b)
        if ra == rb:
            return False
        if self.rango[ra] < self.rango[rb]:
            ra, rb = rb, ra
        self.padre[rb] = ra
        if self.rango[ra] == self.rango[rb]:
            self.rango[ra] += 1
        return True


def kruskal(nodos, aristas):
    """aristas: lista de (u, v, peso)."""
    uf = UnionFind(nodos)
    arbol, pasos, total = [], [], 0
    for u, v, w in sorted(aristas, key=lambda e: (e[2], str(e[0]), str(e[1]))):
        aceptada = uf.unir(u, v)
        pasos.append({"u": u, "v": v, "w": w, "aceptada": aceptada,
                      "motivo": "sin ciclo" if aceptada else "formaría ciclo"})
        if aceptada:
            arbol.append((u, v, w))
            total += w
            if len(arbol) == len(nodos) - 1:
                break
    return {"aristas": arbol, "peso_total": total, "pasos": pasos,
            "conexo": len(arbol) == len(nodos) - 1}


def prim(nodos, aristas, inicio=None):
    adj = {n: [] for n in nodos}
    for u, v, w in aristas:
        adj[u].append((w, u, v))
        adj[v].append((w, v, u))
    inicio = inicio if inicio is not None else nodos[0]
    visitados = {inicio}
    heap = list(adj[inicio])
    heapq.heapify(heap)
    arbol, pasos, total = [], [], 0
    while heap and len(visitados) < len(nodos):
        w, u, v = heapq.heappop(heap)
        if v in visitados:
            pasos.append({"u": u, "v": v, "w": w, "aceptada": False,
                          "motivo": "vértice ya en el árbol"})
            continue
        visitados.add(v)
        arbol.append((u, v, w))
        total += w
        pasos.append({"u": u, "v": v, "w": w, "aceptada": True,
                      "motivo": "arista mínima hacia vértice nuevo"})
        for e in adj[v]:
            if e[2] not in visitados:
                heapq.heappush(heap, e)
    return {"aristas": arbol, "peso_total": total, "pasos": pasos,
            "inicio": inicio, "conexo": len(arbol) == len(nodos) - 1}


def grafo_aleatorio(n: int = 9, semilla: int | None = None, vecinos: int = 3):
    """Puntos en el plano; cada uno se une a sus k vecinos más cercanos
    (peso = distancia euclidiana redondeada). Se garantiza conexidad."""
    rnd = random.Random(semilla)
    nombres = [chr(ord("A") + i) if i < 26 else f"V{i}" for i in range(n)]
    pos = {}
    for nm in nombres:
        for _ in range(200):
            p = (rnd.uniform(40, 560), rnd.uniform(40, 360))
            if all(math.dist(p, q) > 60 for q in pos.values()):
                break
        pos[nm] = p
    aristas = {}
    for a in nombres:
        cercanos = sorted((math.dist(pos[a], pos[b]), b) for b in nombres if b != a)
        for d, b in cercanos[:vecinos]:
            aristas[tuple(sorted((a, b)))] = round(d / 10)
    # conectar componentes si quedó desconexo
    uf = UnionFind(nombres)
    for (a, b) in aristas:
        uf.unir(a, b)
    for a in nombres:
        for b in nombres:
            if uf.encontrar(a) != uf.encontrar(b):
                aristas[tuple(sorted((a, b)))] = round(math.dist(pos[a], pos[b]) / 10)
                uf.unir(a, b)
    return {
        "nodos": nombres,
        "posiciones": {k: [round(x), round(y)] for k, (x, y) in pos.items()},
        "aristas": [[a, b, max(1, w)] for (a, b), w in sorted(aristas.items())],
    }


def parsear_aristas(texto: str):
    """Formato por línea:  A B 4   (también admite comas)."""
    aristas, nodos = [], []
    for num, linea in enumerate(texto.strip().splitlines(), 1):
        partes = linea.replace(",", " ").split()
        if not partes or partes[0].startswith("#"):
            continue
        if len(partes) != 3:
            raise ValueError(f"Línea {num}: se esperan 3 valores 'origen destino peso'.")
        u, v, w = partes[0], partes[1], float(partes[2])
        w = int(w) if w.is_integer() else w
        aristas.append([u, v, w])
        for x in (u, v):
            if x not in nodos:
                nodos.append(x)
    if not aristas:
        raise ValueError("No se encontraron aristas.")
    return nodos, aristas
