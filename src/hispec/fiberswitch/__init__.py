"""The fiber switcher daemons' logic: switch, inspection camera, controller.

Each channel (red and blue) runs two daemons, which hold the three classes of
the design between them:

- daemons/hsfibers/fiberswitch (fiberswitchred, fiberswitchblue):
  - MechanicalSwitch: the switcher PLC, through fiber_switcher.FiberSwitcher,
    sequenced by switch.SwitchSequencer.
  - MechanicalSwitchController: per-port connection policy, inspect-and-clean
    and reference images, in controller.FiberSwitchController, which drives
    the switch directly and the camera daemon through
    camclient.CameraDaemonClient.
- daemons/hsfibers/fiberswitchcam (fiberswitchredcam, fiberswitchbluecam):
  - MechanicalSwitchCamera: the Lightel DI-2000, through di2000.Di2000 (or
    camserver.RemoteDi2000) and lightel's inspection pipeline, wrapped by
    camera.InspectionCamera.

Nothing here imports libby, cv2 or the drivers at module level, so the logic
can be tested with fakes.
"""
