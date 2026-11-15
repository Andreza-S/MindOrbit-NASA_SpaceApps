import demo_seed
from ui import earth_data


def test_overview_sem_dados_e_ordem():
    rows = earth_data.overview_rows(["T3", "T4"])
    assert all(r["sem_dados"] for r in rows)


def test_overview_ordena_por_atencao():
    demo_seed.go_to_day(114, crew_ids=["T1", "T2"])
    rows = earth_data.overview_rows(["T1", "T2", "T3"])
    assert rows[0]["crew_id"] == "T2" and rows[0]["band"] == "vermelho"   # T2 em crise, no dia 114
    assert rows[-1]["crew_id"] == "T3"                                    # sem dados fica por último
    assert earth_data.attention_needed(rows) == ["T2"]
    order = {"vermelho": 0, "amarelo": 1, "verde": 2}
    bands = [order[r["band"]] for r in rows if not r["sem_dados"]]
    assert bands == sorted(bands)


def test_todos_veem_o_mesmo_dia_da_missao():
    demo_seed.go_to_day(66, crew_ids=["T1", "T2"])
    rows = earth_data.overview_rows(["T1", "T2"])
    assert {r["day"] for r in rows} == {66}


def test_trend_e_apoio_nao_trazem_texto_do_diario():
    demo_seed.go_to_day(66, crew_ids=["T1"])
    trend = earth_data.risk_trend("T1")
    assert trend and set(trend[0]) == {"dia", "risco", "faixa"}
    assert len(earth_data.risk_trend("T1", whole_mission=True)) == 66
    assert len(trend) == 14
    rows = earth_data.support_rows("T1")
    assert rows
    for row in rows:
        assert set(row) == {"contramedida", "dias", "respostas"}


def test_opcoes_de_periodo_seguem_os_dias_que_existem():
    assert list(earth_data.view_options(1)) == ["all"]
    assert list(earth_data.view_options(7)) == ["7", "all", "range", "day"]
    assert list(earth_data.view_options(20)) == ["7", "15", "all", "range", "day"]
    assert list(earth_data.view_options(152)) == ["7", "15", "30", "60", "90", "all", "range", "day"]
    assert "dia 1 ao dia 152" in earth_data.view_options(152)["all"]


def test_periodo_escolhido_nunca_passa_do_dia_atual():
    assert earth_data.resolve_view("15", 40)[:2] == (26, 40)
    assert earth_data.resolve_view("all", 7)[:2] == (1, 7)
    assert earth_data.resolve_view("range", 50, 100, 300)[:2] == (50, 50)
    assert earth_data.resolve_view("range", 50, 10, 30)[:2] == (10, 30)
    assert earth_data.resolve_view("day", 50, day=999)[:2] == (36, 50)
    assert earth_data.resolve_view("day", 50, day=3)[:2] == (1, 3)


def test_grafico_e_numeros_seguem_o_periodo():
    demo_seed.go_to_day(40, crew_ids=["T1"])
    pts = earth_data.risk_range("T1", 26, 40)
    assert [p["dia"] for p in pts] == list(range(26, 41))
    st = earth_data.period_stats("T1", 26, 40)
    assert st["days"] == 15 and st["worst"] == max(p["risco"] for p in pts)
    assert earth_data.period_stats("T1", 1, 5)["days"] == 5


def test_relatorio_de_um_dia_passado_nao_muda_o_dia_da_missao():
    import storage
    demo_seed.go_to_day(70, crew_ids=["T1"])
    antigo = earth_data.report_at("T1", 63)                 # T1 em pleno episódio
    assert antigo.period_end_day == 63 and antigo.band == "vermelho"
    assert int(storage.get_setting("sim_day")) == 70
    assert earth_data.clinical_report("T1").period_end_day == 70


def test_apoio_do_periodo_escolhido():
    demo_seed.go_to_day(66, crew_ids=["T1"])
    todos = earth_data.support_rows("T1", 1, 66)
    recorte = earth_data.support_rows("T1", 62, 63)
    assert todos and recorte and sum(1 for _ in recorte) <= sum(1 for _ in todos)
