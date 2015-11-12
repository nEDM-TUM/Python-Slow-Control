from twisted.internet import reactor
from threading import Thread
import logging
import json
from autobahn.twisted.websocket import (WebSocketServerFactory,
                                        listenWS,
                                        WebSocketServerProtocol)

__all__ = [
  "debug", "log", "error", "exception", "listening_addresses",
  "BroadcastLogFactory", "BroadcastLogHandler", "BroadcastLogProtocol"
]

def debug(*args):
    """
    Alias for logging.debug
    """
    _logger.debug(*args)

def log(*args):
    """
    Alias for logging.info
    """
    _logger.info(*args)

def error(*args):
    """
    Alias for logging.error
    """
    _logger.error(*args)

def exception(*args):
    """
    Alias for logging.exception
    """
    _logger.exception(*args)

class BroadcastLogProtocol(WebSocketServerProtocol):
    """
    Internal class to define broadcast log protocol
    """
    def onOpen(self):
        self.factory.register(self)

    def connectionLost(self, reason):
        super(BroadcastLogProtocol, self).connectionLost(reason)
        self.factory.unregister(self)

class BroadcastLogFactory(WebSocketServerFactory):
    """
    Factory for broadcast logger
    """
    def __init__(self, *args, **kw):
        super(BroadcastLogFactory, self).__init__(*args, **kw)
        self.clients = []

    def register(self, client):
        if client not in self.clients:
            self.clients.append(client)

    def unregister(self, client):
        if client in self.clients:
            self.clients.remove(client)

    def broadcast(self, msg):
        prepMsg = self.prepareMessage(json.dumps(msg))
        for c in self.clients:
            c.sendPreparedMessage(prepMsg)


class BroadcastLogHandler(logging.Handler):
    """
    Listens on 0.0.0.0 (all interfaces) and sends log messages to connected
    clients.  Clients must connect via WebSocket and receive logging
    information in JSON format, e.g.::

        { 'level' : 'INFO', 'msg' : 'A sent message' }


    This is used in live logging of Raspberry Pis, for example in the
    nEDM-Interface.
    """
    def __init__(self):
        logging.Handler.__init__(self)
        factory = BroadcastLogFactory("ws://0.0.0.0:0")
        factory.protocol = BroadcastLogProtocol
        self.port = listenWS(factory).getHost()
        self.factory = factory

        # Start the reactor thread, setting daemon to True
        # (daemon = True) allows the program to normally end, which allows the
        # close function to be called, where we explicitly join the reactor
        # thread
        self._th = Thread(target=reactor.run, args=(False,))
        self._th.daemon = True
        self._th.start()

    def getPort(self):
        return self.port

    def _sendRecord(self, msg):
        reactor.callFromThread(self.factory.broadcast, msg)

    def emit(self, record):
        self._sendRecord(dict(level=record.levelname, msg=self.format(record)))

    def close(self):
        logging.Handler.close(self)
        reactor.callFromThread(reactor.stop)
        self._th.join()

_logger = logging.getLogger(__name__)
_logger.setLevel(logging.INFO)
_formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
_handler = None

def use_broadcaster():
    """
    Call this function to enable the use of BroadcastLogHandler
    """
    global _handler
    if _handler: return
    _handler = BroadcastLogHandler()
    _handler.setFormatter(_formatter)
    _logger.addHandler(_handler)


def listening_addresses():
    """
    Return external addresses where we are listening to broadcast the log:

    :returns: list -- [ 'ws://x.x.x.x:y', ... ]
    """
    import netifaces
    port = _handler.getPort().port
    obj = [x[netifaces.AF_INET][0]['addr']
      for x in map(netifaces.ifaddresses, netifaces.interfaces())
      if netifaces.AF_INET in x]
    obj.remove("127.0.0.1")
    return map(lambda x: "ws://{}:{}".format(x,port), obj)

