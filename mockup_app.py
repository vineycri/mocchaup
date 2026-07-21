# -*- coding: utf-8 -*-
"""
============================================================================
 GENERADOR AUTOMÁTICO DE MOCKUPS DE PÓSTERS  (App de escritorio - Tkinter)
============================================================================

Ejercicio académico / proyecto de e-commerce.

¿Qué hace esta aplicación?
--------------------------
1. Carga una imagen de ENTORNO (una pared con marcos vacíos) que sirve de
   fondo. Por defecto se llama "imagen.jpg".
2. Recibe una imagen secundaria: el DISEÑO del póster.
3. Redimensiona ese diseño y lo superpone (composita) automáticamente sobre
   el área del marco vacío definida por las coordenadas (X, Y) y el tamaño
   (ANCHO, ALTO).
4. Recorta el resultado desde el CENTRO para garantizar una relación de
   aspecto exacta de 1:1 (formato cuadrado).
5. Exporta la imagen final a formato .webp con buena compresión.

La aplicación es una ventana de escritorio (Tkinter): permite subir las
imágenes con botones, escribir las coordenadas a mano O dibujarlas con el
ratón sobre la vista previa, ver el resultado en vivo y exportar el .webp.

Requisitos:
    pip install Pillow
Ejecutar:
    python mockup_app.py
============================================================================
"""

# ---------------------------------------------------------------------------
# IMPORTS
# ---------------------------------------------------------------------------
import os                                   # Rutas y comprobación de archivos
import tkinter as tk                        # Librería GUI estándar de Python
from tkinter import filedialog, messagebox  # Diálogos para abrir/guardar
from PIL import Image, ImageTk              # Pillow: procesamiento de imágenes

# Toda la lógica de imagen vive en mockup_core.py (solo Pillow, sin interfaz).
# Aquí importamos tanto las funciones como los valores de configuración.
from mockup_core import (
    IMAGEN_BASE, POS_X, POS_Y, ANCHO_MARCO, ALTO_MARCO,
    CALIDAD_WEBP, NOMBRE_SALIDA, MODO_ENCAJE,
    generar_mockup, exportar_webp,
)


# ===========================================================================
#  INTERFAZ GRÁFICA DE ESCRITORIO (Tkinter)
# ===========================================================================

