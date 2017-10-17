from threading import Lock, ThreadError


class MemDB:

    _db = {}

    def __init__(self):
        self._lock = Lock()

    def set(self, key, value):
        try:
            self._lock.acquire()
            self._db[key] = value
            self._lock.release()
            return True
        except ThreadError:     # catch MemDB related exceptions and return False
            return False

        return False

    def get(self, key):
        ret = None
        try:
            self._lock.acquire()
            if key in self._db:
                ret = self._db[key]
            self._lock.release()
        except ThreadError:     # if only release was wrong, return object
            return ret

        return ret

    def get_multi(self, keys):
        ret = {}
        try:
            self._lock.acquire()
            for key in keys:
                if key in self._db:
                    ret[key] = self._db[key]
            self._lock.release()
        except ThreadError:
            return ret

        return ret

