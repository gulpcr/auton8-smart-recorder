"""
Expression Engine - Safe expression evaluation for calculated assertions

Supports:
- Math: +, -, *, /, %, ** (power), // (floor division)
- Comparisons: ==, !=, <, >, <=, >=
- Logic: and, or, not
- Functions: abs, round, min, max, len, str, int, float, sum, avg
- String: concatenation (+), contains (in)
- Variables: ${varName} syntax
"""

import ast
import operator
import re
import logging
from typing import Any, Dict, Optional, Tuple, List
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class ExpressionError(Exception):
    """Custom exception for expression evaluation errors"""
    pass


class ComparisonMode(Enum):
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    GREATER_THAN = "greater_than"
    GREATER_OR_EQUAL = "greater_or_equal"
    LESS_THAN = "less_than"
    LESS_OR_EQUAL = "less_or_equal"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    MATCHES_REGEX = "matches_regex"
    BETWEEN = "between"


@dataclass
class EvaluationResult:
    """Result of expression evaluation"""
    success: bool
    calculated_value: Any
    actual_value: Any = None
    comparison_mode: str = "equals"
    expression: str = ""
    error_message: str = ""
    variables_used: Dict[str, Any] = field(default_factory=dict)
    breakdown: str = ""  # Human-readable calculation breakdown


@dataclass
class Variable:
    """Variable definition"""
    name: str
    value: Any
    source: str = "manual"  # manual, extracted, calculated
    element_selector: str = ""  # If extracted from page
    description: str = ""


class VariableStore:
    """Manages variables for expression evaluation"""

    def __init__(self):
        self._variables: Dict[str, Variable] = {}
        self._built_in = {
            "PI": 3.14159265359,
            "E": 2.71828182846,
            "TRUE": True,
            "FALSE": False,
            "NULL": None,
        }

    def set(self, name: str, value: Any, source: str = "manual",
            element_selector: str = "", description: str = "") -> None:
        """Set a variable"""
        self._variables[name] = Variable(
            name=name,
            value=value,
            source=source,
            element_selector=element_selector,
            description=description
        )

    def get(self, name: str) -> Any:
        """Get variable value"""
        if name in self._variables:
            return self._variables[name].value
        if name in self._built_in:
            return self._built_in[name]
        raise ExpressionError(f"Variable '{name}' not found")

    def get_all(self) -> Dict[str, Any]:
        """Get all variables as dict"""
        result = dict(self._built_in)
        for name, var in self._variables.items():
            result[name] = var.value
        return result

    def get_variable(self, name: str) -> Optional[Variable]:
        """Get variable object"""
        return self._variables.get(name)

    def list_variables(self) -> List[Variable]:
        """List all user variables"""
        return list(self._variables.values())

    def delete(self, name: str) -> bool:
        """Delete a variable"""
        if name in self._variables:
            del self._variables[name]
            return True
        return False

    def clear(self) -> None:
        """Clear all user variables"""
        self._variables.clear()

    def to_dict(self) -> Dict:
        """Serialize to dict"""
        return {
            name: {
                "value": var.value,
                "source": var.source,
                "element_selector": var.element_selector,
                "description": var.description
            }
            for name, var in self._variables.items()
        }

    def from_dict(self, data: Dict) -> None:
        """Load from dict"""
        self._variables.clear()
        for name, var_data in data.items():
            self._variables[name] = Variable(
                name=name,
                value=var_data.get("value"),
                source=var_data.get("source", "manual"),
                element_selector=var_data.get("element_selector", ""),
                description=var_data.get("description", "")
            )


