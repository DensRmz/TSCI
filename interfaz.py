"""Módulo: Interfaz grafica

Ventana principal del sistema de gestión de incidentes de soporte técnico
modelado con una red de Petri básica (P/T).

Este módulo NO define la red ni la lógica de disparo; usa los módulos
del equipo:
    estructura_red.py     -> crear_red_incidentes()   (lugares, transiciones, arcos)
    motor_petri.py        -> MotorPetri               (habilitación y disparo)
    visualizacion_red.py  -> VisualizacionRed         (dibujo, botones y contadores)

Qué agrega la interfaz a la visualización de la red:
    - Panel "Configuración inicial": capacidad de la cola, técnicos N1 y
      especialistas N2; al aplicar se crea de nuevo la red con esos valores
      usando crear_red_incidentes() (para probar distintos escenarios).
    - Panel "Recursos": ocupación de los técnicos N1, del especialista N2
      y de la cola de espera.
    - Panel "Estado de los incidentes": cuántos incidentes hay en cada
      lugar de la red y cuántos se han registrado.

Los paneles se actualizan cada vez que se ejecuta una transición o se
reinicia la simulación desde la visualización. Los lugares se leen de la
red, así que si se agrega una transición en estructura_red.py (por ejemplo
T6 Reabrir incidente) los paneles siguen funcionando sin modificar este archivo.

Ejecutar (con los demás módulos en la misma carpeta):
    python interfaz.py
"""

import tkinter as tk

from estructura_red import crear_red_incidentes
from motor_petri import MotorPetri

try:
    from visualizacion_red import VisualizacionRed, COLORES as COLORES_VISTA
except ImportError:          # la interfaz abre aunque falte la visualización
    VisualizacionRed = None
    COLORES_VISTA = {}


COLORES = {
    "fondo": "#f3f6fa", "papel": "#ffffff", "texto": "#17283c",
    "suave": "#5d6e83", "borde": "#d5deea",
    "incidente": "#087f8c", "recurso": "#7252a2", "bloqueada": "#e7edf3",
}
COLORES.update(COLORES_VISTA)
COLORES.update({"ok": "#087f66", "error": "#c0392b", "alerta": "#f3ae32"})

FUENTE = "Segoe UI"
RECURSOS = (
    ("Técnicos N1", "P2", "P3", "ocupados"),
    ("Especialista N2", "P5", "P7", "ocupado(s)"),
    ("Cola de espera", "P8", "P1", "espacios usados"),
)


