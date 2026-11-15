"""Integração com o SQLite e o link da Pessoa B. Roda num processo à parte, com banco temporário."""
import os
import subprocess
import sys
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _run(code: str, tmp_path) -> str:
    env = {k: v for k, v in os.environ.items() if k != "MINDORBIT_BACKEND"}
    env["MINDORBIT_DB"] = str(tmp_path / "t.db")
    env["PYTHONPATH"] = str(ROOT)
    r = subprocess.run([sys.executable, "-c", textwrap.dedent(code)], cwd=ROOT, env=env,
                       capture_output=True, text=True, timeout=180)
    assert r.returncode == 0, r.stderr[-2000:]
    return r.stdout


def test_entrar_no_vermelho_manda_relatorio_imediato_pelo_link(tmp_path):
    out = _run("""
        import json, storage, demo_seed, comms
        storage.init_db()
        assert storage.BACKEND_NAME.endswith("db")
        storage.set_setting("delay_mode", "manual"); storage.set_setting("delay_seconds", "0")
        demo_seed.go_to_day(111, crew_ids=["T2"])           # T2 entra no vermelho no dia 111
        comms.tick()
        reps = comms.earth_reports()
        assert [r["report"]["kind"] for r in reps] == ["imediato"], reps
        r = reps[0]["report"]
        assert r["pseudonym"].startswith("A-") and r["period_end_day"] == 111
        assert "text" not in r and "T2" not in json.dumps(r)
        print("OK")
    """, tmp_path)
    assert "OK" in out


def test_blackout_retem_libera_e_mensagem_da_terra_volta(tmp_path):
    out = _run("""
        import storage, demo_seed, comms
        from support import report as rm
        storage.init_db()
        storage.set_setting("delay_mode", "manual"); storage.set_setting("delay_seconds", "0")
        storage.set_setting("blackout", "1")
        demo_seed.go_to_day(111, crew_ids=["T2"])
        comms.tick()
        assert comms.earth_reports() == []
        assert any(p["status"].startswith("retido") for p in comms.queue_status())
        info = rm.last_sent("T2", "imediato"); assert info and info.held
        storage.set_setting("blackout", "0"); comms.tick(); comms.tick()
        assert comms.earth_reports()
        comms.send_directive(rm.pseudonym("T2"), "Vamos conversar na próxima janela.")
        comms.tick()
        assert [d.text for d in comms.pull_directives("T2")] == ["Vamos conversar na próxima janela."]
        print("OK")
    """, tmp_path)
    assert "OK" in out


def test_aviso_de_leitura_volta_pelo_link_com_atraso_e_blackout(tmp_path):
    out = _run("""
        import storage, comms
        from support import report as rm
        storage.init_db()
        storage.set_setting("delay_mode", "manual"); storage.set_setting("delay_seconds", "0")
        pseud = rm.pseudonym("T2")
        comms.send_directive(pseud, "Como você está?")
        assert comms.earth_messages(pseud)[0]["status"] == "enviada"
        comms.tick()                                   # a mensagem chega à nave e o aviso de entrega sai
        d = comms.pull_directives("T2")[0]
        assert d.ref is not None and not d.read
        comms.tick()
        assert comms.earth_messages(pseud)[0]["status"] == "entregue"
        storage.set_setting("blackout", "1")           # o tripulante lê durante o blackout
        storage.mark_read(d.id); assert comms.acknowledge_read(d.id)
        comms.tick(); comms.tick()
        assert comms.earth_messages(pseud)[0]["status"] == "entregue" and comms.unseen_reads() == []
        storage.set_setting("blackout", "0"); comms.tick(); comms.tick()
        m = comms.earth_messages(pseud)[0]
        assert m["status"] == "lida" and m["read_day"] == 1 and len(comms.unseen_reads()) == 1
        comms.mark_reads_seen(); assert comms.unseen_reads() == []
        assert any("confirmação" in p["conteúdo"] for p in comms.queue_status())
        print("OK")
    """, tmp_path)
    assert "OK" in out


