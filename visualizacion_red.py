"""Visualización de la red de Petri de incidentes TI (parte de Kevin).

Guardar junto a estructura_red.py y motor_petri.py. Ejecutar:
    python visualizacion_red.py

Usa Tkinter y la biblioteca estándar de Python. La lógica de fichas pertenece
al MotorPetri del equipo: este módulo consulta sus datos y dibuja el resultado.

Integración en otra ventana:
    vista = VisualizacionRed(raiz, red, motor)
    vista.pack(fill="both", expand=True)
    # Si otro componente modifica la red, llamar después a vista.actualizar().
"""

import math
import tkinter as tk


# Coordenadas de presentación. Los nombres, arcos y fichas se leen de la red.
POSICIONES = {
    "P8": (110, 120), "P2": (480, 120),
    "T0": (110, 320), "P1": (295, 320), "T1": (480, 320),
    "P3": (675, 320), "T2": (870, 320), "P6": (1250, 320),
    "T3": (675, 530), "P4": (870, 530), "T4": (1060, 530),
    "P7": (1250, 530), "P5": (1060, 720), "T5": (1250, 720),
}

# Puntos intermedios de los arcos de retorno para separar los recorridos.
RUTAS = {
    ("T1", "P8"): [(410, 260), (410, 220), (190, 220), (190, 120)],
    ("T2", "P2"): [(870, 40), (480, 40)],
    ("T3", "P2"): [(575, 530), (575, 120)],
    ("T5", "P6"): [(1400, 720), (1400, 320)],
}

# Etiquetas desplazadas cuando hay una flecha vertical junto al nodo.
ETIQUETAS = {
    "P8": (235, 80), "P2": (620, 80), "P3": (675, 225),
    "P7": (1250, 435), "P5": (895, 720), "T4": (1060, 465),
}

COLORES = {
    "fondo": "#f3f6fa", "papel": "#ffffff", "texto": "#17283c",
    "suave": "#5d6e83", "borde": "#d5deea", "arco": "#71849c",
    "incidente": "#087f8c", "incidente_fondo": "#e6f5f5",
    "recurso": "#7252a2", "recurso_fondo": "#f1ecf9",
    "habilitada": "#087f66", "bloqueada": "#e7edf3",
    "ejecutada": "#f3ae32", "cambio": "#fff3d5",
}


