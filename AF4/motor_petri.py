"""Motor de ejecucion para la red de Petri de gestion de incidentes.

Este modulo utiliza la clase RedPetri de estructura_red.py.
No define lugares, transiciones ni arcos: eso corresponde a estructura_red.py.

Modelo acordado en el HTML (una vez que se actualice estructura_red.py):
P1=cola, P2=tecnicos N1 libres, P3=N1 ocupado, P4=cola N2,
P5=especialista libre, P6=resueltos, P7=N2 ocupado, P8=espacios libres.
T0..T5 = registro, asignacion N1, resolucion N1, escalacion,
inicio N2, finalizacion N2.
"""

from collections import Counter


class MotorPetri:
    """Ejecuta las transiciones de una RedPetri creada por estructura_red.py."""

    def __init__(self, red):
        self.red = red
        self.historial = []
        self.pasos = 0

    def esta_habilitada(self, id_transicion):
        """True cuando todas las entradas tienen los tokens requeridos."""
        if id_transicion not in self.red.transiciones:
            raise ValueError(f"Transicion desconocida: {id_transicion}")
        requeridos = Counter()
        for lugar, peso in self.red.entradas(id_transicion):
            if lugar not in self.red.lugares or not isinstance(peso, int) or peso <= 0:
                raise ValueError(f"Arco de entrada invalido: {lugar}, {peso}")
            requeridos[lugar] += peso
        return all(self.red.lugares[lugar].tokens >= cantidad
                   for lugar, cantidad in requeridos.items())

    def transiciones_habilitadas(self):
        """Devuelve los identificadores de transiciones que se pueden disparar."""
        return [id_t for id_t in self.red.transiciones
                if self.esta_habilitada(id_t)]

    def disparar(self, id_transicion):
        """Consume entradas y produce salidas. False si no esta habilitada."""
        if not self.esta_habilitada(id_transicion):
            return False

        entradas = Counter()
        salidas = Counter()
        for lugar, peso in self.red.entradas(id_transicion):
            entradas[lugar] += peso
        for lugar, peso in self.red.salidas(id_transicion):
            if lugar not in self.red.lugares or not isinstance(peso, int) or peso <= 0:
                raise ValueError(f"Arco de salida invalido: {lugar}, {peso}")
            salidas[lugar] += peso

        antes = self.red.marcado()
        for lugar, peso in entradas.items():
            self.red.lugares[lugar].tokens -= peso
        for lugar, peso in salidas.items():
            self.red.lugares[lugar].tokens += peso
        despues = self.red.marcado()

        self.pasos += 1
        self.historial.append({
            "paso": self.pasos,
            "transicion": id_transicion,
            "antes": antes,
            "despues": despues,
        })
        return True

    def obtener_marcado(self):
        return self.red.marcado()

    def reiniciar(self):
        self.red.reiniciar()
        self.historial.clear()
        self.pasos = 0

    def verificar_invariantes(self, capacidad_cola=5, tecnicos=2, especialistas=1):
        """Verifica invariantes del modelo HTML T0-T5, no del modelo antiguo.

        Solo corresponde usarlo cuando estructura_red.py implemente:
        P1+P8=capacidad, P2+P3=tecnicos y P5+P7=especialistas.
        """
        m = self.obtener_marcado()
        return {
            "cola": m["P1"] + m["P8"] == capacidad_cola,
            "tecnicos_n1": m["P2"] + m["P3"] == tecnicos,
            "especialista_n2": m["P5"] + m["P7"] == especialistas,
            "tokens_no_negativos": all(v >= 0 for v in m.values()),
        }


if __name__ == "__main__":
    from estructura_red import crear_red_incidentes

    red = crear_red_incidentes()
    motor = MotorPetri(red)
    print("Marcado inicial:", motor.obtener_marcado())
    print("Transiciones habilitadas:", motor.transiciones_habilitadas())
    print("Nota: verificar_invariantes() se usa tras actualizar estructura_red.py")
