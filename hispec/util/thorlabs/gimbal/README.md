# ThorLabs PPC102 Kinesis Controler

Low-level Python library to control PPC102 2 axis controllers using the Thor Labs communication protocal documentation {https://www.thorlabs.com/Software/Motion%20Control/APT_Communications_Protocol_v39.pdf}

## Features
- Connect and disconnect to PPC102 over Socket
- Move individual axes to positions using open loop(volts) or closed loop(position)

## Example Usage
```python
    from hispec.util.thorlabs.gimbal.PPC102_lib import PPC102_Coms, DATA_CODES

    dev =  PPC102_Coms("BlueGimbalMount.ini")

    #Open connection
    dev.open()

    # set voltage on channel 1 and get result (open loop control)
    dev.set_output_volts(channel=1,volts=100)
    res = dev.get_output_volts(channel=1)

    # switch channels to closed loop
    dev.set_loop(channel=1,loop=2)
    dev.set_loop(channel=2,loop=2)

    # set positions on channel 1 or 2 and get result
    dev.set_position(channel=1,pos=100)
    dev.set_position(channel=2,pos=100)
    cur_pos1 = dev.get_position(channel=1)
    cur_pos2 = dev.get_position(channel=2)

    # switch channels to open loop
    dev.set_loop(channel=1,loop=1)
    dev.set_loop(channel=2,loop=1)

    #Set voltages to zero
    dev.set_output_volts(channel=1,volts=0)
    dev.set_output_volts(channel=2,volts=0)

    # close socket connection
    dev.close()
```

## 🧪 Testing
Unit tests are located in `tests/util/thorlabs/gimbal` directory and use `test_gimbal_mount.py` to test the reliability of set/get enable, loops, position, voltage and setting "max" voltage for a channel. 
