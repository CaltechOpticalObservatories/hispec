from libby import Libby
from libby.daemon import LibbyDaemon
import configparser
from hispec.util.ozoptics.dd100mc import OZController

class YJetAtten(LibbyDaemon):
    """
    Daemon to control the YJ attenuator via OZ Optics DD100-MC controller.
    """
    peer_id = "yjetatten"
    bind = "tcp://*:5555"
    address_book = {
        #"yjetatten": "tcp://192.168.29.:5555",
        "peer-A": "tcp://127.0.0.1:5556"
    }
    dev = None
    host = None
    port = None
    discovery_enabled = True
    discovery_interval_s = 2.0

    def on_start(self, libby: Libby) -> None:
        # set up the daemon from config and initialize the device
        config = configparser.ConfigParser()
        config.read('hscal.config')
        self.host = config.get("Device Control","yjetatten_host")
        self.port = int(config.get("Device Control","yjetatten_port"))
        self.dev = OZController()
        self.add_services({
            "connect":         lambda p: self.connect(),
            "disconnect":      lambda p: self.disconnect(),
            "initialize":      lambda p: self.initialize(),
            "status":          lambda p: self.status(),
            "get.attenuation": lambda p: self.get_atomic_value(item='atten'),
            "set.attenuation": lambda p: self.set_attenuation(p.get('value')),
            "get.position":    lambda p: self.get_atomic_value(item='pos'),
            "set.position":    lambda p: self.set_position(p.get('position')),
        })

        ret = self.connect()
        if ret.get("Connect") == "Failed":
            libby.publish("yjetatten", {"Daemon Startup": "Failed", "Error": ret.get("Error")})
        ret = self.initialize()
        if ret.get("Initialize") == "Failed":
            libby.publish("yjetatten", {"Daemon Startup": "Failed", "Error": ret.get("Error")})
        libby.publish("yjetatten", {"Daemon Startup": "Success"})


    def on_stop(self, libby: Libby | None) -> None:
        # clean up on daemon stop
        ret = self.disconnect()
        if ret.get("Disconnect") == "Failed":
            libby.publish("yjetatten", {"Daemon Shutdown": "Failed", "Error": ret.get("Error")})
        else:
            libby.publish("yjetatten", {"Daemon Shutdown": "Success"})


    def connect(self):
        """ handles connection to the device """
        args = [self.host, self.port]
        try:
            self.dev.connect(*args, con_type='tcp')
        except Exception as e:
            return {"Connect": f"Failed", "Error": str(e)}
        if not self.dev.is_connected():
            return {"Connect": "Failed", "Error": "Unknown"}
        return {"Connect": "Success"}

    def disconnect(self):
        """ handles disconnection from the device """
        try:
            self.dev.disconnect()
        except Exception as e:
            return {"Disconnect": f"Failed", "Error": str(e)}
        if self.dev.is_connected():
            return {"Disconnect": "Failed", "Error": "Unknown"}
        return {"Disconnect": "Success"}

    def initialize(self):
        """ initializes the device (i.e. homing) """
        ret = self.dev.initialize_controller()
        if not self.dev.homed:
            return {"Initialize": "Failed", "Error": ret["error"] if "error" in ret else "Unknown"}
        return {"Initialize": "Success"}

    def status(self):
        """ gets the device params """
        ret = self.dev.get_params()
        return {"Status": ret}

    def get_atomic_value(self, item: str):
        """ gets an atomic value from the device """
        if item not in ['atten','pos']:
            return {"Value": None, "Error": "Invalid item requested"}
        ret = self.dev.get_atomic_value(item)
        if ret is None:
            return {"Value": None, "Error": "Failed to get value"}
        else:
            return {"Value": ret}

    def set_attenuation(self, value: float):
        """ sets the attenuation value on the device """
        ret = self.dev.set_attenuation(value)
        if 'error' in ret:
            return {"Set Attenuation": "Failed", "Error": ret["error"]}
        return {"Set Attenuation": "Success", "Current Attenuation": ret['data']}

    def set_position(self, position: int):
        """ sets the position value on the device """
        ret = self.dev.set_position(position)
        if 'error' in ret:
            return {"Set Position": "Failed", "Error": ret["error"]}
        return {"Set Position": "Success", "Current Position": ret['data']}

if __name__ == "__main__":
    yj_attenuator = YJetAtten()
    yj_attenuator.serve()







