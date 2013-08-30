GraphRunner
=======

A tool to execute functions based on a simple dependency graph

The GraphRunner class enables the creation of scripts by encapsulating targets and dependencies.
Targets define what it is your script needs to do and dependencies relate different targets together.

A single target can be one of:
* A callable that requires 0 arguments
* None, which does nothing (useful for grouping dependencies without requiring a final action)
* A string, which is called using subprocess.check_call(cmd, shell=True)

Dependencies are defined in one of three ways:
* a space-delimited string of targets
* A callable that requires 0 arguments (An "anonymous dependency")
* a list of dependencies

Multiple dependencies can be defined for a single target and they will be appended.

When you execute a target it's dependencies will be recursively executed before the target's action is performed.
Each of the dependencies will only be executed once, and the order is not guaranteed other than what is defined by the dependencies.
Cycles in the graph are possible, and are handled at run time (dependecies of a target are always executed before the target)
Missing dependencies are reported at run time (as KeyError exceptions).
