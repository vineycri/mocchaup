# -*- coding: utf-8 -*-
"""
============================================================================
 GENERADOR AUTOMÁTICO DE MOCKUPS DE PÓSTERS  (App de escritorio - Tkinter)
============================================================================

Ejercicio académico / proyecto de e-commerce.

¿Qué hace esta aplicación?
--------------------------
1. Carga VARIAS imágenes de ENTORNO (paredes con marcos vacíos) que sirven
   de fondo/mockup. Acepta JPG, PNG, WEBP, BMP, TIFF y **AVIF** de entrada.
2. Recibe una imagen secundaria: el DISEÑO del póster (uno, común a todos).
3. Para cada mockup, redimensiona y superpone el diseño sobre el marco.
   El marco se define por RECTÁNGULO (X, Y, ancho, alto) o por PERSPECTIVA
   (4 esquinas), para marcos en ángulo.
4. Recorta cada resultado desde el CENTRO a 1:1 (formato cuadrado).
5. Exporta TODOS a la vez en formato .webp con el prefijo "PROD_".

La aplicación es una ventana de escritorio (Tkinter): subes imágenes con
botones, defines el marco escribiendo coordenadas O con el ratón sobre la
vista previa, y exportas todo en lote.

Requisitos:
    pip install Pillow
    (opcional, para AVIF en versiones antiguas de Pillow: pip install pillow-avif-plugin)
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
from mockup_core import (
    IMAGEN_BASE, POS_X, POS_Y, ANCHO_MARCO, ALTO_MARCO,
    CALIDAD_WEBP, MODO_ENCAJE, EXTENSIONES_ENTRADA, PREFIJO_SALIDA,
    generar_mockup, exportar_webp, nombre_de_salida,
)


# ===========================================================================
#  INTERFAZ GRÁFICA DE ESCRITORIO (Tkinter)
# ===========================================================================

class AppMockup(tk.Tk):
    """Ventana principal de la aplicación."""

    PREVIEW_MAX = 560     # Tamaño máximo (px) de la vista previa.

    def __init__(self):
        super().__init__()
        self.title("Generador de Mockups de Pósters — Lote")
        self.configure(bg="#1e1e2e")
        self.resizable(False, False)

        # --- Estado interno -------------------------------------------------
        # Lista de mockups. Cada uno es un diccionario con su imagen y su
        # región (rectángulo o perspectiva). Ver _nuevo_mockup().
        self.mockups = []
        self.indice_actual = None     # Índice del mockup seleccionado.
        self.img_poster = None        # Diseño del póster (común a todos).

        # Estado de la vista previa.
        self.preview_tk = None
        self.escala_preview = 1.0
        self._offset_x = 0
        self._offset_y = 0
        self._drag_inicio = None
        self._mostrando_resultado = False

        # Variables enlazadas a los campos de la interfaz.
        self.var_tipo = tk.StringVar(value="rect")   # "rect" | "persp"
        self.var_x = tk.IntVar(value=POS_X)
        self.var_y = tk.IntVar(value=POS_Y)
        self.var_w = tk.IntVar(value=ANCHO_MARCO)
        self.var_h = tk.IntVar(value=ALTO_MARCO)
        self.var_modo = tk.StringVar(value=MODO_ENCAJE)
        self.var_calidad = tk.IntVar(value=CALIDAD_WEBP)

        self._construir_interfaz()
        self._cargar_base_por_defecto()

    # ------------------------------------------------------------------ GUI
    def _construir_interfaz(self):
        contenedor = tk.Frame(self, bg="#1e1e2e")
        contenedor.pack(padx=12, pady=12)

        panel = tk.Frame(contenedor, bg="#1e1e2e")
        panel.grid(row=0, column=0, sticky="n", padx=(0, 12))

        def titulo(txt):
            tk.Label(panel, text=txt, bg="#1e1e2e", fg="#89b4fa",
                     font=("Helvetica", 11, "bold")).pack(anchor="w", pady=(10, 2))

        def boton(txt, cmd, color="#585b70"):
            return tk.Button(panel, text=txt, command=cmd, bg=color, fg="white",
                             activebackground="#6c7086", relief="flat",
                             font=("Helvetica", 10), padx=8, pady=6, width=30)

        # ---- 1) Mockups (lista con carga múltiple) ------------------------
        titulo("1) Mockups (imágenes de fondo)")
        boton("📁  Añadir mockups (varios)…", self.anadir_mockups).pack(pady=3)

        marco_lista = tk.Frame(panel, bg="#1e1e2e")
        marco_lista.pack(anchor="w", fill="x")
        self.lista = tk.Listbox(marco_lista, height=5, width=34, bg="#313244",
                                fg="white", selectbackground="#89b4fa",
                                highlightthickness=0, relief="flat",
                                activestyle="none", exportselection=False)
        self.lista.pack(side="left", fill="x", expand=True)
        scroll = tk.Scrollbar(marco_lista, command=self.lista.yview)
        scroll.pack(side="right", fill="y")
        self.lista.config(yscrollcommand=scroll.set)
        self.lista.bind("<<ListboxSelect>>", self._al_seleccionar_mockup)
        tk.Button(panel, text="🗑️  Quitar seleccionado", command=self.quitar_mockup,
                  bg="#45475a", fg="white", relief="flat",
                  font=("Helvetica", 9), width=30).pack(pady=(2, 0))

        # ---- 2) Póster ----------------------------------------------------
        titulo("2) Diseño del póster (común)")
        boton("🖼️  Cargar diseño del póster", self.cargar_poster).pack(pady=3)

        # ---- 3) Región del marco ------------------------------------------
        titulo("3) Marco del mockup seleccionado")
        fila_tipo = tk.Frame(panel, bg="#1e1e2e")
        fila_tipo.pack(anchor="w")
        tk.Radiobutton(fila_tipo, text="Rectángulo", variable=self.var_tipo,
                       value="rect", command=self._cambiar_tipo, bg="#1e1e2e",
                       fg="white", selectcolor="#313244",
                       activebackground="#1e1e2e").pack(side="left")
        tk.Radiobutton(fila_tipo, text="Perspectiva (ángulo)",
                       variable=self.var_tipo, value="persp",
                       command=self._cambiar_tipo, bg="#1e1e2e", fg="white",
                       selectcolor="#313244",
                       activebackground="#1e1e2e").pack(side="left")

        # Campos de rectángulo.
        self.grid_rect = tk.Frame(panel, bg="#1e1e2e")
        self.grid_rect.pack(anchor="w")
        self._campo_coordenada(self.grid_rect, "X:", self.var_x, 0, 0)
        self._campo_coordenada(self.grid_rect, "Y:", self.var_y, 0, 2)
        self._campo_coordenada(self.grid_rect, "Ancho:", self.var_w, 1, 0)
        self._campo_coordenada(self.grid_rect, "Alto:", self.var_h, 1, 2)

        # Ayuda contextual (cambia según el tipo de región).
        self.lbl_ayuda = tk.Label(
            panel,
            text="Rectángulo: escribe X/Y/ancho/alto o arrastra el ratón\n"
                 "sobre la vista previa para dibujar el marco.",
            bg="#1e1e2e", fg="#a6adc8", font=("Helvetica", 8), justify="left")
        self.lbl_ayuda.pack(anchor="w", pady=(4, 0))

        # ---- 4) Encaje y calidad ------------------------------------------
        titulo("4) Encaje del póster")
        menu = tk.OptionMenu(panel, self.var_modo, "fill", "fit", "stretch",
                             command=lambda _v: self._guardar_region_actual())
        menu.configure(bg="#585b70", fg="white", relief="flat",
                       highlightthickness=0, width=28)
        menu.pack(anchor="w", pady=3)

        titulo("Calidad WEBP (0-100)")
        tk.Scale(panel, from_=10, to=100, orient="horizontal",
                 variable=self.var_calidad, bg="#1e1e2e", fg="white",
                 highlightthickness=0, troughcolor="#585b70",
                 length=240).pack(anchor="w")

        # ---- 5) Acciones --------------------------------------------------
        titulo("5) Acciones")
        boton("🔄  Vista previa del seleccionado", self.actualizar_preview,
              color="#89b4fa").pack(pady=3)
        boton(f"💾  Exportar TODOS ({PREFIJO_SALIDA}*.webp)", self.exportar_todos,
              color="#a6e3a1").pack(pady=3)

        self.lbl_estado = tk.Label(panel, text="Listo.", bg="#1e1e2e",
                                   fg="#f9e2af", font=("Helvetica", 9),
                                   wraplength=250, justify="left")
        self.lbl_estado.pack(anchor="w", pady=(12, 0))

        # ---- Vista previa (canvas) ----------------------------------------
        marco_prev = tk.Frame(contenedor, bg="#11111b", bd=2, relief="groove")
        marco_prev.grid(row=0, column=1, sticky="n")
        self.canvas = tk.Canvas(marco_prev, width=self.PREVIEW_MAX,
                                height=self.PREVIEW_MAX, bg="#11111b",
                                highlightthickness=0)
        self.canvas.pack()
        self.canvas.bind("<Button-1>", self._raton_pulsar)
        self.canvas.bind("<B1-Motion>", self._raton_arrastrar)
        self.canvas.bind("<ButtonRelease-1>", self._raton_soltar)

    def _campo_coordenada(self, parent, etiqueta, variable, fila, col):
        tk.Label(parent, text=etiqueta, bg="#1e1e2e", fg="white",
                 font=("Helvetica", 10)).grid(row=fila, column=col,
                                              sticky="e", padx=(0, 2), pady=2)
        e = tk.Entry(parent, textvariable=variable, width=7, bg="#313244",
                     fg="white", insertbackground="white", relief="flat")
        e.grid(row=fila, column=col + 1, padx=(0, 10), pady=2)
        e.bind("<FocusOut>", lambda _e: self._al_editar_campos())
        e.bind("<Return>", lambda _e: self._al_editar_campos())

    # ---------------------------------------------------- MODELO DE MOCKUP
    @staticmethod
    def _nuevo_mockup(ruta, imagen):
        """Crea la estructura de datos de un mockup con región por defecto."""
        w, h = imagen.size
        # Esquinas por defecto para perspectiva: un rectángulo centrado.
        ex0, ey0 = POS_X, POS_Y
        return {
            "ruta": ruta,
            "nombre": os.path.basename(ruta),
            "imagen": imagen,                 # PIL RGBA
            "tipo": "rect",                   # "rect" | "persp"
            "x": POS_X, "y": POS_Y,
            "w": ANCHO_MARCO, "h": ALTO_MARCO,
            # Esquinas (sup-izq, sup-der, inf-der, inf-izq) para perspectiva.
            "esquinas": [(ex0, ey0), (ex0 + ANCHO_MARCO, ey0),
                         (ex0 + ANCHO_MARCO, ey0 + ALTO_MARCO),
                         (ex0, ey0 + ALTO_MARCO)],
            "modo": MODO_ENCAJE,
        }

    def _mockup_actual(self):
        if self.indice_actual is None:
            return None
        return self.mockups[self.indice_actual]

    def _region_de(self, mk):
        """Devuelve el dict de región que espera generar_mockup()."""
        if mk["tipo"] == "persp":
            return {"tipo": "persp", "esquinas": mk["esquinas"]}
        return {"tipo": "rect", "x": mk["x"], "y": mk["y"],
                "w": mk["w"], "h": mk["h"]}

    # ---------------------------------------------------------------- CARGA
    def _cargar_base_por_defecto(self):
        """Si existe 'imagen.jpg' junto al script, la añade como primer mockup."""
        if os.path.exists(IMAGEN_BASE):
            try:
                img = Image.open(IMAGEN_BASE).convert("RGBA")
                self.mockups.append(self._nuevo_mockup(IMAGEN_BASE, img))
                self._refrescar_lista(seleccion=0)
                self._estado(f"Mockup por defecto cargado: {IMAGEN_BASE}")
            except Exception as err:  # noqa: BLE001
                self._estado(f"No se pudo abrir {IMAGEN_BASE}: {err}")
        else:
            self._estado("Añade uno o varios mockups con el botón.")

    def anadir_mockups(self):
        """Botón: seleccionar VARIAS imágenes de fondo (multi-selección)."""
        rutas = filedialog.askopenfilenames(
            title="Selecciona una o varias imágenes de mockup",
            filetypes=[("Imágenes", " ".join(EXTENSIONES_ENTRADA)),
                       ("Todos", "*.*")])
        if not rutas:
            return
        errores = []
        primer_nuevo = len(self.mockups)
        for ruta in rutas:
            try:
                img = Image.open(ruta).convert("RGBA")
                self.mockups.append(self._nuevo_mockup(ruta, img))
            except Exception as err:  # noqa: BLE001
                errores.append(f"{os.path.basename(ruta)}: {err}")
        self._refrescar_lista(seleccion=primer_nuevo)
        msg = f"{len(rutas) - len(errores)} mockup(s) añadido(s)."
        if errores:
            msg += " Errores: " + " | ".join(errores)
            if "avif" in " ".join(errores).lower():
                msg += "  (¿AVIF? Instala 'pillow-avif-plugin'.)"
        self._estado(msg)

    def quitar_mockup(self):
        """Elimina el mockup seleccionado de la lista."""
        if self.indice_actual is None:
            return
        del self.mockups[self.indice_actual]
        nuevo = min(self.indice_actual, len(self.mockups) - 1)
        self._refrescar_lista(seleccion=nuevo if self.mockups else None)

    def cargar_poster(self):
        """Botón: elegir el diseño del póster (común a todos los mockups)."""
        ruta = filedialog.askopenfilename(
            title="Selecciona el diseño del póster",
            filetypes=[("Imágenes", " ".join(EXTENSIONES_ENTRADA)),
                       ("Todos", "*.*")])
        if not ruta:
            return
        try:
            self.img_poster = Image.open(ruta)
            self.img_poster.load()  # Fuerza la lectura (detecta AVIF ausente).
        except Exception as err:  # noqa: BLE001
            messagebox.showerror("No se pudo abrir el póster", str(err))
            return
        self._estado(f"Póster cargado: {os.path.basename(ruta)}")
        self.actualizar_preview()

    # ------------------------------------------------------- LISTA / SELECCIÓN
    def _refrescar_lista(self, seleccion=None):
        self.lista.delete(0, tk.END)
        for mk in self.mockups:
            etiqueta = "▱" if mk["tipo"] == "rect" else "◪"
            self.lista.insert(tk.END, f" {etiqueta}  {mk['nombre']}")
        if seleccion is not None and 0 <= seleccion < len(self.mockups):
            self.lista.selection_clear(0, tk.END)
            self.lista.selection_set(seleccion)
            self.indice_actual = seleccion
            self._cargar_region_en_controles()
            self._render_mockup()
        elif not self.mockups:
            self.indice_actual = None
            self.canvas.delete("all")

    def _al_seleccionar_mockup(self, _evento=None):
        sel = self.lista.curselection()
        if not sel:
            return
        self.indice_actual = sel[0]
        self._cargar_region_en_controles()
        self._render_mockup()

    def _cargar_region_en_controles(self):
        """Vuelca la región del mockup seleccionado en los controles."""
        mk = self._mockup_actual()
        if mk is None:
            return
        self.var_tipo.set(mk["tipo"])
        self.var_x.set(mk["x"]); self.var_y.set(mk["y"])
        self.var_w.set(mk["w"]); self.var_h.set(mk["h"])
        self.var_modo.set(mk["modo"])
        self._actualizar_visibilidad_campos()

    def _guardar_region_actual(self):
        """Guarda en el mockup lo que hay en los controles."""
        mk = self._mockup_actual()
        if mk is None:
            return
        mk["tipo"] = self.var_tipo.get()
        mk["x"], mk["y"] = self.var_x.get(), self.var_y.get()
        mk["w"], mk["h"] = self.var_w.get(), self.var_h.get()
        mk["modo"] = self.var_modo.get()

    # ------------------------------------------------------- TIPO DE REGIÓN
    def _cambiar_tipo(self):
        self._guardar_region_actual()
        self._actualizar_visibilidad_campos()
        self._render_mockup()

    def _actualizar_visibilidad_campos(self):
        """Muestra los campos X/Y/W/H solo en modo rectángulo."""
        if self.var_tipo.get() == "rect":
            for hijo in self.grid_rect.winfo_children():
                hijo.configure(state="normal")
            self.lbl_ayuda.config(
                text="Rectángulo: escribe X/Y/ancho/alto o arrastra el ratón\n"
                     "sobre la vista previa para dibujar el marco.")
        else:
            for hijo in self.grid_rect.winfo_children():
                hijo.configure(state="disabled")
            self.lbl_ayuda.config(
                text="Perspectiva: haz CLIC en las 4 esquinas del marco en\n"
                     "este orden → sup-izq, sup-der, inf-der, inf-izq.")

    def _al_editar_campos(self):
        self._guardar_region_actual()
        self._render_mockup()

    # ---------------------------------------------------------- PROCESADO
    def actualizar_preview(self):
        """Genera la composición del mockup seleccionado y la muestra 1:1."""
        mk = self._mockup_actual()
        if mk is None:
            messagebox.showwarning("Sin mockups", "Añade al menos un mockup.")
            return
        if self.img_poster is None:
            self._estado("Carga un póster para ver la composición.")
            self._render_mockup()
            return
        self._guardar_region_actual()
        try:
            resultado = generar_mockup(mk["imagen"], self.img_poster,
                                       self._region_de(mk), mk["modo"])
            self._mostrar_en_canvas(resultado)
            self._mostrando_resultado = True
            self._estado("Vista previa 1:1 generada. Ajusta si hace falta.")
        except Exception as err:  # noqa: BLE001
            messagebox.showerror("Error al generar", str(err))
            self._estado(f"Error: {err}")

    def exportar_todos(self):
        """Genera y exporta TODOS los mockups a la vez con prefijo PROD_."""
        if not self.mockups:
            messagebox.showwarning("Sin mockups", "Añade al menos un mockup.")
            return
        if self.img_poster is None:
            messagebox.showwarning("Falta el póster",
                                   "Carga el diseño del póster primero.")
            return
        self._guardar_region_actual()
        carpeta = filedialog.askdirectory(
            title="Carpeta donde guardar los PROD_*.webp")
        if not carpeta:
            return
        exportados, errores = [], []
        for mk in self.mockups:
            try:
                resultado = generar_mockup(mk["imagen"], self.img_poster,
                                           self._region_de(mk), mk["modo"])
                salida = os.path.join(carpeta, nombre_de_salida(mk["ruta"]))
                exportar_webp(resultado, salida, self.var_calidad.get())
                exportados.append(os.path.basename(salida))
            except Exception as err:  # noqa: BLE001
                errores.append(f"{mk['nombre']}: {err}")
        resumen = f"✅ {len(exportados)} archivo(s) exportado(s) a:\n{carpeta}"
        if errores:
            resumen += "\n\n⚠️ Errores:\n" + "\n".join(errores)
        self._estado(f"Exportados {len(exportados)} en {carpeta}")
        messagebox.showinfo("Exportación en lote", resumen)

    # -------------------------------------------------------- VISTA PREVIA
    def _render_mockup(self):
        """Muestra el mockup seleccionado con su guía de marco (sin componer)."""
        mk = self._mockup_actual()
        if mk is None:
            return
        self._mostrando_resultado = False
        self._mostrar_en_canvas(mk["imagen"])
        self._dibujar_guia()

    def _mostrar_en_canvas(self, imagen_pil):
        """Escala la imagen para que quepa en el canvas y la dibuja."""
        ancho, alto = imagen_pil.size
        self.escala_preview = min(self.PREVIEW_MAX / ancho,
                                  self.PREVIEW_MAX / alto)
        nuevo = (max(1, round(ancho * self.escala_preview)),
                 max(1, round(alto * self.escala_preview)))
        vista = imagen_pil.convert("RGBA").resize(nuevo, Image.LANCZOS)
        self.preview_tk = ImageTk.PhotoImage(vista)
        self.canvas.delete("all")
        self._offset_x = (self.PREVIEW_MAX - nuevo[0]) // 2
        self._offset_y = (self.PREVIEW_MAX - nuevo[1]) // 2
        self.canvas.create_image(self._offset_x, self._offset_y,
                                 anchor="nw", image=self.preview_tk)

    def _r2c(self, x, y):
        """Convierte coordenadas REALES de imagen a coordenadas del canvas."""
        return (self._offset_x + x * self.escala_preview,
                self._offset_y + y * self.escala_preview)

    def _c2r(self, cx, cy):
        """Convierte coordenadas del canvas a píxeles REALES de la imagen."""
        return (round((cx - self._offset_x) / self.escala_preview),
                round((cy - self._offset_y) / self.escala_preview))

    def _dibujar_guia(self):
        """Dibuja la guía del marco (rectángulo o cuadrilátero) en la vista."""
        mk = self._mockup_actual()
        if mk is None or self.preview_tk is None or self._mostrando_resultado:
            return
        self.canvas.delete("guia")
        if mk["tipo"] == "rect":
            x0, y0 = self._r2c(mk["x"], mk["y"])
            x1, y1 = self._r2c(mk["x"] + mk["w"], mk["y"] + mk["h"])
            self.canvas.create_rectangle(x0, y0, x1, y1, outline="#f38ba8",
                                         width=2, dash=(5, 3), tags="guia")
        else:
            pts = [self._r2c(px, py) for (px, py) in mk["esquinas"]]
            plano = [c for punto in pts for c in punto]
            self.canvas.create_polygon(plano, outline="#f38ba8", width=2,
                                       fill="", tags="guia")
            for i, (cx, cy) in enumerate(pts):
                self.canvas.create_oval(cx - 5, cy - 5, cx + 5, cy + 5,
                                        fill="#f38ba8", outline="white",
                                        tags="guia")
                self.canvas.create_text(cx, cy - 12, text=str(i + 1),
                                        fill="white", tags="guia")

    # ------------------------------------------------- INTERACCIÓN CON RATÓN
    def _raton_pulsar(self, evento):
        mk = self._mockup_actual()
        if mk is None:
            return
        # Si estábamos mostrando el resultado, volvemos al mockup para editar.
        if self._mostrando_resultado:
            self._render_mockup()
        if mk["tipo"] == "rect":
            self._drag_inicio = (evento.x, evento.y)
        else:
            # Perspectiva: cada clic fija una esquina (1..4, luego reinicia).
            self._colocar_esquina(evento.x, evento.y)

    def _raton_arrastrar(self, evento):
        mk = self._mockup_actual()
        if mk is None or mk["tipo"] != "rect" or self._drag_inicio is None:
            return
        x0, y0 = self._drag_inicio
        self.canvas.delete("temp")
        self.canvas.create_rectangle(x0, y0, evento.x, evento.y,
                                     outline="#f38ba8", width=2, dash=(5, 3),
                                     tags="temp")

    def _raton_soltar(self, evento):
        mk = self._mockup_actual()
        if mk is None or mk["tipo"] != "rect" or self._drag_inicio is None:
            return
        x0, y0 = self._drag_inicio
        self._drag_inicio = None
        self.canvas.delete("temp")
        cx0, cx1 = sorted((x0, evento.x))
        cy0, cy1 = sorted((y0, evento.y))
        rx, ry = self._c2r(cx0, cy0)
        rw = round((cx1 - cx0) / self.escala_preview)
        rh = round((cy1 - cy0) / self.escala_preview)
        if rw < 5 or rh < 5:
            self._dibujar_guia()
            return
        self.var_x.set(max(0, rx)); self.var_y.set(max(0, ry))
        self.var_w.set(rw); self.var_h.set(rh)
        self._guardar_region_actual()
        self._dibujar_guia()
        self._estado(f"Marco: X={max(0, rx)}, Y={max(0, ry)}, {rw}x{rh}px")

    def _colocar_esquina(self, cx, cy):
        """Registra una esquina en modo perspectiva (ciclo de 4 clics)."""
        mk = self._mockup_actual()
        # Contador de clics de perspectiva por mockup.
        pendientes = mk.setdefault("_persp_clics", 0)
        if pendientes == 0:
            mk["esquinas"] = [None, None, None, None]
        rx, ry = self._c2r(cx, cy)
        mk["esquinas"][pendientes] = (max(0, rx), max(0, ry))
        pendientes += 1
        mk["_persp_clics"] = pendientes % 4
        # Dibujamos progresivamente los puntos ya colocados.
        self.canvas.delete("guia")
        for i in range(pendientes):
            px, py = mk["esquinas"][i]
            ccx, ccy = self._r2c(px, py)
            self.canvas.create_oval(ccx - 5, ccy - 5, ccx + 5, ccy + 5,
                                    fill="#f38ba8", outline="white", tags="guia")
            self.canvas.create_text(ccx, ccy - 12, text=str(i + 1),
                                    fill="white", tags="guia")
        etiquetas = ["sup-izq", "sup-der", "inf-der", "inf-izq"]
        if pendientes < 4:
            self._estado(f"Marca la esquina {pendientes + 1}: {etiquetas[pendientes]}")
        else:
            self._dibujar_guia()
            self._estado("4 esquinas definidas. Genera la vista previa.")
            if self.img_poster is not None:
                self.actualizar_preview()

    # -------------------------------------------------------------- UTILES
    def _estado(self, texto):
        self.lbl_estado.config(text=texto)


# ===========================================================================
#  PUNTO DE ENTRADA
# ===========================================================================
if __name__ == "__main__":
    app = AppMockup()
    app.mainloop()
