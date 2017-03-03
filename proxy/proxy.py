from server import Server

class Proxy():

    def __init__(self, proxy, logger, allowedfqdns, memcached):
        self._proxy = proxy
        self._logger = logger
        self._allowedfqdns = allowedfqdns
        self._memcached = memcached
        self._jobs = []

    def start(self):
        p = Server(name="Test",args=(self._logger, '', 80, self._allowedfqdns, self._memcached))
        self._jobs.append(p)
        p.start()

        # This will block
        p.join()

    def stop(self):
        for p in self._jobs:
            p.stop()
            self._jobs.remove(p)
