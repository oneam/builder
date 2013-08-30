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

class GraphRunner:
	"""A tool to execute functions based on a simple dependency graph

	The GraphRunner class enables the creation of scripts by encapsulating targets and dependencies.
	Targets define what it is your script needs to do and dependencies relate different targets together.

	A single target can be one of:
	* A callable that requires 0 arguments
	* None, which does nothing (useful for grouping dependencies without requiring a final action)

	Dependencies are defined in one of three ways:
	* a space-delimited string of targets
	* A callable that requires 0 arguments (An "anonymous dependency")
	* a list of dependencies

	Multiple dependencies can be defined for a single target and they will be appended.

	When you execute a target it's dependencies will be recursively executed before the target's action is performed.
	Each of the dependencies will only be executed once, and the order is not guaranteed other than what is defined by the dependencies.
	Cycles in the graph are possible, and are handled at run time (dependecies of a target are always executed before the target)
	Missing dependencies are reported at run time (as KeyError exceptions).

	"""

	def __init__(self):
		self._targets = {}
		self._deps = {}

	def target(self, name, action, deps = []):
		"""Adds a target to the graph"""
		if ' ' in name:
			raise ValueError('name may not contain spaces')

		self._targets[name] = action
		self.depends(name, deps)

	def depends(self, name, deps):
		"""Adds a dependency to the graph"""
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
		"""Executes a target on the graph"""
		if not isinstance(name, str):
			raise TypeError('name must be a string')

		if name not in self._targets:
			raise LookupError(name + ' is not a valid target')

		self._execute(name, [])

	def get_deps(self, name):
		"""Retrieves a list of the dependencies for a given target"""
		if not isinstance(name, str):
			raise TypeError('name must be a string')

		if name not in self._targets:
			raise LookupError(name + ' is not a valid target')

		if name not in self._deps:
			return []

		return self._deps[name]

	def get_targets(self):
		"""Retrieves an alpha sorted list of all targets available on this graph"""
		targets = self._targets.keys()
		targets.sort()
		return targets

	targets = property(get_targets)

	def _add_dep(self, name, dep):
		if name in self._deps:
			deps = self._deps[name]
			if dep not in deps:
				deps.append(dep)
		else:
			self._deps[name] = [dep]

	def _execute(self, name, done):
		if not isinstance(name, str):
			raise TypeError('name must be a string')

		if name in done:
			return

		done.append(name)

		if name in self._deps:
			deps = self._deps[name]
			for dep in deps:
				if callable(dep):
					if dep not in done:
						done.append(dep)
						dep()
				else:
					self._execute(dep, done)

		action = self._targets[name]

		if isinstance(action, str):
			subprocess.check_call(action, shell=True)
		elif callable(action):
			action()
		elif action is None:
			pass
		else:
			raise TypeError(name + ' is not a valid target type')


