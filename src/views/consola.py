"""Utilidades de presentación en consola: colores, entradas validadas y tablas."""

import os
import sys
from enum import Enum
from typing import Callable, TypeVar

import pandas as pd
import readchar
from colorama import Fore, Style, just_fix_windows_console

from src.exceptions import LogisticaError

E = TypeVar("E", bound=Enum)

just_fix_windows_console()
pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 20)
pd.set_option("display.max_colwidth", 30)

_ES_TERMINAL = sys.stdin.isatty()


class VolverAtras(Exception):
    """Se lanza cuando el usuario cancela una carga escribiendo 'x'."""


# --- salida -----------------------------------------------------------------------
def limpiar() -> None:
    if _ES_TERMINAL:
        os.system("cls" if os.name == "nt" else "clear")


def titulo(texto: str) -> None:
    linea = "═" * (len(texto) + 4)
    print(f"\n{Fore.CYAN}{Style.BRIGHT}╔{linea}╗\n║  {texto}  ║\n╚{linea}╝{Style.RESET_ALL}")


def subtitulo(texto: str) -> None:
    print(f"\n{Fore.CYAN}{Style.BRIGHT}── {texto} ──{Style.RESET_ALL}")


def exito(texto: str) -> None:
    print(f"{Fore.GREEN}✔ {texto}{Style.RESET_ALL}")


def error(texto: str) -> None:
    print(f"{Fore.RED}✘ {texto}{Style.RESET_ALL}")


def advertencia(texto: str) -> None:
    print(f"{Fore.YELLOW}⚠ {texto}{Style.RESET_ALL}")


def info(texto: str) -> None:
    print(f"{Fore.WHITE}{Style.DIM}{texto}{Style.RESET_ALL}")


def mostrar_tabla(df: pd.DataFrame, vacio: str = "No hay registros para mostrar.") -> None:
    if df.empty:
        advertencia(vacio)
        return
    print(df.to_string(index=False))


def moneda(valor: float) -> str:
    """Formato argentino: $ 12.345,67"""
    return "$ " + f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


# --- entrada ----------------------------------------------------------------------
def _leer_tecla() -> str:
    """Lee una tecla sin Enter (readchar). Sin terminal real, usa input()."""
    if _ES_TERMINAL:
        return readchar.readkey()
    return (input() or " ")[0]


def pausa(mensaje: str = "Presioná una tecla para continuar...") -> None:
    print(f"\n{Style.DIM}{mensaje}{Style.RESET_ALL}", end="", flush=True)
    _leer_tecla()
    print()


def confirmar(pregunta: str) -> bool:
    print(f"{Fore.YELLOW}{pregunta} [s/n]: {Style.RESET_ALL}", end="", flush=True)
    while True:
        tecla = _leer_tecla().lower()
        if tecla in ("s", "n"):
            print(tecla)
            return tecla == "s"


def menu(opciones: dict[str, str], encabezado: str | None = None) -> str:
    """Muestra opciones y devuelve la tecla elegida (una sola pulsación)."""
    if encabezado:
        titulo(encabezado)
    for tecla, texto in opciones.items():
        color = Fore.RED if tecla == "0" else Fore.YELLOW
        print(f"  {color}{Style.BRIGHT}[{tecla}]{Style.RESET_ALL} {texto}")
    print(f"\n{Style.DIM}Elegí una opción:{Style.RESET_ALL} ", end="", flush=True)
    while True:
        tecla = _leer_tecla().lower()
        if tecla in opciones:
            print(tecla)
            return tecla


def _input(etiqueta: str, actual: object | None) -> str:
    sufijo = f" {Style.DIM}[{actual}]{Style.RESET_ALL}" if actual is not None else ""
    valor = input(f"  {etiqueta}{sufijo}: ").strip()
    if valor.lower() == "x":
        raise VolverAtras()
    return valor


def pedir_texto(etiqueta: str, actual: str | None = None) -> str:
    """Texto obligatorio. Con `actual`, Enter conserva el valor (modo edición)."""
    while True:
        valor = _input(etiqueta, actual)
        if valor:
            return valor
        if actual is not None:
            return actual
        error("El campo es obligatorio (x para cancelar).")


def pedir_entero(etiqueta: str, minimo: int | None = None) -> int:
    while True:
        valor = _input(etiqueta, None)
        try:
            numero = int(valor)
        except ValueError:
            error("Ingresá un número entero válido (x para cancelar).")
            continue
        if minimo is not None and numero < minimo:
            error(f"El valor debe ser mayor o igual a {minimo}.")
            continue
        return numero


def pedir_decimal(etiqueta: str, actual: float | None = None, minimo_exclusivo: float = 0.0,
                  maximo: float | None = None) -> float:
    while True:
        valor = _input(etiqueta, actual)
        if not valor and actual is not None:
            return actual
        try:
            numero = float(valor.replace(",", "."))  # acepta coma decimal
        except ValueError:
            error("Ingresá un número válido, p. ej. 2,5 (x para cancelar).")
            continue
        if numero <= minimo_exclusivo:
            error(f"El valor debe ser mayor a {minimo_exclusivo:g}.")
            continue
        if maximo is not None and numero > maximo:
            error(f"El valor no puede superar {maximo:g}.")
            continue
        return numero


def pedir_opcion_enum(etiqueta: str, enum_cls: type[E], actual: E | None = None,
                      opciones: list[E] | None = None) -> E:
    """Lista los valores del Enum numerados y devuelve el elegido."""
    valores = opciones if opciones is not None else list(enum_cls)
    print(f"  {etiqueta}:")
    for i, valor in enumerate(valores, start=1):
        marca = f" {Style.DIM}(actual){Style.RESET_ALL}" if valor == actual else ""
        print(f"    {Fore.YELLOW}{i}{Style.RESET_ALL}. {valor.value}{marca}")
    while True:
        texto = _input("Opción", actual.value if actual is not None else None)
        if not texto and actual is not None:
            return actual
        if texto.isdigit() and 1 <= int(texto) <= len(valores):
            return valores[int(texto) - 1]
        error(f"Elegí un número entre 1 y {len(valores)} (x para cancelar).")


# --- ejecución segura de acciones ------------------------------------------------
def ejecutar_accion(accion: Callable[[], None]) -> None:
    """Ejecuta una acción del menú mostrando los errores de negocio sin cortar la app."""
    try:
        accion()
    except VolverAtras:
        info("Operación cancelada.")
    except LogisticaError as e:
        error(str(e))
    pausa()