class InterfazPrincipal(tk.Frame):
    """Visualización de la red con los paneles de recursos y estado a un lado."""

    def __init__(self, master, capacidad_cola=5, tecnicos=2, especialistas=1):
        super().__init__(master, bg=COLORES["fondo"])
        self.config_red = {"capacidad_cola": capacidad_cola,
                           "tecnicos": tecnicos, "especialistas": especialistas}
        self.red = None
        self.motor = None
        self.vista = None
        self.barras = {}
        self.estados = {}
        self.contadores = {}
        self.var_config = {}
        self._crear_red()

    def _crear_red(self):
        """Crea la red con la configuración actual y arma de nuevo la ventana."""
        for hijo in self.winfo_children():
            hijo.destroy()
        self.barras.clear()
        self.estados.clear()
        self.contadores.clear()
        self.red = crear_red_incidentes(**self.config_red)
        self.motor = MotorPetri(self.red)
        self._crear_interfaz()
        self._refrescar_paneles()

    def aplicar_configuracion(self):
        """Lee los valores de la configuración y reinicia la simulación con ellos."""
        self.config_red = {clave: variable.get()
                           for clave, variable in self.var_config.items()}
        self._crear_red()
        if self.vista is not None:
            self.vista.mensaje.set(
                "Nueva configuración: cola de {capacidad_cola}, {tecnicos} técnico(s) N1 "
                "y {especialistas} especialista(s) N2. Registra un incidente con T0."
                .format(**self.config_red))

    # Construccion de la ventana
    def _crear_interfaz(self):
        self.vista = self._crear_vista()
        if self.vista is not None:
            ordenados = self.vista.pack_slaves()
            antes = ordenados[1] if len(ordenados) > 1 else self.vista.canvas
            contenedor = tk.Frame(self.vista, bg=COLORES["fondo"], width=300)
            contenedor.pack(side="right", fill="y", padx=(0, 16), pady=(10, 10),
                            before=antes)
            self.vista.canvas.configure(width=760, height=420)
            self.vista.pack(fill="both", expand=True)
        else:
            contenedor = tk.Frame(self, bg=COLORES["fondo"], width=300)
            contenedor.pack(side="right", fill="y", padx=12, pady=12)
        contenedor.pack_propagate(False)
        panel = self._panel_desplazable(contenedor)
        self._crear_configuracion(panel)
        self._crear_recursos(panel)
        self._crear_estado_incidentes(panel)

    def _panel_desplazable(self, contenedor):
        """Marco con barra de desplazamiento por si el panel no cabe en la pantalla."""
        lienzo = tk.Canvas(contenedor, bg=COLORES["fondo"], highlightthickness=0)
        barra = tk.Scrollbar(contenedor, orient="vertical", command=lienzo.yview)
        lienzo.configure(yscrollcommand=barra.set)
        lienzo.pack(side="left", fill="both", expand=True)
        panel = tk.Frame(lienzo, bg=COLORES["fondo"])
        ventana = lienzo.create_window(0, 0, window=panel, anchor="nw")

        def ajustar(_evento=None):
            lienzo.itemconfigure(ventana, width=lienzo.winfo_width())
            lienzo.configure(scrollregion=(0, 0, lienzo.winfo_width(),
                                           panel.winfo_reqheight()))
            # La barra solo aparece cuando el contenido no cabe.
            if panel.winfo_reqheight() > lienzo.winfo_height() + 1:
                if not barra.winfo_ismapped():
                    barra.pack(side="right", fill="y", before=lienzo)
            elif barra.winfo_ismapped():
                barra.pack_forget()
                lienzo.yview_moveto(0)

        def rueda(evento):
            if barra.winfo_ismapped():
                pasos = -1 if (evento.num == 4 or evento.delta > 0) else 1
                lienzo.yview_scroll(pasos, "units")

        lienzo.bind("<Configure>", ajustar)
        panel.bind("<Configure>", ajustar)
        for secuencia in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            contenedor.bind_all(secuencia, rueda, add="+")
        return panel

    def _crear_vista(self):
        if VisualizacionRed is None:
            self._aviso_vista("No se encontró visualizacion_red.py.")
            return None
        try:
            vista = VisualizacionRed(self, self.red, self.motor)
        except ValueError as error:
            self._aviso_vista(str(error))
            return None
        actualizar_vista = vista.actualizar

        def actualizar_todo():
            actualizar_vista()
            self._refrescar_paneles()
        vista.actualizar = actualizar_todo
        return vista

    def _aviso_vista(self, detalle):
        tk.Label(self, bg=COLORES["fondo"], fg=COLORES["suave"],
                 font=(FUENTE, -13), justify="center",
                 text="La visualización de la red no está disponible.\n" + detalle
                 ).pack(side="left", fill="both", expand=True)

    def _tarjeta(self, padre, titulo, **pack):
        """Bloque blanco con título, igual a los contadores de la visualización."""
        marco = tk.Frame(padre, bg=COLORES["papel"], padx=12, pady=8,
                         highlightthickness=1, highlightbackground=COLORES["borde"])
        marco.pack(**pack)
        tk.Label(marco, text=titulo, bg=COLORES["papel"], fg=COLORES["texto"],
                 font=(FUENTE, -14, "bold")).pack(anchor="w", pady=(0, 4))
        return marco

    def _crear_configuracion(self, padre):
        marco = self._tarjeta(padre, "Configuración inicial", fill="x")
        campos = tk.Frame(marco, bg=COLORES["papel"])
        campos.pack(fill="x")
        self.var_config = {}
        for fila, (clave, texto, maximo) in enumerate((
                ("capacidad_cola", "Capacidad de la cola (P8)", 20),
                ("tecnicos", "Técnicos N1 (P2)", 10),
                ("especialistas", "Especialistas N2 (P5)", 5))):
            tk.Label(campos, text=texto, bg=COLORES["papel"], fg=COLORES["suave"],
                     font=(FUENTE, -12)).grid(row=fila, column=0, sticky="w", pady=1)
            variable = tk.IntVar(master=self, value=self.config_red[clave])
            tk.Spinbox(campos, from_=1, to=maximo, width=5, textvariable=variable,
                       font=(FUENTE, -12), justify="center",
                       state="readonly").grid(row=fila, column=1, sticky="e", pady=1)
            self.var_config[clave] = variable
        campos.columnconfigure(0, weight=1)
        tk.Button(marco, text="Aplicar y reiniciar", command=self.aplicar_configuracion,
                  bg=COLORES["texto"], fg="white", activebackground="#2a3f57",
                  activeforeground="white", relief="flat", padx=10, pady=3,
                  cursor="hand2", font=(FUENTE, -12, "bold")).pack(fill="x", pady=(6, 0))

    def _crear_recursos(self, padre):
        marco = self._tarjeta(padre, "Recursos", fill="x", pady=(8, 0))
        for titulo, _libre, _ocupado, _texto in RECURSOS:
            fila = tk.Frame(marco, bg=COLORES["papel"])
            fila.pack(fill="x", pady=2)
            encabezado = tk.Frame(fila, bg=COLORES["papel"])
            encabezado.pack(fill="x")
            tk.Label(encabezado, text=titulo, bg=COLORES["papel"], fg=COLORES["texto"],
                     font=(FUENTE, -12)).pack(side="left")
            detalle = tk.Label(encabezado, bg=COLORES["papel"], fg=COLORES["suave"],
                               font=(FUENTE, -11))
            detalle.pack(side="right")
            barra = tk.Canvas(fila, height=10, bg=COLORES["bloqueada"],
                              highlightthickness=0)
            barra.pack(fill="x", pady=(2, 0))
            barra.bind("<Configure>", lambda _e: self._dibujar_barras())
            self.barras[titulo] = (barra, detalle)

    def _crear_estado_incidentes(self, padre):
        marco = self._tarjeta(padre, "Estado de los incidentes", fill="x", pady=(8, 0))
        filas = [(l.id, f"{l.nombre} ({l.id})")
                 for l in self.red.lugares.values() if not l.es_recurso]
        filas += [("registrados", "Registrados (T0)")]
        if "T6" in self.red.transiciones:
            filas += [("reabiertos", "Reabiertos (T6)")]
        for clave, texto in filas:
            fila = tk.Frame(marco, bg=COLORES["papel"])
            fila.pack(fill="x", pady=1)
            color = COLORES["incidente"] if clave.startswith("P") else COLORES["suave"]
            tk.Label(fila, text="●", bg=COLORES["papel"], fg=color,
                     font=(FUENTE, -10)).pack(side="left")
            tk.Label(fila, text=texto, bg=COLORES["papel"], fg=COLORES["texto"],
                     font=(FUENTE, -12)).pack(side="left", padx=(4, 0))
            valor = tk.Label(fila, bg=COLORES["papel"], fg=COLORES["texto"],
                             font=(FUENTE, -12, "bold"))
            valor.pack(side="right")
            if clave.startswith("P"):
                self.estados[clave] = valor
            else:
                self.contadores[clave] = valor

    # Actualizacion de los paneles
    def _refrescar_paneles(self):
        marcado = self.motor.obtener_marcado()
        for id_lugar, etiqueta in self.estados.items():
            etiqueta.configure(text=str(marcado[id_lugar]))
        disparos = [registro["transicion"] for registro in self.motor.historial]
        if "registrados" in self.contadores:
            self.contadores["registrados"].configure(text=str(disparos.count("T0")))
        if "reabiertos" in self.contadores:
            self.contadores["reabiertos"].configure(text=str(disparos.count("T6")))
        self._dibujar_barras()

    def _dibujar_barras(self):
        marcado = self.motor.obtener_marcado()
        for titulo, libre, ocupado, texto in RECURSOS:
            if titulo not in self.barras:
                continue
            barra, detalle = self.barras[titulo]
            total = marcado[libre] + marcado[ocupado]
            usados = marcado[ocupado]
            proporcion = usados / total if total else 0
            color = (COLORES["error"] if proporcion >= 1 else
                     COLORES["alerta"] if proporcion >= 0.5 else COLORES["ok"])
            barra.delete("all")
            if usados:
                barra.create_rectangle(0, 0, barra.winfo_width() * proporcion, 10,
                                       fill=color, outline="")
            detalle.configure(text=f"{usados} de {total} {texto}",
                              fg=COLORES["error"] if proporcion >= 1 else COLORES["suave"])


def main():
    raiz = tk.Tk()
    raiz.title("Red de Petri · Gestión de incidentes TI")
    ancho = min(1600, raiz.winfo_screenwidth() - 80)
    alto = min(1020, raiz.winfo_screenheight() - 100)
    raiz.geometry(f"{ancho}x{alto}")
    raiz.minsize(900, 560)
    try:
        raiz.state("zoomed")      
    except tk.TclError:
        pass
    InterfazPrincipal(raiz).pack(fill="both", expand=True)
    raiz.mainloop()


if __name__ == "__main__":
    main()