class VisualizacionRed(tk.Frame):
    """Vista de los ocho lugares y seis transiciones del modelo del equipo."""

    def __init__(self, master, red, motor):
        super().__init__(master, bg=COLORES["fondo"])
        if motor.red is not red:
            raise ValueError("La vista y el motor deben compartir la misma red.")
        identificadores = set(red.lugares) | set(red.transiciones)
        if identificadores != set(POSICIONES):
            raise ValueError("Este diseño requiere los lugares P1–P8 y T0–T5.")
        self.red = red
        self.motor = motor
        self._ultima = None
        self._cambiados = set()
        self._temporizador = None
        self._ancho = 1440
        self._alto = 830
        self.botones = {}
        self.contadores = {}
        self.mensaje = tk.StringVar(master=self, value="Registra un incidente con T0 para comenzar.")
        self._crear_interfaz()
        self.actualizar()
        self.bind("<Destroy>", self._al_destruir, add="+")

    def _crear_interfaz(self):
        cabecera = tk.Frame(self, bg=COLORES["texto"], padx=22, pady=14)
        cabecera.pack(fill="x")
        tk.Label(cabecera, text="Gestión de incidentes TI", bg=COLORES["texto"],
                 fg="white", font=("Segoe UI", -24, "bold")).pack(anchor="w")
        tk.Label(cabecera, text="Red de Petri P/T · Soporte en una planta industrial",
                 bg=COLORES["texto"], fg="#c0d1e3",
                 font=("Segoe UI", -13)).pack(anchor="w", pady=(3, 0))

        metricas = tk.Frame(self, bg=COLORES["fondo"], padx=18, pady=10)
        metricas.pack(fill="x")
        titulos = ("En cola", "Técnicos N1 libres", "Especialista libre",
                   "Resueltos", "Transiciones ejecutadas")
        for columna, titulo in enumerate(titulos):
            metricas.columnconfigure(columna, weight=1, uniform="metricas")
            bloque = tk.Frame(metricas, bg=COLORES["papel"], padx=12, pady=8)
            bloque.grid(row=0, column=columna, sticky="nsew", padx=4)
            tk.Label(bloque, text=titulo, bg=COLORES["papel"], fg=COLORES["suave"],
                     font=("Segoe UI", -12)).pack(anchor="w")
            valor = tk.StringVar(master=self)
            self.contadores[titulo] = valor
            tk.Label(bloque, textvariable=valor, bg=COLORES["papel"],
                     fg=COLORES["texto"], font=("Segoe UI", -21, "bold")).pack(anchor="w")

        controles = tk.Frame(self, bg=COLORES["fondo"], padx=18)
        controles.pack(fill="x", pady=(0, 8))
        for indice, transicion in enumerate(self.red.transiciones.values()):
            columna = indice % 3
            controles.columnconfigure(columna, weight=1, uniform="controles")
            boton = tk.Button(
                controles, text=f"{transicion.id}  ·  {transicion.nombre}",
                command=lambda id_t=transicion.id: self.ejecutar_transicion(id_t),
                font=("Segoe UI", -13, "bold"), relief="flat", borderwidth=0,
                padx=8, pady=8, cursor="hand2", takefocus=True,
            )
            boton.grid(row=indice // 3, column=columna, sticky="ew", padx=4, pady=3)
            self.botones[transicion.id] = boton

        barra = tk.Frame(self, bg=COLORES["fondo"], padx=22)
        barra.pack(fill="x", pady=(0, 5))
        for etiqueta, color in (("● Incidente", "incidente"),
                                ("● Recurso disponible", "recurso")):
            tk.Label(barra, text=etiqueta, bg=COLORES["fondo"], fg=COLORES[color],
                     font=("Segoe UI", -12)).pack(side="left", padx=(0, 12))
        tk.Label(barra, text="Verde: habilitada   ·   Gris: bloqueada   ·   Ámbar: ejecutada",
                 bg=COLORES["fondo"], fg=COLORES["suave"],
                 font=("Segoe UI", -12)).pack(side="left", padx=20)
        tk.Button(barra, text="Reiniciar", command=self.reiniciar,
                  bg=COLORES["papel"], fg=COLORES["texto"], relief="solid",
                  bd=1, padx=14, pady=4, cursor="hand2",
                  font=("Segoe UI", -12)).pack(side="right")

        self.canvas = tk.Canvas(self, background=COLORES["papel"],
                                highlightthickness=1, highlightbackground=COLORES["borde"],
                                width=1440, height=830)
        self.canvas.pack(fill="both", expand=True, padx=22)
        self.canvas.bind("<Configure>", self._al_redimensionar)
        self.canvas.bind("<Motion>", self._cursor_sobre_red)

        pie = tk.Frame(self, bg=COLORES["fondo"], padx=22, pady=9)
        pie.pack(fill="x", side="bottom", before=self.canvas)
        self.estado = tk.Label(pie, textvariable=self.mensaje, bg=COLORES["fondo"],
                               fg=COLORES["texto"], font=("Segoe UI", -12),
                               anchor="w", justify="left", wraplength=980)
        self.estado.pack(fill="x")
        pie.bind("<Configure>", lambda e: self.estado.configure(wraplength=max(200, e.width - 44)))

    def actualizar(self):
        """Refresca fichas y habilitación; también se puede llamar desde otro módulo."""
        marcado = self.motor.obtener_marcado()
        for titulo, id_lugar in (("En cola", "P1"), ("Técnicos N1 libres", "P2"),
                                ("Especialista libre", "P5"), ("Resueltos", "P6")):
            self.contadores[titulo].set(str(marcado[id_lugar]))
        self.contadores["Transiciones ejecutadas"].set(str(self.motor.pasos))
        habilitadas = set(self.motor.transiciones_habilitadas())
        for id_t, boton in self.botones.items():
            disponible = id_t in habilitadas
            boton.configure(state="normal" if disponible else "disabled",
                            bg=COLORES["habilitada"] if disponible else COLORES["bloqueada"],
                            fg="white" if disponible else COLORES["suave"],
                            disabledforeground=COLORES["suave"],
                            activebackground="#06644f", activeforeground="white")
        self._dibujar()

    def ejecutar_transicion(self, id_transicion):
        """Pide el disparo al motor y representa el nuevo marcado sin editar tokens."""
        antes = self.motor.obtener_marcado()
        if not self.motor.disparar(id_transicion):
            faltantes = []
            # Agrupar entradas permite explicar también arcos paralelos.
            requeridos = {}
            for id_lugar, peso in self.red.entradas(id_transicion):
                requeridos[id_lugar] = requeridos.get(id_lugar, 0) + peso
            for id_lugar, cantidad in requeridos.items():
                if antes[id_lugar] < cantidad:
                    faltantes.append(self.red.lugares[id_lugar].nombre)
            self.mensaje.set(f"{id_transicion} bloqueada. Faltan fichas en: "
                             + ", ".join(faltantes) + ".")
            self.actualizar()
            return False
        despues = self.motor.obtener_marcado()
        self._cancelar_resaltado()
        self._ultima = id_transicion
        self._cambiados = {id_l for id_l in despues if antes[id_l] != despues[id_l]}
        cambios = "; ".join(f"{id_l}: {antes[id_l]} → {despues[id_l]}"
                            for id_l in self.red.lugares if id_l in self._cambiados)
        nombre = self.red.transiciones[id_transicion].nombre
        self.mensaje.set(f"Paso {self.motor.pasos} · {id_transicion}: {nombre}. {cambios}")
        self.actualizar()
        self._temporizador = self.after(650, self._quitar_resaltado)
        return True

    def reiniciar(self):
        self._cancelar_resaltado()
        self._ultima = None
        self._cambiados.clear()
        self.motor.reiniciar()
        self.mensaje.set("Simulación reiniciada. Registra un incidente con T0 para comenzar.")
        self.actualizar()

    def _cancelar_resaltado(self):
        if self._temporizador is not None:
            self.after_cancel(self._temporizador)
            self._temporizador = None

    def _quitar_resaltado(self):
        self._temporizador = None
        self._ultima = None
        self._cambiados.clear()
        self._dibujar()

    def _al_destruir(self, evento):
        if evento.widget is self:
            self._cancelar_resaltado()

    def _al_redimensionar(self, evento):
        self._ancho, self._alto = evento.width, evento.height
        self._dibujar()

    def _cursor_sobre_red(self, _evento):
        tags = self.canvas.gettags("current")
        self.canvas.configure(cursor="hand2" if "transicion" in tags else "")

    def _dibujar(self):
        """Ajusta el plano a la ventana y dibuja primero arcos y después nodos."""
        self.canvas.delete("all")
        escala = min(self._ancho / 1440, self._alto / 830)
        margen_x = (self._ancho - 1440 * escala) / 2
        margen_y = (self._alto - 830 * escala) / 2

        def punto(x, y):
            return (margen_x + x * escala, margen_y + y * escala)

        def fuente(tamano, negrita=False):
            return ("Segoe UI", -max(9, round(tamano * escala)),
                    "bold" if negrita else "normal")

        habilitadas = set(self.motor.transiciones_habilitadas())
        for arco in self.red.arcos:
            ruta = [POSICIONES[arco.origen]]
            ruta += RUTAS.get((arco.origen, arco.destino), [])
            ruta += [POSICIONES[arco.destino]]
            ruta[0] = self._borde(arco.origen, ruta[1])
            ruta[-1] = self._borde(arco.destino, ruta[-2])
            coordenadas = [valor for xy in ruta for valor in punto(*xy)]
            activo = self._ultima in (arco.origen, arco.destino)
            color = COLORES["ejecutada"] if activo else COLORES["arco"]
            # Un borde blanco separa visualmente los arcos cuando se cruzan.
            self.canvas.create_line(*coordenadas, fill=COLORES["papel"],
                                    width=max(4, escala * 5), tags=("fondo_arco",))
            self.canvas.create_line(*coordenadas, fill=color, width=max(1.4, escala * 2),
                                    arrow="last", arrowshape=(10 * escala, 12 * escala, 5 * escala),
                                    tags=("arco",))
            if arco.peso != 1:
                x, y = ruta[0]
                x2, y2 = ruta[1]
                self.canvas.create_text(*punto((x + x2) / 2 + 10, (y + y2) / 2 - 12),
                                        text=str(arco.peso), fill=COLORES["texto"],
                                        font=fuente(14, True), tags=("peso",))

        for lugar in self.red.lugares.values():
            x, y = POSICIONES[lugar.id]
            recurso = lugar.es_recurso
            color = COLORES["recurso" if recurso else "incidente"]
            fondo = COLORES["recurso_fondo" if recurso else "incidente_fondo"]
            if lugar.id in self._cambiados:
                fondo = COLORES["cambio"]
            self.canvas.create_oval(*punto(x - 36, y - 36), *punto(x + 36, y + 36),
                                    fill=fondo, outline=color, width=2,
                                    tags=("lugar", lugar.id))
            pos_id = (1002, 720) if lugar.id == "P5" else (x, y - 55)
            self.canvas.create_text(*punto(*pos_id), text=lugar.id,
                                    fill=color, font=fuente(16, True), tags=("id_lugar",))
            pos_nombre = ETIQUETAS.get(lugar.id, (x, y + 59))
            self.canvas.create_text(*punto(*pos_nombre), text=lugar.nombre,
                                    fill=COLORES["texto"], font=fuente(14),
                                    width=155 * escala, justify="center", tags=("nombre_lugar",))
            self._dibujar_tokens(lugar, punto, fuente, color, escala)

        for transicion in self.red.transiciones.values():
            x, y = POSICIONES[transicion.id]
            habilitada = transicion.id in habilitadas
            ejecutada = transicion.id == self._ultima
            fondo = (COLORES["ejecutada"] if ejecutada else
                     COLORES["habilitada"] if habilitada else COLORES["bloqueada"])
            texto = COLORES["texto"] if ejecutada or not habilitada else "white"
            tag = f"transicion_{transicion.id}"
            self.canvas.create_rectangle(*punto(x - 47, y - 21), *punto(x + 47, y + 21),
                                         fill=fondo, outline=COLORES["borde"], width=1,
                                         tags=("transicion", tag))
            self.canvas.create_text(*punto(x, y), text=transicion.id, fill=texto,
                                    font=fuente(16, True), tags=("transicion", tag))
            pos_nombre = ETIQUETAS.get(transicion.id, (x, y + 53))
            self.canvas.create_text(*punto(*pos_nombre), text=transicion.nombre,
                                    fill=COLORES["texto"], width=150 * escala,
                                    font=fuente(14), justify="center", tags=("transicion", tag))
            self.canvas.tag_bind(tag, "<Button-1>",
                                 lambda _e, id_t=transicion.id: self.ejecutar_transicion(id_t))

    def _dibujar_tokens(self, lugar, punto, fuente, color, escala):
        x, y = POSICIONES[lugar.id]
        cantidad = lugar.tokens
        # Hasta cinco fichas se ven individualmente. Para cantidades mayores,
        # se muestra el número exacto para que no se amontonen los puntos.
        patrones = {
            0: [], 1: [(0, 0)], 2: [(-12, 0), (12, 0)],
            3: [(0, -12), (-12, 10), (12, 10)],
            4: [(-12, -12), (12, -12), (-12, 12), (12, 12)],
            5: [(-14, -14), (14, -14), (0, 0), (-14, 14), (14, 14)],
        }
        if cantidad in patrones:
            for dx, dy in patrones[cantidad]:
                self.canvas.create_oval(*punto(x + dx - 5, y + dy - 5),
                                        *punto(x + dx + 5, y + dy + 5),
                                        fill=color, outline="", tags=("token", lugar.id))
            if cantidad == 0:
                self.canvas.create_text(*punto(x, y), text="0", fill=COLORES["suave"],
                                        font=fuente(17), tags=("cantidad", lugar.id))
        else:
            self.canvas.create_text(*punto(x, y), text=str(cantidad), fill=color,
                                    font=fuente(23, True), tags=("cantidad", lugar.id))

    def _borde(self, id_nodo, hacia):
        """Recorta cada flecha en el borde del círculo o rectángulo."""
        x, y = POSICIONES[id_nodo]
        dx, dy = hacia[0] - x, hacia[1] - y
        if id_nodo in self.red.lugares:
            distancia = math.hypot(dx, dy)
            factor = 36 / distancia if distancia else 0
        else:
            factores = [47 / abs(dx)] if dx else []
            if dy:
                factores.append(21 / abs(dy))
            factor = min(factores) if factores else 0
        return x + dx * factor, y + dy * factor


def main():
    from estructura_red import crear_red_incidentes
    from motor_petri import MotorPetri

    red = crear_red_incidentes()
    motor = MotorPetri(red)
    raiz = tk.Tk()
    raiz.title("Red de Petri · Gestión de incidentes TI")
    ancho = min(1500, raiz.winfo_screenwidth() - 80)
    alto = min(1020, raiz.winfo_screenheight() - 100)
    raiz.geometry(f"{ancho}x{alto}")
    raiz.minsize(1040, 740)
    VisualizacionRed(raiz, red, motor).pack(fill="both", expand=True)
    raiz.mainloop()


if __name__ == "__main__":
    main()
