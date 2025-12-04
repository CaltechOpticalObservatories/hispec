import logging
from libby.daemon import LibbyDaemon
from hispec.util.ozoptics.dd100mc import OZController

class YJetAtten(LibbyDaemon):
    """
    Daemon to control the YJ attenuator via OZ Optics DD100-MC controller.
    """
    peer_id = "yjetatten"
    group_id = "hscal"

    # RabbitMQ config
    transport = "rabbitmq"
    rabbitmq_url = "amqp://localhost"
    discovery_enabled = True
    discovery_interval_s = 2.0

    # pub/sub topics
    topics = {}

    def __init__(self, host=None, port=None):
        """ initialize the YJ attenuator daemon
        Args:
            host (str): hostname or IP address of the DD100-MC controller
            port (int): port number of the DD100-MC controller
        """
        self.host = host
        self.port = port

        # OZoptics DD100-MC controller instance
        self.dev = OZController()

        # daemon state
        self.state = {
            'connected': False,
            'error': ''
        }

        # set up logging
        self.logger = logging.getLogger(self.peer_id)

        # call parent init
        super().__init__()


    def on_start(self, libby):
        """ called when daemon starts """
        self.logger.info("Starting YJ attenuator daemon")

        services = {
            "connect":         lambda p: self.connect(),
            "disconnect":      lambda p: self.disconnect(),
            "initialize":      lambda p: self.initialize(),
            "reset":           lambda p: self.reset(),
            "params.get":      lambda p: self.get_stage_params(),
            "attenuation.get": lambda p: self.get_atomic_value(item='atten'),
            "attenuation.set": lambda p: self.set_attenuation(p.get('attenuation')),
            "position.get":    lambda p: self.get_atomic_value(item='pos'),
            "position.set":    lambda p: self.set_position(p.get('position')),
            "position.step":   lambda p: self.step(p.get('direction')),
        }
        self.add_services(services)
        self.logger.info('Registered %d RPC services', len(services))

        if self.host is None or self.port is None:
            self.logger.error("No host or port specified")
            self.state['error'] = "No host or port specified"
        else:
            ret = self.connect()
            if not ret["ok"]:
                self.state['error'] = ret.get("error")
            else:
                ret = self.initialize()
                if not ret["ok"]:
                    self.state['error'] = ret.get("error")
                else:
                    self.state['connected'] = True
                    self.state['error'] = ''

        libby.publish("yjetatten.status", self.state)

    def on_stop(self, libby):
        # clean up on daemon stop
        ret = self.disconnect()
        if not ret["ok"]:
            libby.publish("yjetatten", {"Daemon Shutdown": "Failed", "Error": ret.get("error")})
        else:
            libby.publish("yjetatten", {"Daemon Shutdown": "Success"})


    def connect(self):
        """ handles connection to the device """
        if self.state['connected']:
            return {"ok": True, "message": "Already connected"}

        try:
            self.dev.connect(host=self.host, port=self.port, con_type='tcp')
            if self.dev.is_connected():
                self.logger.info("Connected to YJ Attenuator controller at %s:%d", self.host, self.port)
                return {"ok": True, "message": "Connected to controller"}
            else:
                self.logger.error("Failed to connect to YJ Attenuator controller")
                return {"ok": False, "error": "Failed to connect to controller"}
        except Exception as e:
            self.logger.error("Exception while connecting to YJ Attenuator controller: %s", str(e))
            return {"ok": False, "error": f"Failed to connect to controller {str(e)}"}

    def disconnect(self):
        """ handles disconnection from the device """
        if not self.state['connected']:
            return {"ok": True, "message": "Already disconnected"}

        try:
            self.dev.disconnect()
            if not self.dev.is_connected():
                self.logger.info("Disconnected from YJ Attenuator controller")
                return {"ok": True, "message": "Disconnected from controller"}
            else:
                self.logger.error("Failed to disconnect from YJ Attenuator controller")
                return {"ok": False, "error": "Failed to disconnect from controller"}
        except Exception as e:
            self.logger.error("Exception while disconnecting from YJ Attenuator controller: %s", str(e))
            return {"ok": False, "error": f"Failed to disconnect from controller {str(e)}"}


    def initialize(self):
        """ initializes the device (i.e. homing) """
        if self.dev.initialize():
            self.logger.info("Initialized YJ Attenuator controller")
            return {"ok": True, "message": "Successfully homed device"}
        else:
            self.logger.error("Failed to initialize YJ Attenuator controller")
            return {"ok": False, "error": "Failed to home device"}

    def reset(self):
        """ resets the device """
        ret = self.dev.reset()
        if ret is not None:
            self.logger.info("Reset YJ Attenuator controller")
            return {"ok": True, "message": "Successfully reset device", "reset": ret}
        else:
            self.logger.error("Failed to reset YJ Attenuator controller")
            return {"ok": False, "error": "Failed to reset device"}

    def get_stage_params(self):
        """ gets the device params """
        ret = self.dev.get_params()
        if ret is not None:
            self.logger.debug("get_params: %s", str(ret))
            return {"ok": True, "params": ret}
        else:
            self.logger.error("Failed to get YJ Attenuator controller params")
            return {"ok": False, "error": "Failed to get device params"}

    def get_atomic_value(self, item: str):
        """ gets an atomic value from the device """
        if item not in ['atten','pos']:
            self.logger.error("Invalid item requested: %s", item)
            return {"ok": False, "error": "Invalid item requested"}
        ret = self.dev.get_atomic_value(item)
        if ret is None:
            self.logger.error(f"Failed to get {item} from YJ Attenuator controller")
            return {"ok": False, "error": f"Failed to get {item} value"}
        else:
            self.logger.debug("get_%s: %s", item, str(ret))
            return {"ok": True, item: ret}

    def set_attenuation(self, attenuation: float):
        """ sets the attenuation value on the device """
        if self.dev.set_attenuation(attenuation):
            self.logger.info("Successfully set attenuation to %f", attenuation)
            return {"ok": True, "message": "Successfully set attenuation"}
        else:
            self.logger.error("Failed to set attenuation to %f", attenuation)
            return {"ok": False, "error": "Failed to set attenuation"}

    def set_position(self, position: int):
        """ sets the position value on the device """
        if self.dev.set_pos(position):
            self.logger.info("Successfully set position to %d", position)
            return {"ok": True, "message": "Successfully set position"}
        else:
            self.logger.error("Failed to set position to %d", position)
            return {"ok": False, "error": "Failed to set position"}

    def step(self, direction: str):
        """ steps the device in the given direction """
        if direction not in ['F', 'B']:
            return {"ok": False, "error": "Invalid direction, must be 'F' or 'B'"}
        ret = self.dev.step(direction)
        if ret is not None:
            self.logger.info("Successfully stepped device %s to position %d", direction, ret)
            return {"ok": True, "message": "Successfully stepped device", "position": ret}
        else:
            self.logger.error("Failed to step device %s", direction)
            return {"ok": False, "error": "Failed to step device"}


if __name__ == "__main__":
    yj_attenuator = YJetAtten()
    yj_attenuator.serve()







