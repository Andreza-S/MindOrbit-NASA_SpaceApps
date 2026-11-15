import storage
from support import link_status as ls


def _modo_manual(minutos="10"):
    storage.set_setting("delay_mode", "manual")
    storage.set_setting("delay_seconds", minutos)


def test_link_ativo_informa_o_tempo_do_sinal():
    _modo_manual("16")
    s = ls.link_status()
    assert s.active and s.one_way_min == 16 and s.round_trip_min == 32
    assert "16,0 min" in ls.astronaut_text(s) and "32,0 min" in ls.astronaut_text(s)
    assert "chega à nave em cerca de 16,0 min" == ls.pending_eta(s)
    assert ls.short_text(s).startswith("📡 Link ativo")


def test_tempo_real_nasa_jpl_no_modo_padrao():
    storage.set_setting("sim_day", "1")
    s = ls.link_status()
    assert 15 < s.one_way_min < 21                      # 19,5 min no começo da missão


def test_blackout_com_previsao_e_fim_automatico():
    _modo_manual()
    storage.set_setting("sim_day", "10")
    ls.start_blackout(duration_days=3)
    s = ls.link_status()
    assert not s.active and s.until_day == 13 and s.days_left == 3 and s.last_contact_day == 9
    assert "previsão é voltar no dia 13 (em 3 dias)" in ls.astronaut_text(s)
    assert "O seu apoio a bordo continua funcionando." in ls.astronaut_text(s)
    assert "Último contato no dia 9" in ls.earth_text(s) and "retida até o link voltar" == ls.pending_eta(s)
    storage.set_setting("sim_day", "12")
    assert ls.link_status().days_left == 1
    storage.set_setting("sim_day", "13")
    assert ls.link_status().active                      # o dia previsto chegou: o link volta sozinho
    assert str(storage.get_setting("blackout")) == "0"


def test_blackout_sem_previsao():
    _modo_manual()
    ls.start_blackout()
    s = ls.link_status()
    assert not s.active and s.until_day is None and s.days_left is None
    assert "Ainda não há previsão de retorno" in ls.astronaut_text(s)
    assert "sem previsão de retorno" in ls.short_text(s)
    ls.end_blackout()
    assert ls.link_status().active


def test_formato_do_tempo():
    assert ls.fmt_minutes(15.6) == "15,6 min" and ls.fmt_minutes(90) == "1,5 h"
