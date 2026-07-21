# -*- coding: utf-8 -*-
"""
============================================================================
 NÚCLEO DE PROCESAMIENTO GRÁFICO  (solo Pillow, sin interfaz)
============================================================================

Este módulo contiene TODA la lógica de imagen del generador de mockups:
encajar el póster, superponerlo sobre la base (en RECTÁNGULO o con
PERSPECTIVA/ángulo), recortar a 1:1 y exportar a .webp.

Se mantiene separado de la interfaz (mockup_app.py) para que:
  - Sea fácil de leer y explicar paso a paso (ejercicio académico).
  - Se pueda usar también como script de línea de comandos por lotes.
  - Se pueda probar de forma automática sin abrir una ventana.

Uso como script (sin ventana):
    python mockup_core.py diseno.png                       (usa IMAGEN_BASE)
    python mockup_core.py diseno.png mockup1.jpg mockup2.jpg ...
    -> genera un archivo "PROD_<nombre>.webp" por cada mockup.
============================================================================
"""

import os
import sys
from PIL import Image

# --- Soporte de AVIF de ENTRADA --------------------------------------------
# Pillow reciente trae AVIF nativo; en versiones anteriores hace falta el
# plugin 'pillow-avif-plugin'. Lo importamos de forma opcional: si está
# instalado, registra el lector de AVIF; si no, seguimos sin fallar.
try:
    import pillow_avif  # noqa: F401  (registra el soporte AVIF al importarse)
except ImportError:
    pass


# ===========================================================================
#  VARIABLES GLOBALES DE CONFIGURACIÓN  ── AJUSTA AQUÍ MANUALMENTE ──
# ===========================================================================
# La interfaz gráfica también permite cambiar estos valores en vivo, pero
# aquí quedan como valores por defecto claros y comentados.

# --- Imagen base por defecto (el entorno / la pared con el marco vacío) ----
IMAGEN_BASE = "imagen.jpg"     # Nombre EXACTO del archivo de fondo por defecto.

# --- Coordenadas de la ESQUINA SUPERIOR IZQUIERDA del marco vacío ----------
# Se miden en píxeles desde la esquina superior izquierda de la imagen base.
POS_X = 300                    # Posición horizontal (X) donde empieza el marco.
POS_Y = 200                    # Posición vertical   (Y) donde empieza el marco.

# --- Tamaño del área de inserción (el hueco del marco) ---------------------
ANCHO_MARCO = 500              # Ancho (en px) del hueco donde entra el póster.
ALTO_MARCO = 700              # Alto  (en px) del hueco donde entra el póster.

# --- Parámetros de EXPORTACIÓN ---------------------------------------------
FORMATO_SALIDA = "webp"        # Formato de salida solicitado.
CALIDAD_WEBP = 85            # Calidad 0-100. 80-90 = buena compresión/calidad.
PREFIJO_SALIDA = "PROD_"       # Prefijo de los archivos exportados (PROD_...).

# --- Tamaño de SALIDA ------------------------------------------------------
# False = la imagen final conserva el MISMO TAMAÑO que la imagen de mockup.
# True  = la imagen final se recorta a 1:1 (cuadrado) desde el centro.
RECORTAR_1A1 = False

# --- Modo de encaje del póster dentro del marco ----------------------------
# "stretch" = deforma el póster para llenar exactamente el marco.
# "fit"     = mantiene la proporción del póster (puede dejar bordes).
# "fill"    = mantiene proporción y RELLENA el marco recortando lo que sobra.
MODO_ENCAJE = "fill"

# Extensiones de imagen aceptadas COMO ENTRADA (incluye AVIF).
EXTENSIONES_ENTRADA = ("*.jpg", "*.jpeg", "*.png", "*.webp",
                       "*.bmp", "*.avif", "*.tif", "*.tiff")
# ===========================================================================


# ---------------------------------------------------------------------------
#  UTILIDADES DE ENCAJE (redimensionar el póster al hueco)
# ---------------------------------------------------------------------------

