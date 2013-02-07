#
#  Copyright (c) 2013 Sam Leitch. All rights reserved.
#
#  Permission is hereby granted, free of charge, to any person obtaining a copy
#  of this software and associated documentation files (the "Software"), to
#  deal in the Software without restriction, including without limitation the
#  rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
#  sell copies of the Software, and to permit persons to whom the Software is
#  furnished to do so, subject to the following conditions:
#
#  The above copyright notice and this permission notice shall be included in
#  all copies or substantial portions of the Software.
#
#  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
#  FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
#  IN THE SOFTWARE.
#

import unittest, subprocess

class Builder:
	"""A very simple build script tool

	The Builder class enables the creation of very simple build scripts by encapsulating targets and dependencies.
	Targets define what it is your build script needs to do and dependencies relate different targets together.

	A single target can be one of 3 types:
	* A callable that requires 0 arguments
	* A string that defines a command line to be executed
	* None, which does nothing (useful for grouping dependencies without requiring a final action)

	Dependencies are defined in one of three ways:
	* a space-delimited string of targets
	* A callable that requires 0 arguments (An "anonymous dependency")
	* a list of valid dependencies

	Multiple dependencies can be defined for a single target and they will be appended.

	When you execute a target, the builder will first recursively execute the target's dependencies, then execute the target's action.
	Each of the dependencies will only be executed once, and the order is not guaranteed other than what is defined by the dependencies.

	"""

	def __init__(self):
		self._targets = {}
		self._deps = {}

	def target(self, name, action, deps = []):
		"""Adds a target to the builder"""
		if ' ' in name:
			raise ValueError('name may not contain spaces')

		self._targets[name] = action
		self.depends(name, deps)

	def depends(self, name, deps):
		"""Adds a dependency to the builder"""
		if not isinstance(name, str):
			raise TypeError('name must be a string')

		if callable(deps):
			self._add_dep(name, deps)
		elif isinstance(deps, list):
			for dep in deps:
				self.depends(name, dep)
		elif isinstance(deps, str):
			for dep in deps.strip().split():
				self._add_dep(name, dep)
		else:
			raise TypeError(str(type(deps)) + ' is not a valid dependancy type')

	def execute(self, name):
		"""Executes a target on the builder"""
		if not isinstance(name, str):
			raise TypeError('name must be a string')

		if name not in self._targets:
			raise LookupError(name + ' is not a valid target')

		self._execute(name, [])

	def get_targets(self):
		"""Retrieves a sorted list of all targets available on this builder"""
		targets = self._targets.keys()
		targets.sort()
		return targets

	targets = property(get_targets)

	def _add_dep(self, name, dep):
		if name in self._deps:
			if dep not in self._deps:
				self._deps[name].append(dep)
		else:
			self._deps[name] = [dep]

	def _execute(self, name, done):
		if name in self._deps:
			deps = self._deps[name]
			for dep in deps:
				if callable(dep) and dep not in done:
					done.append(dep)
					dep()
				else:
					self._execute(dep, done)

		action = self._targets[name]

		if name not in done:
			done.append(name)
			if isinstance(action, str):
				subprocess.check_call(action, shell=True)
			elif callable(action):
				action()
			elif action is None:
				pass
			else:
				raise TypeError(name + ' is not a valid target type')


class BuilderTestCase(unittest.TestCase):
	"""Unit tests for the Builder class"""
	def setUp(self):
		self.targetCalled = 0

	def target(self):
		self.targetCalled += 1

	def test_add_target(self):
		builder = Builder()
		builder.target('target', self.target)
		self.assertIn('target', builder._targets)

	def test_add_target_with_space(self):
		builder = Builder()
		with self.assertRaises(ValueError):
			builder.target('target with space', self.target)

	def test_execute(self):
		builder = Builder()
		builder.target('target', self.target)
		builder.execute('target')
		self.assertEquals(self.targetCalled, 1)

	def test_add_dep(self):
		builder = Builder()
		builder.target('target', self.target)
		builder.target('target2', self.target)
		builder.depends('target', 'target2')
		self.assertIn('target', builder._deps)

	def test_execute_string_dep(self):
		builder = Builder()
		builder.target('target', self.target)
		builder.target('target2', self.target)
		builder.depends('target', 'target2')
		builder.execute('target')
		self.assertEquals(self.targetCalled, 2)

	def test_execute_function_dep(self):
		builder = Builder()
		builder.target('target', self.target)
		builder.depends('target', self.target)
		builder.execute('target')
		self.assertEquals(self.targetCalled, 2)

	def test_execute_list_dep(self):
		builder = Builder()
		builder.target('target', self.target)
		builder.target('target2', self.target)
		builder.depends('target', ['target2', self.target])
		builder.execute('target')
		self.assertEquals(self.targetCalled, 3)

	def test_execute_multi_string_dep(self):
		builder = Builder()
		builder.target('target', self.target)
		builder.target('target2', self.target)
		builder.target('target3', self.target)
		builder.depends('target', 'target2 target3')
		builder.execute('target')
		self.assertEquals(self.targetCalled, 3)

	def test_execute_dup_dep(self):
		builder = Builder()
		builder.target('target', self.target)
		builder.target('target2', self.target)
		builder.target('target3', self.target)
		builder.depends('target', 'target2')
		builder.depends('target', 'target3')
		builder.depends('target2', 'target3')
		builder.execute('target')
		self.assertEquals(self.targetCalled, 3)

	def test_execute_command(self):
		builder = Builder()
		builder.target('target', 'echo test')
		builder.execute('target')

	def test_execute_string_dep_in_target(self):
		builder = Builder()
		builder.target('target', self.target)
		builder.target('target2', self.target, 'target')
		builder.execute('target2')
		self.assertEquals(self.targetCalled, 2)

	def test_execute_none_target(self):
		builder = Builder()
		builder.target('target', self.target)
		builder.target('noneTarget', None)
		builder.depends('noneTarget', 'target')
		builder.execute('noneTarget')
		self.assertEquals(self.targetCalled, 1)

	def test_dep_order(self):
		target1_complete = {'value': False}

		def target1_dep():
			self.assertEquals(self.targetCalled, 1)
			target1_complete['value'] = True

		def target2_dep():
			self.assertEquals(target1_complete['value'], True)

		builder = Builder()
		builder.target('target', self.target)
		builder.target('target2', target1_dep)
		builder.target('target3', target2_dep, 'target2')
		builder.depends('target2', 'target')
		builder.execute('target3')
		self.assertEquals(self.targetCalled, 1)
		self.assertEquals(target1_complete['value'], True)

	def test_get_targets(self):
		builder = Builder()
		builder.target('target1', None)
		builder.target('target2', self.target)
		builder.target('target3', 'echo target3')
		targets = builder.targets
		self.assertEquals(len(targets), 3)
		self.assertIn('target1', targets)
		self.assertIn('target2', targets)
		self.assertIn('target3', targets)

if __name__ == '__main__':
    unittest.main()
