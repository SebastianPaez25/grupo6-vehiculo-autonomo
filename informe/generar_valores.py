"""Genera informe/final/valores.tex y las tablas de resultados a partir de resultados/*.json.

Así cada número del informe sale de los experimentos y no se copia a mano:
    python -m experimentos.ejecutar_todos
    python informe/generar_valores.py
"""
import csv
import json
import math
import os

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(RAIZ, "resultados")
SALIDA = os.path.join(RAIZ, "informe", "final")


def j(nombre):
    with open(os.path.join(RES, nombre), encoding="utf-8") as f:
        return json.load(f)


def num(x, d=2):
    """Número con coma decimal (estilo colombiano)."""
    if isinstance(x, int) or (isinstance(x, float) and x.is_integer() and d == 0):
        s = f"{int(x):,}".replace(",", "\\,")
        return s
    return f"{x:.{d}f}".replace(".", "{,}")


def entero(x):
    return f"{int(round(x)):,}".replace(",", "\\,")


def main():
    os.makedirs(SALIDA, exist_ok=True)
    v = {}
    c1, c2, c3 = j("c1_resumen.json"), j("c2_resumen.json"), j("c3_resumen.json")
    c4, c5, c6 = j("c4_resumen.json"), j("c5_resumen.json"), j("c6_resumen.json")

    # ---- C1
    p = c1["pendientes_tiempo"]
    v["cUnoPendUni"], v["cUnoPendAgr"], v["cUnoPendVer"] = (num(p["D&V uniforme"]), num(p["D&V agrupada"]),
                                                            num(p["D&V vertical"]))
    v["cUnoPendFB"] = num(p["fuerza bruta"])
    v["cUnoPendTeo"] = num(c1["pendiente_teorica_nlogn_2^10_a_max"])
    r = c1["pendientes_por_rango"]
    # En modo --rapido puede no haber 3 tamaños en un rango: se usa la pendiente global.
    bajos = [x.get("n<=2^14", p[k]) for k, x in r.items()]
    altos = [x.get("n>=2^14", p[k]) for k, x in r.items()]
    v["cUnoBajoMin"], v["cUnoBajoMax"] = num(min(bajos)), num(max(bajos))
    v["cUnoAltoMin"], v["cUnoAltoMax"] = num(min(altos)), num(max(altos))
    v["cUnoPendComb"] = num(c1["pendientes_operaciones"]["combinacion"])
    v["cUnoPendDist"] = num(c1["pendientes_operaciones"]["distancias_uniforme"])
    v["cUnoMaxVecinos"] = str(max(c1["max_vecinos_franja"].values()))
    v["cUnoSpeedup"] = num(c1["speedup_en_n_max_fb"], 1)
    v["cUnoCruce"] = str(c1["cruce_dv_mas_rapido_desde_n"])
    comb = list(c1["combinacion_sobre_nlogn"].values())
    v["cUnoCombIni"], v["cUnoCombFin"] = num(comb[4]), num(comb[-1])

    # ---- C2
    ct = c2["contable"]
    v["cDosN"] = entero(ct["n"])
    v["cDosCosto"] = entero(ct["costo_real_total"])
    v["cDosCota"] = entero(ct["cota_3n"])
    v["cDosMaxRazon"] = f"{ct['max_C(n)/n']:.5f}".replace(".", "{,}")
    v["cDosMinRazon"] = num(ct["min_C(n)/n_desde_64"])
    v["cDosBancoMin"] = entero(ct["banco_minimo"])
    v["cDosDuplic"] = str(ct["redimensionamientos"])
    v["cDosPendT"] = num(c2["pendiente_tiempo"])
    pr = c2["pendientes_por_rango"]
    v["cDosPendBajo"] = num(pr.get("n<=2^14", c2["pendiente_tiempo"]))
    v["cDosPendAlto"] = num(pr.get("n>=2^14", c2["pendiente_tiempo"]))
    us = list(c2["us_por_insercion"].values())
    v["cDosUsIni"], v["cDosUsFin"] = num(us[0], 1), num(us[-1], 1)
    e = c2["espacio"]
    v["cDosPendN"], v["cDosPendTabla"], v["cDosPendDensa"] = (num(e["pendiente_N_vs_L/r"]),
                                                              num(e["pendiente_tabla_vs_L/r"]),
                                                              num(e["pendiente_densa_vs_L/r"]))
    v["cDosBytesVox"] = entero(sum(e["bytes_por_voxel_tabla_python"]) / len(e["bytes_por_voxel_tabla_python"]))
    ult = e["filas"][-1]
    v["cDosMiBTabla"] = num(ult["bytes_tabla_python"] / 2 ** 20, 0)
    v["cDosMiBDensa"] = num(ult["bytes_densa_int32"] / 2 ** 20, 0)
    v["cDosLrMax"] = str(ult["L/r"])

    # ---- C3
    o = c3["optimalidad"]
    v["cTresFact"], v["cTresIguales"] = str(o["factibles"]), str(o["voraz_igual_al_optimo"])
    v["cTresInst"], v["cTresInfact"] = str(o["instancias"]), str(o["infactibles"])
    v["cTresInfactOk"] = str(o["infactibles_detectadas"])
    v["cTresLargo"], v["cTresExceso"] = str(o["mas_largo_primero_suboptimo"]), str(o["exceso_maximo_mas_largo"])
    if o["ejemplo_suboptimo"]:
        v["cTresEjOpt"] = str(o["ejemplo_suboptimo"]["optimo"])
        v["cTresEjLargo"] = str(o["ejemplo_suboptimo"]["mas_largo"])
    pc = c3["pendientes"]
    v["cTresPendTotal"], v["cTresPendBarrido"] = num(pc["voraz completo"]), num(pc["solo barrido"])
    v["cTresPendTotalBajo"] = num(c3["pendientes_por_rango"]["voraz completo"].get("n<=2^14", pc["voraz completo"]))
    v["cTresPendBarridoBajo"] = num(c3["pendientes_por_rango"]["solo barrido"].get("n<=2^14", pc["solo barrido"]))
    v["cTresPendComp"] = num(c3["pendiente_comparaciones"])
    v["cTresPendTeo"] = num(c3["pendiente_teorica_nlogn"])
    with open(os.path.join(RES, "c3_tiempo.csv"), encoding="utf-8") as f:
        total = {int(r["n"]): float(r["mediana"]) for r in csv.DictReader(f)}
    with open(os.path.join(RES, "c3_barrido.csv"), encoding="utf-8") as f:
        barrido = {int(r["n"]): float(r["mediana"]) for r in csv.DictReader(f)}
    fr = [barrido[n] / total[n] for n in total]
    v["cTresFracBarrido"] = num(100 * sum(fr) / len(fr), 1)

    # ---- C4
    peq = c4["pequenas"]
    ult = peq[-1]
    v["cCuatroFactor"] = num(c4["factor_crecimiento_por_celda_sin_poda"])
    v["cCuatroK"] = str(ult["k"])
    v["cCuatroSinMed"] = entero(ult["nodos_sin_poda_mediana"])
    v["cCuatroSinMax"] = entero(ult["nodos_sin_poda_max"])
    v["cCuatroCortes"] = str(ult["instancias_cortadas"])
    v["cCuatroConMed"] = entero(ult["nodos_con_poda_mediana"])
    v["cCuatroBfsMed"] = entero(ult["nodos_bfs_mediana"])
    v["cCuatroRazon"] = entero(ult["razon_sin_con"])
    v["cCuatroTSin"] = num(ult["t_sin_poda_s"], 2)
    v["cCuatroTCon"] = num(1000 * ult["t_con_poda_s"], 2)
    v["cCuatroPendBfs"] = num(c4["pendiente_bfs"])
    v["cCuatroPendPoda"] = num(c4["pendiente_nodos_poda"])
    pe = c4["poda_escala"][-1]
    v["cCuatroPodaK"] = str(pe["k"])
    v["cCuatroPodaMed"] = entero(pe["nodos_mediana"])
    v["cCuatroPodaMax"] = entero(pe["nodos_max"])
    v["cCuatroPodaCortes"] = str(pe["instancias_cortadas"])
    pq = c4["parqueadero"]
    v["cCuatroParqLong"] = str(pq["longitud"])
    v["cCuatroParqCon"] = entero(pq["nodos_con_poda"])
    v["cCuatroParqSin"] = entero(pq["nodos_sin_poda"])
    v["cCuatroParqBfs"] = entero(pq["nodos_bfs"])
    with open(os.path.join(SALIDA, "tabla_c4.tex"), "w", encoding="utf-8") as f:
        for x in peq:
            corte = f"$^{{*}}$" if x["instancias_cortadas"] else ""
            f.write(f"${x['k']}\\times{x['k']}$ & {x['celdas']} & {entero(x['nodos_sin_poda_mediana'])}{corte} & "
                    f"{entero(x['nodos_con_poda_mediana'])} & {entero(x['nodos_bfs_mediana'])} & "
                    f"{entero(x['razon_sin_con'])} \\\\\n")

    # ---- C5
    v["cCincoExactaCarga"] = "sí" if c5["carga_exacta"] else "no"
    v["cCincoExactaPunto"] = "sí" if c5["puntual_exacta"] else "no"
    v["cCincoRangos"] = "sí" if c5["rangos_dentro_de_la_formula"] else "no"
    v["cCincoPendT"] = num(c5["pendiente_tiempo_carga"])
    v["cCincoPendES"] = num(c5["pendiente_es_carga"])
    cons = c5["construccion"]
    v["cCincoNMax"] = entero(cons[-1]["N"])
    v["cCincoMMax"] = entero(cons[-1]["M"])
    v["cCincoMB"] = entero(cons[-1]["M_sobre_B"])
    v["cCincoH"] = str(cons[-1]["h"])
    v["cCincoRecorrido"] = entero(cons[-1]["recorrido_completo"])
    with open(os.path.join(SALIDA, "tabla_c5_construccion.tex"), "w", encoding="utf-8") as f:
        for x in cons:
            f.write(f"{entero(x['N'])} & {entero(x['M_sobre_B'])} & {x['h']} / {x['h_predicha']} & "
                    f"{entero(x['lect_carga'])} / {entero(x['lect_carga_pred'])} & "
                    f"{entero(x['escr_carga'])} / {entero(x['escr_carga_pred'])} & "
                    f"{x['lect_puntual_max']} / {x['h_predicha']} & {num(x['t_carga_s'], 2)} \\\\\n")
    with open(os.path.join(SALIDA, "tabla_c5_rangos.tex"), "w", encoding="utf-8") as f:
        for x in c5["rangos"]:
            f.write(f"{entero(x['k'])} & {x['lect_min']} & {num(x['lect_mediana'], 0) if float(x['lect_mediana']).is_integer() else num(x['lect_mediana'], 1)} & "
                    f"{x['lect_max']} & [{x['pred_inferior']}, {x['pred_superior']}] & "
                    f"{'sí' if x['dentro'] else 'no'} \\\\\n")
    with open(os.path.join(SALIDA, "tabla_c5_bloque.tex"), "w", encoding="utf-8") as f:
        for x in c5["tamano_bloque"]:
            f.write(f"{entero(x['bloque_bytes'])} & {x['b']} & {x['f']} & {x['h']} / {x['h_predicha']} & "
                    f"{num(x['lect_puntual'], 0)} & {num(x['lect_rango_10k_mediana'], 0)} & {x['pred_rango_sup']} \\\\\n")
    ins = {x["llenado"]: x for x in c5["inserciones"]}
    for clave, ll in (("Cien", 1.0), ("Setenta", 0.7)):
        x = ins[ll]
        v[f"cCincoIns{clave}N"] = entero(x["inserciones"])
        v[f"cCincoIns{clave}Lect"] = num(x["lecturas_por_insercion"], 2)
        v[f"cCincoIns{clave}Escr"] = num(x["escrituras_por_insercion"], 2)
        v[f"cCincoIns{clave}Div"] = entero(100 * x["fraccion_con_division"])
        v[f"cCincoIns{clave}Exactas"] = entero(x["formula_exacta_en"])
        v[f"cCincoIns{clave}H"] = str(x["h"])

    # ---- C6
    v["cSeisGrafos"] = str(c6["grafos"])
    v["cSeisCumplen"] = str(c6["cumplen_M_le_OPT_le_C_le_2OPT"])
    v["cSeisMediaCalles"] = num(c6["razon_media"]["calles"])
    v["cSeisMediaAleat"] = num(c6["razon_media"]["aleatorio"])
    v["cSeisMax"], v["cSeisMin"] = num(c6["razon_max"]), num(c6["razon_min"])
    v["cSeisGradoMax"] = num(c6["razon_media_grado_max"])
    v["cSeisPendT"] = num(c6["pendiente_tiempo"])
    v["cSeisFactorFB"] = num(c6["factor_fuerza_bruta_por_vertice"])
    v["cSeisAjC"], v["cSeisAjOpt"] = str(c6["caso_ajustado"]["C"]), str(c6["caso_ajustado"]["OPT"])
    fb = c6["fuerza_bruta"]
    v["cSeisFBVmax"], v["cSeisFBTmax"] = str(fb[-1]["V"]), num(fb[-1]["s"], 2)

    with open(os.path.join(SALIDA, "valores.tex"), "w", encoding="utf-8") as f:
        f.write("% Generado por informe/generar_valores.py a partir de resultados/*.json. No editar a mano.\n")
        for k, x in v.items():
            f.write(f"\\newcommand{{\\{k}}}{{{x}}}\n")
    print(f"{len(v)} valores escritos en {SALIDA}")


if __name__ == "__main__":
    main()
