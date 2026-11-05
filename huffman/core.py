"""
Algoritmo de Huffman (técnica voraz) para compresión de texto.

Flujo:
    1. calcular_frecuencias(texto)      -> {carácter: frecuencia}
    2. construir_arbol(frecuencias)     -> raíz del árbol binario óptimo
       (en cada paso se toman, de forma voraz, los dos nodos de menor
        frecuencia de una cola de prioridad y se fusionan)
    3. generar_codigos(raiz)            -> {carácter: "0101..."}
    4. codificar(texto, codigos)        -> cadena de bits
    5. decodificar(bits, raiz)          -> texto original

Además, `comprimir` / `descomprimir` empaquetan los bits en bytes reales
dentro de un archivo binario .huf (cabecera con la tabla de frecuencias
+ datos), de modo que el tamaño comprimido es un tamaño en disco real.
"""

from __future__ import annotations

import heapq
import math
import struct
from collections import Counter
from dataclasses import dataclass, field
from itertools import count

MAGIC = b"HUF1"
ENCODINGS = ["utf-8", "latin-1"]


# --------------------------------------------------------------------------- #
#  Estructuras
# --------------------------------------------------------------------------- #
@dataclass
class Nodo:
    freq: int
    simbolo: str | None = None          # sólo las hojas tienen símbolo
    izq: "Nodo | None" = None
    der: "Nodo | None" = None
    id: int = field(default=0)

    @property
    def es_hoja(self) -> bool:
        return self.simbolo is not None


# --------------------------------------------------------------------------- #
#  1. Frecuencias
# --------------------------------------------------------------------------- #
def calcular_frecuencias(texto: str) -> dict[str, int]:
    """Cuenta cuántas veces aparece cada carácter del texto."""
    return dict(Counter(texto))


# --------------------------------------------------------------------------- #
#  2. Construcción voraz del árbol
# --------------------------------------------------------------------------- #
def construir_arbol(frecuencias: dict[str, int], registrar_pasos: bool = False):
    """
    Construye el árbol de Huffman con una cola de prioridad (min-heap).

    Elección voraz: en cada iteración se extraen los DOS nodos de menor
    frecuencia y se reemplazan por un nodo padre cuya frecuencia es la suma.
    Se repite n-1 veces hasta que sólo queda la raíz.

    El desempate es determinista (orden de inserción), así el decodificador
    reconstruye exactamente el mismo árbol a partir de la tabla de
    frecuencias guardada en la cabecera.

    Complejidad: O(n log n), con n = número de símbolos distintos.
    """
    if not frecuencias:
        raise ValueError("El texto está vacío: no hay nada que comprimir.")

    contador = count()
    heap: list[tuple[int, int, Nodo]] = []
    for simbolo in sorted(frecuencias):
        orden = next(contador)
        nodo = Nodo(frecuencias[simbolo], simbolo, id=orden)
        heap.append((nodo.freq, orden, nodo))
    heapq.heapify(heap)

    pasos = []

    # Caso especial: un solo símbolo distinto -> se le asigna el código "0".
    if len(heap) == 1:
        _, _, unico = heap[0]
        raiz = Nodo(unico.freq, izq=unico, id=next(contador))
        return (raiz, pasos) if registrar_pasos else raiz

    while len(heap) > 1:
        f1, _, a = heapq.heappop(heap)   # menor frecuencia
        f2, _, b = heapq.heappop(heap)   # segunda menor frecuencia
        orden = next(contador)
        padre = Nodo(f1 + f2, izq=a, der=b, id=orden)
        heapq.heappush(heap, (padre.freq, orden, padre))
        if registrar_pasos:
            pasos.append({
                "izq": _etiqueta(a), "f_izq": f1,
                "der": _etiqueta(b), "f_der": f2,
                "suma": f1 + f2, "restantes": len(heap),
            })

    raiz = heap[0][2]
    return (raiz, pasos) if registrar_pasos else raiz


def _etiqueta(n: Nodo) -> str:
    return visible(n.simbolo) if n.es_hoja else f"n{n.id}"


# --------------------------------------------------------------------------- #
#  3. Códigos
# --------------------------------------------------------------------------- #
def generar_codigos(raiz: Nodo) -> dict[str, str]:
    """Recorre el árbol: rama izquierda = '0', rama derecha = '1'."""
    codigos: dict[str, str] = {}
    pila = [(raiz, "")]
    while pila:
        nodo, prefijo = pila.pop()
        if nodo.es_hoja:
            codigos[nodo.simbolo] = prefijo or "0"
            continue
        if nodo.der:
            pila.append((nodo.der, prefijo + "1"))
        if nodo.izq:
            pila.append((nodo.izq, prefijo + "0"))
    return codigos


# --------------------------------------------------------------------------- #
#  4 y 5. Codificar / decodificar (a nivel de bits)
# --------------------------------------------------------------------------- #
def codificar(texto: str, codigos: dict[str, str]) -> str:
    return "".join(map(codigos.__getitem__, texto))


