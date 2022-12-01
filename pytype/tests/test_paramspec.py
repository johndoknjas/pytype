"""PEP 612 tests."""

from pytype.tests import test_base
from pytype.tests import test_utils


@test_utils.skipBeforePy((3, 10), "ParamSpec is new in 3.10")
class ParamSpecTest(test_base.BaseTest):
  """Tests for ParamSpec."""

  def test_basic(self):
    ty = self.Infer("""
      from typing import ParamSpec
      P = ParamSpec("P")
    """)
    self.assertTypesMatchPytd(ty, """
      from typing import ParamSpec
      P = ParamSpec("P")
    """)

  def test_import(self):
    with test_utils.Tempdir() as d:
      d.create_file("a.pyi", """P = ParamSpec("P")""")
      ty = self.Infer("""
        from a import P
      """, pythonpath=[d.path])
      self.assertTypesMatchPytd(ty, """
        from typing import ParamSpec
        P = ParamSpec("P")
      """)

  def test_invalid(self):
    ty, errors = self.InferWithErrors("""
      from typing import ParamSpec
      T = ParamSpec()  # invalid-typevar[e1]
      T = ParamSpec("T")  # ok
      T = ParamSpec(42)  # invalid-typevar[e2]
      T = ParamSpec(str())  # invalid-typevar[e3]
      T = ParamSpec("T", str, int if __random__ else float)  # invalid-typevar[e4]
      T = ParamSpec("T", 0, float)  # invalid-typevar[e5]
      T = ParamSpec("T", str)  # invalid-typevar[e6]
      # pytype: disable=not-supported-yet
      S = ParamSpec("S", covariant=False)  # ok
      T = ParamSpec("T", covariant=False)  # duplicate ok
    """)
    self.assertTypesMatchPytd(ty, """
      from typing import ParamSpec
      S = ParamSpec("S")
      T = ParamSpec("T")
    """)
    self.assertErrorRegexes(errors, {
        "e1": r"wrong arguments", "e2": r"Expected.*str.*Actual.*int",
        "e3": r"constant str", "e4": r"constraint.*Must be constant",
        "e5": r"Expected.*_1:.*type.*Actual.*_1: int", "e6": r"0 or more than 1"
    })

  def test_print_args(self):
    ty = self.Infer("""
      from typing import ParamSpec
      S = ParamSpec("S", bound=float, covariant=True)
    """, deep=False)
    # The "covariant" keyword is ignored for now.
    self.assertTypesMatchPytd(ty, """
      from typing import ParamSpec
      S = ParamSpec("S", bound=float)
    """)

  def test_paramspec_in_def(self):
    ty = self.Infer("""
      from typing import Callable, ParamSpec
      P = ParamSpec("P")

      def f(x: Callable[P, int]) -> Callable[P, int]:
        return x
    """)
    self.assertTypesMatchPytd(ty, """
      from typing import Callable, ParamSpec
      P = ParamSpec("P")

      def f(x: Callable[..., int]) -> Callable[..., int]: ...
    """)

  def test_concatenate_in_def(self):
    ty = self.Infer("""
      from typing import Callable, Concatenate, ParamSpec
      P = ParamSpec("P")

      def f(x: Callable[Concatenate[int, P], int]) -> Callable[P, int]:
        return x
    """)
    self.assertTypesMatchPytd(ty, """
      from typing import Callable, ParamSpec
      P = ParamSpec("P")

      def f(x: Callable[..., int]) -> Callable[..., int]: ...
    """)


