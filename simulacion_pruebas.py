from estructura_red import crear_red_incidentes
from motor_petri import MotorPetri


class SimuladorEscenarios:
    """Ejecuta secuencias de prueba sobre MotorPetri y registra todos los eventos."""

    def __init__(self, nombre_escenario, capacidad_cola=5, tecnicos=2, especialistas=1):
        self.nombre_escenario = nombre_escenario
        self.capacidad_cola = capacidad_cola
        self.tecnicos = tecnicos
        self.especialistas = especialistas
        self.red = crear_red_incidentes(
            capacidad_cola=capacidad_cola,
            tecnicos=tecnicos,
            especialistas=especialistas
        )
        self.motor = MotorPetri(self.red)
        self.bitacora = []

    def intentar_transicion(self, id_transicion, comentario=""):
        """Intenta disparar una transición, registra el resultado y valida invariantes."""
        antes = self.motor.obtener_marcado()
        habilitadas_antes = self.motor.transiciones_habilitadas()
        exito = self.motor.disparar(id_transicion)
        despues = self.motor.obtener_marcado()
        invariantes = self.motor.verificar_invariantes(
            capacidad_cola=self.capacidad_cola,
            tecnicos=self.tecnicos,
            especialistas=self.especialistas
        )
        invariantes_ok = all(invariantes.values())

        nombre_t = self.red.transiciones[id_transicion].nombre
        estado_txt = "EJECUTADA" if exito else "BLOQUEADA"

        registro = {
            "intento": len(self.bitacora) + 1,
            "transicion": id_transicion,
            "nombre": nombre_t,
            "resultado": estado_txt,
            "exito": exito,
            "habilitadas_antes": habilitadas_antes,
            "antes": antes,
            "despues": despues,
            "invariantes": invariantes,
            "invariantes_ok": invariantes_ok,
            "comentario": comentario
        }
        self.bitacora.append(registro)
        return exito

    def ejecutar_secuencia(self, lista_pasos):
        """Recibe una lista de tuplas (id_transicion, comentario) y las ejecuta en orden."""
        for id_transicion, comentario in lista_pasos:
            self.intentar_transicion(id_transicion, comentario)

    def imprimir_reporte(self):
        """Muestra en consola la tabla de resultados y la comprobación final del escenario."""
        print("=" * 95)
        print(f"ESCENARIO: {self.nombre_escenario}")
        print(f"Configuración -> Cola máx (P8): {self.capacidad_cola} | "
              f"Técnicos N1 (P2): {self.tecnicos} | Especialistas N2 (P5): {self.especialistas}")
        print("-" * 95)
        m_ini = {id_l: l.tokens_iniciales for id_l, l in self.red.lugares.items()}
        print(f"Marcado inicial: {self._formatear_marcado(m_ini)}")
        print("-" * 95)

        for reg in self.bitacora:
            marcado_str = self._formatear_marcado(reg["despues"])
            inv_str = "OK" if reg["invariantes_ok"] else "ERROR"
            print(f"[{reg['intento']:02d}] {reg['transicion']} ({reg['nombre']:<24}) -> "
                  f"{reg['resultado']:<9} | Inv: {inv_str}")
            if reg["comentario"]:
                print(f"     Nota: {reg['comentario']}")
            print(f"     Estado: {marcado_str}")

        total_intentos = len(self.bitacora)
        ejecutadas = sum(1 for r in self.bitacora if r["exito"])
        bloqueadas = total_intentos - ejecutadas
        todas_inv_ok = all(r["invariantes_ok"] for r in self.bitacora)

        print("-" * 95)
        print(f"Resumen: {ejecutadas} transiciones ejecutadas | "
              f"{bloqueadas} transiciones bloqueadas correctamente | "
              f"Pasos en motor: {self.motor.pasos}")
        print(f"Comprobación de invariantes en todos los pasos: "
              f"{'EXITOSA (100%)' if todas_inv_ok else 'FALLIDA'}")
        print("=" * 95 + "\n")

    @staticmethod
    def _formatear_marcado(m):
        return (f"P1(Cola):{m['P1']} P2(LibN1):{m['P2']} P3(AtN1):{m['P3']} "
                f"P4(EscN2):{m['P4']} P5(LibN2):{m['P5']} P6(Res):{m['P6']} "
                f"P7(AtN2):{m['P7']} P8(Esp):{m['P8']}")


