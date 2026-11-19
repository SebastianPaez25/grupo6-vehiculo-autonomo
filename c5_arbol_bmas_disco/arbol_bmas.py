"""C5 - Árbol B+ en disco para el historial de telemetría, indexado por marca de tiempo.

Todo acceso a disco pasa por DiscoSimulado, que cuenta lecturas y escrituras de bloque.

Formatos de bloque (tamaño BS bytes, little endian)
---------------------------------------------------
Registro de telemetría: (t: int64 ms, x, y, v, rumbo: float32)      -> 24 bytes
Hoja:     cabecera (tipo=1, n, siguiente hoja) 8 bytes + n registros  -> B = (BS-8)//24 registros
Interno:  cabecera (tipo=2, n, hijo_0) 8 bytes + n pares (clave, hijo) de 12 bytes
          -> hasta F = (BS-8)//12 + 1 hijos. clave_i = menor marca de tiempo del hijo i.
Bloque 0: superbloque (raíz, altura, n, número de hojas, B, F).

Modelo de memoria externa: N registros, bloques de B registros, memoria interna de M
registros (M/B bloques). El árbol solo mantiene en memoria el camino actual: a lo sumo
h + 2 bloques, y se exige h + 2 <= M/B.

Fórmulas de E/S (h = altura, b = registros por hoja tras la carga, f = hijos por nodo interno)
  carga masiva desde el archivo de telemetría:
      lecturas  = 1 + ceil(N / B_log)                   (cabecera + recorrido secuencial)
      escrituras = L + I_1 + I_2 + ... + 1,  L = ceil(N/b), I_1 = ceil(L/f), I_j = ceil(I_{j-1}/f)
                 = Theta(N/B)                            (+1 del superbloque)
  búsqueda puntual:            lecturas = h
  consulta por rango con k resultados:
      (h - 1) + ceil(k/b)  <=  lecturas  <=  h + ceil(k/b)  ( = O(log_F N + k/B) )
  inserción: lecturas = h;  escrituras = 1 + 2s + [la raíz se dividió],  s = nodos divididos
"""
import math
import struct

REG = struct.Struct("<qffff")
CAB = struct.Struct("<BxHi")
PAR = struct.Struct("<qi")
SUPER = struct.Struct("<iiqiii")
CAB_LOG = struct.Struct("<qi")
HOJA, INTERNO = 1, 2


def capacidad_hoja(tamano_bloque):
    return (tamano_bloque - CAB.size) // REG.size


def capacidad_interno(tamano_bloque):
    """Máximo número de hijos de un nodo interno."""
    return (tamano_bloque - CAB.size) // PAR.size + 1


def _cuantos_menores_o_iguales(claves, t):
    """Búsqueda binaria propia: número de claves <= t (claves ordenadas)."""
    lo, hi = 0, len(claves)
    while lo < hi:
        mid = (lo + hi) // 2
        if claves[mid] <= t:
            lo = mid + 1
        else:
            hi = mid
    return lo


def _primer_indice_mayor_o_igual(registros, t):
    lo, hi = 0, len(registros)
    while lo < hi:
        mid = (lo + hi) // 2
        if registros[mid][0] < t:
            lo = mid + 1
        else:
            hi = mid
    return lo


class MemoriaInsuficiente(Exception):
    """El árbol necesitaría más de M/B bloques en memoria interna."""


# ====================================================================== archivo de telemetría
class ArchivoTelemetria:
    """Archivo secuencial (heap) de registros en un DiscoSimulado: bloque 0 = cabecera (n, B_log)."""

    def __init__(self, disco):
        self.disco = disco
        self.B = (disco.tamano_bloque - 8) // REG.size
        self.n = 0
        self._cabecera_leida = False

    def escribir(self, registros):
        """Escribe un flujo de registros por bloques (solo un bloque en memoria)."""
        lote, i = [], 1
        for r in registros:
            lote.append(r)
            if len(lote) == self.B:
                self.disco.escribir_bloque(i, self._codificar(lote))
                self.n += len(lote)
                lote, i = [], i + 1
        if lote:
            self.disco.escribir_bloque(i, self._codificar(lote))
            self.n += len(lote)
        self.disco.escribir_bloque(0, CAB_LOG.pack(self.n, self.B))
        return self.n

    def leer(self):
        """Recorre el archivo bloque a bloque: 1 + ceil(n/B) lecturas (la cabecera se lee una vez)."""
        n, B = self.cabecera() if not self._cabecera_leida else (self.n, self.B)
        bloques = math.ceil(n / B)
        for i in range(1, bloques + 1):
            datos = self.disco.leer_bloque(i)
            k = struct.unpack_from("<H", datos)[0]
            yield from REG.iter_unpack(datos[8:8 + k * REG.size])

    def cabecera(self):
        n, B = CAB_LOG.unpack_from(self.disco.leer_bloque(0))
        self.n, self.B = n, B
        self._cabecera_leida = True
        return n, B

    @staticmethod
    def _codificar(lote):
        return struct.pack("<H6x", len(lote)) + b"".join(REG.pack(*r) for r in lote)


