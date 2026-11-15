"""Escolhe o armazenamento: o SQLite da Pessoa B (storage/db.py) se existir;
senão, o armazenamento em memória da Pessoa A (storage/memory_db.py)."""
import os

# MINDORBIT_BACKEND=memory força o armazenamento em memória (usado pelos testes unitários).
if os.environ.get("MINDORBIT_BACKEND") == "memory":
    from storage import memory_db as backend  # noqa: F401
else:
    try:
        from storage import db as backend  # noqa: F401
    except ImportError:
        from storage import memory_db as backend  # noqa: F401

init_db = backend.init_db
reset_demo = backend.reset_demo
save_entry = backend.save_entry
save_analysis = backend.save_analysis
get_history = backend.get_history
list_entries_text = backend.list_entries_text
get_setting = backend.get_setting
set_setting = backend.set_setting
list_directives = backend.list_directives
mark_read = backend.mark_read
BACKEND_NAME = backend.__name__

# Opcionais (Pessoa B): se existirem, o app lê sensores e padrões do banco
get_sensor_day = getattr(backend, "get_sensor_day", None)
get_baseline = getattr(backend, "get_baseline", None)

# Acompanhamento da contramedida (RF18): opcional; sem ele, o app só não pergunta
save_countermeasure = getattr(backend, "save_countermeasure", None)
get_pending_followup = getattr(backend, "get_pending_followup", None)
record_followup = getattr(backend, "record_followup", None)
list_countermeasures = getattr(backend, "list_countermeasures", None)

# Envio de mensagens da Terra (opcional): a aba da Terra de reserva só mostra o formulário se existir
save_directive = getattr(backend, "save_directive", None)