class AppMockup(tk.Tk):
    """Ventana principal de la aplicación."""

    # Tamaño máximo (en px) de la vista previa dentro de la ventana.
    PREVIEW_MAX = 560

    def __init__(self):
        super().__init__()
        self.title("Generador de Mockups de Pósters")
        self.configure(bg="#1e1e2e")
        self.resizable(False, False)

        # --- Estado interno de la aplicación -------------------------------
        self.img_base = None          # Objeto PIL de la imagen de fondo.
        self.img_poster = None        # Objeto PIL del diseño del póster.
        self.img_resultado = None     # Última composición generada (PIL).
        self.preview_tk = None        # Referencia para que Tk no borre la img.
        self.escala_preview = 1.0     # Relación px_preview / px_reales.
        self._drag_inicio = None      # Punto inicial al dibujar con el ratón.
        self._rect_id = None          # ID del rectángulo dibujado en el canvas.

        # Variables enlazadas a los campos de coordenadas de la interfaz.
        self.var_x = tk.IntVar(value=POS_X)
        self.var_y = tk.IntVar(value=POS_Y)
        self.var_w = tk.IntVar(value=ANCHO_MARCO)
        self.var_h = tk.IntVar(value=ALTO_MARCO)
        self.var_modo = tk.StringVar(value=MODO_ENCAJE)
        self.var_calidad = tk.IntVar(value=CALIDAD_WEBP)

        # Construimos la interfaz y cargamos la base por defecto si existe.
        self._construir_interfaz()
        self._cargar_base_por_defecto()

    # ------------------------------------------------------------------ GUI
    def _construir_interfaz(self):
        """Crea todos los widgets: panel de control + vista previa."""
        contenedor = tk.Frame(self, bg="#1e1e2e")
        contenedor.pack(padx=12, pady=12)

        # ---- Columna izquierda: PANEL DE CONTROL --------------------------
        panel = tk.Frame(contenedor, bg="#1e1e2e")
        panel.grid(row=0, column=0, sticky="n", padx=(0, 12))

        def titulo(txt):
            tk.Label(panel, text=txt, bg="#1e1e2e", fg="#89b4fa",
                     font=("Helvetica", 11, "bold")).pack(anchor="w", pady=(10, 2))

        def boton(txt, cmd, color="#585b70"):
            return tk.Button(panel, text=txt, command=cmd, bg=color, fg="white",
                             activebackground="#6c7086", relief="flat",
                             font=("Helvetica", 10), padx=8, pady=6, width=26)

        titulo("1) Imágenes")
        boton("📁  Cargar imagen base (fondo)", self.cargar_base).pack(pady=3)
        boton("🖼️  Cargar diseño del póster", self.cargar_poster).pack(pady=3)

        titulo("2) Coordenadas del marco (px)")
        grid = tk.Frame(panel, bg="#1e1e2e")
        grid.pack(anchor="w")
        self._campo_coordenada(grid, "X:", self.var_x, 0, 0)
        self._campo_coordenada(grid, "Y:", self.var_y, 0, 2)
        self._campo_coordenada(grid, "Ancho:", self.var_w, 1, 0)
        self._campo_coordenada(grid, "Alto:", self.var_h, 1, 2)
        tk.Label(panel,
                 text="Consejo: también puedes DIBUJAR el marco\narrastrando el ratón sobre la vista previa.",
                 bg="#1e1e2e", fg="#a6adc8", font=("Helvetica", 8),
                 justify="left").pack(anchor="w", pady=(4, 0))

        titulo("3) Encaje del póster")
        menu = tk.OptionMenu(panel, self.var_modo, "fill", "fit", "stretch")
        menu.configure(bg="#585b70", fg="white", relief="flat",
                       highlightthickness=0, width=24)
        menu.pack(anchor="w", pady=3)

        titulo("4) Calidad WEBP (0-100)")
        tk.Scale(panel, from_=10, to=100, orient="horizontal",
                 variable=self.var_calidad, bg="#1e1e2e", fg="white",
                 highlightthickness=0, troughcolor="#585b70",
                 length=210).pack(anchor="w")

        titulo("5) Acciones")
        boton("🔄  Generar vista previa", self.actualizar_preview,
              color="#89b4fa").pack(pady=3)
        boton("💾  Exportar a .webp", self.exportar, color="#a6e3a1").pack(pady=3)

        # Etiqueta de estado en la parte inferior del panel.
        self.lbl_estado = tk.Label(panel, text="Listo.", bg="#1e1e2e",
                                    fg="#f9e2af", font=("Helvetica", 9),
                                    wraplength=220, justify="left")
        self.lbl_estado.pack(anchor="w", pady=(12, 0))

        # ---- Columna derecha: VISTA PREVIA (canvas) -----------------------
        marco_prev = tk.Frame(contenedor, bg="#11111b", bd=2, relief="groove")
        marco_prev.grid(row=0, column=1, sticky="n")
        self.canvas = tk.Canvas(marco_prev, width=self.PREVIEW_MAX,
                                height=self.PREVIEW_MAX, bg="#11111b",
                                highlightthickness=0)
        self.canvas.pack()
        # Eventos de ratón para dibujar el rectángulo del marco.
        self.canvas.bind("<Button-1>", self._raton_pulsar)
        self.canvas.bind("<B1-Motion>", self._raton_arrastrar)
        self.canvas.bind("<ButtonRelease-1>", self._raton_soltar)

    def _campo_coordenada(self, parent, etiqueta, variable, fila, col):
        """Crea una etiqueta + campo de entrada numérico para una coordenada."""
        tk.Label(parent, text=etiqueta, bg="#1e1e2e", fg="white",
                 font=("Helvetica", 10)).grid(row=fila, column=col,
                                              sticky="e", padx=(0, 2), pady=2)
        e = tk.Entry(parent, textvariable=variable, width=7, bg="#313244",
                     fg="white", insertbackground="white", relief="flat")
        e.grid(row=fila, column=col + 1, padx=(0, 10), pady=2)
        # Al terminar de escribir, refrescamos el rectángulo de la vista previa.
        e.bind("<FocusOut>", lambda _e: self._dibujar_rectangulo_guia())
        e.bind("<Return>", lambda _e: self._dibujar_rectangulo_guia())

    # -------------------------------------------------------------- CARGA
    def _cargar_base_por_defecto(self):
        """Si existe 'imagen.jpg' junto al script, la carga automáticamente."""
        if os.path.exists(IMAGEN_BASE):
            try:
                self.img_base = Image.open(IMAGEN_BASE).convert("RGBA")
                self._mostrar_en_canvas(self.img_base)
                self._estado(f"Imagen base cargada: {IMAGEN_BASE}")
            except Exception as err:  # noqa: BLE001
                self._estado(f"No se pudo abrir {IMAGEN_BASE}: {err}")
        else:
            self._estado(f"No se encontró '{IMAGEN_BASE}'. Cárgala con el botón.")

    def cargar_base(self):
        """Botón: elegir la imagen de fondo desde el disco."""
        ruta = filedialog.askopenfilename(
            title="Selecciona la imagen base (fondo)",
            filetypes=[("Imágenes", "*.jpg *.jpeg *.png *.webp *.bmp")])
        if not ruta:
            return
        self.img_base = Image.open(ruta).convert("RGBA")
        self._mostrar_en_canvas(self.img_base)
        self._estado(f"Base cargada: {os.path.basename(ruta)}")

    def cargar_poster(self):
        """Botón: elegir la imagen del diseño del póster desde el disco."""
        ruta = filedialog.askopenfilename(
            title="Selecciona el diseño del póster",
            filetypes=[("Imágenes", "*.jpg *.jpeg *.png *.webp *.bmp")])
        if not ruta:
            return
        self.img_poster = Image.open(ruta)
        self._estado(f"Póster cargado: {os.path.basename(ruta)}")
        self.actualizar_preview()

    # --------------------------------------------------------- PROCESADO
    def actualizar_preview(self):
        """Genera la composición con las coordenadas actuales y la muestra."""
        if self.img_base is None:
            messagebox.showwarning("Falta la base",
                                   "Primero carga la imagen base (fondo).")
            return
        if self.img_poster is None:
            # Sin póster todavía: mostramos solo la base con la guía del marco.
            self._mostrar_en_canvas(self.img_base)
            self._dibujar_rectangulo_guia()
            self._estado("Carga un póster para ver la composición.")
            return
        try:
            self.img_resultado = generar_mockup(
                self.img_base, self.img_poster,
                self.var_x.get(), self.var_y.get(),
                self.var_w.get(), self.var_h.get(),
                modo=self.var_modo.get())
            # La vista previa muestra el resultado ya cuadrado (1:1).
            self._mostrar_en_canvas(self.img_resultado, dibujar_guia=False)
            self._estado("Vista previa generada (resultado 1:1). "
                         "Ajusta coordenadas si hace falta.")
        except Exception as err:  # noqa: BLE001
            messagebox.showerror("Error al generar", str(err))
            self._estado(f"Error: {err}")

    def exportar(self):
        """Genera la composición final y la guarda como .webp."""
        if self.img_base is None or self.img_poster is None:
            messagebox.showwarning(
                "Faltan imágenes",
                "Necesitas cargar la imagen base y el diseño del póster.")
            return
        # Regeneramos con los valores actuales para exportar lo más reciente.
        self.img_resultado = generar_mockup(
            self.img_base, self.img_poster,
            self.var_x.get(), self.var_y.get(),
            self.var_w.get(), self.var_h.get(),
            modo=self.var_modo.get())
        ruta = filedialog.asksaveasfilename(
            title="Guardar mockup como...",
            defaultextension=".webp",
            initialfile=NOMBRE_SALIDA,
            filetypes=[("Imagen WEBP", "*.webp")])
        if not ruta:
            return
        exportar_webp(self.img_resultado, ruta, self.var_calidad.get())
        self._estado(f"✅ Exportado: {ruta}")
        messagebox.showinfo("Exportación completa",
                            f"Mockup guardado en:\n{ruta}")

    # ------------------------------------------------------- VISTA PREVIA
    def _mostrar_en_canvas(self, imagen_pil, dibujar_guia=True):
        """
        Escala 'imagen_pil' para que quepa en el canvas manteniendo su
        proporción, la dibuja y (opcionalmente) pinta la guía del marco.
        Guarda la escala para poder convertir clics de ratón a px reales.
        """
        ancho, alto = imagen_pil.size
        # Factor para que la imagen quepa en PREVIEW_MAX x PREVIEW_MAX.
        self.escala_preview = min(self.PREVIEW_MAX / ancho,
                                  self.PREVIEW_MAX / alto)
        nuevo = (max(1, round(ancho * self.escala_preview)),
                 max(1, round(alto * self.escala_preview)))
        vista = imagen_pil.convert("RGBA").resize(nuevo, Image.LANCZOS)
        self.preview_tk = ImageTk.PhotoImage(vista)

        self.canvas.delete("all")
        # Centramos la imagen dentro del canvas.
        self._offset_x = (self.PREVIEW_MAX - nuevo[0]) // 2
        self._offset_y = (self.PREVIEW_MAX - nuevo[1]) // 2
        self.canvas.create_image(self._offset_x, self._offset_y,
                                 anchor="nw", image=self.preview_tk)
        self._rect_id = None
        if dibujar_guia:
            self._dibujar_rectangulo_guia()

    def _dibujar_rectangulo_guia(self):
        """Dibuja el rectángulo (guía) del marco sobre la vista previa."""
        if self.img_base is None or self.img_resultado is not None:
            # Solo tiene sentido sobre la base sin resultado compuesto.
            pass
        if self.preview_tk is None:
            return
        # Convertimos coordenadas reales -> coordenadas del canvas.
        x = self._offset_x + self.var_x.get() * self.escala_preview
        y = self._offset_y + self.var_y.get() * self.escala_preview
        w = self.var_w.get() * self.escala_preview
        h = self.var_h.get() * self.escala_preview
        if self._rect_id is not None:
            self.canvas.delete(self._rect_id)
        self._rect_id = self.canvas.create_rectangle(
            x, y, x + w, y + h, outline="#f38ba8", width=2, dash=(5, 3))

    # ------------------------------------------------- DIBUJAR CON EL RATÓN
    def _raton_pulsar(self, evento):
        """Guarda el punto inicial al empezar a arrastrar el marco."""
        if self.img_base is None:
            return
        # Al empezar a dibujar, salimos del modo "resultado" para ver la base.
        if self.img_resultado is not None:
            self.img_resultado = None
            self._mostrar_en_canvas(self.img_base, dibujar_guia=False)
        self._drag_inicio = (evento.x, evento.y)

    def _raton_arrastrar(self, evento):
        """Redibuja el rectángulo mientras se arrastra el ratón."""
        if self._drag_inicio is None:
            return
        x0, y0 = self._drag_inicio
        if self._rect_id is not None:
            self.canvas.delete(self._rect_id)
        self._rect_id = self.canvas.create_rectangle(
            x0, y0, evento.x, evento.y, outline="#f38ba8", width=2, dash=(5, 3))

    def _raton_soltar(self, evento):
        """Al soltar, convierte el rectángulo a px reales y actualiza campos."""
        if self._drag_inicio is None:
            return
        x0, y0 = self._drag_inicio
        x1, y1 = evento.x, evento.y
        self._drag_inicio = None
        # Normalizamos por si se arrastró de derecha a izquierda / abajo-arriba.
        cx0, cx1 = sorted((x0, x1))
        cy0, cy1 = sorted((y0, y1))
        # Convertimos de coordenadas de canvas a píxeles reales de la imagen.
        rx = round((cx0 - self._offset_x) / self.escala_preview)
        ry = round((cy0 - self._offset_y) / self.escala_preview)
        rw = round((cx1 - cx0) / self.escala_preview)
        rh = round((cy1 - cy0) / self.escala_preview)
        if rw < 5 or rh < 5:
            return  # Movimiento demasiado pequeño: lo ignoramos.
        # Actualizamos los campos numéricos con lo dibujado.
        self.var_x.set(max(0, rx))
        self.var_y.set(max(0, ry))
        self.var_w.set(rw)
        self.var_h.set(rh)
        self._estado(f"Marco definido: X={rx}, Y={ry}, {rw}x{rh}px")
        # Si ya hay póster, regeneramos la composición al instante.
        if self.img_poster is not None:
            self.actualizar_preview()

    # -------------------------------------------------------------- UTILES
    def _estado(self, texto):
        """Actualiza la etiqueta de estado inferior."""
        self.lbl_estado.config(text=texto)


# ===========================================================================
#  PUNTO DE ENTRADA
# ===========================================================================
if __name__ == "__main__":
    # Lanzamos la ventana de la aplicación.
    app = AppMockup()
    app.mainloop()