# ====================================================================== nodos
class _Nodo:
    __slots__ = ("tipo", "extra", "claves", "hijos", "registros")

    def __init__(self, tipo):
        self.tipo = tipo
        self.extra = -1        # hoja: siguiente hoja
        self.claves = []       # interno
        self.hijos = []        # interno
        self.registros = []    # hoja


def _codificar_hoja(registros, siguiente):
    return CAB.pack(HOJA, len(registros), siguiente) + b"".join(REG.pack(*r) for r in registros)


def _codificar_interno(claves, hijos):
    cuerpo = b"".join(PAR.pack(k, h) for k, h in zip(claves, hijos[1:]))
    return CAB.pack(INTERNO, len(claves), hijos[0]) + cuerpo


def _decodificar(datos):
    tipo, n, extra = CAB.unpack_from(datos)
    nodo = _Nodo(tipo)
    if tipo == HOJA:
        nodo.extra = extra
        nodo.registros = list(REG.iter_unpack(datos[8:8 + n * REG.size]))
    elif tipo == INTERNO:
        nodo.hijos = [extra]
        for k, h in PAR.iter_unpack(datos[8:8 + n * PAR.size]):
            nodo.claves.append(k)
            nodo.hijos.append(h)
    else:
        raise ValueError(f"bloque con tipo desconocido {tipo}")
    return nodo