def encajar_poster(poster, ancho_destino, alto_destino, modo="fill"):
    """
    Redimensiona el 'poster' para que quepa en un rectángulo de tamaño
    (ancho_destino x alto_destino) según el 'modo' elegido.

    Devuelve una imagen RGBA exactamente del tamaño del rectángulo destino.
    """
    # Trabajamos siempre en RGBA para poder manejar transparencias/pegado.
    poster = poster.convert("RGBA")

    if modo == "stretch":
        # Deforma el diseño para llenar el marco por completo.
        return poster.resize((ancho_destino, alto_destino), Image.LANCZOS)

    # Proporciones (ancho/alto) del póster y del marco de destino.
    prop_poster = poster.width / poster.height
    prop_marco = ancho_destino / alto_destino

    if modo == "fit":
        # "fit": el póster entero cabe dentro del marco (puede sobrar espacio).
        if prop_poster > prop_marco:
            nuevo_ancho = ancho_destino
            nuevo_alto = round(ancho_destino / prop_poster)
        else:
            nuevo_alto = alto_destino
            nuevo_ancho = round(alto_destino * prop_poster)
        redimensionado = poster.resize((nuevo_ancho, nuevo_alto), Image.LANCZOS)
        # Lienzo transparente del tamaño del marco y pegamos centrado.
        lienzo = Image.new("RGBA", (ancho_destino, alto_destino), (0, 0, 0, 0))
        offset_x = (ancho_destino - nuevo_ancho) // 2
        offset_y = (alto_destino - nuevo_alto) // 2
        lienzo.paste(redimensionado, (offset_x, offset_y), redimensionado)
        return lienzo

    # modo == "fill" (por defecto): rellena el marco y recorta lo que sobra.
    if prop_poster > prop_marco:
        # El póster es más ancho: ajustamos por alto y recortamos los lados.
        nuevo_alto = alto_destino
        nuevo_ancho = round(alto_destino * prop_poster)
    else:
        # El póster es más alto: ajustamos por ancho y recortamos arriba/abajo.
        nuevo_ancho = ancho_destino
        nuevo_alto = round(ancho_destino / prop_poster)
    redimensionado = poster.resize((nuevo_ancho, nuevo_alto), Image.LANCZOS)
    # Recorte centrado hasta el tamaño exacto del marco.
    izquierda = (nuevo_ancho - ancho_destino) // 2
    arriba = (nuevo_alto - alto_destino) // 2
    return redimensionado.crop(
        (izquierda, arriba, izquierda + ancho_destino, arriba + alto_destino)
    )


# ---------------------------------------------------------------------------
#  PERSPECTIVA (ángulo): superponer el póster sobre un marco inclinado
# ---------------------------------------------------------------------------

def _resolver_sistema(A, b):
    """
    Resuelve el sistema lineal A·x = b por eliminación de Gauss.
    'A' es una lista de filas (listas) y 'b' una lista. Devuelve x.
    Se usa para calcular los 8 coeficientes de la transformación de
    perspectiva SIN depender de numpy ni de OpenCV.
    """
    n = len(A)
    # Matriz aumentada [A | b].
    M = [list(A[i]) + [b[i]] for i in range(n)]
    for col in range(n):
        # Pivoteo parcial: colocamos la fila con mayor valor absoluto arriba.
        pivote = max(range(col, n), key=lambda r: abs(M[r][col]))
        M[col], M[pivote] = M[pivote], M[col]
        valor = M[col][col]
        # Normalizamos la fila del pivote.
        for j in range(col, n + 1):
            M[col][j] /= valor
        # Eliminamos la columna en el resto de filas.
        for r in range(n):
            if r != col and M[r][col] != 0.0:
                factor = M[r][col]
                for j in range(col, n + 1):
                    M[r][j] -= factor * M[col][j]
    return [M[i][n] for i in range(n)]


