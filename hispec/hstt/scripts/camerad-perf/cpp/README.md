## Description of Test Files
- run_camerad_expose:
  - Overview:
    - Used to run a batch of images through camerad for testing
    - Configures camerad and the Archon for a given set of test parameters (subwindow, exposure time, etc.)
  - Use:
    - Start camerad
    - Run this script
- TimingJitter_DownstreamRunner
  - Overview:
    - Tests the timing at the output of the ZMQ socket from camerad.
    - This lets check whether the ZMQ layer is adding latency/jitter to the image readout.
    - Outputs a CSV file with timestamps
  - Use:
    - Start camerad
    - Start this script
    - Start a camerad acquisition (can use run_camerad_expose)
    - Plot results using TimingJitter_DownstreamPlotter
- TimingJitter_DownstreamPlotter
  - Overview: Used to plot results from _DownstreamRunner
  - Use: Provide a `filename` at top of a CSV file from the Runner
