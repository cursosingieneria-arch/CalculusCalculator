"""Reconstrucción segura de expresiones SymPy desde texto no confiable.

Motivación (hallazgo de seguridad S1): la carga de archivos de proyecto
(.cca/.json) pasaba cadenas controladas por el archivo a ``sympy.sympify`` /
``parse_expr``, que evalúan código Python arbitrario. Abrir un archivo de un
tercero ejecutaba código (RCE).

Este módulo evalúa una expresión recorriendo el AST de Python y admitiendo solo
un conjunto acotado de nodos y nombres (números, símbolos, operadores
aritméticos y llamadas a un catálogo fijo de constructores de SymPy). Nunca usa
``eval``/``exec`` ni acceso a atributos, por lo que ``__import__``,
``().__class__`` y similares quedan descartados por construcción.

Es deliberadamente independiente de Qt para poder probarse sin entorno gráfico.
"""

import ast
import re

import sympy
from sympy import Symbol
from sympy.geometry import (
    Point, Point2D, Point3D, Line, Line3D, Ray, Ray3D,
    Segment, Segment3D, Circle, Triangle, Polygon, Plane, Ellipse,
)
# Las clases concretas que usa el repr de SymPy (Line -> Line2D, etc.)
from sympy.geometry.line import Line2D, Ray2D, Segment2D
from sympy.geometry.polygon import RegularPolygon


class UnsafeExpressionError(ValueError):
    """La cadena contiene construcciones no permitidas (posible intento de inyección)."""


# Catálogo de nombres invocables/constantes permitidos. Todo lo demás que sea un
# identificador se interpreta como símbolo matemático (Symbol).
_SAFE_CALLABLES = {
    # Núcleo numérico
    "Rational": sympy.Rational, "Integer": sympy.Integer, "Float": sympy.Float,
    "Add": sympy.Add, "Mul": sympy.Mul, "Pow": sympy.Pow,
    "sqrt": sympy.sqrt, "root": sympy.root, "Abs": sympy.Abs,
    "exp": sympy.exp, "log": sympy.log, "ln": sympy.log,
    # Trigonometría e hiperbólicas
    "sin": sympy.sin, "cos": sympy.cos, "tan": sympy.tan,
    "cot": sympy.cot, "sec": sympy.sec, "csc": sympy.csc,
    "asin": sympy.asin, "acos": sympy.acos, "atan": sympy.atan, "atan2": sympy.atan2,
    "sinh": sympy.sinh, "cosh": sympy.cosh, "tanh": sympy.tanh,
    # Símbolos estructurales que a veces aparecen en repr
    "Symbol": sympy.Symbol, "Tuple": sympy.Tuple, "Matrix": sympy.Matrix,
    # Geometría plana y sólida (repr de objetos guardados)
    "Point": Point, "Point2D": Point2D, "Point3D": Point3D,
    "Line": Line, "Line3D": Line3D, "Ray": Ray, "Ray3D": Ray3D,
    "Segment": Segment, "Segment3D": Segment3D,
    "Circle": Circle, "Ellipse": Ellipse,
    "Triangle": Triangle, "Polygon": Polygon, "Plane": Plane,
    # Clases concretas que emite repr() de SymPy
    "Line2D": Line2D, "Ray2D": Ray2D, "Segment2D": Segment2D,
    "RegularPolygon": RegularPolygon,
}

_SAFE_CONSTANTS = {
    "pi": sympy.pi, "E": sympy.E, "I": sympy.I,
    "oo": sympy.oo, "zoo": sympy.zoo, "nan": sympy.nan,
    "true": sympy.true, "false": sympy.false,
    "Reals": sympy.Reals, "Rationals": sympy.Rationals, "Integers": sympy.Integers,
    "Complexes": sympy.Complexes, "EmptySet": sympy.EmptySet,
}

_BIN_OPS = {
    ast.Add: lambda a, b: a + b,
    ast.Sub: lambda a, b: a - b,
    ast.Mult: lambda a, b: a * b,
    ast.Div: lambda a, b: a / b,
    ast.Pow: lambda a, b: a ** b,
    ast.Mod: lambda a, b: a % b,
    ast.FloorDiv: lambda a, b: a // b,
}
_UNARY_OPS = {
    ast.UAdd: lambda a: +a,
    ast.USub: lambda a: -a,
}


