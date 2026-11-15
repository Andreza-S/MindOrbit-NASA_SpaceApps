import config
import demo_seed
import storage


def test_salto_preenche_historico_de_todos_e_mantem_o_dia():
    gravados = demo_seed.go_to_day(30)
    assert set(gravados) == set(config.CREW_IDS) and all(n == 30 for n in gravados.values())
    assert int(storage.get_setting("sim_day")) == 30
    assert demo_seed.missing_crews(30) == []
    assert demo_seed.go_to_day(30) == {}                  # idempotente


def test_sem_incluir_o_dia_ele_fica_em_branco_e_o_diario_e_obrigatorio():
    demo_seed.go_to_day(30, include_day=False)
    assert int(storage.get_setting("sim_day")) == 30
    assert demo_seed.missing_crews(30) == list(config.CREW_IDS)
    assert demo_seed.missing_crews(29) == []
    assert demo_seed.fill_missing(30, ["T1"]) == ["T1"]
    assert demo_seed.missing_crews(30) == ["T2", "T3", "T4"]
    assert demo_seed.fill_missing(30) == ["T2", "T3", "T4"]
    assert demo_seed.missing_crews(30) == []


def test_voltar_no_tempo_nao_apaga_nada():
    demo_seed.go_to_day(40)
    demo_seed.go_to_day(10)
    assert int(storage.get_setting("sim_day")) == 10
    assert [a.day for a in storage.get_history("T1", 30)] == list(range(1, 11))   # só enxerga até o dia 10
    assert len(demo_seed.all_analyses("T1")) == 40                                 # o resto continua guardado


def test_limites_do_dia():
    demo_seed.go_to_day(500, crew_ids=["T4"])
    assert int(storage.get_setting("sim_day")) == config.MISSION_DAYS
    demo_seed.go_to_day(0, crew_ids=["T4"])
    assert int(storage.get_setting("sim_day")) == 1


def test_reiniciar_a_demo_apaga_tudo_e_volta_ao_dia_1():
    demo_seed.go_to_day(40)
    storage.set_setting("delay_mode", "manual")
    storage.reset_demo()
    assert int(storage.get_setting("sim_day")) == 1
    assert demo_seed.all_analyses("T1") == []
    assert storage.get_setting("delay_mode") == "manual"          # preferência do link fica
    demo_seed.go_to_day(10)
    assert len(demo_seed.all_analyses("T1")) == 10
