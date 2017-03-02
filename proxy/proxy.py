from receiver import Receiver

class Proxy():

    def __init__(self, proxy, logger):
        self._proxy = proxy
        self._logger = logger
        self._jobs = []

        p = Receiver(name="receiver-%s" % "id", args=(self._logger, '224.1.1.1', 2001))
        self._jobs.append(p)
        p = Receiver(name="receiver-%s" % "id", args=(self._logger, '224.1.1.1', 2002))
        self._jobs.append(p)
        p = Receiver(name="receiver-%s" % "id", args=(self._logger, '224.1.1.1', 2003))
        self._jobs.append(p)

    def start(self):
        for p in self._jobs:
            p.start()

    def stop(self):
        pass