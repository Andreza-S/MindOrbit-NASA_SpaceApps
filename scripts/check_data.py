"""Verifica os critérios de aceite do briefing (seção 7). Imprime OK, FALHOU ou PULADO para cada um.

Rodar na raiz do repositório:  python -m scripts.check_data   (ou: python scripts/check_data.py)
Os testes de banco (9 e 10) usam um banco temporário: o data/mindorbit.db não é tocado.
"""
import csv
import filecmp
import json
import os
import sys
import tempfile
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
_TMP = tempfile.mkdtemp(prefix="mindorbit_check_")
os.environ["MINDORBIT_DB"] = str(Path(_TMP) / "teste.db")

import config  # noqa: E402
from simulator import generate  # noqa: E402

DADOS = config.DATA_DIR
CABECALHO = ["date", "crew_id", "sleep_h", "activity_min", "hr_rest"]
SENSOR_PRINCIPAL = {"T1": "sleep", "T2": "activity", "T3": "sleep"}
resultados = []


def registrar(n, nome, ok, detalhe=""):
    status = "PULADO" if ok is None else ("OK" if ok else "FALHOU")
    resultados.append(status)
    print(f"[{status:6}] {n:>2}. {nome}" + (f" — {detalhe}" if detalhe else ""))


def ler_csv():
    with open(DADOS / "sensores.csv", newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        return r.fieldnames, list(r)


def ler_padroes():
    return {cid: json.loads((DADOS / "baselines" / f"{cid}.json").read_text(encoding="utf-8"))
            for cid in config.CREW_IDS}


def z_ruim(linha, p, sensor):
    if sensor == "sleep":
        return (p["sleep_mean"] - float(linha["sleep_h"])) / p["sleep_std"]
    if sensor == "activity":
        return (p["activity_mean"] - float(linha["activity_min"])) / p["activity_std"]
    return (float(linha["hr_rest"]) - p["hr_mean"]) / p["hr_std"]


def dia_de(data_iso):
    from datetime import date
    return (date.fromisoformat(data_iso) - date.fromisoformat(config.date_for_day(1))).days + 1


def centrais(cid):
    ep = generate.EPISODES[cid]
    meio = (ep["start"] + ep["end"]) // 2
    return range(meio - 2, meio + 3)


def fora_de_episodio(cid, dia, folga=5):
    ep = generate.EPISODES.get(cid)
    return not ep or dia < ep["start"] - folga or dia > ep["end"] + folga


def rodar_missao():
    """Roda o núcleo da Pessoa A na missão inteira, com histórico acumulado (critérios 6, 7 e 8)."""
    from core.pipeline import analyze_entry
    from ingest.baseline import load_baseline
    from ingest.sensors import load_sensors
    from models import Entry
    diarios = {(d["crew_id"], d["day"]): d["text"]
               for d in json.loads((DADOS / "diarios_demo.json").read_text(encoding="utf-8"))}
    sensores = load_sensors()
    faixas = {}
    for cid in config.CREW_IDS:
        padrao, hist = load_baseline(cid), []
        for dia in range(1, generate.DIAS + 1):
            data = config.date_for_day(dia)
            entrada = Entry(id=dia, crew_id=cid, day=dia, date=data, text=diarios[(cid, dia)])
            janela = [a for a in hist if a.day > dia - config.WINDOW_DAYS]
            a = analyze_entry(entrada, janela, padrao, sensores.get((cid, data)))
            hist.append(a)
            faixas[(cid, dia)] = a.band
    return faixas


def main():
    print(f"Verificando {DADOS}\n")

    cab, linhas = ler_csv()
    pares = {(r["crew_id"], r["date"]) for r in linhas}
    esperados = {(c, config.date_for_day(d)) for c in config.CREW_IDS for d in range(1, generate.DIAS + 1)}
    registrar(1, "sensores.csv: 720 linhas, cabeçalho exato, sem repetição nem falta",
              len(linhas) == 720 and cab == CABECALHO and len(pares) == 720 and pares == esperados,
              f"{len(linhas)} linhas, {config.date_for_day(1)} a {config.date_for_day(generate.DIAS)}")

    try:
        from ingest.baseline import load_baseline
        from ingest.sensors import load_sensors
        load_sensors()
        for cid in config.CREW_IDS:
            load_baseline(cid)
        registrar(2, "load_sensors() e load_baseline() leem tudo", True)
    except Exception as e:  # noqa: BLE001
        registrar(2, "load_sensors() e load_baseline() leem tudo", False, repr(e))

    padroes = ler_padroes()
    dentro, total = {}, {}
    for r in linhas:
        cid, dia = r["crew_id"], dia_de(r["date"])
        if not fora_de_episodio(cid, dia, folga=0):
            continue
        for s in ("sleep", "activity", "hr"):
            total[s] = total.get(s, 0) + 1
            dentro[s] = dentro.get(s, 0) + (abs(z_ruim(r, padroes[cid], s)) < 2)
    pct = {s: dentro[s] / total[s] for s in total}
    registrar(3, "dias normais: ≥90% de cada sensor a menos de 2 desvios", all(v >= 0.9 for v in pct.values()),
              ", ".join(f"{s} {v:.0%}" for s, v in pct.items()))

    medias = {}
    for cid, sensor in SENSOR_PRINCIPAL.items():
        zs = [z_ruim(r, padroes[cid], sensor) for r in linhas
              if r["crew_id"] == cid and dia_de(r["date"]) in centrais(cid)]
        medias[cid] = sum(zs) / len(zs)
    registrar(4, "episódios: escore-z médio do sensor principal > 1,5 nos 5 dias centrais",
              all(v > 1.5 for v in medias.values()), ", ".join(f"{c} {v:.2f}" for c, v in medias.items()))

    diarios = json.loads((DADOS / "diarios_demo.json").read_text(encoding="utf-8"))
    chaves = {(d["crew_id"], d["day"]) for d in diarios}
    registrar(5, "diarios_demo.json: 720 entradas, uma por tripulante e dia, nenhuma vazia",
              len(diarios) == 720 and len(chaves) == 720 and all(d["text"].strip() for d in diarios))

    faixas = rodar_missao()
    t4 = [faixas[("T4", d)] for d in range(1, generate.DIAS + 1)]
    v4 = sum(f == "verde" for f in t4) / len(t4)
    registrar(6, "T4 verde em ≥90% dos dias", v4 >= 0.9, f"{v4:.0%}")
    ep = [faixas[(c, d)] for c in generate.EPISODES for d in centrais(c)]
    ae = sum(f in ("amarelo", "vermelho") for f in ep) / len(ep)
    registrar(7, "episódios: ≥60% amarelo ou vermelho nos 5 dias centrais", ae >= 0.6, f"{ae:.0%}")
    fora = [f for (c, d), f in faixas.items() if fora_de_episodio(c, d)]
    vf = sum(f == "verde" for f in fora) / len(fora)
    registrar(8, "fora dos episódios (folga de 5 dias): ≥85% verde", vf >= 0.85, f"{vf:.0%}")

    from storage import db
    from simulator import feed
    db.init_db(backfill=False)
    db.set_setting("sim_day", 10)
    n1 = feed.ingest_day(10)
    n2 = feed.ingest_day(10)
    futuro = feed.ingest_day(11)
    with db.connect() as con:
        linhas_10 = con.execute("SELECT COUNT(*) FROM sensor_readings WHERE day = 10").fetchone()[0]
        maior = con.execute("SELECT MAX(day) FROM sensor_readings").fetchone()[0]
    registrar(9, "ingest_day idempotente e nunca grava dia > sim_day",
              n1 == 4 and n2 == 0 and futuro == 0 and linhas_10 == 4 and maior <= 10,
              f"1ª chamada {n1}, 2ª {n2}, dia futuro {futuro}")

    db.set_setting("blackout", "1")
    db.init_db(backfill=False)
    blackout_mantido = db.get_setting("blackout") == "1"
    from models import Analysis, Entry
    entrada = db.save_entry(Entry(None, "T1", 10, config.date_for_day(10), "texto de teste"))
    analise = Analysis(entry_id=entrada, crew_id="T1", day=10, themes=["cansaco_sono"], polarity=-0.5,
                       z={"sleep": -1.2, "activity": 0.0, "hr": 0.0, "polarity": -1.0},
                       persistence={"cansaco_sono": 1}, alerts=[], confirmed_by={}, risk=20, band="verde",
                       main_theme="cansaco_sono", mood="cansado")
    db.save_analysis(analise)
    analise.mood_confirmed = "neutro"
    db.save_analysis(analise)
    with db.connect() as con:
        n_analises = con.execute("SELECT COUNT(*) FROM analyses WHERE entry_id = ?", (entrada,)).fetchone()[0]
        humor = con.execute("SELECT mood_confirmed FROM analyses WHERE entry_id = ?", (entrada,)).fetchone()[0]
    registrar(10, "init_db() repetido não apaga nada e save_analysis faz upsert",
              blackout_mantido and n_analises == 1 and humor == "neutro" and db.get_sensor_day("T1", config.date_for_day(10)) is not None)

    a, b = Path(_TMP) / "a", Path(_TMP) / "b"
    t0 = time.time()
    generate.gerar(a, gravar_banco=False)
    duracao = time.time() - t0
    generate.gerar(b, gravar_banco=False)
    arquivos = ["sensores.csv", "diarios_demo.json"] + [f"baselines/{c}.json" for c in config.CREW_IDS]
    iguais = all(filecmp.cmp(a / f, b / f, shallow=False) for f in arquivos)
    iguais_repo = all(filecmp.cmp(a / f, DADOS / f, shallow=False) for f in arquivos)
    registrar(11, "gerar tudo em < 10 s e duas execuções idênticas", duracao < 10 and iguais,
              f"{duracao:.1f} s; igual ao data/ do repositório: {'sim' if iguais_repo else 'não (rode o generate de novo)'}")

    print("\nExtras (não são critérios):")
    for cid, p in padroes.items():
        print(f"  {cid}: tom habitual {p['polarity_mean']:+.3f} ± {p['polarity_std']:.3f} "
              f"({'ok' if -0.2 <= p['polarity_mean'] <= 0.6 else 'FORA de -0,2 a 0,6'}), temas {p['usual_themes']}")
    frases_ep = [f for lista in generate.EPISODIO.values() for f in lista]
    neg = sum(any(w in f.lower().split() for w in ("não", "nem", "nunca", "sem")) for f in frases_ep)
    print(f"  frases de episódio com negação: {neg}/{len(frases_ep)} (meta: ≥ 1/4)")
    from core.themes import detect_themes
    vazam = [f for f in generate.NORMAL_POSITIVO + generate.NORMAL_NEUTRO if detect_themes(f)]
    print(f"  frases normais que marcam tema: {vazam or 'nenhuma'}")

    falhas = resultados.count("FALHOU")
    print(f"\n{resultados.count('OK')} OK · {falhas} FALHOU · {resultados.count('PULADO')} PULADO")
    sys.exit(1 if falhas else 0)


if __name__ == "__main__":
    main()