def _coeficientes_perspectiva(destino, origen):
    """
    Calcula los 8 coeficientes que Pillow necesita en Image.transform(...,
    Image.PERSPECTIVE, ...). 'destino' son las 4 esquinas en la imagen de
    SALIDA y 'origen' las 4 esquinas correspondientes en la de ENTRADA.
    (Ambas en el mismo orden: sup-izq, sup-der, inf-der, inf-izq.)
    """
    A, b = [], []
    for (dx, dy), (sx, sy) in zip(destino, origen):
        A.append([dx, dy, 1, 0, 0, 0, -sx * dx, -sx * dy]); b.append(sx)
        A.append([0, 0, 0, dx, dy, 1, -sy * dx, -sy * dy]); b.append(sy)
    return _resolver_sistema(A, b)


def _dimension_media_del_marco(esquinas):
    """Estima ancho y alto 'medios' del cuadrilátero para pre-encajar el póster."""
    (x0, y0), (x1, y1), (x2, y2), (x3, y3) = esquinas
    def dist(a, b):
        return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5
    ancho = (dist((x0, y0), (x1, y1)) + dist((x3, y3), (x2, y2))) / 2  # sup + inf
    alto = (dist((x0, y0), (x3, y3)) + dist((x1, y1), (x2, y2))) / 2  # izq + der
    return max(1, round(ancho)), max(1, round(alto))


def componer_perspectiva(base, poster, esquinas, modo="fill"):
    """
    Pega el 'poster' sobre 'base' deformándolo para encajar en el
    cuadrilátero definido por 'esquinas' (4 puntos: sup-izq, sup-der,
    inf-der, inf-izq). Devuelve la base compuesta (RGBA), SIN recortar.
    """
    base = base.convert("RGBA").copy()
    W, H = base.size

    # 1) Pre-encajamos el póster a la proporción media del marco (respeta el
    #    modo fill/fit/stretch antes de deformar por perspectiva).
    ancho_m, alto_m = _dimension_media_del_marco(esquinas)
    poster_encajado = encajar_poster(poster, ancho_m, alto_m, modo)
    w, h = poster_encajado.size

    # 2) Esquinas de ORIGEN (el póster) en el orden sup-izq, sup-der, inf-der,
    #    inf-izq, para que coincidan con el orden de 'esquinas' (destino).
    origen = [(0, 0), (w, 0), (w, h), (0, h)]
    coeffs = _coeficientes_perspectiva(esquinas, origen)

    # 3) Deformamos el póster a un lienzo del tamaño de la base.
    deformado = poster_encajado.transform(
        (W, H), Image.PERSPECTIVE, coeffs, resample=Image.BICUBIC)

    # 4) Lo pegamos respetando su transparencia (fuera del marco es 0).
    base.paste(deformado, (0, 0), deformado)
    return base


def componer_rectangulo(base, poster, pos_x, pos_y, ancho, alto, modo="fill"):
    """
    Pega el 'poster' sobre 'base' en un rectángulo recto de tamaño
    (ancho x alto) con la esquina superior izquierda en (pos_x, pos_y).
    Devuelve la base compuesta (RGBA), SIN recortar.
    """
    base = base.convert("RGBA").copy()
    poster_encajado = encajar_poster(poster, ancho, alto, modo)
    # El tercer argumento (máscara) respeta la transparencia del póster.
    base.paste(poster_encajado, (pos_x, pos_y), poster_encajado)
    return base


# ---------------------------------------------------------------------------
#  RECORTE 1:1 Y ORQUESTACIÓN
# ---------------------------------------------------------------------------

def recortar_cuadrado_centrado(imagen):
    """
    Recorta la imagen desde el CENTRO para obtener una relación de
    aspecto 1:1 (cuadrado). El lado del cuadrado es el menor de ancho/alto.
    """
    ancho, alto = imagen.size
    lado = min(ancho, alto)                 # Lado del cuadrado resultante.
    izquierda = (ancho - lado) // 2         # Cuánto recortar por la izquierda.
    arriba = (alto - lado) // 2             # Cuánto recortar por arriba.
    # crop recibe (izquierda, arriba, derecha, abajo).
    return imagen.crop((izquierda, arriba, izquierda + lado, arriba + lado))


