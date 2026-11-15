"""Catálogo de contramedidas guiadas por tema (RF10)."""
from typing import Optional

import config
from models import Countermeasure
from support.i18n import N_, t

CATALOG: dict[str, Countermeasure] = {
    "cansaco_sono": Countermeasure(
        theme="cansaco_sono",
        title=N_("Rotina de sono"),
        steps=[
            N_("Escolha um horário fixo para se deitar hoje e para acordar amanhã."),
            N_("Reduza a luz do ambiente uma hora antes de dormir."),
            N_("Deixe telas e tarefas para depois do descanso."),
        ],
    ),
    "ansiedade": Countermeasure(
        theme="ansiedade",
        title=N_("Respiração guiada de 3 minutos"),
        steps=[
            N_("Sente-se com as costas apoiadas e os ombros soltos."),
            N_("Inspire pelo nariz contando até 4, segure até 2 e solte devagar contando até 6."),
            N_("Repita até o temporizador terminar."),
        ],
        timer_seconds=180,
    ),
    "humor_baixo": Countermeasure(
        theme="humor_baixo",
        title=N_("Uma atividade prazerosa agendada"),
        steps=[
            N_("Escolha algo que você gosta e cabe hoje: música, leitura ou um jogo."),
            N_("Marque um horário e reserve 20 minutos para isso."),
            N_("Depois, anote no diário como se sentiu."),
        ],
    ),
    "saudade_isolamento": Countermeasure(
        theme="saudade_isolamento",
        title=N_("Mensagem para a família e atividade em grupo"),
        steps=[
            N_("Grave uma mensagem curta para alguém de casa."),
            N_("Convide alguém da tripulação para uma atividade juntos hoje."),
        ],
    ),
    "conflito": Countermeasure(
        theme="conflito",
        title=N_("Tempo a sós e roteiro de conversa"),
        steps=[
            N_("Reserve 15 minutos sozinho para esfriar a cabeça."),
            N_("Depois, escolha um momento calmo para conversar."),
            N_("Comece descrevendo como você se sentiu, sem apontar culpados."),
        ],
        timer_seconds=900,
    ),
    "sobrecarga": Countermeasure(
        theme="sobrecarga",
        title=N_("Pausa programada e três prioridades"),
        steps=[
            N_("Faça uma pausa de 10 minutos agora."),
            N_("Liste as três tarefas que realmente precisam acontecer hoje."),
            N_("O resto pode esperar, e dá para avisar a tripulação."),
        ],
        timer_seconds=600,
    ),
    "monotonia": Countermeasure(
        theme="monotonia",
        title=N_("Uma atividade nova"),
        steps=[
            N_("Escolha uma atividade nova da lista da missão."),
            N_("Reserve um horário para ela ainda hoje."),
        ],
    ),
    # Usada quando o alerta vem só do tom ou dos sensores, sem um tema claro.
    "geral": Countermeasure(
        theme="geral",
        title=N_("Pausa curta"),
        steps=[
            N_("Faça uma pausa de 2 minutos longe das tarefas."),
            N_("Beba água e alongue os ombros e o pescoço."),
        ],
        timer_seconds=120,
    ),
}

# Quando não há tema, o sensor que mais desvia aponta a contramedida
_SENSOR_TO_THEME = {"sleep": "cansaco_sono", "hr": "ansiedade", "activity": "humor_baixo"}


def get_countermeasure(theme: Optional[str]) -> Countermeasure:
    base = CATALOG.get(theme or "geral", CATALOG["geral"])
    timer = base.timer_seconds
    # No ensaio da demo, o temporizador pode ser encurtado em config.py
    if timer is not None and config.DEMO_TIMER_SECONDS is not None:
        timer = min(timer, config.DEMO_TIMER_SECONDS)
    return Countermeasure(base.theme, t(base.title), [t(s) for s in base.steps], timer)


def theme_from_sensors(bad_dev: dict[str, float]) -> Optional[str]:
    """Tema sugerido pelo sensor mais desviado (ou None se nenhum desvia)."""
    sensor_dev = {s: bad_dev.get(s, 0.0) for s in _SENSOR_TO_THEME}
    worst = max(sensor_dev, key=sensor_dev.get)
    return _SENSOR_TO_THEME[worst] if sensor_dev[worst] > config.SENSOR_CONFIRM_Z else None
