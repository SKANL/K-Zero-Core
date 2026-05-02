"""
Herramienta: Calculadora matemática segura.

Usa el módulo `ast` para evaluar expresiones sin ejecutar código arbitrario.
Soporta: +, -, *, /, //, %, ** y funciones matemáticas comunes (sqrt, sin, cos, etc.).
"""
import ast
import math
import operator
from typing import Union

# Operadores binarios permitidos
_SAFE_BINARY_OPS: dict = {
    ast.Add:      operator.add,
    ast.Sub:      operator.sub,
    ast.Mult:     operator.mul,
    ast.Div:      operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod:      operator.mod,
    ast.Pow:      operator.pow,
}

# Operadores unarios permitidos
_SAFE_UNARY_OPS: dict = {
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

# Constantes y funciones matemáticas permitidas
_SAFE_NAMES: dict = {
    "pi":    math.pi,
    "e":     math.e,
    "tau":   math.tau,
    "inf":   math.inf,
    "sqrt":  math.sqrt,
    "cbrt":  math.cbrt,
    "abs":   abs,
    "round": round,
    "floor": math.floor,
    "ceil":  math.ceil,
    "log":   math.log,
    "log2":  math.log2,
    "log10": math.log10,
    "sin":   math.sin,
    "cos":   math.cos,
    "tan":   math.tan,
    "asin":  math.asin,
    "acos":  math.acos,
    "atan":  math.atan,
    "exp":   math.exp,
    "factorial": math.factorial,
}


def _evaluar_nodo(nodo: ast.AST) -> Union[int, float]:
    """Evalúa recursivamente un nodo AST usando solo operaciones permitidas."""
    if isinstance(nodo, ast.Expression):
        return _evaluar_nodo(nodo.body)

    if isinstance(nodo, ast.Constant) and isinstance(nodo.value, (int, float)):
        return nodo.value

    if isinstance(nodo, ast.Name) and nodo.id in _SAFE_NAMES:
        val = _SAFE_NAMES[nodo.id]
        if callable(val):
            raise ValueError(f"'{nodo.id}' es una función y requiere argumentos.")
        return val

    if isinstance(nodo, ast.Call):
        if not (isinstance(nodo.func, ast.Name) and nodo.func.id in _SAFE_NAMES):
            raise ValueError(f"Función no permitida: {ast.dump(nodo.func)}")
        func = _SAFE_NAMES[nodo.func.id]
        if not callable(func):
            raise ValueError(f"'{nodo.func.id}' no es una función.")
        args = [_evaluar_nodo(a) for a in nodo.args]
        return func(*args)

    if isinstance(nodo, ast.BinOp) and type(nodo.op) in _SAFE_BINARY_OPS:
        left = _evaluar_nodo(nodo.left)
        right = _evaluar_nodo(nodo.right)
        return _SAFE_BINARY_OPS[type(nodo.op)](left, right)

    if isinstance(nodo, ast.UnaryOp) and type(nodo.op) in _SAFE_UNARY_OPS:
        return _SAFE_UNARY_OPS[type(nodo.op)](_evaluar_nodo(nodo.operand))

    raise ValueError(f"Operación no permitida: '{ast.dump(nodo)}'")


def calcular_matematica(expresion: str) -> str:
    """
    Calcula el resultado de una expresión matemática de forma segura.

    Soporta operadores básicos (+, -, *, /, //, %, **) y funciones como
    sqrt, sin, cos, tan, log, log2, log10, floor, ceil, round, factorial.
    Constantes disponibles: pi, e, tau.

    Args:
        expresion: Expresión matemática a evaluar. Ejemplos: "2 + 2", "sqrt(16)",
                   "sin(pi / 2)", "factorial(5)", "log(100, 10)".

    Returns:
        El resultado numérico como string, o un mensaje de error si la expresión es inválida.
    """
    try:
        arbol = ast.parse(expresion.strip(), mode="eval")
        resultado = _evaluar_nodo(arbol)
        # Retornar entero si el resultado no tiene parte decimal
        if isinstance(resultado, float) and resultado.is_integer():
            return str(int(resultado))
        return str(round(resultado, 10))
    except ZeroDivisionError:
        return "Error: división entre cero."
    except ValueError as e:
        return f"Error: {e}"
    except Exception as e:
        return f"Error al calcular '{expresion}': {e}"
