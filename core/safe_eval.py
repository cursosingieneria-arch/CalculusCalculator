"""Evaluación numérica segura para los motores de cálculo.

Motivación (hallazgos S2/S3): los motores «Python内置» y «Mpmath» evaluaban la
expresión del usuario con ``eval(expr)`` sin espacio de nombres restringido, lo
que permite ejecutar código Python arbitrario (``__import__``, ``open``…). Este
módulo evalúa recorriendo el AST y admitiendo solo números, operadores
aritméticos y llamadas a un catálogo de nombres provisto por el llamador. Nunca
usa ``eval``/``exec`` ni acceso a atributos, por lo que las primitivas de
ejecución quedan descartadas por construcción.

Es independiente de Qt para poder probarse sin entorno gráfico.
"""

import ast


class UnsafeExpressionError(ValueError):
    """La expresión contiene construcciones fuera del subconjunto numérico permitido."""


_BIN_OPS = {
    ast.Add: lambda a, b: a + b,
    ast.Sub: lambda a, b: a - b,
    ast.Mult: lambda a, b: a * b,
    ast.Div: lambda a, b: a / b,
    ast.FloorDiv: lambda a, b: a // b,
    ast.Mod: lambda a, b: a % b,
    ast.Pow: lambda a, b: a ** b,
}
_UNARY_OPS = {
    ast.UAdd: lambda a: +a,
    ast.USub: lambda a: -a,
}


def _eval_node(node, names):
    if isinstance(node, ast.Expression):
        return _eval_node(node.body, names)

    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float, complex)):
            return node.value
        raise UnsafeExpressionError("literal no numérico no permitido")

    if isinstance(node, ast.Name):
        if node.id in names:
            return names[node.id]
        raise UnsafeExpressionError("nombre no permitido: %s" % node.id)

    if isinstance(node, ast.BinOp):
        op = _BIN_OPS.get(type(node.op))
        if op is None:
            raise UnsafeExpressionError("operador binario no permitido")
        return op(_eval_node(node.left, names), _eval_node(node.right, names))

    if isinstance(node, ast.UnaryOp):
        op = _UNARY_OPS.get(type(node.op))
        if op is None:
            raise UnsafeExpressionError("operador unario no permitido")
        return op(_eval_node(node.operand, names))

    if isinstance(node, (ast.Tuple, ast.List)):
        return [_eval_node(e, names) for e in node.elts]

    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name) or node.func.id not in names:
            raise UnsafeExpressionError("llamada no permitida")
        func = names[node.func.id]
        if not callable(func):
            raise UnsafeExpressionError("%s no es invocable" % node.func.id)
        args = [_eval_node(a, names) for a in node.args]
        kwargs = {}
        for kw in node.keywords:
            if kw.arg is None:
                raise UnsafeExpressionError("desempaquetado de argumentos no permitido")
            kwargs[kw.arg] = _eval_node(kw.value, names)
        return func(*args, **kwargs)

    raise UnsafeExpressionError("construcción no permitida: %s" % type(node).__name__)


def safe_eval(expr, names):
    """Evalúa ``expr`` (cadena) con solo los ``names`` dados, sin ejecutar código.

    ``names`` es un dict {nombre: valor_o_callable}. Lanza
    :class:`UnsafeExpressionError` ante construcciones no permitidas o
    ``SyntaxError`` si la cadena no es analizable.
    """
    if not isinstance(expr, str):
        raise UnsafeExpressionError("se esperaba una cadena")
    tree = ast.parse(expr, mode="eval")
    return _eval_node(tree, names)


# Catálogo numérico para el motor «Python内置»: constructores/funciones built-in
# seguras. No incluye __import__, open, eval, exec ni acceso a atributos.
def _safe_python_builtins():
    import math
    from fractions import Fraction
    return {
        "abs": abs, "round": round, "pow": pow, "min": min, "max": max,
        "sum": sum, "int": int, "float": float, "complex": complex,
        "bool": bool, "divmod": divmod, "len": len,
        "Fraction": Fraction,
        # Constantes y funciones matemáticas de uso habitual
        "pi": math.pi, "e": math.e, "tau": math.tau, "inf": math.inf,
        "sqrt": math.sqrt, "exp": math.exp, "log": math.log, "log2": math.log2,
        "log10": math.log10, "factorial": math.factorial, "gcd": math.gcd,
        "sin": math.sin, "cos": math.cos, "tan": math.tan,
        "asin": math.asin, "acos": math.acos, "atan": math.atan, "atan2": math.atan2,
        "sinh": math.sinh, "cosh": math.cosh, "tanh": math.tanh,
        "floor": math.floor, "ceil": math.ceil, "hypot": math.hypot,
    }


PY_ENGINE_NAMES = _safe_python_builtins()
