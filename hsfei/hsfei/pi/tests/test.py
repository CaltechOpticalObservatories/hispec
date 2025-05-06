from hsfei import PIControllerBase

if __name__ == "__main__":
    controller = PIControllerBase()
    controller.connect_tcp("192.168.1.100", 10005)
    print(controller.get_idn())
    print(controller.getSerialNumber())
    print(controller.get_axes())
    print(controller.get_position(0))

    controller.disconnect()