def escenario_1_flujo_normal_y_limite_n1():
    """Prueba la configuración base (cola=5, N1=2, N2=1) y el límite de 2 técnicos N1."""
    sim = SimuladorEscenarios(
        nombre_escenario="1. Configuración Base y Límite de Técnicos N1",
        capacidad_cola=5,
        tecnicos=2,
        especialistas=1
    )
    pasos = [
        ("T0", "Entra el incidente 1 a la cola"),
        ("T0", "Entra el incidente 2 a la cola"),
        ("T0", "Entra el incidente 3 a la cola"),
        ("T1", "Se asigna incidente 1 al Técnico N1 #1 (recupera 1 espacio en P8)"),
        ("T1", "Se asigna incidente 2 al Técnico N1 #2 (P2 queda en 0 técnicos libres)"),
        ("T1", "PRUEBA DE BLOQUEO: Se intenta asignar incidente 3 sin técnicos N1 libres"),
        ("T2", "Técnico N1 resuelve incidente 1 y queda libre en P2"),
        ("T1", "Ahora sí se asigna el incidente 3 al Técnico N1 que se liberó"),
        ("T2", "Se resuelve el incidente 2 en N1"),
        ("T2", "Se resuelve el incidente 3 en N1"),
    ]
    sim.ejecutar_secuencia(pasos)
    sim.imprimir_reporte()
    return sim


def escenario_2_escalamiento_y_cuello_botella_n2():
    """Simula múltiples escalamientos cuando solo hay 1 especialista de Nivel 2."""
    sim = SimuladorEscenarios(
        nombre_escenario="2. Escalamiento a Nivel 2 y Cuello de Botella del Especialista",
        capacidad_cola=5,
        tecnicos=2,
        especialistas=1
    )
    pasos = [
        ("T0", "Se registra incidente complejo 1"),
        ("T0", "Se registra incidente complejo 2"),
        ("T1", "Técnico N1 #1 toma el incidente 1"),
        ("T1", "Técnico N1 #2 toma el incidente 2"),
        ("T3", "Técnico N1 #1 no puede resolverlo: escala a P4 y queda libre en P2"),
        ("T3", "Técnico N1 #2 tampoco puede resolverlo: escala a P4 y queda libre en P2"),
        ("T4", "El único Especialista N2 toma el primer caso escalado (P5 pasa a 0)"),
        ("T4", "PRUEBA DE BLOQUEO: Se intenta asignar el 2do caso escalado con N2 ocupado"),
        ("T5", "Especialista N2 termina el primer caso (va a P6) y vuelve a quedar libre en P5"),
        ("T4", "Especialista N2 ahora toma el segundo caso que esperaba en P4"),
        ("T5", "Especialista N2 finaliza el segundo caso escalado"),
    ]
    sim.ejecutar_secuencia(pasos)
    sim.imprimir_reporte()
    return sim


def escenario_3_saturacion_de_cola():
    """Simula una ráfaga de incidentes con cola pequeña (capacidad=3) y solo 1 técnico N1."""
    sim = SimuladorEscenarios(
        nombre_escenario="3. Saturación de Cola de Espera con Personal Mínimo (1 Técnico N1)",
        capacidad_cola=3,
        tecnicos=1,
        especialistas=1
    )
    pasos = [
        ("T0", "Llega ticket 1 (quedan 2 espacios en P8)"),
        ("T0", "Llega ticket 2 (queda 1 espacio en P8)"),
        ("T0", "Llega ticket 3 (cola llena: P8 queda en 0)"),
        ("T0", "PRUEBA DE BLOQUEO: Llega ticket 4 pero la cola alcanzó su capacidad máxima"),
        ("T1", "El único técnico N1 toma el ticket 1 (libera 1 espacio en P8)"),
        ("T0", "Ahora el ticket 4 sí puede registrarse usando el espacio liberado"),
        ("T2", "El técnico N1 resuelve el ticket 1"),
        ("T1", "El técnico N1 toma el ticket 2"),
        ("T2", "El técnico N1 resuelve el ticket 2"),
    ]
    sim.ejecutar_secuencia(pasos)
    sim.imprimir_reporte()
    return sim


def escenario_4_intentos_invalidos_en_vacio():
    """Comprueba que ninguna transición de atención o cierre se dispare con el sistema vacío."""
    sim = SimuladorEscenarios(
        nombre_escenario="4. Validación de Seguridad con Red en Estado Inicial (Sin Incidentes)",
        capacidad_cola=5,
        tecnicos=2,
        especialistas=1
    )
    pasos = [
        ("T1", "PRUEBA: Intentar asignar a N1 cuando no hay tickets en P1"),
        ("T2", "PRUEBA: Intentar resolver en N1 cuando no hay nadie en P3"),
        ("T3", "PRUEBA: Intentar escalar a N2 cuando no hay nadie en P3"),
        ("T4", "PRUEBA: Intentar iniciar N2 cuando no hay escalados en P4"),
        ("T5", "PRUEBA: Intentar finalizar N2 cuando P7 está vacío"),
    ]
    sim.ejecutar_secuencia(pasos)
    sim.imprimir_reporte()
    return sim


if __name__ == "__main__":
    escenario_1_flujo_normal_y_limite_n1()
    escenario_2_escalamiento_y_cuello_botella_n2()
    escenario_3_saturacion_de_cola()
    escenario_4_intentos_invalidos_en_vacio()