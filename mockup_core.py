# -*- coding: utf-8 -*-
"""
============================================================================
 NÚCLEO DE PROCESAMIENTO GRÁFICO  (solo Pillow, sin interfaz)
============================================================================

Este módulo contiene TODA la lógica de imagen del generador de mockups:
encajar el póster, superponerlo sobre la base, recortar a 1:1 y exportar.

Se mantiene separado de la interfaz (mockup_app.py) para que:
  - Sea fácil de leer y explicar paso a paso (ejercicio académico).
  - Se pueda usar también como script de línea de comandos.
  - Se pueda probar de forma automática sin abrir una ventana.

Uso como script (sin ventana):
    python mockup_core.py diseno.png            -> genera 'mockup_final.webp'
    python mockup_core.py diseno.png salida.webp
============================================================================
"""

import sys
from PIL import Image


# ===========================================================================
#  VARIABLES GLOBALES DE CONFIGURACIÓN  ── AJUSTA AQUÍ MANUALMENTE ──
# ===========================================================================
# La interfaz gráfica también permite cambiar estos valores en vivo, pero
# aquí quedan como valores por defecto claros y comentados.

# --- Imagen base (el entorno / la pared con el marco vacío) -----------------
IMAGEN_BASE = "imagen.jpg"     # Nombre EXACTO del archivo de fondo.

# --- Coordenadas de la ESQUINA SUPERIOR IZQUIERDA del marco vacío ----------
# Se miden en píxeles desde la esquina superior izquierda de "imagen.jpg".
POS_X = 300                    # Posición horizontal (X) donde empieza el marco.
POS_Y = 200                    # Posición vertical   (Y) donde empieza el marco.

# --- Tamaño del área de inserción (el hueco del marco) ---------------------
ANCHO_MARCO = 500              # Ancho (en px) del hueco donde entra el póster.
ALTO_MARCO = 700              # Alto  (en px) del hueco donde entra el póster.

# --- Parámetros de EXPORTACIÓN ---------------------------------------------
FORMATO_SALIDA = "webp"        # Formato de salida solicitado.
CALIDAD_WEBP = 85            # Calidad 0-100. 80-90 = buena compresión/calidad.
NOMBRE_SALIDA = "mockup_final.webp"   # Nombre del archivo exportado.

# --- Modo de encaje del póster dentro del marco ----------------------------
# "stretch" = deforma el póster para llenar exactamente el marco.
# "fit"     = mantiene la proporción del póster (puede dejar bordes).
# "fill"    = mantiene proporción y RELLENA el marco recortando lo que sobra.
MODO_ENCAJE = "fill"
# ===========================================================================


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


def generar_mockup(imagen_base, imagen_poster,
                   pos_x, pos_y, ancho_marco, alto_marco,
                   modo=MODO_ENCAJE):
    """
    Orquesta todo el flujo gráfico y devuelve la imagen final (cuadrada, RGB):

        1) Encaja el póster en el tamaño del marco.
        2) Lo pega sobre la imagen base en (pos_x, pos_y).
        3) Recorta el resultado a 1:1 desde el centro.

    Ambos parámetros de imagen pueden ser una ruta (str) o un objeto Image.
    """
    # Permitimos pasar rutas o imágenes ya abiertas (útil para la GUI).
    base = Image.open(imagen_base) if isinstance(imagen_base, str) else imagen_base
    poster = Image.open(imagen_poster) if isinstance(imagen_poster, str) else imagen_poster

    # PASO 1 — La base la llevamos a RGBA para poder pegar con transparencia.
    base = base.convert("RGBA").copy()

    # PASO 2 — Redimensionamos/encajamos el póster al hueco del marco.
    poster_encajado = encajar_poster(poster, ancho_marco, alto_marco, modo)

    # PASO 3 — Superponemos el póster sobre la base en las coordenadas dadas.
    #          El tercer argumento (máscara) respeta la transparencia.
    base.paste(poster_encajado, (pos_x, pos_y), poster_encajado)

    # PASO 4 — Recorte cuadrado 1:1 centrado.
    cuadrado = recortar_cuadrado_centrado(base)

    # PASO 5 — Volvemos a RGB porque WEBP para e-commerce no necesita alfa.
    return cuadrado.convert("RGB")


def exportar_webp(imagen, ruta_salida, calidad=CALIDAD_WEBP):
    """Guarda la imagen en formato .webp con buena compresión."""
    # method=6 = máxima compresión (más lento, mejor tamaño/calidad).
    imagen.save(ruta_salida, format="WEBP", quality=calidad, method=6)
    return ruta_salida


# ===========================================================================
#  MODO SCRIPT (sin ventana): útil para automatizar por lotes.
# ===========================================================================
if __name__ == "__main__":
    # Uso: python mockup_core.py <diseno_poster> [salida.webp]
    if len(sys.argv) < 2:
        print("Uso: python mockup_core.py <diseno_poster> [salida.webp]")
        sys.exit(1)

    ruta_poster = sys.argv[1]
    ruta_salida = sys.argv[2] if len(sys.argv) > 2 else NOMBRE_SALIDA

    print(f"Base:   {IMAGEN_BASE}")
    print(f"Póster: {ruta_poster}")
    print(f"Marco:  X={POS_X}, Y={POS_Y}, {ANCHO_MARCO}x{ALTO_MARCO}px "
          f"(modo={MODO_ENCAJE})")

    resultado = generar_mockup(IMAGEN_BASE, ruta_poster,
                               POS_X, POS_Y, ANCHO_MARCO, ALTO_MARCO,
                               modo=MODO_ENCAJE)
    exportar_webp(resultado, ruta_salida, CALIDAD_WEBP)
    print(f"✅ Mockup guardado en: {ruta_salida}  (cuadrado 1:1, .webp)")
