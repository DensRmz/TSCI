"""
estructura_red.py
Módulo: Estructura de la red (parte de Carleone)

Red de Petri básica (P/T) para la gestión de incidentes de soporte técnico
en una planta industrial. Define 8 lugares, 6 transiciones (T0-T5), los arcos
(todos de peso 1) y el marcado inicial.

Modelo acordado (coincide con el documento y con motor_petri.py):
    P1 Incidentes en cola          P5 Especialista N2 disponible
    P2 Técnicos N1 disponibles     P6 Incidentes resueltos
    P3 En atención N1              P7 En atención N2
    P4 Cola de escalación N2       P8 Espacios disponibles en cola

    T0 Registrar incidente         T3 Escalar a N2
    T1 Asignar incidente a N1      T4 Iniciar atención N2
    T2 Resolver en N1              T5 Finalizar atención N2

Este módulo SOLO define la estructura (datos). La lógica de ejecución
(habilitación, consumo y generación de tokens) está en motor_petri.py.

Invariantes del modelo:
    P1 + P8 = capacidad de la cola      P2 + P3 = técnicos N1
    P5 + P7 = especialistas N2

Uso desde otros módulos:
    from estructura_red import crear_red_incidentes
    red = crear_red_incidentes(capacidad_cola=5, tecnicos=2, especialistas=1)
    red.entradas("T1")    # [(lugar, peso), ...] que consume T1
    red.salidas("T1")     # [(lugar, peso), ...] que genera T1
"""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple


@dataclass
class Lugar:
    """Un lugar (place) de la red. 'tokens' es el marcado actual."""
    id: str
    nombre: str
    descripcion: str
    tokens: int = 0
    tokens_iniciales: int = 0
    es_recurso: bool = False  # True si representa recursos (técnicos, especialista, espacios)


@dataclass
class Transicion:
    """Una transición de la red (un evento del proceso)."""
    id: str
    nombre: str
    descripcion: str


@dataclass
class Arco:
    """
    Arco dirigido con peso.
    - Lugar -> Transición  (arco de entrada: la transición consume tokens)
    - Transición -> Lugar  (arco de salida: la transición genera tokens)
    """
    origen: str
    destino: str
    peso: int = 1


@dataclass
class RedPetri:
    lugares: Dict[str, Lugar] = field(default_factory=dict)
    transiciones: Dict[str, Transicion] = field(default_factory=dict)
    arcos: List[Arco] = field(default_factory=list)

    # --- construcción -----------------------------------------------------
    def agregar_lugar(self, id, nombre, descripcion, tokens=0, es_recurso=False):
        self.lugares[id] = Lugar(id, nombre, descripcion, tokens, tokens, es_recurso)

    def agregar_transicion(self, id, nombre, descripcion):
        self.transiciones[id] = Transicion(id, nombre, descripcion)

    def agregar_arco(self, origen, destino, peso=1):
        """Valida que el arco conecte un lugar con una transición (o viceversa)."""
        lugar_a_trans = origen in self.lugares and destino in self.transiciones
        trans_a_lugar = origen in self.transiciones and destino in self.lugares
        if not (lugar_a_trans or trans_a_lugar):
            raise ValueError(
                f"Arco inválido {origen} -> {destino}: debe conectar un lugar "
                f"con una transición."
            )
        self.arcos.append(Arco(origen, destino, peso))

    # --- consultas de estructura (las usa el resto del sistema) -----------
    def entradas(self, id_transicion: str) -> List[Tuple[str, int]]:
        """Lugares de entrada de una transición, con el peso del arco."""
        return [(a.origen, a.peso) for a in self.arcos if a.destino == id_transicion]

    def salidas(self, id_transicion: str) -> List[Tuple[str, int]]:
        """Lugares de salida de una transición, con el peso del arco."""
        return [(a.destino, a.peso) for a in self.arcos if a.origen == id_transicion]

    def marcado(self) -> Dict[str, int]:
        """Marcado actual: {id_lugar: tokens}."""
        return {id_l: l.tokens for id_l, l in self.lugares.items()}

    def reiniciar(self):
        """Regresa la red a su marcado inicial."""
        for l in self.lugares.values():
            l.tokens = l.tokens_iniciales

    def resumen(self) -> str:
        lineas = ["LUGARES (marcado inicial)"]
        for l in self.lugares.values():
            tipo = "recurso" if l.es_recurso else "incidente"
            lineas.append(f"  {l.id}  {l.nombre:<30} tokens={l.tokens}  [{tipo}]")
        lineas.append("\nTRANSICIONES")
        for t in self.transiciones.values():
            ent = ", ".join(f"{p}(x{w})" for p, w in self.entradas(t.id))
            sal = ", ".join(f"{p}(x{w})" for p, w in self.salidas(t.id))
            lineas.append(f"  {t.id}  {t.nombre:<28} [{ent}]  ->  [{sal}]")
        return "\n".join(lineas)


