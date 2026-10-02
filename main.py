"""Punto de entrada de la Plataforma de Gestión Logística.

Ejecutar desde la raíz del proyecto:
    python main.py
"""

import sys


def main() -> int:
    # Evita errores de codificación con tildes/emojis si la salida se redirige
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    # imports diferidos: si falta una dependencia se informa con un mensaje claro
    from colorama import Fore, Style

    from src.exceptions import LogisticaError
    from src.views.app import App

    try:
        App().ejecutar()
    except KeyboardInterrupt:
        print(f"\n{Fore.CYAN}Programa interrumpido. ¡Hasta luego!{Style.RESET_ALL}")
    except LogisticaError as e:
        print(f"{Fore.RED}Error: {e}{Style.RESET_ALL}")
        return 1
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except ModuleNotFoundError as e:
        print(f"Falta instalar una dependencia ({e.name}). Ejecutá: pip install -r requirements.txt")
        sys.exit(1)
