builder
=======

A very simple build script library

This library enables the creation of very simple build scripts by encapsulating targets and dependencies.
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
