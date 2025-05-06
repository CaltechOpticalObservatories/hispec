from hsfei import PIControllerBase

if __name__ == "__main__":
    controller = PIControllerBase()
    controller.connect_tcp("192.168.1.100", 10005)
    print(controller.get_idn())
    print(controller.get_serial_number())
    print(controller.get_axes())
    print(controller.get_position(0))
    print(controller.get_error_code())
    print(controller.servo_status(1))
    # print(controller.halt_motion())
    controller.set_named_position("1", 'test')

    controller.disconnect()
