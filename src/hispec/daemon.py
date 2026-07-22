from libby.daemon import LibbyDaemon


class HispecDaemon(LibbyDaemon):
    """Instantiates the HispecDaemon base using LibbyDaemon.
    Transport is with rabbitmq and discovery is false since rabbitmq includes it's own discovery.
    """

    transport = "rabbitmq"
    discovery_enabled = False