class SafeExpressionEvaluator:
    """
    Safe expression evaluator using AST parsing.
    Only allows whitelisted operations.
    """

    # Allowed binary operators
    BINARY_OPS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
        ast.LShift: operator.lshift,
        ast.RShift: operator.rshift,
        ast.BitOr: operator.or_,
        ast.BitXor: operator.xor,
        ast.BitAnd: operator.and_,
    }

    # Allowed comparison operators
    COMPARE_OPS = {
        ast.Eq: operator.eq,
        ast.NotEq: operator.ne,
        ast.Lt: operator.lt,
        ast.LtE: operator.le,
        ast.Gt: operator.gt,
        ast.GtE: operator.ge,
        ast.In: lambda a, b: a in b,
        ast.NotIn: lambda a, b: a not in b,
    }

    # Allowed unary operators
    UNARY_OPS = {
        ast.UAdd: operator.pos,
        ast.USub: operator.neg,
        ast.Not: operator.not_,
        ast.Invert: operator.invert,
    }

    # Allowed functions
    SAFE_FUNCTIONS = {
        "abs": abs,
        "round": round,
        "min": min,
        "max": max,
        "len": len,
        "str": str,
        "int": int,
        "float": float,
        "bool": bool,
        "sum": sum,
        "avg": lambda x: sum(x) / len(x) if x else 0,
        "upper": lambda s: str(s).upper(),
        "lower": lambda s: str(s).lower(),
        "strip": lambda s: str(s).strip(),
        "replace": lambda s, old, new: str(s).replace(old, new),
        "split": lambda s, sep=None: str(s).split(sep),
        "join": lambda sep, lst: sep.join(str(x) for x in lst),
        "contains": lambda s, sub: sub in str(s),
        "startswith": lambda s, prefix: str(s).startswith(prefix),
        "endswith": lambda s, suffix: str(s).endswith(suffix),
        "format": lambda template, *args, **kwargs: template.format(*args, **kwargs),
        "concat": lambda *args: "".join(str(a) for a in args),
        "number": lambda s: float(re.sub(r'[^\d.\-]', '', str(s))) if s else 0,
        "extract_number": lambda s: float(re.search(r'[\d.]+', str(s)).group()) if re.search(r'[\d.]+', str(s)) else 0,
    }

    # Variable pattern: ${varName} or $varName
    VAR_PATTERN = re.compile(r'\$\{?(\w+)\}?')

    def __init__(self, variable_store: Optional[VariableStore] = None):
        self.variables = variable_store or VariableStore()

    def _substitute_variables(self, expression: str) -> Tuple[str, Dict[str, Any]]:
        """Replace ${var} with actual values and return substituted expression"""
        used_vars = {}

        def replace_var(match):
            var_name = match.group(1)
            try:
                value = self.variables.get(var_name)
                used_vars[var_name] = value
                # Return appropriate representation
                if isinstance(value, str):
                    return repr(value)
                return str(value)
            except ExpressionError:
                raise ExpressionError(f"Undefined variable: ${var_name}")

        substituted = self.VAR_PATTERN.sub(replace_var, expression)
        return substituted, used_vars

    def _eval_node(self, node: ast.AST) -> Any:
        """Recursively evaluate AST node"""

        if isinstance(node, ast.Expression):
            return self._eval_node(node.body)

        elif isinstance(node, ast.Constant):
            return node.value

        elif isinstance(node, ast.Num):  # Python 3.7 compatibility
            return node.n

        elif isinstance(node, ast.Str):  # Python 3.7 compatibility
            return node.s

        elif isinstance(node, ast.List):
            return [self._eval_node(elem) for elem in node.elts]

        elif isinstance(node, ast.Tuple):
            return tuple(self._eval_node(elem) for elem in node.elts)

        elif isinstance(node, ast.Dict):
            return {
                self._eval_node(k): self._eval_node(v)
                for k, v in zip(node.keys, node.values)
            }

        elif isinstance(node, ast.BinOp):
            op_type = type(node.op)
            if op_type not in self.BINARY_OPS:
                raise ExpressionError(f"Unsupported operator: {op_type.__name__}")
            left = self._eval_node(node.left)
            right = self._eval_node(node.right)
            return self.BINARY_OPS[op_type](left, right)

        elif isinstance(node, ast.UnaryOp):
            op_type = type(node.op)
            if op_type not in self.UNARY_OPS:
                raise ExpressionError(f"Unsupported unary operator: {op_type.__name__}")
            operand = self._eval_node(node.operand)
            return self.UNARY_OPS[op_type](operand)

        elif isinstance(node, ast.Compare):
            left = self._eval_node(node.left)
            for op, comparator in zip(node.ops, node.comparators):
                op_type = type(op)
                if op_type not in self.COMPARE_OPS:
                    raise ExpressionError(f"Unsupported comparison: {op_type.__name__}")
                right = self._eval_node(comparator)
                if not self.COMPARE_OPS[op_type](left, right):
                    return False
                left = right
            return True

        elif isinstance(node, ast.BoolOp):
            if isinstance(node.op, ast.And):
                return all(self._eval_node(v) for v in node.values)
            elif isinstance(node.op, ast.Or):
                return any(self._eval_node(v) for v in node.values)

        elif isinstance(node, ast.IfExp):
            # Ternary: value_if_true if condition else value_if_false
            if self._eval_node(node.test):
                return self._eval_node(node.body)
            return self._eval_node(node.orelse)

        elif isinstance(node, ast.Call):
            # Function calls
            if isinstance(node.func, ast.Name):
                func_name = node.func.id
                if func_name not in self.SAFE_FUNCTIONS:
                    raise ExpressionError(f"Unknown function: {func_name}")
                func = self.SAFE_FUNCTIONS[func_name]
                args = [self._eval_node(arg) for arg in node.args]
                kwargs = {kw.arg: self._eval_node(kw.value) for kw in node.keywords}
                return func(*args, **kwargs)
            raise ExpressionError("Complex function calls not supported")

        elif isinstance(node, ast.Name):
            # Variable reference (after substitution, shouldn't happen often)
            name = node.id
            if name in self.SAFE_FUNCTIONS:
                return self.SAFE_FUNCTIONS[name]
            if name == "True":
                return True
            if name == "False":
                return False
            if name == "None":
                return None
            raise ExpressionError(f"Unknown identifier: {name}")

        elif isinstance(node, ast.Subscript):
            # Index/slice access: list[0], dict["key"]
            value = self._eval_node(node.value)
            if isinstance(node.slice, ast.Index):  # Python 3.8-
                index = self._eval_node(node.slice.value)
            else:  # Python 3.9+
                index = self._eval_node(node.slice)
            return value[index]

        else:
            raise ExpressionError(f"Unsupported expression type: {type(node).__name__}")

    def evaluate(self, expression: str) -> Tuple[Any, Dict[str, Any]]:
        """
        Evaluate an expression and return (result, variables_used)

        Args:
            expression: Expression string like "${price} * ${quantity} + 5"

        Returns:
            Tuple of (calculated_value, dict of variables used)
        """
        try:
            # Substitute variables
            substituted, used_vars = self._substitute_variables(expression)

            # Parse the expression
            tree = ast.parse(substituted, mode='eval')

            # Evaluate
            result = self._eval_node(tree)

            return result, used_vars

        except SyntaxError as e:
            raise ExpressionError(f"Syntax error in expression: {e}")
        except Exception as e:
            if isinstance(e, ExpressionError):
                raise
            raise ExpressionError(f"Evaluation error: {e}")

    def create_breakdown(self, expression: str, used_vars: Dict[str, Any], result: Any) -> str:
        """Create human-readable breakdown of calculation"""
        lines = []

        # Show variables
        if used_vars:
            lines.append("Variables:")
            for name, value in used_vars.items():
                lines.append(f"  ${name} = {value}")

        # Show expression
        lines.append(f"\nExpression: {expression}")

        # Show substituted expression
        substituted, _ = self._substitute_variables(expression)
        if substituted != expression:
            lines.append(f"Substituted: {substituted}")

        # Show result
        lines.append(f"Result: {result}")

        return "\n".join(lines)