class GraphRunnerTestCase(unittest.TestCase):
	"""Unit tests for the GraphRunner class"""

	def setUp(self):
		self.targetCalled = 0
		self.harness = GraphRunner()

	def target(self):
		self.targetCalled += 1

	def test_add_target(self):
		self.harness.target('target', self.target)
		self.assertIn('target', self.harness._targets)

	def test_add_target_with_space(self):
		with self.assertRaises(ValueError):
			self.harness.target('target with space', self.target)

	def test_execute(self):
		self.harness.target('target', self.target)
		self.harness.execute('target')
		self.assertEquals(self.targetCalled, 1)

	def test_add_dep(self):
		self.harness.target('target', self.target)
		self.harness.target('target2', self.target)
		self.harness.depends('target', 'target2')
		self.assertIn('target', self.harness._deps)

	def test_execute_string_dep(self):
		self.harness.target('target', self.target)
		self.harness.target('target2', self.target)
		self.harness.depends('target', 'target2')
		self.harness.execute('target')
		self.assertEquals(self.targetCalled, 2)

	def test_execute_function_dep(self):
		self.harness.target('target', self.target)
		self.harness.depends('target', self.target)
		self.harness.execute('target')
		self.assertEquals(self.targetCalled, 2)

	def test_execute_list_dep(self):
		self.harness.target('target', self.target)
		self.harness.target('target2', self.target)
		self.harness.target('target3', self.target)
		self.harness.depends('target', ['target2', 'target3', self.target])
		self.harness.execute('target')
		self.assertEquals(self.targetCalled, 4)

	def test_execute_list_dep_simple_syntax(self):
		self.harness.target('target2', self.target)
		self.harness.target('target3', self.target)
		self.harness.target('target', self.target, ['target2', 'target3', self.target])
		self.harness.execute('target')
		self.assertEquals(self.targetCalled, 4)

	def test_execute_multi_string_dep(self):
		self.harness.target('target', self.target)
		self.harness.target('target2', self.target)
		self.harness.target('target3', self.target)
		self.harness.depends('target', 'target2 target3')
		self.harness.execute('target')
		self.assertEquals(self.targetCalled, 3)

	def test_execute_dup_dep(self):
		self.harness.target('target', self.target)
		self.harness.target('target2', self.target)
		self.harness.target('target3', self.target)
		self.harness.target('target4', self.target)
		self.harness.depends('target3', 'target4')
		self.harness.depends('target2', ['target3', 'target4'])
		self.harness.depends('target', 'target2 target3 target4')
		self.harness.execute('target')
		self.assertEquals(self.targetCalled, 4)

	def test_execute_command(self):
		self.harness.target('target', 'echo test')
		self.harness.execute('target')

	def test_execute_string_dep_in_target(self):
		self.harness.target('target', self.target)
		self.harness.target('target2', self.target, 'target')
		self.harness.execute('target2')
		self.assertEquals(self.targetCalled, 2)

	def test_execute_none_target(self):
		self.harness.target('target', self.target)
		self.harness.target('noneTarget', None)
		self.harness.depends('noneTarget', 'target')
		self.harness.execute('noneTarget')
		self.assertEquals(self.targetCalled, 1)

	def test_dep_order(self):
		target1_complete = {'value': False}

		def target1_dep():
			self.assertEquals(self.targetCalled, 1)
			target1_complete['value'] = True

		def target2_dep():
			self.assertEquals(target1_complete['value'], True)

		self.harness.target('target', self.target)
		self.harness.target('target2', target1_dep)
		self.harness.target('target3', target2_dep, 'target2')
		self.harness.depends('target2', 'target')
		self.harness.execute('target3')
		self.assertEquals(self.targetCalled, 1)
		self.assertEquals(target1_complete['value'], True)

	def test_get_targets(self):
		self.harness.target('target1', None)
		self.harness.target('target2', self.target)
		self.harness.target('target3', 'echo target3')
		targets = self.harness.targets
		self.assertEquals(len(targets), 3)
		self.assertIn('target1', targets)
		self.assertIn('target2', targets)
		self.assertIn('target3', targets)

	def test_circular_dep(self):
		self.harness.target('target', self.target)
		self.harness.target('target2', self.target)
		self.harness.depends('target', 'target2')
		self.harness.depends('target2', 'target')
		self.harness.execute('target')
		self.assertEquals(self.targetCalled, 2)

	def test_missing_dep(self):
		self.harness.target('target', self.target)
		self.harness.depends('target', 'target2')
		with self.assertRaises(KeyError):
			self.harness.execute('target')

	def test_execute_once(self):
		anonymous = lambda : self.target()
		self.harness.target('target', self.target)
		self.harness.target('target2', self.target)
		self.harness.target('target3', self.target)
		self.harness.depends('target', 'target2 target3')
		self.harness.depends('target2', 'target3')
		self.harness.depends('target', anonymous)
		self.harness.depends('target2', anonymous)
		self.harness.depends('target3', anonymous)
		self.harness.execute('target')
		self.assertEquals(self.targetCalled, 4) # 3 unique named targets and 1 unique anonymous dependency


if __name__ == '__main__':
	unittest.main()
