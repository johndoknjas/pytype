"""A printer for human-readable output of types and variables."""

import re
import typing

from typing import Iterable

from pytype.abstract import abstract
from pytype.abstract import abstract_utils
from pytype.pytd import escape
from pytype.pytd import optimize
from pytype.pytd import pytd
from pytype.pytd import pytd_utils
from pytype.pytd import visitors
from pytype.typegraph import cfg


def show_constant(val: abstract.BaseValue) -> str:
  """Pretty-print a value if it is a constant.

  Recurses into a constant, printing the underlying Python value for constants
  and just using "..." for everything else (e.g., Variables). This is useful for
  generating clear error messages that show the exact values related to an error
  while preventing implementation details from leaking into the message.

  Args:
    val: an abstract value.

  Returns:
    A string of the pretty-printed constant.
  """
  def _ellipsis_printer(v):
    if isinstance(v, abstract.PythonConstant):
      return v.str_of_constant(_ellipsis_printer)
    return "..."
  return _ellipsis_printer(val)


class PrettyPrinter:
  """Pretty print types for errors."""

  def print_pytd(self, pytd_type: pytd.Type) -> str:
    """Print the name of the pytd type."""
    typ = pytd_utils.CanonicalOrdering(
        optimize.Optimize(
            pytd_type.Visit(visitors.RemoveUnknownClasses())))
    name = pytd_utils.Print(typ)
    # Clean up autogenerated namedtuple names, e.g. "namedtuple-X-a-_0-c"
    # becomes just "X", by extracting out just the type name.
    if "namedtuple" in name:
      return escape.unpack_namedtuple(name)
    nested_class_match = re.search(r"_(?:\w+)_DOT_", name)
    if nested_class_match:
      # Pytype doesn't have true support for nested classes. Instead, for
      #   class Foo:
      #     class Bar: ...
      # it outputs:
      #   class _Foo_DOT_Bar: ...
      #   class Foo:
      #     Bar = ...  # type: Type[_Foo_DOT_Bar]
      # Replace _Foo_DOT_Bar with Foo.Bar in error messages for readability.
      # TODO(b/35138984): Get rid of this hack.
      start = nested_class_match.start()
      return name[:start] + name[start+1:].replace("_DOT_", ".")
    return name

  def join_printed_types(self, types: Iterable[str]) -> str:
    """Pretty-print the union of the printed types."""
    types = set(types)  # dedup
    if len(types) == 1:
      return next(iter(types))
    elif types:
      literal_contents = set()
      optional = False
      new_types = []
      for t in types:
        if t.startswith("Literal["):
          literal_contents.update(t[len("Literal["):-1].split(", "))
        elif t == "None":
          optional = True
        else:
          new_types.append(t)
      if literal_contents:
        literal = f"Literal[{', '.join(sorted(literal_contents))}]"
        new_types.append(literal)
      if len(new_types) > 1:
        out = f"Union[{', '.join(sorted(new_types))}]"
      else:
        out = new_types[0]
      if optional:
        out = f"Optional[{out}]"
      return out
    else:
      return "nothing"

  def print_as_generic_type(self, t) -> str:
    convert = t.ctx.pytd_convert
    generic = pytd_utils.MakeClassOrContainerType(
        t.get_instance_type().base_type,
        t.formal_type_parameters.keys(),
        False)
    with convert.set_output_mode(convert.OutputMode.DETAILED):
      return self.print_pytd(generic)

  def print_as_expected_type(self, t: abstract.BaseValue, instance=None) -> str:
    """Print abstract value t as a pytd type."""
    convert = t.ctx.pytd_convert
    if isinstance(t, (abstract.Unknown, abstract.Unsolvable,
                      abstract.Class)) or t.is_late_annotation():
      with convert.set_output_mode(convert.OutputMode.DETAILED):
        return self.print_pytd(t.get_instance_type(instance=instance))
    elif isinstance(t, abstract.Union):
      return self.join_printed_types(
          self.print_as_expected_type(o) for o in t.options)
    elif t.is_concrete:
      typ = typing.cast(abstract.PythonConstant, t)
      return re.sub(
          r"(\\n|\s)+", " ",
          typ.str_of_constant(self.print_as_expected_type))
    elif (isinstance(t, (abstract.AnnotationClass, abstract.Singleton)) or
          t.cls == t):
      return t.name
    else:
      return f"<instance of {self.print_as_expected_type(t.cls, t)}>"

  def print_as_actual_type(self, t, literal=False) -> str:
    convert = t.ctx.pytd_convert
    if literal:
      output_mode = convert.OutputMode.LITERAL
    else:
      output_mode = convert.OutputMode.DETAILED
    with convert.set_output_mode(output_mode):
      return self.print_pytd(t.to_type())

  def print_as_function_def(self, fn: abstract.Function) -> str:
    convert = fn.ctx.pytd_convert
    name = fn.name.rsplit(".", 1)[-1]  # We want `def bar()` not `def Foo.bar()`
    with convert.set_output_mode(convert.OutputMode.DETAILED):
      pytd_def = convert.value_to_pytd_def(fn.ctx.root_node, fn, name)
    return pytd_utils.Print(pytd_def)

  def print_pytd_signature(self, sig: pytd.Signature) -> str:
    return self.print_pytd(sig)

  def print_var_as_type(self, var: cfg.Variable, node: cfg.CFGNode) -> str:
    """Print a pytype variable as a type."""
    if not var.bindings:
      return "nothing"
    convert = var.data[0].ctx.pytd_convert
    with convert.set_output_mode(convert.OutputMode.DETAILED):
      typ = pytd_utils.JoinTypes(
          b.data.to_type()
          for b in abstract_utils.expand_type_parameter_instances(var.bindings)
          if node.HasCombination([b]))
    return self.print_pytd(typ)

  def show_variable(self, var: cfg.Variable) -> str:
    """Show variable as 'name: typ' or 'pyval: typ' if available."""
    if not var.data:
      return self.print_pytd(pytd.NothingType())
    val = var.data[0]
    name = val.ctx.vm.get_var_name(var)
    typ = self.join_printed_types(
        self.print_as_actual_type(t) for t in var.data)
    if name:
      return f"'{name}: {typ}'"
    elif len(var.data) == 1 and hasattr(val, "pyval"):
      name = show_constant(val)
      return f"'{name}: {typ}'"
    else:
      return f"'{typ}'"