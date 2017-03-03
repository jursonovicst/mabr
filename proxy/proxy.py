from server import Server

class Proxy():

    def __init__(self, proxy, logger, allowedfqdns):
        self._proxy = proxy
        self._logger = logger
        self._allowedfqdns = allowedfqdns
        self._jobs = []

#        p = Receiver(name="receiver-%s" % "id", args=(self._logger, '224.1.1.1', 2001))
#        self._jobs.append(p)
#        p = Receiver(name="receiver-%s" % "id", args=(self._logger, '224.1.1.1', 2002))
#        self._jobs.append(p)
#        p = Receiver(name="receiver-%s" % "id", args=(self._logger, '224.1.1.1', 2003))
#        self._jobs.append(p)


    def start(self):
        p = Server(name="Test",args=(self._logger, '', 80, self._allowedfqdns))
        self._jobs.append(p)
        p.start()

        # This will block
        p.join()

    def stop(self):
        for p in self._jobs:
            p.stop()
            self._jobs.remove(p)
