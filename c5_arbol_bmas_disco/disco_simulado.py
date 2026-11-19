"""Disco simulado común (sección 4.1 del enunciado).

Guarda bloques de tamaño fijo en un archivo binario y cuenta cada lectura y escritura de
bloque. Ningún otro código abre el archivo: todo acceso a disco pasa por esta clase, que es
la que permite comparar las E/S contadas con las predichas por el modelo de memoria externa.
"""
import os


class DiscoSimulado:
    def __init__(self, ruta, tamano_bloque=4096):
        if tamano_bloque < 64:
            raise ValueError("tamano_bloque demasiado pequeño")
        self.ruta = ruta
        self.tamano_bloque = tamano_bloque
        existe = os.path.exists(ruta)
        self._f = open(ruta, "r+b" if existe else "w+b")
        self._f.seek(0, os.SEEK_END)
        self.num_bloques = self._f.tell() // tamano_bloque
        self.lecturas = 0
        self.escrituras = 0

    # ----------------------------------------------------------- API contada
    def leer_bloque(self, i):
        """Devuelve los bytes del bloque i. Cuenta 1 lectura."""
        if not 0 <= i < self.num_bloques:
            raise IndexError(f"bloque {i} no existe (hay {self.num_bloques})")
        self._f.seek(i * self.tamano_bloque)
        datos = self._f.read(self.tamano_bloque)
        self.lecturas += 1
        return datos

    def escribir_bloque(self, i, datos):
        """Escribe ``datos`` (a lo sumo tamano_bloque bytes, se rellena con ceros) en el bloque i.

        Si i está más allá del final, el archivo crece (los bloques intermedios quedan en ceros
        hasta que se escriban). Cuenta 1 escritura.
        """
        if len(datos) > self.tamano_bloque:
            raise ValueError("los datos no caben en un bloque")
        if i < 0:
            raise IndexError(f"bloque {i} inválido")
        self._f.seek(i * self.tamano_bloque)
        self._f.write(datos + b"\x00" * (self.tamano_bloque - len(datos)))
        if i >= self.num_bloques:
            self.num_bloques = i + 1
        self.escrituras += 1

    # ----------------------------------------------------------- utilidades
    def reiniciar_contadores(self):
        self.lecturas = 0
        self.escrituras = 0

    def contadores(self):
        return self.lecturas, self.escrituras

    def cerrar(self):
        self._f.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.cerrar()