@test_utils.skipBeforePy((3, 10), "ParamSpec is new in 3.10")
class PyiParamSpecTest(test_base.BaseTest):
  """Tests for ParamSpec imported from pyi files."""

  def test_decorator(self):
    with self.DepTree([("foo.pyi", """
      from typing import TypeVar, ParamSpec, Callable, List

      T = TypeVar("T")
      P = ParamSpec("P")

      def decorator(fn: Callable[P, T]) -> Callable[P, List[T]]: ...
    """)]):
      ty, _ = self.InferWithErrors("""
        import foo

        class A:
          pass

        @foo.decorator
        def h(a: A, b: str) -> int:
          return 10

        p = h(A(), b='2')
        q = h(1, 2)  # wrong-arg-types
      """)
    self.assertTypesMatchPytd(ty, """
      import foo
      from typing import List, Any

      p: List[int]
      q: Any

      class A: ...

      def h(a: A, b: str) -> List[int]: ...
   """)

  def test_method_decoration(self):
    with self.DepTree([("foo.pyi", """
      from typing import TypeVar, ParamSpec, Callable, List

      T = TypeVar("T")
      P = ParamSpec("P")

      def decorator(fn: Callable[P, T]) -> Callable[P, List[T]]: ...
    """)]):
      ty, _ = self.InferWithErrors("""
        import foo

        class A:
          pass

        class B:
          @foo.decorator
          def h(a: A, b: str) -> int:
            return 10
      """)
    self.assertTypesMatchPytd(ty, """
      import foo
      from typing import List, Any

      class A: ...

      class B:
        def h(a: A, b: str) -> List[int]: ...
   """)

  def test_imported_paramspec(self):
    with self.DepTree([("foo.pyi", """
      from typing import TypeVar, ParamSpec, Callable, List

      T = TypeVar("T")
      P = ParamSpec("P")

      def decorator(fn: Callable[P, T]) -> Callable[P, List[T]]: ...
    """)]):
      ty, _ = self.InferWithErrors("""
        from foo import decorator

        class A:
          pass

        @decorator
        def h(a: A, b: str) -> int:
          return 10

        p = h(A(), b='2')
        q = h(1, 2)  # wrong-arg-types
      """)
    self.assertTypesMatchPytd(ty, """
      from typing import Callable, List, ParamSpec, TypeVar, Any

      p: List[int]
      q: Any

      P = ParamSpec('P')
      T = TypeVar('T')

      class A: ...

      def decorator(fn: Callable[P, T]) -> Callable[P, List[T]]: ...
      def h(a: A, b: str) -> List[int]: ...
   """)

  def test_concatenate(self):
    # TODO(b/217789659):
    # - Should change_arg preserve the name of the posarg?
    # - Should paramspecs in error messages be changed to ...?
    with self.DepTree([("foo.pyi", """
      from typing import TypeVar, ParamSpec, Concatenate, Callable

      T = TypeVar("T")
      P = ParamSpec("P")

      def change_arg(fn: Callable[Concatenate[int, P], T]) -> Callable[Concatenate[str, P], T]: ...
      def drop_arg(fn: Callable[Concatenate[int, P], T]) -> Callable[P, T]: ...
      def add_arg(fn: Callable[P, T]) -> Callable[Concatenate[int, P], T]: ...
      def mismatched(fn: Callable[Concatenate[str, P], T]) -> Callable[Concatenate[str, P], T]: ...
    """)]):
      ty, err = self.InferWithErrors("""
        import foo

        @foo.change_arg
        def f(a: int, b: str) -> int:
          return 10

        @foo.drop_arg
        def g(a: int, b: str) -> int:
          return 10

        @foo.add_arg
        def h(a: int, b: str) -> int:
          return 10

        @foo.mismatched
        def k(a: int, b: str) -> int:  # wrong-arg-types[e]
          return 10
      """)
    self.assertTypesMatchPytd(ty, """
      import foo
      from typing import Any

      k: Any

      def f(_0: str, b: str) -> int: ...
      def g(b: str) -> int: ...
      def h(_0: int, /, a: int, b: str) -> int: ...
   """)
    self.assertErrorSequences(err, {
        "e": ["Expected", "fn: Callable[Concatenate[str, P], Any]",
              "Actual", "fn: Callable[[int, str], int]"]})


if __name__ == "__main__":
  test_base.main()