def generar_mockup(imagen_base, imagen_poster, region, modo=MODO_ENCAJE,
                   recortar_1a1=RECORTAR_1A1):
    """
    Orquesta todo el flujo y devuelve la imagen final (RGB).

    'region' es un diccionario que describe DÓNDE va el póster:
      - Rectángulo:  {"tipo": "rect", "x":.., "y":.., "w":.., "h":..}
      - Perspectiva: {"tipo": "persp", "esquinas": [(x,y) x4]}
        (esquinas en orden: sup-izq, sup-der, inf-der, inf-izq)

    'recortar_1a1':
      - False (por defecto): la salida conserva el MISMO TAMAÑO que el mockup.
      - True: la salida se recorta a 1:1 (cuadrado) desde el centro.

    'imagen_base' e 'imagen_poster' pueden ser una ruta (str) o un Image.
    """
    base = Image.open(imagen_base) if isinstance(imagen_base, str) else imagen_base
    poster = Image.open(imagen_poster) if isinstance(imagen_poster, str) else imagen_poster

    if region.get("tipo") == "persp":
        compuesta = componer_perspectiva(base, poster, region["esquinas"], modo)
    else:
        compuesta = componer_rectangulo(
            base, poster, region["x"], region["y"],
            region["w"], region["h"], modo)

    # Opcionalmente recortamos a 1:1; si no, mantenemos el tamaño del mockup.
    if recortar_1a1:
        compuesta = recortar_cuadrado_centrado(compuesta)

    # Vuelta a RGB (WEBP para e-commerce no necesita canal alfa).
    return compuesta.convert("RGB")


def nombre_de_salida(ruta_o_nombre_base, prefijo=PREFIJO_SALIDA):
    """
    Construye el nombre de salida a partir del nombre de la imagen base:
    p.ej. 'sala.jpg' -> 'PROD_sala.webp'.
    """
    base = os.path.basename(str(ruta_o_nombre_base))
    stem, _ext = os.path.splitext(base)
    return f"{prefijo}{stem}.{FORMATO_SALIDA}"


def exportar_webp(imagen, ruta_salida, calidad=CALIDAD_WEBP):
    """Guarda la imagen en formato .webp con buena compresión."""
    # method=6 = máxima compresión (más lento, mejor tamaño/calidad).
    imagen.save(ruta_salida, format="WEBP", quality=calidad, method=6)
    return ruta_salida


# ===========================================================================
#  MODO SCRIPT (sin ventana): exporta en LOTE con las coordenadas globales.
# ===========================================================================
if __name__ == "__main__":
    # Uso: python mockup_core.py <poster> [base1 base2 ...]
    if len(sys.argv) < 2:
        print("Uso: python mockup_core.py <poster> [mockup1 mockup2 ...]")
        print("Si no indicas mockups, se usa IMAGEN_BASE =", IMAGEN_BASE)
        sys.exit(1)

    ruta_poster = sys.argv[1]
    bases = sys.argv[2:] if len(sys.argv) > 2 else [IMAGEN_BASE]

    # Región rectangular por defecto (definida en las variables globales).
    region_defecto = {"tipo": "rect", "x": POS_X, "y": POS_Y,
                      "w": ANCHO_MARCO, "h": ALTO_MARCO}

    print(f"Póster: {ruta_poster}")
    print(f"Marco por defecto: X={POS_X}, Y={POS_Y}, "
          f"{ANCHO_MARCO}x{ALTO_MARCO}px (modo={MODO_ENCAJE})")

    tam = "1:1" if RECORTAR_1A1 else "tamaño del mockup"
    for base in bases:
        resultado = generar_mockup(base, ruta_poster, region_defecto,
                                   MODO_ENCAJE, RECORTAR_1A1)
        salida = nombre_de_salida(base)
        exportar_webp(resultado, salida, CALIDAD_WEBP)
        print(f"  ✅ {base}  ->  {salida}  "
              f"({resultado.size[0]}x{resultado.size[1]}, {tam})")

    print("Listo.")
