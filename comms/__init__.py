"""Comunicação nave ↔ Terra (Pessoa B).

O que a aba do astronauta usa (contrato com a Pessoa A):
    send_report(crew_id, immediate)   gera o relatório, empacota e põe na fila de subida
    pull_directives(crew_id)          entrega o que já chegou da Terra e devolve os direcionamentos

O que a aba da Terra usa:
    send_directive(pseudonym, text), earth_reports(), queue_status(), earth_messages(), unseen_reads()
"""
from comms.link import (earth_messages, earth_reports, mark_reads_seen, queue_status, send_ack,
                        send_directive, tick, unseen_reads)
from comms.report import build_report

__all__ = ["send_report", "send_weekly_reports", "pull_directives", "send_directive", "earth_reports",
           "queue_status", "tick", "earth_messages", "unseen_reads", "mark_reads_seen", "acknowledge_read", "build_report"]


def send_report(crew_id: str, immediate: bool) -> None:
    """RF13: relatório semanal, ou imediato quando o índice entra no vermelho. Sem texto do diário."""
    from comms.link import enqueue_up
    report = build_report(crew_id, immediate)
    if report is not None:
        enqueue_up(report)


def send_weekly_reports() -> int:
    """Atalho de demonstração: envia agora um relatório semanal de cada tripulante com histórico.

    O envio normal é automático (support.report.after_entry, nos dias 7, 14, 21…).
    Este atalho também registra o envio, para o aviso do astronauta continuar certo.
    """
    import config
    import storage
    from comms.link import enqueue_up
    from support import report as report_mod
    n = 0
    for crew_id in config.CREW_IDS:
        report = build_report(crew_id, immediate=False)
        if report is not None:
            enqueue_up(report)
            storage.set_setting(f"weekly_sent_{crew_id}", str(report.period_end_day))
            report_mod.record_sent(crew_id, report.period_end_day, "semanal")
            n += 1
    return n


def acknowledge_read(directive_id: int) -> bool:
    """A nave avisa a Terra que o tripulante leu a mensagem. Só vale para mensagens que vieram da Terra."""
    from storage import db
    from support.report import pseudonym
    directive = db.get_directive(directive_id)
    if directive is None or directive.ref is None:
        return False
    send_ack(pseudonym(directive.crew_id), directive.ref, "lida")
    return True


def pull_directives(crew_id: str):
    """Processa a fila (entrega o que já chegou) e devolve os direcionamentos desse tripulante."""
    import storage
    tick()
    return storage.list_directives(crew_id)
