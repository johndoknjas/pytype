"""Tests for typing.Self."""

from pytype.tests import test_base
from pytype.tests import test_utils


class SelfTest(test_base.BaseTest):
  """Tests for typing.Self."""

  def test_instance_method_return(self):
    self.CheckWithErrors("""
      from typing_extensions import Self  # not-supported-yet
      class A:
        def f(self) -> Self:
          return self
      class B(A):
        pass
      assert_type(A().f(), A)
      assert_type(B().f(), B)
    """)

  def test_parameterized_return(self):
    self.CheckWithErrors("""
      from typing import List
      from typing_extensions import Self  # not-supported-yet
      class A:
        def f(self) -> List[Self]:
          return [self]
      class B(A):
        pass
      assert_type(A().f(), "List[A]")
      assert_type(B().f(), "List[B]")
    """)

  def test_parameter(self):
    errors = self.CheckWithErrors("""
      from typing_extensions import Self  # not-supported-yet
      class A:
        def f(self, other: Self) -> bool:
          return False
      class B(A):
        pass
      B().f(B())  # ok
      B().f(0)  # wrong-arg-types[e]
    """)
    self.assertErrorSequences(
        errors, {"e": ["Expected", "B", "Actual", "int"]})

  def test_nested_class(self):
    self.CheckWithErrors("""
      from typing_extensions import Self  # not-supported-yet
      class A:
        class B:
          def f(self) -> Self:
            return self
      class C(A.B):
        pass
      assert_type(A.B().f(), A.B)
      assert_type(C().f(), C)
    """)

  @test_utils.skipBeforePy((3, 11), "typing.Self is new in 3.11")
  def test_import_from_typing(self):
    self.CheckWithErrors("""
      from typing import Self  # not-supported-yet
      class A:
        def f(self) -> Self:
          return self
      class B(A):
        pass
      assert_type(A().f(), A)
      assert_type(B().f(), B)
    """)


class SelfPyiTest(test_base.BaseTest):
  """Tests for typing.Self usage in type stubs."""

  def test_instance_method_return(self):
    with self.DepTree([("foo.pyi", """
      from typing import Self
      class A:
        def f(self) -> Self: ...
    """)]):
      self.Check("""
        import foo
        class B(foo.A):
          pass
        assert_type(foo.A().f(), foo.A)
        assert_type(B().f(), B)
      """)

  def test_classmethod_return(self):
    with self.DepTree([("foo.pyi", """
      from typing import Self
      class A:
        @classmethod
        def f(cls) -> Self: ...
    """)]):
      self.Check("""
        import foo
        class B(foo.A):
          pass
        assert_type(foo.A.f(), foo.A)
        assert_type(B.f(), B)
      """)

  def test_new_return(self):
    with self.DepTree([("foo.pyi", """
      from typing import Self
      class A:
        def __new__(cls) -> Self: ...
    """)]):
      self.Check("""
        import foo
        class B(foo.A):
          pass
        assert_type(foo.A(), foo.A)
        assert_type(B(), B)
      """)

  def test_parameterized_return(self):
    with self.DepTree([("foo.pyi", """
      from typing import Self
      class A:
        def f(self) -> list[Self]: ...
    """)]):
      self.Check("""
        import foo
        class B(foo.A):
          pass
        assert_type(foo.A().f(), "List[foo.A]")
        assert_type(B().f(), "List[B]")
      """)

  def test_parameter(self):
    with self.DepTree([("foo.pyi", """
      from typing import Self
      class A:
        def f(self, other: Self) -> bool: ...
    """)]):
      errors = self.CheckWithErrors("""
        import foo
        class B(foo.A):
          pass
        B().f(B())  # ok
        B().f(0)  # wrong-arg-types[e]
      """)
      self.assertErrorSequences(
          errors, {"e": ["Expected", "B", "Actual", "int"]})

  def test_nested_class(self):
    with self.DepTree([("foo.pyi", """
      from typing import Self
      class A:
        class B:
          def f(self) -> Self: ...
    """)]):
      self.Check("""
        import foo
        class C(foo.A.B):
          pass
        assert_type(foo.A.B().f(), foo.A.B)
        assert_type(C().f(), C)
      """)


class SelfReingestTest(test_base.BaseTest):
  """Tests for outputting typing.Self to a stub and reading the stub back in."""

  def test_instance_method_return(self):
    with self.DepTree([("foo.py", """
      from typing_extensions import Self  # pytype: disable=not-supported-yet
      class A:
        def f(self) -> Self:
          return self
    """)]):
      self.Check("""
        import foo
        class B(foo.A):
          pass
        assert_type(foo.A().f(), foo.A)
        assert_type(B().f(), B)
      """)

  def test_parameterized_return(self):
    with self.DepTree([("foo.py", """
      from typing import List
      from typing_extensions import Self  # pytype: disable=not-supported-yet
      class A:
        def f(self) -> List[Self]:
          return [self]
    """)]):
      self.Check("""
        import foo
        class B(foo.A):
          pass
        assert_type(foo.A().f(), "List[foo.A]")
        assert_type(B().f(), "List[B]")
      """)

  def test_parameter(self):
    with self.DepTree([("foo.py", """
      from typing_extensions import Self  # pytype: disable=not-supported-yet
      class A:
        def f(self, other: Self) -> bool:
          return False
    """)]):
      errors = self.CheckWithErrors("""
        import foo
        class B(foo.A):
          pass
        B().f(B())  # ok
        B().f(0)  # wrong-arg-types[e]
      """)
      self.assertErrorSequences(
          errors, {"e": ["Expected", "B", "Actual", "int"]})

  def test_nested_class(self):
    with self.DepTree([("foo.py", """
      from typing_extensions import Self  # pytype: disable=not-supported-yet
      class A:
        class B:
          def f(self) -> Self:
            return self
    """)]):
      self.Check("""
        import foo
        class C(foo.A.B):
          pass
        assert_type(foo.A.B().f(), foo.A.B)
        assert_type(C().f(), C)
      """)


if __name__ == "__main__":
  test_base.main()
