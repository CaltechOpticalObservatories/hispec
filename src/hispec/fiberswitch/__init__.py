"""The fiber switcher daemon's logic: switch, inspection camera, controller.

daemons/hsfibers/fiberswitch runs one instance per channel (red and blue),
each holding the three classes of the design:

- MechanicalSwitch: the switcher PLC, through fiber_switcher.FiberSwitcher,
  sequenced by switch.SwitchSequencer.
- MechanicalSwitchCamera: the Lightel DI-2000, through di2000.Di2000 and
  lightel's inspection pipeline, wrapped by camera.InspectionCamera.
- MechanicalSwitchController: per-port connection policy, inspect-and-clean
  and reference images, in controller.FiberSwitchController, which drives
  the other two directly.

Nothing here imports libby, cv2 or the drivers at module level, so the logic
can be tested with fakes.
"""
