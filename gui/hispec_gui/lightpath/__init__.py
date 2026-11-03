"""Light path GUI: a schematic of the HISPEC optical path, one node per mechanism.

Run with `hispec-lightpath`, or `python -m hispec_gui.lightpath`. The window
reads node states from a StateSource; for now that is MockSource, and a
libby-backed source that talks to the daemons comes next.
"""
