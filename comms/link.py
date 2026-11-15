"""Fila do link nave ↔ Terra, com atraso e blackout (RF15, RNF02).

Nada espera resposta: a nave só põe pacotes na fila. Cada pacote só sai quando não há
blackout e chega delay_seconds depois (demonstração acelerada do atraso Terra–Marte).
"""
import dataclasses
import json
import time
from datetime import datetime

import storage
from comms.package import pack, unpack
from models import Directive, Report
from storage import db
from support.i18n import t

RETIDO = 1e18      # deliver_at de um pacote retido pelo blackout


def _blackout() -> bool:
    return storage.get_setting("blackout") == "1"


def _delay() -> float:
    """Segundos de atraso na demo. No modo "jpl", 1 minuto real de atraso Terra–Marte vira 1 s na tela."""
    if storage.get_setting("delay_mode") == "jpl":
        from simulator.light_delay import atraso_minutos
        return atraso_minutos(int(storage.get_setting("sim_day")))
    return float(storage.get_setting("delay_seconds"))


def _enqueue(direction: str, obj: dict) -> int:
    payload, checksum = pack(obj)
    agora = time.time()
    deliver_at = RETIDO if _blackout() else agora + _delay()
    with db.connect() as con:
        return con.execute("INSERT INTO link_queue (direction, payload, checksum, created_at, deliver_at) "
                           "VALUES (?, ?, ?, ?, ?)", (direction, payload, checksum, agora, deliver_at)).lastrowid


def enqueue_up(report: Report) -> int:
    return _enqueue("up", {"kind": "report", **dataclasses.asdict(report)})


def _mission_day() -> int:
    return int(storage.get_setting("sim_day"))


def send_directive(pseudonym: str, text: str) -> int:
    """Terra → nave: mensagem do psicólogo, pelo mesmo link. Fica registrada como "enviada" até a nave confirmar."""
    with db.connect() as con:
        ref = con.execute("INSERT INTO earth_messages (pseudonym, text, sent_day) VALUES (?, ?, ?)",
                          (pseudonym, text, _mission_day())).lastrowid
    return _enqueue("down", {"kind": "directive", "pseudonym": pseudonym, "text": text, "ref": ref,
                             "sent_at": datetime.now().strftime("%d/%m %H:%M")})


def send_ack(pseudonym: str, ref, status: str) -> int:
    """Nave → Terra: confirma que a mensagem chegou ("entregue") ou foi vista ("lida").

    Leva só o pseudônimo, o número da mensagem e o dia da missão. Nenhum texto.
    """
    return _enqueue("up", {"kind": "ack", "pseudonym": pseudonym, "ref": ref, "status": status,
                           "day": _mission_day()})


def tick() -> int:
    """Libera os retidos quando o blackout acaba e entrega o que já chegou. Devolve quantos entregou."""
    from support.link_status import refresh_blackout
    refresh_blackout()                 # o blackout com duração prevista termina sozinho
    agora = time.time()
    with db.connect() as con:
        if not _blackout():
            con.execute("UPDATE link_queue SET deliver_at = ? WHERE status = 'queued' AND deliver_at >= ?",
                        (agora + _delay(), RETIDO))
        prontos = con.execute("SELECT * FROM link_queue WHERE status = 'queued' AND deliver_at <= ? ORDER BY id",
                              (agora,)).fetchall()
    entregues = 0
    for p in prontos:
        try:
            obj = unpack(bytes(p["payload"]), p["checksum"])
        except ValueError:
            _status(p["id"], "rejected")
            continue
        if p["direction"] == "up" and obj.get("kind") == "ack":
            _apply_ack(obj)
        elif p["direction"] == "up":
            with db.connect() as con:
                con.execute("INSERT INTO earth_reports (pseudonym, received_at, report) VALUES (?, ?, ?)",
                            (obj["pseudonym"], datetime.now().isoformat(timespec="seconds"),
                             json.dumps(obj, ensure_ascii=False)))
        else:
            crew_id = _crew_for(obj["pseudonym"])
            if crew_id:
                db.save_directive(Directive(None, crew_id, obj["text"], obj["sent_at"], ref=obj.get("ref")))
                if obj.get("ref") is not None:
                    send_ack(obj["pseudonym"], obj["ref"], "entregue")
        _status(p["id"], "delivered")
        entregues += 1
    return entregues


