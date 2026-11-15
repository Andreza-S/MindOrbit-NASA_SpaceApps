"""Gera os dados simulados do MindOrbit (Pessoa B).

Cria, com semente fixa:
  data/baselines/T1.json .. T4.json   padrão de bem-estar
  data/sensores.csv                    180 dias x 4 tripulantes
  data/diarios_demo.json               720 entradas de diário
e grava os padrões e a tripulação no banco.

Rodar na raiz do repositório:  python -m simulator.generate
"""
import argparse
import csv
import json
import random
import statistics
import time
from pathlib import Path

import numpy as np

import config
from core.sentiment import polarity
from core.themes import detect_themes
from models import Baseline

RAIZ = Path(__file__).resolve().parents[1]
DIAS = 180
N_PRE_VOO = 30
PISO_POLARIDADE = 0.15

# Padrões de partida (seção 5 do briefing)
PADROES = {
    "T1": {"sleep": (7.2, 0.6), "activity": (48, 12), "hr": (58, 3.0), "habitual": "sobrecarga"},
    "T2": {"sleep": (6.9, 0.5), "activity": (42, 10), "hr": (61, 3.5), "habitual": None},
    "T3": {"sleep": (7.6, 0.6), "activity": (60, 14), "hr": (54, 2.5), "habitual": "monotonia"},
    "T4": {"sleep": (7.0, 0.7), "activity": (35, 9), "hr": (64, 3.0), "habitual": None},
}

# Episódios plantados (seção 6). Efeitos em relação ao padrão.
EPISODES = {
    "T1": {"start": 60, "end": 68, "themes": ["cansaco_sono"],
           "sleep": -1.5, "hr": +4.0, "activity": -0.15},
    "T2": {"start": 110, "end": 118, "themes": ["humor_baixo", "saudade_isolamento"],
           "sleep": -0.5, "hr": +1.0, "activity": -0.50},
    "T3": {"start": 140, "end": 148, "themes": ["sobrecarga"],
           "sleep": -1.2, "hr": +3.0, "activity": 0.0},
}

FAIXAS = {"sleep": (3, 10), "activity": (0, 150), "hr": (40, 100)}

# Modelos de frases. Os normais evitam palavras de tema e as armadilhas da seção 8
# (rotina, tarefas, clima, casa, igual, pressão, sono, acordei).
NORMAL_POSITIVO = [
    "Dia tranquilo, treinei e estou bem.",
    "Foi um ótimo dia, me senti calmo e produtivo.",
    "Gostei muito da conversa com a equipe no jantar.",
    "Me sinto disposto e motivado.",
    "Vi a Terra pela janela e fiquei em paz.",
    "Treino leve e um bom filme à noite.",
    "Estou animado com o experimento de amanhã.",
    "Dormi bem e comecei o dia descansado.",
]
NORMAL_NEUTRO = [
    "Fiz a manutenção do sistema de água e revisei o cronograma.",
    "Terminei o experimento da manhã.",
    "Limpei os filtros de ar e organizei o módulo.",
    "Revisei os procedimentos de emergência com a comandante.",
    "Coletei amostras para o laboratório.",
    "Atualizei o inventário de suprimentos.",
]
HABITUAL = {
    "sobrecarga": ["Semana com prazo apertado no treinamento.", "Um pouco de correria no fim do turno."],
    "monotonia": ["Treino de simulação um pouco repetitivo hoje.", "Hoje teve um certo tédio no turno da noite."],
}
# Em cada tema, a palavra do tema vem antes da negação, para a negação não "apagar" o tema.
EPISODIO = {
    "cansaco_sono": [
        "Acordei várias vezes durante a noite e estou exausto.",
        "Estou exausto, não consegui dormir direito de novo.",
        "A insônia voltou e o cansaço pesa.",
        "Passei a madrugada em claro e me sinto esgotado.",
        "Muito cansado hoje, não descansei nada.",
        "Tive pesadelo de novo e estou sonolento.",
        "Estou com olheiras e não estou bem.",
        "O cansaço não passa, nem o café ajudou.",
    ],
    "humor_baixo": [
        "Estou triste e desanimado, sem vontade de treinar.",
        "Hoje tudo parece vazio.",
        "Me sinto desmotivado e não estou bem.",
        "Chorei um pouco antes de deitar.",
        "Estou abatido, nada parece ter graça.",
        "Uma tristeza que não vai embora.",
    ],
    "saudade_isolamento": [
        "Senti muita saudade da família hoje.",
        "Me sinto sozinho aqui.",
        "A solidão pesa e não paro de pensar nos meus filhos.",
        "Saudade da minha filha, não falei com ela esta semana.",
        "Isolado, sinto falta das pessoas.",
        "Me sinto solitário, nem as mensagens ajudam.",
    ],
    "sobrecarga": [
        "Estou atrasado e a pressão do prazo só aumenta.",
        "Atividades demais para pouco tempo, estou sobrecarregado.",
        "Correria o dia todo, não deu tempo de almoçar.",
        "Trabalho acumulado e o prazo não espera.",
        "Sobrecarregado, não consigo dar conta de tudo.",
        "Mais um experimento atrasado, me sinto sufocado.",
        "Tudo é urgente e não paro um minuto.",
    ],
}


