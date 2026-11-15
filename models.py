"""Contratos de dados do MindOrbit (compartilhados entre Pessoa A e Pessoa B).

Mudar um campo aqui exige avisar a outra pessoa.
"""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SensorDay:
    date: str
    crew_id: str
    sleep_h: float
    activity_min: float
    hr_rest: float


@dataclass
class Baseline:
    """Padrão de bem-estar do astronauta, criado antes do voo."""
    crew_id: str
    sleep_mean: float
    sleep_std: float
    activity_mean: float
    activity_std: float
    hr_mean: float
    hr_std: float
    polarity_mean: float
    polarity_std: float
    usual_themes: list[str] = field(default_factory=list)


@dataclass
class Entry:
    id: Optional[int]
    crew_id: str
    day: int
    date: str
    text: str


@dataclass
class Analysis:
    entry_id: int
    crew_id: str
    day: int
    themes: list[str]
    polarity: float
    z: dict[str, float]               # chaves: sleep, activity, hr, polarity
    persistence: dict[str, int]       # tema -> dias na janela de 7
    alerts: list[str]                 # temas em 4+ dias
    confirmed_by: dict[str, str]      # tema -> sensor que confirma
    risk: int                         # 0-100
    band: str                         # "verde" | "amarelo" | "vermelho"
    main_theme: Optional[str]
    mood: str
    mood_confirmed: Optional[str] = None


@dataclass
class Countermeasure:
    theme: str
    title: str
    steps: list[str]
    timer_seconds: Optional[int] = None


@dataclass
class Feedback:
    text: str
    reason: str                       # cita o tema ou o sensor (RNF06)
    countermeasure: Optional[Countermeasure]
    escalate: bool


@dataclass
class Report:
    """Relatório clínico para a equipe de saúde da Terra. O astronauta NÃO o vê: só recebe o aviso
    de que foi enviado. Nunca contém texto do diário nem dados brutos de sensores (RNF03).

    Contrato v5 (v4 + contextos que se repetem ou fogem do habitual).
    """
    pseudonym: str                    # fixo na missão, ex.: "A-70BB90"
    period_start_day: int             # dia da missão (não data de calendário)
    period_end_day: int               # = dia atual da missão
    mission_total_days: int           # ex.: 180
    kind: str                         # "semanal" | "imediato"
    risk: int
    band: str
    risk_breakdown: dict[str, float]  # pontos do índice: tone, persistence, sensors (máx. 35, 35, 30)
    breakdown_notes: list[str]        # ajustes que mudaram a persistência
    onset_day: Optional[int]          # dia em que a piora atual começou (None se não há piora)
    trend: list[int]                  # índice dos últimos 7 dias
    theme_days: dict[str, int]        # tema -> dias na janela
    alert_reasons: list[str]          # qual tema ou sensor gerou o alerta (RNF06)
    sensor_dev: dict[str, str]        # sleep/activity/hr -> dentro|abaixo|bem abaixo|acima|bem acima
    discordance: list[str]            # quando o texto não reclama mas um sensor desvia muito
    mood: Optional[str]               # só se o astronauta confirmou
    support: list[dict]               # {"title", "days", "answer"}
    missing_diary_days: list[int]     # dias da semana sem entrada (o silêncio é um sinal)
    data_days: dict[str, int]         # {"janela", "diario", "sensores"}: dias com dados na semana
    last_directive_read: Optional[bool]   # None = a Terra ainda não enviou mensagem
    immediate: bool                   # True quando kind == "imediato"
    # --- v4: mais descritivo para a equipe de saúde ---
    summary: str                      # parágrafo-resumo em linguagem clara (sem datas de calendário)
    trend_days: list[int]             # dias da missão correspondentes a `trend`
    trend_bands: list[str]            # faixa de cada dia de `trend`
    week: dict                        # {"mean", "worst", "worst_day", "bands": {verde, amarelo, vermelho}, "days"}
    prev_week: Optional[dict]         # o mesmo para a semana anterior (None se ainda não existe)
    breakdown_why: dict[str, str]     # tone/persistence/sensors -> frase explicando os pontos
    sensor_days_off: dict[str, int]   # sensor -> dias da semana fora do padrão (na direção ruim)
    habitual_themes: list[str]        # temas da semana que já são habituais para este tripulante
    mission_context: dict             # {"episodes": [{start, end, peak, ongoing}], "days_not_green", "days_total"}
    # --- v5: contextos que se repetem ou fogem do habitual (só categorias do catálogo e contagens de dias) ---
    contexts: dict                    # {"recurring": [...], "out_of_norm": [{kind, text}], "combos": [{text}], ...}


@dataclass
class Directive:
    id: Optional[int]
    crew_id: str
    text: str
    sent_at: str
    read: bool = False
    ref: Optional[int] = None         # número da mensagem na Terra (para o aviso de leitura voltar a ela)


@dataclass
class CountermeasureLog:
    """Contramedida sugerida ao astronauta e o que aconteceu depois (RF18)."""
    id: Optional[int]
    entry_id: int
    crew_id: str
    day: int
    theme: str
    title: str
    done: Optional[bool] = None       # None = ainda não respondeu
    helped: Optional[bool] = None