def test_blackout_com_duracao_libera_a_fila_sozinho(tmp_path):
    out = _run("""
        import storage, demo_seed, comms
        from support import link_status as ls
        storage.init_db()
        storage.set_setting("delay_mode", "manual"); storage.set_setting("delay_seconds", "0")
        demo_seed.go_to_day(109, crew_ids=["T2"], include_day=False)
        ls.start_blackout(duration_days=2)                  # volta no dia 111
        demo_seed.go_to_day(111, crew_ids=["T2"], include_day=False)   # o dia chega; o diário ainda não
        assert ls.link_status().active                      # terminou sozinho
        demo_seed.fill_missing(111, ["T2"])                 # o relatório imediato sai, agora com o link ativo
        comms.tick(); comms.tick()
        assert any(r["report"]["kind"] == "imediato" for r in comms.earth_reports())
        print("OK")
    """, tmp_path)
    assert "OK" in out


def test_historico_simulado_nao_gera_relatorios_retroativos(tmp_path):
    out = _run("""
        import storage, demo_seed, comms
        storage.init_db()
        storage.set_setting("delay_mode", "manual"); storage.set_setting("delay_seconds", "0")
        demo_seed.go_to_day(63, include_day=False)
        comms.tick(); assert comms.earth_reports() == []
        assert demo_seed.missing_crews(63) == ["T1", "T2", "T3", "T4"]
        print("OK")
    """, tmp_path)
    assert "OK" in out


def test_contramedidas_e_sensores_no_sqlite(tmp_path):
    out = _run("""
        import storage, demo_seed
        storage.init_db()
        demo_seed.go_to_day(66, crew_ids=["T1"])
        assert storage.get_sensor_day("T1", "2026-03-05") is not None      # chegou ao banco
        logs = storage.list_countermeasures("T1", 30)
        assert logs
        cm = logs[-1]
        assert storage.get_pending_followup("T1", cm.day + 1) is not None
        storage.record_followup(cm.id, True, True)
        p = storage.get_pending_followup("T1", cm.day + 1)
        assert p is None or p.id != cm.id          # a respondida deixa de ser pendente
        print("OK")
    """, tmp_path)
    assert "OK" in out


def test_dados_antigos_no_banco_somem_ao_reiniciar(tmp_path):
    out = _run("""
        import storage, demo_seed, comms
        storage.init_db()
        demo_seed.go_to_day(30)
        storage.reset_demo()
        assert int(storage.get_setting("sim_day")) == 1
        assert demo_seed.all_analyses("T2") == [] and comms.earth_reports() == []
        from ingest.source import baseline_for
        assert baseline_for("T2")[1] is False                    # os padrões continuam
        demo_seed.go_to_day(8)
        assert [a.risk <= 20 for a in demo_seed.all_analyses("T2")] == [True] * 8   # sem restos de dados velhos
        print("OK")
    """, tmp_path)
    assert "OK" in out


def test_app_abre_sem_erro_com_sqlite(tmp_path):
    import pytest
    pytest.importorskip("streamlit")
    out = _run("""
        from streamlit.testing.v1 import AppTest
        at = AppTest.from_file("app.py", default_timeout=60).run()
        assert not at.exception, at.exception
        print("OK")
    """, tmp_path)
    assert "OK" in out


def test_dados_da_demo_passam_nos_criterios_da_pessoa_b(tmp_path):
    r = subprocess.run([sys.executable, "scripts/check_data.py"], cwd=ROOT, capture_output=True, text=True,
                       env={**os.environ, "MINDORBIT_DB": str(tmp_path / "c.db"), "PYTHONPATH": str(ROOT)},
                       timeout=180)
    assert r.returncode == 0, r.stdout[-1500:] + r.stderr[-500:]
    assert "0 FALHOU" in r.stdout