def decodificar(bits: str, raiz: Nodo) -> str:
    """
    Decodificación recorriendo el árbol: se baja a la izquierda con '0' y a
    la derecha con '1'; al llegar a una hoja se emite su símbolo y se vuelve
    a la raíz.  Para textos grandes se usa una tabla de búsqueda de K bits
    que resuelve la mayoría de los códigos en un solo paso (los códigos más
    largos que K se terminan de recorrer en el árbol).
    """
    if raiz.der is None:                       # un solo símbolo
        return raiz.izq.simbolo * len(bits)

    K = 12
    tabla = _tabla_busqueda(raiz, K)
    n = len(bits)
    relleno = bits + "0" * K
    salida = []
    i = 0
    while i < n:
        entrada = tabla[int(relleno[i:i + K], 2)]
        if entrada[0] is not None:             # código completo en K bits
            salida.append(entrada[0])
            i += entrada[1]
        else:                                  # código largo: seguir el árbol
            nodo = entrada[2]
            i += K
            while not nodo.es_hoja:
                nodo = nodo.izq if relleno[i] == "0" else nodo.der
                i += 1
            salida.append(nodo.simbolo)
    return "".join(salida)


def _tabla_busqueda(raiz: Nodo, K: int):
    tabla = []
    for valor in range(1 << K):
        nodo = raiz
        for p in range(K):
            bit = (valor >> (K - 1 - p)) & 1
            nodo = nodo.der if bit else nodo.izq
            if nodo.es_hoja:
                tabla.append((nodo.simbolo, p + 1, None))
                break
        else:
            tabla.append((None, K, nodo))
    return tabla


# --------------------------------------------------------------------------- #
#  Formato binario .huf
# --------------------------------------------------------------------------- #
#   MAGIC "HUF1" | enc (1B) | nsimbolos (4B) |
#   por símbolo: longitud UTF-8 (1B) + bytes + frecuencia (4B) |
#   número de bits válidos (8B) | bits empaquetados
def bits_a_bytes(bits: str) -> bytes:
    if not bits:
        return b""
    resto = (-len(bits)) % 8
    bits += "0" * resto
    return int(bits, 2).to_bytes(len(bits) // 8, "big")


def bytes_a_bits(datos: bytes, nbits: int) -> str:
    if nbits == 0:
        return ""
    total = len(datos) * 8
    return format(int.from_bytes(datos, "big"), f"0{total}b")[:nbits]


def comprimir(texto: str, encoding: str = "utf-8") -> tuple[bytes, dict]:
    freqs = calcular_frecuencias(texto)
    raiz = construir_arbol(freqs)
    codigos = generar_codigos(raiz)
    bits = codificar(texto, codigos)

    cabecera = bytearray(MAGIC)
    cabecera += struct.pack(">BI", ENCODINGS.index(encoding), len(freqs))
    for simbolo in sorted(freqs):
        b = simbolo.encode("utf-8", "surrogatepass")
        cabecera += struct.pack(">B", len(b)) + b + struct.pack(">I", freqs[simbolo])
    cabecera += struct.pack(">Q", len(bits))
    datos = bits_a_bytes(bits)
    return bytes(cabecera) + datos, {
        "freqs": freqs, "raiz": raiz, "codigos": codigos, "bits": bits,
        "bytes_cabecera": len(cabecera), "bytes_datos": len(datos),
    }


def leer_cabecera(blob: bytes):
    if blob[:4] != MAGIC:
        raise ValueError("No es un archivo .huf válido (firma incorrecta).")
    pos = 4
    enc_idx, n = struct.unpack_from(">BI", blob, pos)
    pos += 5
    freqs = {}
    for _ in range(n):
        (lb,) = struct.unpack_from(">B", blob, pos)
        pos += 1
        simbolo = blob[pos:pos + lb].decode("utf-8", "surrogatepass")
        pos += lb
        (f,) = struct.unpack_from(">I", blob, pos)
        pos += 4
        freqs[simbolo] = f
    (nbits,) = struct.unpack_from(">Q", blob, pos)
    pos += 8
    return ENCODINGS[enc_idx], freqs, nbits, pos


def descomprimir(blob: bytes) -> tuple[str, str]:
    """Devuelve (texto, encoding original)."""
    encoding, freqs, nbits, pos = leer_cabecera(blob)
    raiz = construir_arbol(freqs)
    bits = bytes_a_bits(blob[pos:], nbits)
    return decodificar(bits, raiz), encoding


# --------------------------------------------------------------------------- #
#  Utilidades para el análisis / GUI
# --------------------------------------------------------------------------- #
def visible(c: str) -> str:
    """Representación legible de caracteres especiales."""
    especiales = {" ": "␣", "\n": "\\n", "\r": "\\r", "\t": "\\t", "﻿": "BOM"}
    if c in especiales:
        return especiales[c]
    if not c.isprintable():
        return f"U+{ord(c):04X}"
    return c


def entropia(freqs: dict[str, int]) -> float:
    total = sum(freqs.values())
    return -sum((f / total) * math.log2(f / total) for f in freqs.values())


def arbol_a_dict(nodo: Nodo, prefijo: str = "") -> dict:
    if nodo.es_hoja:
        return {"name": visible(nodo.simbolo), "freq": nodo.freq,
                "code": prefijo or "0", "leaf": True}
    hijos = []
    if nodo.izq:
        hijos.append(arbol_a_dict(nodo.izq, prefijo + "0"))
    if nodo.der:
        hijos.append(arbol_a_dict(nodo.der, prefijo + "1"))
    return {"name": str(nodo.freq), "freq": nodo.freq, "code": prefijo,
            "leaf": False, "children": hijos}


def decodificar_texto(datos: bytes) -> tuple[str, str]:
    """Intenta UTF-8 (lo normal en Project Gutenberg) y si falla, Latin-1."""
    try:
        return datos.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        return datos.decode("latin-1"), "latin-1"
