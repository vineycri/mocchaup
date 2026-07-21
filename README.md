# 🖼️ Generador Automático de Mockups de Pósters

Aplicación de escritorio (Python + Tkinter + Pillow) que automatiza la
creación de mockups de pósters para un proyecto de e-commerce.

Toma **varias** fotografías de entornos (paredes con **marcos vacíos**), les
superpone el **diseño de un póster** y los exporta **todos a la vez** en
**.webp** con el prefijo **`PROD_`**. Por defecto cada resultado conserva el
**mismo tamaño que su imagen de mockup** (opcionalmente se puede recortar a
**1:1**). Soporta marcos rectos y **en ángulo (perspectiva)**, y acepta
**AVIF** (además de JPG/PNG/WEBP/BMP/TIFF) como imágenes de entrada.

Proyecto pensado como **ejercicio académico**: el código está muy comentado
y estructurado paso a paso.

## ✨ Novedades

- **Carga múltiple de mockups** y **exportación por lotes** (un `PROD_*.webp`
  por cada mockup, todos con un clic).
- **Modo perspectiva (ángulo):** define el marco con **4 esquinas** para
  marcos inclinados. Se implementa con Pillow (`Image.PERSPECTIVE`) y un
  solver propio, **sin depender de OpenCV ni numpy**.
- **Entrada AVIF** (y JPG/PNG/WEBP/BMP/TIFF).
- **Salida con prefijo `PROD_`** (p.ej. `sala.jpg` → `PROD_sala.webp`).
- **Salida al mismo tamaño que el mockup** por defecto (con casilla opcional
  para recortar a 1:1).

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

1. **Añadir mockups:** botón *"Añadir mockups (varios)…"* — puedes seleccionar
   **varias imágenes** a la vez. Aparecen en la lista (si existe `imagen.jpg`
   se añade sola al abrir). Selecciona uno para editar su marco.
2. **Cargar diseño del póster:** elige la imagen del póster (común a todos).
3. **Definir el marco del mockup seleccionado**, eligiendo el tipo:
   - **Rectángulo:** escribe **X, Y, Ancho, Alto** o **arrastra el ratón**
     sobre la vista previa para dibujarlo.
   - **Perspectiva (ángulo):** haz **clic en las 4 esquinas** del marco en
     este orden → **sup-izq, sup-der, inf-der, inf-izq**.

   Cada mockup guarda su propio marco de forma independiente.
4. **Encaje del póster:**
   - `fill` → rellena el marco y recorta lo que sobra (recomendado).
   - `fit` → mete el póster entero (puede dejar bordes).
   - `stretch` → deforma el póster para llenar exactamente el marco.
5. **Tamaño de salida:** por defecto cada archivo conserva el **mismo tamaño
   que su mockup**. Marca *"Recortar a 1:1 (cuadrado)"* si quieres salida
   cuadrada.
6. **Vista previa del seleccionado** para ver cómo queda.
7. **Exportar TODOS** → elige una carpeta y se genera un `PROD_*.webp` por
   cada mockup de la lista.

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
python mockup_core.py poster.png                       # usa imagen.jpg -> PROD_imagen.webp
python mockup_core.py poster.png sala.jpg salon.png cocina.avif
# genera PROD_sala.webp, PROD_salon.webp, PROD_cocina.webp
```

---

## 🔎 ¿Cómo funciona el procesamiento? (paso a paso)

1. **Encaje:** el póster se redimensiona al tamaño del marco (`encajar_poster`).
2. **Superposición:** se pega sobre la base en `(POS_X, POS_Y)`, respetando
   transparencias (`generar_mockup`).
3. **Tamaño de salida:** por defecto se conserva el del mockup; si activas
   `RECORTAR_1A1`, se recorta al cuadrado desde el centro
   (`recortar_cuadrado_centrado`).
4. **Exportación:** se guarda como `.webp` con compresión (`exportar_webp`).

> El código usa **Pillow (PIL)**. El modo perspectiva se resuelve con
> `Image.PERSPECTIVE` y un solver de sistemas propio, sin numpy ni OpenCV.
