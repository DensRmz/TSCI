"""
estructura_red.py
Módulo: Estructura de la red (parte de Carleone)

Red de Petri básica para la gestión de incidentes de soporte técnico.
Define 8 lugares, 7 transiciones, los arcos y el marcado inicial.

Este módulo SOLO define la estructura (datos). La lógica de ejecución
(verificar si una transición está habilitada, consumir/generar tokens)
corresponde al motor de ejecución (Dennis) y la gestión de incidentes (Van).

Uso desde otros módulos:
    from estructura_red import crear_red_incidentes
    red = crear_red_incidentes(incidentes=5, tecnicos=2, especialistas=1)
    red.lugares["P1"].tokens          # tokens actuales en un lugar
    red.entradas("T1")                # [(lugar, peso), ...] que consume T1
    red.salidas("T1")                 # [(lugar, peso), ...] que genera T1
"""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple


# ---------------------------------------------------------------------------
# Elementos básicos de la red
# ---------------------------------------------------------------------------
@dataclass
class Lugar:
    """Un lugar (place) de la red. 'tokens' es el marcado actual."""
    id: str
    nombre: str
    descripcion: str
    tokens: int = 0
    tokens_iniciales: int = 0
    es_recurso: bool = False  # True si representa recursos (técnicos/especialistas)


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

    # --- consultas de estructura (las usa el resto del sistema) ----------------
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
            lineas.append(f"  {l.id}  {l.nombre:<28} tokens={l.tokens}  [{tipo}]")
        lineas.append("\nTRANSICIONES")
        for t in self.transiciones.values():
            ent = ", ".join(f"{p}(x{w})" for p, w in self.entradas(t.id))
            sal = ", ".join(f"{p}(x{w})" for p, w in self.salidas(t.id))
            lineas.append(f"  {t.id}  {t.nombre:<28} [{ent}]  ->  [{sal}]")
        return "\n".join(lineas)


# ---------------------------------------------------------------------------
# Construcción de la red de incidentes (8 lugares, 7 transiciones)
# ---------------------------------------------------------------------------
def crear_red_incidentes(incidentes: int = 5, tecnicos: int = 2,
                         especialistas: int = 1) -> RedPetri:
    """
    Crea la red de Petri del sistema de gestión de incidentes.

    Parámetros (marcado inicial, modificables para las pruebas de Isaul):
        incidentes     -> tokens en P1 (incidentes registrados en espera)
        tecnicos       -> tokens en P2 (técnicos de nivel 1 disponibles)
        especialistas  -> tokens en P5 (especialistas disponibles)
    """
    red = RedPetri()

    # ----- 8 LUGARES -----
    red.agregar_lugar("P1", "Incidentes en espera",
                      "Incidentes registrados que aún no tienen técnico asignado.",
                      tokens=incidentes)
    red.agregar_lugar("P2", "Técnicos disponibles",
                      "Técnicos de nivel 1 libres para atender un incidente.",
                      tokens=tecnicos, es_recurso=True)
    red.agregar_lugar("P3", "En atención (nivel 1)",
                      "Incidentes que un técnico de nivel 1 está atendiendo.")
    red.agregar_lugar("P4", "Escalados (en espera de especialista)",
                      "Incidentes que el técnico no pudo resolver y esperan a un especialista.")
    red.agregar_lugar("P5", "Especialistas disponibles",
                      "Especialistas libres para atender incidentes escalados.",
                      tokens=especialistas, es_recurso=True)
    red.agregar_lugar("P6", "En atención (especialista)",
                      "Incidentes escalados que un especialista está atendiendo.")
    red.agregar_lugar("P7", "Resueltos (por confirmar)",
                      "Incidentes con solución aplicada, pendientes de confirmación del usuario.")
    red.agregar_lugar("P8", "Incidentes cerrados",
                      "Incidentes confirmados por el usuario y cerrados.")

    # ----- 7 TRANSICIONES -----
    red.agregar_transicion("T1", "Asignar a técnico",
                           "Un técnico libre toma un incidente en espera.")
    red.agregar_transicion("T2", "Resolver (nivel 1)",
                           "El técnico resuelve el incidente y queda libre.")
    red.agregar_transicion("T3", "Escalar a especialista",
                           "El técnico no puede resolverlo: lo escala y queda libre.")
    red.agregar_transicion("T4", "Asignar a especialista",
                           "Un especialista libre toma un incidente escalado.")
    red.agregar_transicion("T5", "Resolver (especialista)",
                           "El especialista resuelve el incidente y queda libre.")
    red.agregar_transicion("T6", "Confirmar y cerrar",
                           "El usuario confirma la solución y el incidente se cierra.")
    red.agregar_transicion("T7", "Reabrir incidente",
                           "El usuario rechaza la solución: el incidente vuelve a la cola.")

    # ----- ARCOS -----
    # T1: P1 + P2 -> P3
    red.agregar_arco("P1", "T1"); red.agregar_arco("P2", "T1"); red.agregar_arco("T1", "P3")
    # T2: P3 -> P7 + P2 (libera al técnico)
    red.agregar_arco("P3", "T2"); red.agregar_arco("T2", "P7"); red.agregar_arco("T2", "P2")
    # T3: P3 -> P4 + P2 (libera al técnico)
    red.agregar_arco("P3", "T3"); red.agregar_arco("T3", "P4"); red.agregar_arco("T3", "P2")
    # T4: P4 + P5 -> P6
    red.agregar_arco("P4", "T4"); red.agregar_arco("P5", "T4"); red.agregar_arco("T4", "P6")
    # T5: P6 -> P7 + P5 (libera al especialista)
    red.agregar_arco("P6", "T5"); red.agregar_arco("T5", "P7"); red.agregar_arco("T5", "P5")
    # T6: P7 -> P8
    red.agregar_arco("P7", "T6"); red.agregar_arco("T6", "P8")
    # T7: P7 -> P1 (reapertura)
    red.agregar_arco("P7", "T7"); red.agregar_arco("T7", "P1")

    return red


if __name__ == "__main__":
    red = crear_red_incidentes()
    assert len(red.lugares) == 8, "La red debe tener 8 lugares"
    assert len(red.transiciones) == 7, "La red debe tener 7 transiciones"
    print(red.resumen())
    print(f"\nTotal: {len(red.lugares)} lugares, {len(red.transiciones)} transiciones, "
          f"{len(red.arcos)} arcos")
