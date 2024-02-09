from pytype.rewrite import abstract
from pytype.rewrite import stack
from pytype.rewrite.flow import variables

import unittest


class DataStackTest(unittest.TestCase):

  def test_push(self):
    s = stack.DataStack()
    var = variables.Variable.from_value(abstract.PythonConstant(5))
    s.push(var)
    self.assertEqual(s._stack, [var])

  def test_pop(self):
    s = stack.DataStack()
    var = variables.Variable.from_value(abstract.PythonConstant(5))
    s.push(var)
    popped = s.pop()
    self.assertEqual(popped, var)
    self.assertFalse(s._stack)

  def test_top(self):
    s = stack.DataStack()
    var = variables.Variable.from_value(abstract.PythonConstant(5))
    s.push(var)
    top = s.top()
    self.assertEqual(top, var)
    self.assertEqual(s._stack, [var])

  def test_bool(self):
    s = stack.DataStack()
    self.assertFalse(s)
    s.push(variables.Variable.from_value(abstract.PythonConstant(5)))
    self.assertTrue(s)

  def test_len(self):
    s = stack.DataStack()
    self.assertEqual(len(s), 0)  # pylint: disable=g-generic-assert
    s.push(variables.Variable.from_value(abstract.PythonConstant(5)))
    self.assertEqual(len(s), 1)

  def test_popn(self):
    s = stack.DataStack()
    var1 = variables.Variable.from_value(abstract.PythonConstant(1))
    var2 = variables.Variable.from_value(abstract.PythonConstant(2))
    s.push(var1)
    s.push(var2)
    popped1, popped2 = s.popn(2)
    self.assertEqual(popped1, var1)
    self.assertEqual(popped2, var2)
    self.assertFalse(s)

  def test_popn_zero(self):
    s = stack.DataStack()
    popped = s.popn(0)
    self.assertFalse(popped)

  def test_popn_too_many(self):
    s = stack.DataStack()
    with self.assertRaises(IndexError):
      s.popn(1)

  def test_pop_and_discard(self):
    s = stack.DataStack()
    s.push(variables.Variable.from_value(abstract.PythonConstant(5)))
    ret = s.pop_and_discard()
    self.assertIsNone(ret)
    self.assertFalse(s)

  def test_peek(self):
    s = stack.DataStack()
    var = variables.Variable.from_value(abstract.PythonConstant(5))
    s.push(var)
    peeked = s.peek(1)
    self.assertEqual(peeked, var)
    self.assertEqual(len(s), 1)

  def test_peek_error(self):
    s = stack.DataStack()
    with self.assertRaises(IndexError):
      s.peek(0)
    with self.assertRaises(IndexError):
      s.peek(1)


if __name__ == '__main__':
  unittest.main()
