"""Roda o fluxo A (apoio a bordo) sem Streamlit, para conferir o núcleo de ponta a ponta.

    python scripts/cli_demo.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
import storage
from core.pipeline import analyze_entry
from ingest.baseline import load_baseline_or_default
from models import Entry, SensorDay
from support.feedback import build_feedback

# (dia, texto, sono_h, atividade_min, fc_repouso)
DIAS = [
    (1, "Dia tranquilo, treinei e estou bem. Foi um ótimo dia, estou feliz.", 7.3, 50, 58),
    (2, "Rotina normal, tudo certo. Me sinto calmo e produtivo.", 7.0, 46, 59),
    (3, "Dormi pouco e acordei cansado, mas segui as tarefas.", 6.6, 44, 60),
    (4, "Não consegui dormir direito de novo, estou exausto.", 6.0, 40, 62),
    (5, "Insônia outra vez. Estou muito cansado e preocupado com as tarefas.", 5.8, 36, 64),
    (6, "Exausto. Acordei várias vezes, não estou bem e a pressão do prazo aumentou.", 5.6, 33, 65),
    (7, "Não aguento mais esse cansaço, estou esgotado e sozinho.", 5.4, 30, 66),
]


def main() -> None:
    crew = "T1"
    baseline, example = load_baseline_or_default(crew)
    print(f"Armazenamento: {storage.BACKEND_NAME} | padrão de exemplo: {example}\n")
    for day, text, sleep, act, hr in DIAS:
        storage.set_setting("sim_day", str(day))
        entry = Entry(None, crew, day, config.date_for_day(day), text)
        entry.id = storage.save_entry(entry)
        history = storage.get_history(crew, config.WINDOW_DAYS)
        sensors = SensorDay(entry.date, crew, sleep, act, hr)
        a = analyze_entry(entry, history, baseline, sensors)
        fb = build_feedback(a)
        storage.save_analysis(a)
        print(f"Dia {day}: índice {a.risk:3d} [{a.band:8s}] humor={a.mood:14s} "
              f"temas={a.themes} alertas={a.alerts}")
        if fb.reason:
            print(f"        motivo: {fb.reason}")
        if fb.countermeasure:
            print(f"        contramedida: {fb.countermeasure.title}")
        if fb.escalate:
            print("        >>> ESCALONAR: oficial médico + relatório imediato à Terra")


if __name__ == "__main__":
    main()
