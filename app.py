"""
Huffman Web Compressor — servidor Flask.

* En Vercel: este archivo es el punto de entrada (preset Flask). Toda la app
  queda en una sola Vercel Function y la carpeta public/ (la GUI) se sirve
  desde la CDN.
* En local:  python app.py   ->  http://127.0.0.1:5000
"""

import base64
import math
import os
import sys
import time
import zlib

from flask import Flask, jsonify, request, send_from_directory

RAIZ = os.path.dirname(os.path.abspath(__file__))
PUBLIC = os.path.join(RAIZ, "public")
sys.path.insert(0, RAIZ)

from huffman import core, mst  # noqa: E402

MAX_BYTES = int(4.4 * 1024 * 1024)   # límite de cuerpo de petición en Vercel ≈ 4.5 MB

app = Flask(__name__, static_folder=None)
app.config["MAX_CONTENT_LENGTH"] = MAX_BYTES + 64 * 1024


@app.errorhandler(413)
def demasiado_grande(_):
    return jsonify(error="El archivo supera el límite de ~4.4 MB permitido por el servidor."), 413


@app.errorhandler(ValueError)
def valor_invalido(e):
    return jsonify(error=str(e)), 400


@app.get("/api/salud")
def salud():
    return jsonify(ok=True)


# --------------------------------------------------------------------------- #
#  Huffman
# --------------------------------------------------------------------------- #
@app.post("/api/comprimir")
def api_comprimir():
    archivo = request.files.get("archivo")
    if archivo:
        nombre = archivo.filename or "archivo.txt"
        crudo = archivo.read()
    else:
        nombre = "texto_pegado.txt"
        crudo = (request.form.get("texto") or "").encode("utf-8")
    if not crudo:
        raise ValueError("No se recibió ningún texto.")

    texto, encoding = core.decodificar_texto(crudo)

    t0 = time.perf_counter()
    raiz, pasos = core.construir_arbol(core.calcular_frecuencias(texto), registrar_pasos=True)
    t_arbol = time.perf_counter() - t0

    t0 = time.perf_counter()
    blob, info = core.comprimir(texto, encoding)
    t_comp = time.perf_counter() - t0

    t0 = time.perf_counter()
    recuperado, _ = core.descomprimir(blob)
    t_desc = time.perf_counter() - t0
    identico = recuperado.encode(encoding) == crudo

    freqs, codigos, bits = info["freqs"], info["codigos"], info["bits"]
    total_chars = len(texto)
    n_simbolos = len(freqs)
    bits_promedio = len(bits) / total_chars
    h = core.entropia(freqs)

    tabla = sorted(
        ({
            "simbolo": core.visible(c),
            "codepoint": f"U+{ord(c):04X}",
            "frecuencia": f,
            "probabilidad": f / total_chars,
            "codigo": codigos[c],
            "longitud": len(codigos[c]),
            "bits_totales": f * len(codigos[c]),
        } for c, f in freqs.items()),
        key=lambda r: (-r["frecuencia"], r["codigo"]),
    )

    zip_bytes = len(zlib.compress(crudo, 9))
    huf_total = len(blob)
    fijo_min = max(1, math.ceil(math.log2(n_simbolos))) if n_simbolos > 1 else 1

    # vista previa de la codificación: primeros caracteres con su código
    vista = [{"c": core.visible(c), "code": codigos[c]} for c in texto[:80]]

    return jsonify(
        nombre=nombre,
        encoding=encoding,
        tabla=tabla,
        arbol=core.arbol_a_dict(raiz),
        pasos=pasos,
        vista_codificacion=vista,
        bits_inicio=bits[:1024],
        texto_inicio=texto[:1500],
        decodificado_inicio=recuperado[:1500],
        identico=identico,
        huf_b64=base64.b64encode(blob).decode("ascii"),
        stats={
            "caracteres": total_chars,
            "simbolos_distintos": n_simbolos,
            "bytes_original": len(crudo),
            "bits_original": len(crudo) * 8,
            "bits_huffman": len(bits),
            "bytes_datos": info["bytes_datos"],
            "bytes_cabecera": info["bytes_cabecera"],
            "bytes_huf": huf_total,
            "razon": huf_total / len(crudo),
            "ahorro": 1 - huf_total / len(crudo),
            "ahorro_sin_cabecera": 1 - info["bytes_datos"] / len(crudo),
            "bits_por_simbolo": bits_promedio,
            "entropia": h,
            "eficiencia": h / bits_promedio if bits_promedio else 1.0,
            "bits_fijo_minimo": fijo_min,
            "bytes_fijo_minimo": math.ceil(fijo_min * total_chars / 8),
            "bytes_zlib": zip_bytes,
            "altura_arbol": max(len(c) for c in codigos.values()),
            "t_arbol_ms": t_arbol * 1000,
            "t_comprimir_ms": t_comp * 1000,
            "t_descomprimir_ms": t_desc * 1000,
        },
    )


@app.post("/api/descomprimir")
def api_descomprimir():
    archivo = request.files.get("archivo")
    if not archivo:
        raise ValueError("Sube un archivo .huf.")
    blob = archivo.read()
    t0 = time.perf_counter()
    texto, encoding = core.descomprimir(blob)
    dt = time.perf_counter() - t0
    datos = texto.encode(encoding)
    base = os.path.splitext(archivo.filename or "archivo")[0]
    return jsonify(
        nombre=f"{base}_descomprimido.txt",
        encoding=encoding,
        bytes_huf=len(blob),
        bytes_texto=len(datos),
        caracteres=len(texto),
        t_ms=dt * 1000,
        texto_inicio=texto[:3000],
        texto_b64=base64.b64encode(datos).decode("ascii"),
    )


# --------------------------------------------------------------------------- #
#  Árbol de expansión mínima
# --------------------------------------------------------------------------- #
@app.post("/api/mst")
def api_mst():
    datos = request.get_json(silent=True) or {}
    if datos.get("modo") == "manual":
        nodos, aristas = mst.parsear_aristas(datos.get("texto", ""))
        r = 160
        posiciones = {
            n: [300 + round(r * math.cos(2 * math.pi * i / len(nodos) - math.pi / 2)),
                200 + round(r * math.sin(2 * math.pi * i / len(nodos) - math.pi / 2))]
            for i, n in enumerate(nodos)
        }
        grafo = {"nodos": nodos, "aristas": aristas, "posiciones": posiciones}
    else:
        n = max(3, min(int(datos.get("n", 9)), 20))
        semilla = datos.get("semilla")
        grafo = mst.grafo_aleatorio(n, semilla=int(semilla) if semilla not in (None, "") else None)

    inicio = datos.get("inicio") or grafo["nodos"][0]
    if inicio not in grafo["nodos"]:
        inicio = grafo["nodos"][0]
    return jsonify(
        grafo=grafo,
        kruskal=mst.kruskal(grafo["nodos"], grafo["aristas"]),
        prim=mst.prim(grafo["nodos"], grafo["aristas"], inicio),
    )


# --------------------------------------------------------------------------- #
#  Interfaz (en Vercel la sirve la CDN desde public/; esto es para local)
# --------------------------------------------------------------------------- #
@app.get("/")
def inicio():
    return send_from_directory(PUBLIC, "index.html")


@app.get("/<path:ruta>")
def estaticos(ruta):
    return send_from_directory(PUBLIC, ruta)


if __name__ == "__main__":
    app.run(debug=True, port=int(os.environ.get("PORT", 5000)))
