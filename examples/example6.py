import sys
import os
sys.path.insert(0, os.path.abspath(".."))

from twisted.internet import reactor, ssl
from twisted.python import log
from twunnel import local_proxy_server, logger, proxy_server
from examples import example

log.startLogging(sys.stdout)

configuration = \
{
    "LOGGER":
    {
        "LEVEL": 3
    }
}

logger.configure(configuration)

port_LOCAL_PROXY_SERVER = None

def start_LOCAL_PROXY_SERVER():
    global port_LOCAL_PROXY_SERVER
    
    configuration = \
    {
        "PROXY_SERVERS": [],
        "LOCAL_PROXY_SERVER":
        {
            "TYPE": "HTTPS",
            "ADDRESS": "127.0.0.1",
            "PORT": 8443
        },
        "REMOTE_PROXY_SERVERS": []
    }
    
    port_LOCAL_PROXY_SERVER = local_proxy_server.createPort(configuration)
    port_LOCAL_PROXY_SERVER.startListening()

def stop_LOCAL_PROXY_SERVER():
    global port_LOCAL_PROXY_SERVER
    
    port_LOCAL_PROXY_SERVER.stopListening()

def connect(port):
    factory = example.ProtocolFactory()
    factory.address = "www.google.com"
    factory.port = port
    
    configuration = \
    {
        "PROXY_SERVERS":
        [
            {
                "TYPE": "HTTPS",
                "ADDRESS": "127.0.0.1",
                "PORT": 8443
            }
        ]
    }
    
    contextFactory = None
    if factory.port == 443:
        contextFactory = ssl.ClientContextFactory()
    
    tunnel = proxy_server.createTunnel(configuration)
    tunnel.connect(factory.address, factory.port, factory, contextFactory)

reactor.callLater(0, start_LOCAL_PROXY_SERVER)
reactor.callLater(10, connect, 80)
reactor.callLater(15, connect, 443)
reactor.callLater(20, stop_LOCAL_PROXY_SERVER)
reactor.callLater(25, reactor.stop)
reactor.run()