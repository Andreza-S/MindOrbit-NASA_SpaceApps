"""Preenche o histórico da demo com os diários simulados, pelo mesmo caminho do app.

Rodar na raiz do repositório:  python -m scripts.seed_db            (usa o sim_day atual)
                               python -m scripts.seed_db --dia 57   (leva a missão ao dia 57 antes)
O dia pedido fica em branco, para o astronauta escrever. Idempotente: dias que já têm análise são pulados.
Na aplicação, a barra lateral faz o mesmo com o campo "Ir para o dia da missão".
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import demo_seed  # noqa: E402
import storage  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description="Preenche o histórico da demo.")
    ap.add_argument("--dia", type=int, help="dia da missão em que a demo vai começar")
    args = ap.parse_args()
    storage.init_db()
    dia = args.dia or int(storage.get_setting("sim_day"))
    gravados = demo_seed.go_to_day(dia, include_day=False)
    print(f"Histórico até o dia {dia - 1}: {gravados or 'nada novo'}. A demo começa no dia {dia}.")


if __name__ == "__main__":
    main()
