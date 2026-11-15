"""Pesos, faixas e limites do protótipo.

Todos são suposições a calibrar com os dados simulados, sem validação clínica.
"""
from pathlib import Path

from support.i18n import N_   # marca textos exibidos na tela (a tradução é feita ao exibir)

ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"
LEXICON_DIR = DATA_DIR / "lexicon"
BASELINE_DIR = DATA_DIR / "baselines"
SENSORS_CSV = DATA_DIR / "sensores.csv"
SUPPORT_TEXTS = ROOT / "support" / "texts.json"
SUPPORT_TEXTS_EN = ROOT / "support" / "texts_en.json"   # mesmos textos, em inglês (mesma estrutura)

# --- Janela e alertas ---
WINDOW_DAYS = 7          # janela de persistência
ALERT_DAYS = 4           # tema em 4+ dias vira alerta
HISTORY_CHART_DAYS = 14  # gráfico do histórico pessoal
FOLLOWUP_MAX_DAYS = 3    # pergunta "a atividade ajudou?" por até 3 dias depois

# --- Escore-z ---
Z_CAP = 3.0              # corte do desvio ruim, em desvios-padrão
STD_FLOOR = 1e-6

# --- Cruzamento com sensores ---
SENSOR_CONFIRM_Z = 1.0   # desvio ruim acima disso confirma o tema
CONFIRM_BOOST = 0.25     # reforço na persistência quando há confirmação

# --- Índice de risco (soma 1.0) ---
W_TONE = 0.35
W_PERSIST = 0.35
W_SENSORS = 0.30
# Pesos internos do componente de sensores (sono 15, atividade 10, freq. 5 de 30)
SENSOR_WEIGHTS = {"sleep": 15 / 30, "activity": 10 / 30, "hr": 5 / 30}

# Se nenhum tema negativo apareceu hoje, a persistência de dias anteriores pesa menos.
# Faz o índice descer na recuperação em vez de ficar amarelo por uma semana.
PERSIST_NO_THEME_TODAY = 0.5

# --- Faixas ---
BAND_GREEN_MAX = 33
BAND_YELLOW_MAX = 66

# --- Temas ---
THEMES = [
    "cansaco_sono", "ansiedade", "humor_baixo", "saudade_isolamento",
    "conflito", "sobrecarga", "monotonia",
]

# Sensor que confirma cada tema (None = nenhum). Chaves: sleep, activity, hr
THEME_SENSOR = {
    "cansaco_sono": "sleep",
    "ansiedade": "hr",
    "humor_baixo": "activity",
    "saudade_isolamento": None,
    "conflito": None,
    "sobrecarga": "sleep",
    "monotonia": "activity",
}

# Rótulo amigável do tema (sem termos clínicos, RNF10)
THEME_LABELS = {
    "cansaco_sono": N_("cansaço e sono"),
    "ansiedade": N_("preocupação e tensão"),
    "humor_baixo": N_("desânimo"),
    "saudade_isolamento": N_("saudade"),
    "conflito": N_("tensão com a tripulação"),
    "sobrecarga": N_("sobrecarga"),
    "monotonia": N_("monotonia"),
}

# Humor do dia a partir do tema principal
MOOD_BY_THEME = {
    "cansaco_sono": N_("cansado"),
    "ansiedade": N_("ansioso"),
    "humor_baixo": N_("triste"),
    "saudade_isolamento": N_("com saudade"),
    "conflito": N_("irritado"),
    "sobrecarga": N_("sobrecarregado"),
    "monotonia": N_("entediado"),   # rótulo acrescentado: a lista do escopo não tinha um para monotonia
}
MOOD_LABELS = [N_("bem"), N_("cansado"), N_("ansioso"), N_("triste"), N_("irritado"),
               N_("sobrecarregado"), N_("com saudade"), N_("entediado"), N_("neutro")]
MOOD_GOOD_POLARITY = 0.2

# --- Léxico ---
MIN_STEM_LEN = 4         # termos menores casam só por igualdade exata
NEGATION_WINDOW = 2      # palavras depois de "não", "nem", "nunca"

# --- Missão simulada ---
MISSION_START_DATE = "2026-03-01"   # dia 1 da missão
MISSION_DAYS = 180
CREW_IDS = ["T1", "T2", "T3", "T4"]

# --- Demo ---
DEMO_TIMER_SECONDS = 15  # temporizador curto para ensaio; None = usar o valor real

# --- Link (Pessoa B usa) ---
DEFAULT_DELAY_SECONDS = 10
PSEUDONYM_SALT = "mindorbit-demo"


def date_for_day(day: int) -> str:
    """Data ISO correspondente ao dia da missão (dia 1 = MISSION_START_DATE)."""
    from datetime import date, timedelta
    return (date.fromisoformat(MISSION_START_DATE) + timedelta(days=day - 1)).isoformat()