def intensidade(crew_id: str, day: int) -> float:
    ep = EPISODES.get(crew_id)
    if not ep or day < ep["start"] or day > ep["end"]:
        return 0.0
    da_ponta = min(day - ep["start"], ep["end"] - day)
    return {0: 0.33, 1: 0.66}.get(da_ponta, 1.0)


class Sorteador:
    """Escolhe frases sem repetir as do dia anterior do mesmo tripulante."""

    def __init__(self, rnd: random.Random):
        self.rnd = rnd
        self.ontem = set()
        self.hoje = set()

    def frase(self, lista):
        opcoes = [f for f in lista if f not in self.ontem and f not in self.hoje] or lista
        f = self.rnd.choice(opcoes)
        self.hoje.add(f)
        return f

    def virar_dia(self):
        self.ontem, self.hoje = self.hoje, set()


def texto_normal(s: Sorteador, rnd: random.Random, habitual=None, p_habitual=0.0):
    n = rnd.randint(1, 3)
    frases = [s.frase(NORMAL_NEUTRO)]
    frases += [s.frase(NORMAL_POSITIVO if rnd.random() < 0.45 else NORMAL_NEUTRO) for _ in range(n - 1)]
    rnd.shuffle(frases)
    if habitual and rnd.random() < p_habitual:
        frases[-1] = s.frase(HABITUAL[habitual])
    return " ".join(frases)


def texto_episodio(s: Sorteador, rnd: random.Random, temas, inten):
    if inten < 1.0:
        frases = [s.frase(EPISODIO[rnd.choice(temas)]), s.frase(NORMAL_NEUTRO + NORMAL_POSITIVO)]
        if inten < 0.5:
            rnd.shuffle(frases)
        return " ".join(frases)
    frases = [s.frase(EPISODIO[t]) for t in rnd.sample(temas, k=len(temas))][: rnd.randint(1, 2)]
    if len(frases) == 1 and rnd.random() < 0.5:
        frases.append(s.frase(EPISODIO[temas[0]]))
    if rnd.random() < 0.3:
        frases.append(s.frase(NORMAL_NEUTRO))
    return " ".join(frases)