# ====================================================================== árbol
class ArbolBMas:
    def __init__(self, disco, memoria_registros=None):
        """Abre el árbol guardado en ``disco`` (lee el superbloque: 1 lectura)."""
        self.disco = disco
        self.B = capacidad_hoja(disco.tamano_bloque)
        self.F = capacidad_interno(disco.tamano_bloque)
        self.memoria_registros = memoria_registros
        if disco.num_bloques == 0:
            raise ValueError("disco vacío: use ArbolBMas.carga_masiva")
        raiz, altura, n, hojas, B, F = SUPER.unpack_from(disco.leer_bloque(0))
        if (B, F) != (self.B, self.F):
            raise ValueError("el disco fue creado con otro tamaño de bloque")
        self.raiz, self.altura, self.n, self.hojas = raiz, altura, n, hojas
        self._verificar_memoria()

    # ------------------------------------------------------------------ construcción
    @classmethod
    def carga_masiva(cls, disco, archivo, llenado=1.0, memoria_registros=None):
        """Construye el árbol leyendo una sola vez el archivo de telemetría (ya ordenado por t).

        Las hojas ocupan los bloques 1..L y los nodos internos los siguientes; como los
        identificadores se pueden calcular de antemano, cada nodo se escribe UNA vez y en
        memoria solo hay un nodo en construcción por nivel.
        """
        if disco.num_bloques != 0:
            raise ValueError("el disco del árbol debe estar vacío")
        B, F = capacidad_hoja(disco.tamano_bloque), capacidad_interno(disco.tamano_bloque)
        b = max(1, int(llenado * B))
        f = max(2, int(llenado * F))
        n, _ = archivo.cabecera()                          # 1 lectura
        if n == 0:
            raise ValueError("archivo de telemetría vacío")
        # Número de nodos por nivel y primer identificador de cada nivel.
        conteos = [math.ceil(n / b)]
        while conteos[-1] > 1:
            conteos.append(math.ceil(conteos[-1] / f))
        altura = len(conteos)
        base = [1]
        for c in conteos[:-1]:
            base.append(base[-1] + c)
        _verificar(altura, B, memoria_registros)

        # Un nodo en construcción por nivel interno (es lo único que se guarda en memoria).
        abiertos = {}

        def nuevo_abierto(nivel, m):
            c, nodos = conteos[nivel - 1], conteos[nivel]
            fin = ((m + 1) * c) // nodos           # reparto parejo de hijos entre los nodos
            return {"m": m, "claves": [], "hijos": [], "minimo": None, "fin": fin}

        def agregar(nivel, clave_min, id_hijo, j):
            """Agrega el hijo número j del nivel inferior al nodo que le toca en ``nivel``."""
            if nivel == altura:
                return
            if nivel not in abiertos:
                abiertos[nivel] = nuevo_abierto(nivel, 0)
            nodo = abiertos[nivel]
            if nodo["hijos"]:
                nodo["claves"].append(clave_min)
            else:
                nodo["minimo"] = clave_min
            nodo["hijos"].append(id_hijo)
            if j + 1 == nodo["fin"]:                # nodo completo: escribir y subir
                id_nodo = base[nivel] + nodo["m"]
                disco.escribir_bloque(id_nodo, _codificar_interno(nodo["claves"], nodo["hijos"]))
                if nodo["m"] + 1 < conteos[nivel]:
                    abiertos[nivel] = nuevo_abierto(nivel, nodo["m"] + 1)
                agregar(nivel + 1, nodo["minimo"], id_nodo, nodo["m"])

        hoja, j = [], 0
        for r in archivo.leer():
            hoja.append(r)
            if len(hoja) == b:
                cls._escribir_hoja(disco, base, j, conteos[0], hoja)
                agregar(1, hoja[0][0], base[0] + j, j)
                hoja, j = [], j + 1
        if hoja:
            cls._escribir_hoja(disco, base, j, conteos[0], hoja)
            agregar(1, hoja[0][0], base[0] + j, j)
        raiz = base[-1]
        disco.escribir_bloque(0, SUPER.pack(raiz, altura, n, conteos[0], B, F))
        arbol = cls.__new__(cls)
        arbol.disco, arbol.B, arbol.F = disco, B, F
        arbol.memoria_registros = memoria_registros
        arbol.raiz, arbol.altura, arbol.n, arbol.hojas = raiz, altura, n, conteos[0]
        arbol.registros_por_hoja = b
        arbol.hijos_por_nodo = f
        arbol.conteos_por_nivel = conteos
        return arbol

    @staticmethod
    def _escribir_hoja(disco, base, j, total_hojas, registros):
        siguiente = base[0] + j + 1 if j + 1 < total_hojas else -1
        disco.escribir_bloque(base[0] + j, _codificar_hoja(registros, siguiente))

    # ------------------------------------------------------------------ consultas
    def _leer(self, i):
        return _decodificar(self.disco.leer_bloque(i))

    def _hoja_para(self, t):
        """Desciende de la raíz a la hoja donde estaría t: h lecturas."""
        nodo = self._leer(self.raiz)
        while nodo.tipo == INTERNO:
            nodo = self._leer(nodo.hijos[_cuantos_menores_o_iguales(nodo.claves, t)])
        return nodo

    def rango(self, t1, t2):
        """Genera los registros con t1 <= t <= t2 en orden (sin cargarlos todos en memoria)."""
        if t1 > t2:
            return
        hoja = self._hoja_para(t1)
        i = _primer_indice_mayor_o_igual(hoja.registros, t1)
        while True:
            regs = hoja.registros
            while i < len(regs):
                if regs[i][0] > t2:
                    return
                yield regs[i]
                i += 1
            if hoja.extra == -1:
                return
            hoja = self._leer(hoja.extra)
            i = 0

    def contar_rango(self, t1, t2):
        k = 0
        for _ in self.rango(t1, t2):
            k += 1
        return k

    def buscar(self, t):
        """Registro con marca de tiempo exactamente t, o None. h lecturas."""
        hoja = self._hoja_para(t)
        i = _primer_indice_mayor_o_igual(hoja.registros, t)
        if i < len(hoja.registros) and hoja.registros[i][0] == t:
            return hoja.registros[i]
        return None

    # ------------------------------------------------------------------ inserción
    def insertar(self, registro):
        """Inserta un registro (p. ej. telemetría que llegó tarde). False si la marca ya existe.

        Lecturas = h (el camino); escrituras = 1 + 2s + [la raíz se dividió].
        """
        t = registro[0]
        camino = []                                    # (id, nodo, índice del hijo tomado)
        id_nodo = self.raiz
        nodo = self._leer(id_nodo)
        while nodo.tipo == INTERNO:
            k = _cuantos_menores_o_iguales(nodo.claves, t)
            camino.append((id_nodo, nodo, k))
            id_nodo = nodo.hijos[k]
            nodo = self._leer(id_nodo)
        i = _primer_indice_mayor_o_igual(nodo.registros, t)
        if i < len(nodo.registros) and nodo.registros[i][0] == t:
            return False
        nodo.registros.insert(i, tuple(registro))
        self.n += 1
        if len(nodo.registros) <= self.B:
            self.disco.escribir_bloque(id_nodo, _codificar_hoja(nodo.registros, nodo.extra))
            return True
        # División de la hoja: la mitad derecha va a un bloque nuevo.
        mitad = len(nodo.registros) // 2
        derecha = nodo.registros[mitad:]
        id_der = self.disco.num_bloques
        self.disco.escribir_bloque(id_der, _codificar_hoja(derecha, nodo.extra))
        self.disco.escribir_bloque(id_nodo, _codificar_hoja(nodo.registros[:mitad], id_der))
        self.hojas += 1
        separador, nuevo = derecha[0][0], id_der
        # Propagar hacia arriba.
        while camino:
            id_p, padre, k = camino.pop()
            padre.claves.insert(k, separador)
            padre.hijos.insert(k + 1, nuevo)
            if len(padre.hijos) <= self.F:
                self.disco.escribir_bloque(id_p, _codificar_interno(padre.claves, padre.hijos))
                return True
            m = len(padre.claves) // 2
            sube = padre.claves[m]
            id_der = self.disco.num_bloques
            self.disco.escribir_bloque(id_der, _codificar_interno(padre.claves[m + 1:], padre.hijos[m + 1:]))
            self.disco.escribir_bloque(id_p, _codificar_interno(padre.claves[:m], padre.hijos[:m + 1]))
            separador, nuevo = sube, id_der
        # La raíz se dividió: el árbol crece un nivel.
        id_raiz = self.disco.num_bloques
        self.disco.escribir_bloque(id_raiz, _codificar_interno([separador], [self.raiz, nuevo]))
        self.raiz = id_raiz
        self.altura += 1
        self._verificar_memoria()
        return True

    def guardar(self):
        """Escribe el superbloque (1 escritura)."""
        self.disco.escribir_bloque(0, SUPER.pack(self.raiz, self.altura, self.n, self.hojas, self.B, self.F))

    # ------------------------------------------------------------------ memoria y validación
    def _verificar_memoria(self):
        _verificar(self.altura, self.B, self.memoria_registros)

    def bloques_en_memoria_max(self):
        return self.altura + 2

    def validar(self):
        """Recorre todo el árbol (solo para pruebas): orden, separadores y cadena de hojas."""
        lecturas = self.disco.lecturas
        total, ultimo = 0, None
        niveles_hoja = set()

        def visitar(id_nodo, nivel, lo, hi):
            nonlocal total, ultimo
            nodo = self._leer(id_nodo)
            if nodo.tipo == HOJA:
                niveles_hoja.add(nivel)
                for r in nodo.registros:
                    assert (lo is None or r[0] >= lo) and (hi is None or r[0] < hi)
                    assert ultimo is None or r[0] > ultimo
                    ultimo = r[0]
                    total += 1
                return
            assert len(nodo.hijos) == len(nodo.claves) + 1 <= self.F
            assert all(a < b for a, b in zip(nodo.claves, nodo.claves[1:]))
            cotas = [lo] + nodo.claves + [hi]
            for h, a, b in zip(nodo.hijos, cotas, cotas[1:]):
                visitar(h, nivel + 1, a, b)

        visitar(self.raiz, 1, None, None)
        assert niveles_hoja == {self.altura}
        assert total == self.n
        self.disco.lecturas = lecturas
        return True


def _verificar(altura, B, memoria_registros):
    if memoria_registros is None:
        return
    disponibles = memoria_registros // B
    if altura + 2 > disponibles:
        raise MemoriaInsuficiente(f"se necesitan {altura + 2} bloques y M/B = {disponibles}")


def escrituras_carga_masiva_predichas(n, b, f):
    """L + I_1 + ... + 1 (superbloque)."""
    total, c = 0, math.ceil(n / b)
    total += c
    while c > 1:
        c = math.ceil(c / f)
        total += c
    return total + 1


def altura_predicha(n, b, f):
    """h = 1 + ceil(log_f(ceil(n/b))) (1 si todo cabe en una hoja)."""
    c, h = math.ceil(n / b), 1
    while c > 1:
        c = math.ceil(c / f)
        h += 1
    return h
