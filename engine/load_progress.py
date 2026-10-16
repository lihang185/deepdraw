"""Throttled pickle stream progress; no Qt event processing during decoding."""
import time


class ProgressReader:
    def __init__(self, stream, callback):
        self.stream = stream
        self.callback = callback
        position = stream.tell()
        stream.seek(0, 2)
        self.total = stream.tell()
        stream.seek(position)
        self.last_report = 0
        self.report(True)

    def report(self, force=False):
        now = time.monotonic()
        if self.callback and (force or now-self.last_report >= .15):
            self.last_report = now
            self.callback('读取模型', self.stream.tell(), self.total)

    def read(self, size=-1):
        data = self.stream.read(size)
        self.report()
        return data

    def readline(self, size=-1):
        data = self.stream.readline(size)
        self.report()
        return data

    def readinto(self, buffer):
        count = self.stream.readinto(buffer)
        self.report()
        return count