def gerar(saida: Path = config.DATA_DIR, gravar_banco: bool = True) -> dict:
    rnd = random.Random(42)
    rng = np.random.default_rng(42)
    saida = Path(saida)
    (saida / "baselines").mkdir(parents=True, exist_ok=True)

    padroes = {}
    for cid in config.CREW_IDS:
        p = PADROES[cid]
        s = Sorteador(rnd)
        textos = []
        for _ in range(N_PRE_VOO):
            textos.append(texto_normal(s, rnd, p["habitual"], 0.25))
            s.virar_dia()
        notas = [polarity(t) for t in textos]
        contagem = {}
        for t in textos:
            for tema in detect_themes(t):
                contagem[tema] = contagem.get(tema, 0) + 1
        habituais = sorted((t for t, n in contagem.items() if n / N_PRE_VOO >= 0.15),
                           key=lambda t: (-contagem[t], t))[:2]
        padroes[cid] = Baseline(
            crew_id=cid,
            sleep_mean=p["sleep"][0], sleep_std=p["sleep"][1],
            activity_mean=float(p["activity"][0]), activity_std=float(p["activity"][1]),
            hr_mean=float(p["hr"][0]), hr_std=float(p["hr"][1]),
            polarity_mean=round(statistics.mean(notas), 3),
            polarity_std=round(max(statistics.stdev(notas), PISO_POLARIDADE), 3),
            usual_themes=habituais,
        )

    linhas, diarios = [], []
    sorteadores = {cid: Sorteador(rnd) for cid in config.CREW_IDS}
    for day in range(1, DIAS + 1):
        data = config.date_for_day(day)
        for cid in config.CREW_IDS:
            b, ep, inten = padroes[cid], EPISODES.get(cid, {}), intensidade(cid, day)
            sono = rng.normal(b.sleep_mean, b.sleep_std) + inten * ep.get("sleep", 0)
            ativ = rng.normal(b.activity_mean, b.activity_std) * (1 + inten * ep.get("activity", 0))
            fc = rng.normal(b.hr_mean, b.hr_std) + inten * ep.get("hr", 0)
            linhas.append({
                "date": data, "crew_id": cid,
                "sleep_h": round(float(np.clip(sono, *FAIXAS["sleep"])), 1),
                "activity_min": int(round(float(np.clip(ativ, *FAIXAS["activity"])))),
                "hr_rest": round(float(np.clip(fc, *FAIXAS["hr"])), 1),
            })
            s = sorteadores[cid]
            if inten > 0:
                texto = texto_episodio(s, rnd, ep["themes"], inten)
            else:
                texto = texto_normal(s, rnd, PADROES[cid]["habitual"], 0.08)
            s.virar_dia()
            diarios.append({"crew_id": cid, "day": day, "text": texto})

    with open(saida / "sensores.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["date", "crew_id", "sleep_h", "activity_min", "hr_rest"],
                           lineterminator="\n")
        w.writeheader()
        w.writerows(linhas)
    (saida / "diarios_demo.json").write_text(json.dumps(diarios, ensure_ascii=False, indent=1) + "\n",
                                             encoding="utf-8")
    for cid, b in padroes.items():
        d = {"crew_id": b.crew_id, "sleep_mean": b.sleep_mean, "sleep_std": b.sleep_std,
             "activity_mean": b.activity_mean, "activity_std": b.activity_std,
             "hr_mean": b.hr_mean, "hr_std": b.hr_std,
             "polarity_mean": b.polarity_mean, "polarity_std": b.polarity_std,
             "usual_themes": list(b.usual_themes)}
        (saida / "baselines" / f"{cid}.json").write_text(json.dumps(d, ensure_ascii=False) + "\n", encoding="utf-8")

    if gravar_banco:
        from storage import db
        db.init_db(backfill=False)
        for b in padroes.values():
            db.save_baseline(b)
    return padroes


def main():
    ap = argparse.ArgumentParser(description="Gera padrões, sensores e diários simulados.")
    ap.add_argument("--saida", default=str(config.DATA_DIR))
    ap.add_argument("--sem-banco", action="store_true", help="não grava padrões no SQLite")
    args = ap.parse_args()
    t = time.time()
    padroes = gerar(Path(args.saida), gravar_banco=not args.sem_banco)
    for b in padroes.values():
        print(f"{b.crew_id}: tom {b.polarity_mean:+.3f} ± {b.polarity_std:.3f} · temas habituais {b.usual_themes}")
    print(f"Pronto em {time.time() - t:.1f} s → {args.saida}")
    from simulator import light_delay
    light_delay.main(DIAS)


if __name__ == "__main__":
    main()
