"""Relatório para a Terra (RF13): um só formato, o da nave (support/report.py, contrato v3).

A Pessoa B cuida do transporte (fila, atraso, blackout, criptografia); o conteúdo do relatório
é montado por support/report.py, que já aplica o anonimato e nunca inclui o texto do diário (RNF03).
"""
from support.report import build_report  # noqa: F401