def _apply_ack(obj: dict) -> None:
    """Lado da Terra: atualiza o que se sabe da mensagem. Só chega depois do atraso do sinal."""
    with db.connect() as con:
        if obj["status"] == "lida":
            con.execute("UPDATE earth_messages SET status = 'lida', read_day = ?, unseen = 1 WHERE id = ?",
                        (obj["day"], obj["ref"]))
        else:   # "entregue" nunca volta uma mensagem já lida para trás
            con.execute("UPDATE earth_messages SET status = 'entregue', delivered_day = ? "
                        "WHERE id = ? AND status = 'enviada'", (obj["day"], obj["ref"]))


def _status(packet_id: int, status: str) -> None:
    with db.connect() as con:
        con.execute("UPDATE link_queue SET status = ? WHERE id = ?", (status, packet_id))


def _crew_for(pseudonym: str):
    """Só a nave sabe quem é quem: traduz o pseudônimo de volta para o tripulante."""
    with db.connect() as con:
        r = con.execute("SELECT crew_id FROM crew WHERE pseudonym = ?", (pseudonym,)).fetchone()
    return r["crew_id"] if r else None


def earth_reports() -> list[dict]:
    """Lado da Terra: relatórios recebidos, do mais novo para o mais antigo."""
    with db.connect() as con:
        rows = con.execute("SELECT * FROM earth_reports ORDER BY id DESC").fetchall()
    return [{"id": r["id"], "pseudonym": r["pseudonym"], "received_at": r["received_at"],
             "report": json.loads(r["report"])} for r in rows]


def queue_status(limit: int = 12) -> list[dict]:
    """Últimos pacotes da fila, com o status legível."""
    agora = time.time()
    with db.connect() as con:
        rows = con.execute("SELECT * FROM link_queue ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    out = []
    for r in rows:
        if r["status"] == "delivered":
            code, status = "delivered", t("entregue")
        elif r["status"] == "rejected":
            code, status = "rejected", t("rejeitado")
        elif r["deliver_at"] >= RETIDO:
            code, status = "held", t("retido (blackout)")
        else:
            code = "transit"
            status = t("em trânsito, chega em {sec} s", sec=max(0, int(r["deliver_at"] - agora)) + 1)
        try:
            obj = unpack(bytes(r["payload"]), r["checksum"])
            if obj["kind"] == "report":
                conteudo = t("relatório {kind} · {who}", kind=t("imediato") if obj["immediate"] else t("semanal"),
                             who=obj["pseudonym"])
            elif obj["kind"] == "ack":
                conteudo = t("confirmação de {what} · {who}",
                             what=t("leitura") if obj["status"] == "lida" else t("entrega"), who=obj["pseudonym"])
            else:
                conteudo = t("direcionamento → {who}", who=obj["pseudonym"])
        except ValueError:
            conteudo = t("pacote inválido")
        out.append({"#": r["id"], "sentido": t("nave → Terra") if r["direction"] == "up" else t("Terra → nave"),
                    "conteúdo": conteudo, "bytes": len(r["payload"]), "status": status, "code": code})
    return out


def earth_messages(pseudonym=None) -> list[dict]:
    """Lado da Terra: mensagens enviadas e o que se sabe de cada uma, da mais nova para a mais antiga."""
    q, args = "SELECT * FROM earth_messages", ()
    if pseudonym:
        q, args = q + " WHERE pseudonym = ?", (pseudonym,)
    with db.connect() as con:
        rows = con.execute(q + " ORDER BY id DESC", args).fetchall()
    return [dict(r) for r in rows]


def unseen_reads() -> list[dict]:
    """Leituras novas, que a equipe ainda não viu (notificação na aba da Terra)."""
    return [m for m in earth_messages() if m["unseen"]]


def mark_reads_seen() -> None:
    with db.connect() as con:
        con.execute("UPDATE earth_messages SET unseen = 0")