class CalculatedAssertion:
    """
    Performs calculated assertions - evaluates expression and compares with actual value
    """

    def __init__(self, variable_store: Optional[VariableStore] = None):
        self.variable_store = variable_store or VariableStore()
        self.evaluator = SafeExpressionEvaluator(self.variable_store)

    def compare(self, calculated: Any, actual: Any, mode: ComparisonMode,
                tolerance: float = 0.0) -> bool:
        """Compare calculated value with actual value"""

        try:
            if mode == ComparisonMode.EQUALS:
                if isinstance(calculated, (int, float)) and isinstance(actual, (int, float)):
                    return abs(calculated - actual) <= tolerance
                return calculated == actual

            elif mode == ComparisonMode.NOT_EQUALS:
                return calculated != actual

            elif mode == ComparisonMode.GREATER_THAN:
                return float(actual) > float(calculated)

            elif mode == ComparisonMode.GREATER_OR_EQUAL:
                return float(actual) >= float(calculated)

            elif mode == ComparisonMode.LESS_THAN:
                return float(actual) < float(calculated)

            elif mode == ComparisonMode.LESS_OR_EQUAL:
                return float(actual) <= float(calculated)

            elif mode == ComparisonMode.CONTAINS:
                return str(calculated) in str(actual)

            elif mode == ComparisonMode.NOT_CONTAINS:
                return str(calculated) not in str(actual)

            elif mode == ComparisonMode.STARTS_WITH:
                return str(actual).startswith(str(calculated))

            elif mode == ComparisonMode.ENDS_WITH:
                return str(actual).endswith(str(calculated))

            elif mode == ComparisonMode.MATCHES_REGEX:
                return bool(re.search(str(calculated), str(actual)))

            elif mode == ComparisonMode.BETWEEN:
                # calculated should be a tuple/list of (min, max)
                if isinstance(calculated, (list, tuple)) and len(calculated) == 2:
                    return calculated[0] <= float(actual) <= calculated[1]
                return False

            return False

        except (ValueError, TypeError) as e:
            logger.warning(f"Comparison error: {e}")
            return False

    def assert_expression(
        self,
        expression: str,
        actual_value: Any,
        comparison_mode: ComparisonMode = ComparisonMode.EQUALS,
        tolerance: float = 0.0
    ) -> EvaluationResult:
        """
        Evaluate expression and compare with actual value

        Args:
            expression: Expression to evaluate (e.g., "${price} * ${qty}")
            actual_value: Actual value to compare against
            comparison_mode: How to compare
            tolerance: Tolerance for numeric comparisons

        Returns:
            EvaluationResult with success status and details
        """
        try:
            # Evaluate expression
            calculated, used_vars = self.evaluator.evaluate(expression)

            # Compare
            success = self.compare(calculated, actual_value, comparison_mode, tolerance)

            # Create breakdown
            breakdown = self.evaluator.create_breakdown(expression, used_vars, calculated)
            breakdown += f"\n\nActual value: {actual_value}"
            breakdown += f"\nComparison: {comparison_mode.value}"
            breakdown += f"\nResult: {'PASS' if success else 'FAIL'}"

            return EvaluationResult(
                success=success,
                calculated_value=calculated,
                actual_value=actual_value,
                comparison_mode=comparison_mode.value,
                expression=expression,
                variables_used=used_vars,
                breakdown=breakdown
            )

        except ExpressionError as e:
            return EvaluationResult(
                success=False,
                calculated_value=None,
                actual_value=actual_value,
                comparison_mode=comparison_mode.value,
                expression=expression,
                error_message=str(e),
                breakdown=f"Error: {e}"
            )

    def evaluate_only(self, expression: str) -> EvaluationResult:
        """Just evaluate expression without comparison"""
        try:
            calculated, used_vars = self.evaluator.evaluate(expression)
            breakdown = self.evaluator.create_breakdown(expression, used_vars, calculated)

            return EvaluationResult(
                success=True,
                calculated_value=calculated,
                expression=expression,
                variables_used=used_vars,
                breakdown=breakdown
            )
        except ExpressionError as e:
            return EvaluationResult(
                success=False,
                calculated_value=None,
                expression=expression,
                error_message=str(e),
                breakdown=f"Error: {e}"
            )


# Singleton variable store for the application
_global_variable_store = VariableStore()


def get_variable_store() -> VariableStore:
    """Get the global variable store"""
    return _global_variable_store


def get_assertion_engine() -> CalculatedAssertion:
    """Get assertion engine with global variable store"""
    return CalculatedAssertion(_global_variable_store)