def crear_red_incidentes(capacidad_cola: int = 5, tecnicos: int = 2,
                         especialistas: int = 1) -> RedPetri:
    """
    Crea la red de Petri del sistema de gestión de incidentes.

    Parámetros (marcado inicial, modificables para las pruebas):
        capacidad_cola -> tokens en P8 (espacios libres de la cola)
        tecnicos       -> tokens en P2 (técnicos de Nivel 1 disponibles)
        especialistas  -> tokens en P5 (especialistas de Nivel 2 disponibles)
    """
    red = RedPetri()

    # ----- 8 LUGARES -----
    red.agregar_lugar("P1", "Incidentes en cola",
                      "Tickets que esperan atención de Nivel 1; cada ficha es un incidente pendiente.")
    red.agregar_lugar("P2", "Técnicos N1 disponibles",
                      "Técnicos de Nivel 1 libres; cada ficha es un técnico que puede recibir un incidente.",
                      tokens=tecnicos, es_recurso=True)
    red.agregar_lugar("P3", "En atención N1",
                      "Incidentes que un técnico de Nivel 1 está diagnosticando o atendiendo.")
    red.agregar_lugar("P4", "Cola de escalación N2",
                      "Incidentes enviados a Nivel 2 que esperan al especialista.")
    red.agregar_lugar("P5", "Especialista N2 disponible",
                      "Su ficha indica que el especialista puede comenzar una atención.",
                      tokens=especialistas, es_recurso=True)
    red.agregar_lugar("P6", "Incidentes resueltos",
                      "Casos cuya atención terminó satisfactoriamente en cualquiera de los dos niveles.")
    red.agregar_lugar("P7", "En atención N2",
                      "Incidentes que está atendiendo el especialista.")
    red.agregar_lugar("P8", "Espacios disponibles en cola",
                      "Capacidad libre de la cola; cada ficha permite registrar un nuevo ticket.",
                      tokens=capacidad_cola, es_recurso=True)

    # ----- 6 TRANSICIONES -----
    red.agregar_transicion("T0", "Registrar incidente",
                           "Hay un espacio libre en P8: se consume y se añade un incidente a P1.")
    red.agregar_transicion("T1", "Asignar incidente a N1",
                           "Hay incidente en P1 y técnico en P2: pasa a P3 y devuelve un espacio a P8.")
    red.agregar_transicion("T2", "Resolver en N1",
                           "El técnico resuelve el incidente: va a P6 y el técnico vuelve a P2.")
    red.agregar_transicion("T3", "Escalar a N2",
                           "El técnico no puede resolverlo: va a P4 y el técnico vuelve a P2.")
    red.agregar_transicion("T4", "Iniciar atención N2",
                           "Hay incidente en P4 y especialista en P5: el incidente pasa a P7.")
    red.agregar_transicion("T5", "Finalizar atención N2",
                           "El especialista termina: el incidente va a P6 y el especialista vuelve a P5.")

    # ----- ARCOS (todos de peso 1) -----
    red.agregar_arco("P8", "T0"); red.agregar_arco("T0", "P1")
    red.agregar_arco("P1", "T1"); red.agregar_arco("P2", "T1")
    red.agregar_arco("T1", "P3"); red.agregar_arco("T1", "P8")
    red.agregar_arco("P3", "T2"); red.agregar_arco("T2", "P6"); red.agregar_arco("T2", "P2")
    red.agregar_arco("P3", "T3"); red.agregar_arco("T3", "P4"); red.agregar_arco("T3", "P2")
    red.agregar_arco("P4", "T4"); red.agregar_arco("P5", "T4"); red.agregar_arco("T4", "P7")
    red.agregar_arco("P7", "T5"); red.agregar_arco("T5", "P6"); red.agregar_arco("T5", "P5")

    return red


if __name__ == "__main__":
    red = crear_red_incidentes()
    assert len(red.lugares) == 8, "La red debe tener 8 lugares"
    assert len(red.transiciones) == 6, "La red debe tener 6 transiciones (T0-T5)"
    print(red.resumen())
    print(f"\nTotal: {len(red.lugares)} lugares, {len(red.transiciones)} transiciones, "
          f"{len(red.arcos)} arcos")