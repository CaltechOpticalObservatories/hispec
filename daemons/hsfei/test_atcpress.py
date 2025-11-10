import time
from libby.daemon import LibbyDaemon

class PeerA(LibbyDaemon):
    peer_id = "peer-A"
    bind = "tcp://*:5556"
    address_book = {
        "atcpress": "tcp://127.0.0.1:5555",
    }
    discovery_enabled = True
    discovery_interval_s = 2.0

    def on_start(self, libby):
        try:
            if not libby.wait_for_key("atcpress", "get.data", timeout_s=2.5):
                libby.learn_peer_keys("atcpress",
                                      ["connect", "disconnect", "get.data", "set.units"])
        except AttributeError:
            pass

        print("[PeerA] asking atcpress: get.data pressure1")
        res = libby.rpc("atcpress", "get.data",
                        {"item": "pressure1", "t0": time.time()}, ttl_ms=8000)
        print("[PeerA] result:", res)

        # publish a status
        libby.publish("alerts.status", {"source": "atcpress", "ok": True})
        print("[PeerA] published alerts.status")

if __name__ == "__main__":
    PeerA().serve()
