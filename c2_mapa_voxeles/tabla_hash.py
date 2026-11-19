"""C2 - Mapa de vóxeles como tabla hash dinámica con duplicación de tamaño.

Cada vóxel ocupado (i, j, k) guarda cuántos puntos LiDAR cayeron en él.
Solo se almacenan los vóxeles ocupados: espacio Theta(N) en vez de Theta((L/r)^3).

Diseño
------
- Encadenamiento separado: cada cubeta es una lista de pares [clave, valor].
- Factor de carga máximo ALFA = 3/4. Si al insertar una clave NUEVA el número de
  claves pasaría a superar ALFA * m, la tabla se duplica (m -> 2m) y se re-insertan
  todas las claves (rehash).
- Función hash: hash espacial de Teschner et al. (2003) para enteros 3D, seguido de
  hashing multiplicativo de Fibonacci (multiply-shift) para tomar los bits altos.

Análisis amortizado por el método contable (instrumentado en ``banco``)
---------------------------------------------------------------------
Costo real (unidades de "colocar una clave en una cubeta"):
  - inserción nueva sin redimensionar: 1
  - inserción nueva que dispara el rehash de n claves: n + 1
  - actualización de una clave existente: 1 (no cambia el tamaño)
Costo amortizado asignado: c_hat = 3 por inserción nueva, 1 por actualización.
  1 crédito paga la propia colocación; 2 quedan en el banco: uno moverá a esta
  clave en el próximo rehash y otro moverá a una clave "vieja" que ya gastó el suyo.
Invariante: banco >= 0 siempre  =>  suma c_i <= suma c_hat_i <= 3n  =>  O(1) amortizado.
"""

ALFA_NUM, ALFA_DEN = 3, 4          # factor de carga máximo 3/4
_P1, _P2, _P3 = 73856093, 19349663, 83492791
_FIB = 0x9E3779B97F4A7C15         # 2^64 / phi (razón áurea)
_MASK64 = (1 << 64) - 1
COSTO_AMORTIZADO_INSERCION = 3


class TablaHashVoxeles:
    def __init__(self, capacidad_inicial=8, instrumentar=True):
        if capacidad_inicial < 4 or capacidad_inicial & (capacidad_inicial - 1):
            raise ValueError("la capacidad debe ser potencia de 2 y >= 4")
        self._bits = capacidad_inicial.bit_length() - 1
        self._cubetas = [[] for _ in range(capacidad_inicial)]
        self._n = 0
        self.instrumentar = instrumentar
        # contabilidad del método contable
        self.costo_real_total = 0
        self.costo_amortizado_total = 0
        self.banco = 0
        self.banco_minimo = 0
        self.redimensionamientos = 0
        self.historial = []  # costo real por operación (si instrumentar)

    # ------------------------------------------------------------ hash
    def _indice(self, clave, bits=None):
        bits = self._bits if bits is None else bits
        i, j, k = clave
        h = ((i * _P1) ^ (j * _P2) ^ (k * _P3)) & _MASK64
        return ((h * _FIB) & _MASK64) >> (64 - bits)

    # ------------------------------------------------------------ API
    @property
    def capacidad(self):
        return len(self._cubetas)

    def __len__(self):
        return self._n

    def factor_carga(self):
        return self._n / len(self._cubetas)

    def obtener(self, clave, defecto=None):
        for par in self._cubetas[self._indice(clave)]:
            if par[0] == clave:
                return par[1]
        return defecto

    def __contains__(self, clave):
        return self.obtener(clave, None) is not None

    def insertar(self, clave, valor=1):
        """Inserta o sobrescribe. Devuelve el costo real de la operación."""
        cubeta = self._cubetas[self._indice(clave)]
        for par in cubeta:
            if par[0] == clave:
                par[1] = valor
                return self._contabilizar(1, 1)
        return self._insertar_nueva(clave, valor)

    def sumar(self, clave, delta=1):
        """Registra ``delta`` puntos más en el vóxel ``clave`` (lo crea si no existe)."""
        cubeta = self._cubetas[self._indice(clave)]
        for par in cubeta:
            if par[0] == clave:
                par[1] += delta
                return self._contabilizar(1, 1)
        return self._insertar_nueva(clave, delta)

    def items(self):
        for cubeta in self._cubetas:
            for clave, valor in cubeta:
                yield clave, valor

    # ------------------------------------------------------------ interno
    def _insertar_nueva(self, clave, valor):
        costo = 1
        if (self._n + 1) * ALFA_DEN > ALFA_NUM * len(self._cubetas):
            costo += self._duplicar()
        self._cubetas[self._indice(clave)].append([clave, valor])
        self._n += 1
        return self._contabilizar(costo, COSTO_AMORTIZADO_INSERCION)

    def _duplicar(self):
        """m -> 2m y re-inserta las n claves. Devuelve n (claves movidas)."""
        viejas = self._cubetas
        self._bits += 1
        self._cubetas = [[] for _ in range(1 << self._bits)]
        movidas = 0
        for cubeta in viejas:
            for par in cubeta:
                self._cubetas[self._indice(par[0])].append(par)
                movidas += 1
        self.redimensionamientos += 1
        return movidas

    def _contabilizar(self, real, amortizado):
        if self.instrumentar:
            self.costo_real_total += real
            self.costo_amortizado_total += amortizado
            self.banco += amortizado - real
            if self.banco < self.banco_minimo:
                self.banco_minimo = self.banco
            self.historial.append(real)
        return real
