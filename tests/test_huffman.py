"""Pruebas:  python -m pytest -q   (o  python tests/test_huffman.py)"""
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from huffman import core, mst  # noqa: E402


def ida_y_vuelta(texto):
    blob, _ = core.comprimir(texto)
    return core.descomprimir(blob)[0] == texto


def test_casos_borde():
    for t in ["a", "aaaaaaa", "ab", "abracadabra", "ñandú café ☕ 😀\r\n﻿"]:
        assert ida_y_vuelta(t), t


def test_codigo_prefijo_y_optimo():
    freqs = {"a": 45, "b": 13, "c": 12, "d": 16, "e": 9, "f": 5}   # ejemplo clásico (CLRS)
    codigos = core.generar_codigos(core.construir_arbol(freqs))
    # ningún código es prefijo de otro
    cs = list(codigos.values())
    assert not any(a != b and b.startswith(a) for a in cs for b in cs)
    # costo óptimo conocido: 224 bits
    assert sum(freqs[s] * len(c) for s, c in codigos.items()) == 224


def test_texto_grande_con_codigos_largos():
    rnd = random.Random(0)
    alfabeto = [chr(c) for c in range(32, 400)]
    pesos = [2 ** (-i / 6) for i in range(len(alfabeto))]
    texto = "".join(rnd.choices(alfabeto, pesos, k=200_000))
    assert ida_y_vuelta(texto)


def test_entropia_cota():
    texto = "the quick brown fox jumps over the lazy dog " * 50
    freqs = core.calcular_frecuencias(texto)
    codigos = core.generar_codigos(core.construir_arbol(freqs))
    L = sum(freqs[c] * len(codigos[c]) for c in freqs) / len(texto)
    H = core.entropia(freqs)
    assert H <= L < H + 1


def test_mst_clrs():
    texto = "A B 4\nA H 8\nB C 8\nB H 11\nC D 7\nC F 4\nC I 2\nD E 9\nD F 14\nE F 10\nF G 2\nG H 1\nG I 6\nH I 7"
    nodos, aristas = mst.parsear_aristas(texto)
    assert mst.kruskal(nodos, aristas)["peso_total"] == 37
    assert mst.prim(nodos, aristas)["peso_total"] == 37


def test_mst_aleatorio_kruskal_igual_prim():
    for semilla in range(20):
        g = mst.grafo_aleatorio(12, semilla)
        k = mst.kruskal(g["nodos"], g["aristas"])
        p = mst.prim(g["nodos"], g["aristas"])
        assert k["conexo"] and p["conexo"]
        assert k["peso_total"] == p["peso_total"]


if __name__ == "__main__":
    for nombre, f in list(globals().items()):
        if nombre.startswith("test_"):
            f()
            print("✔", nombre)
