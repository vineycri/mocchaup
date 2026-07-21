# 🖼️ Generador Automático de Mockups de Pósters

Aplicación de escritorio (Python + Tkinter + Pillow) que automatiza la
creación de mockups de pósters para un proyecto de e-commerce.

Toma una fotografía de un entorno (una **pared con un marco vacío**), le
superpone el **diseño de un póster**, recorta el resultado a **1:1
(cuadrado)** y lo exporta en **.webp** con buena compresión.

Proyecto pensado como **ejercicio académico**: el código está muy comentado
y estructurado paso a paso.

---

## 📂 Estructura del proyecto

| Archivo            | Qué contiene                                                        |
|--------------------|---------------------------------------------------------------------|
| `mockup_app.py`    | La **aplicación de escritorio** (ventana Tkinter). **Ejecuta este.** |
| `mockup_core.py`   | El **núcleo gráfico** (solo Pillow). Reutilizable como script.       |
| `requirements.txt` | Dependencias (Pillow).                                               |
| `imagen.jpg`       | Tu imagen base (la pared con el marco). **Debes añadirla tú.**       |

---

## 🚀 Instalación y ejecución

1. Instala Python 3.8 o superior (en Windows/macOS ya incluye Tkinter).
2. Instala las dependencias:

   ```bash
   pip install -r requirements.txt
   ```

3. Coloca tu imagen de fondo con el nombre **exacto** `imagen.jpg` en la
   misma carpeta (o cárgala luego desde la app con el botón).
4. Lanza la aplicación:

   ```bash
   python mockup_app.py
   ```

> En Linux, si al ejecutar aparece `ModuleNotFoundError: No module named 'tkinter'`,
> instala el paquete del sistema: `sudo apt install python3-tk`.

---

## 🖱️ Cómo usar la app

1. **Cargar imagen base (fondo):** se carga automáticamente si existe
   `imagen.jpg`; si no, úsala con el botón.
2. **Cargar diseño del póster:** elige la imagen del póster.
3. **Definir el marco** (dos formas):
   - Escribe **X, Y, Ancho, Alto** en los campos, **o**
   - **Dibuja el rectángulo arrastrando el ratón** sobre la vista previa
     (los campos se rellenan solos).
4. **Encaje del póster:**
   - `fill` → rellena el marco y recorta lo que sobra (recomendado).
   - `fit` → mete el póster entero (puede dejar bordes).
   - `stretch` → deforma el póster para llenar exactamente el marco.
5. **Generar vista previa** para ver el resultado ya cuadrado (1:1).
6. **Exportar a .webp** y elige dónde guardarlo.

---

## ⚙️ Ajustar coordenadas por código (opcional)

Al inicio de `mockup_core.py` hay variables globales claras y comentadas:

```python
IMAGEN_BASE = "imagen.jpg"   # Nombre del archivo de fondo
POS_X = 300                  # X de la esquina superior izquierda del marco
POS_Y = 200                  # Y de la esquina superior izquierda del marco
ANCHO_MARCO = 500            # Ancho del hueco del marco (px)
ALTO_MARCO  = 700            # Alto del hueco del marco (px)
CALIDAD_WEBP = 85            # Calidad de exportación (0-100)
MODO_ENCAJE = "fill"         # fill | fit | stretch
```

Estos valores son los que la app usa **por defecto** al abrirse.

---

## 🤖 Uso por línea de comandos (sin ventana)

`mockup_core.py` también funciona como script para automatizar por lotes,
usando las coordenadas definidas en sus variables globales:

```bash
python mockup_core.py diseno_del_poster.png            # -> mockup_final.webp
python mockup_core.py diseno_del_poster.png salida.webp
```

---

## 🔎 ¿Cómo funciona el procesamiento? (paso a paso)

1. **Encaje:** el póster se redimensiona al tamaño del marco (`encajar_poster`).
2. **Superposición:** se pega sobre la base en `(POS_X, POS_Y)`, respetando
   transparencias (`generar_mockup`).
3. **Recorte 1:1:** el resultado se recorta al cuadrado desde el centro
   (`recortar_cuadrado_centrado`).
4. **Exportación:** se guarda como `.webp` con compresión (`exportar_webp`).

> El código usa **Pillow (PIL)**. Para el encaje simple del póster no hace
> falta corrección de perspectiva; si tu marco estuviera en ángulo, se podría
> ampliar con OpenCV y una transformación de perspectiva.