def _eval_node(node):
    if isinstance(node, ast.Expression):
        return _eval_node(node.body)

    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float, complex)):
            return sympy.sympify(node.value)  # literal numérico: conversión directa, sin texto
        raise UnsafeExpressionError("literal no numérico no permitido: %r" % (node.value,))

    if isinstance(node, ast.Name):
        name = node.id
        if name in _SAFE_CONSTANTS:
            return _SAFE_CONSTANTS[name]
        if name in _SAFE_CALLABLES:
            return _SAFE_CALLABLES[name]
        if name.startswith("_"):
            raise UnsafeExpressionError("identificador no permitido: %s" % name)
        return Symbol(name)

    if isinstance(node, ast.BinOp):
        op = _BIN_OPS.get(type(node.op))
        if op is None:
            raise UnsafeExpressionError("operador binario no permitido: %s" % type(node.op).__name__)
        return op(_eval_node(node.left), _eval_node(node.right))

    if isinstance(node, ast.UnaryOp):
        op = _UNARY_OPS.get(type(node.op))
        if op is None:
            raise UnsafeExpressionError("operador unario no permitido: %s" % type(node.op).__name__)
        return op(_eval_node(node.operand))

    if isinstance(node, (ast.Tuple, ast.List)):
        return tuple(_eval_node(e) for e in node.elts)

    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name) or node.func.id not in _SAFE_CALLABLES:
            raise UnsafeExpressionError("llamada no permitida")
        func = _SAFE_CALLABLES[node.func.id]
        args = [_eval_node(a) for a in node.args]
        kwargs = {}
        for kw in node.keywords:
            if kw.arg is None:
                raise UnsafeExpressionError("desempaquetado de argumentos no permitido")
            kwargs[kw.arg] = _eval_node(kw.value)
        return func(*args, **kwargs)

    raise UnsafeExpressionError("nodo no permitido: %s" % type(node).__name__)


def safe_sympify(text):
    """Reconstruye una expresión SymPy desde ``text`` sin evaluar código Python.

    Lanza :class:`UnsafeExpressionError` si la cadena contiene construcciones
    fuera del subconjunto permitido, o ``SyntaxError`` si no es analizable.
    """
    if not isinstance(text, str):
        raise UnsafeExpressionError("se esperaba una cadena")
    tree = ast.parse(text, mode="eval")
    return _eval_node(tree)


def _preprocess_func_calls(expr_str, fs):
    """Expande llamadas f(arg) sustituyendo el cuerpo de la función (solo texto).

    Portado de ``core.sympify._preprocess_func_calls`` para usarse sin Qt. Es
    manipulación de cadenas pura (sin eval): el resultado se valida después con
    ``safe_sympify``, por lo que no introduce ejecución de código.
    """
    if not fs:
        return expr_str
    func_names = sorted(fs.keys(), key=len, reverse=True)
    result = expr_str
    # Límite de iteraciones: corta recursiones circulares en definiciones del archivo.
    for _ in range(1000):
        best_pos = len(result)
        best_func = None
        for func_name in func_names:
            match = re.search(r'\b' + re.escape(func_name) + r'\(', result)
            pos = match.start() if match else -1
            if pos != -1 and pos < best_pos:
                best_pos = pos
                best_func = func_name
        if best_func is None:
            break
        start_arg = best_pos + len(best_func) + 1
        depth = 1
        end_arg = start_arg
        while depth > 0 and end_arg < len(result):
            if result[end_arg] == '(':
                depth += 1
            elif result[end_arg] == ')':
                depth -= 1
            end_arg += 1
        if depth != 0:
            break
        arg_str = result[start_arg:end_arg - 1]
        var_name = fs[best_func][3]
        body_str = fs[best_func][1]
        expanded_body = re.sub(r'\b' + re.escape(var_name) + r'\b', '(' + arg_str + ')', body_str)
        result = result[:best_pos] + '(' + expanded_body + ')' + result[end_arg:]
    return result


def safe_sympify_savefile(text, fs=None):
    """Reconstrucción segura de una cadena guardada en un archivo de proyecto.

    Reproduce el enrutamiento de ``core.sympify.sympify`` (prefijo ``$`` para
    LaTeX, expansión de funciones ``f(x)``) pero SIN evaluar código Python:
    - ``$...``  -> ``latex2sympy`` (analizador LaTeX, no ejecuta Python).
    - resto     -> expansión textual de ``f(x)`` + ``safe_sympify`` (AST acotado).

    Devuelve la expresión, o lanza ``UnsafeExpressionError`` / ``SyntaxError`` si
    la cadena no es segura o no es analizable. El llamador decide cómo manejar el
    fallo (p. ej. omitir ese objeto y avisar), nunca ejecutando la cadena.
    """
    if text == "":
        return Symbol("")
    if isinstance(text, str) and text[:1] == "$":
        from latex2sympy2_extended import latex2sympy
        return latex2sympy(text[1:])
    expanded = _preprocess_func_calls(text, fs or {})
    return safe_sympify(expanded)
