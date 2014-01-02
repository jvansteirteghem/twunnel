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

port_LOCAL_PROXY_SERVER_1 = None
port_LOCAL_PROXY_SERVER_2 = None

def start_LOCAL_PROXY_SERVER_1():
    global port_LOCAL_PROXY_SERVER_1
    
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
    
    port_LOCAL_PROXY_SERVER_1 = local_proxy_server.createPort(configuration)
    port_LOCAL_PROXY_SERVER_1.startListening()

def stop_LOCAL_PROXY_SERVER_1():
    global port_LOCAL_PROXY_SERVER_1
    
    port_LOCAL_PROXY_SERVER_1.stopListening()

def start_LOCAL_PROXY_SERVER_2():
    global port_LOCAL_PROXY_SERVER_2
    
    configuration = \
    {
        "PROXY_SERVERS": [],
        "LOCAL_PROXY_SERVER":
        {
            "TYPE": "SOCKS5",
            "ADDRESS": "127.0.0.1",
            "PORT": 1080
        },
        "REMOTE_PROXY_SERVERS": []
    }
    
    port_LOCAL_PROXY_SERVER_2 = local_proxy_server.createPort(configuration)
    port_LOCAL_PROXY_SERVER_2.startListening()

def stop_LOCAL_PROXY_SERVER_2():
    global port_LOCAL_PROXY_SERVER_2
    
    port_LOCAL_PROXY_SERVER_2.stopListening()

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
            },
            {
                "TYPE": "SOCKS5",
                "ADDRESS": "127.0.0.1",
                "PORT": 1080
            }
        ]
    }
    
    contextFactory = None
    if factory.port == 443:
        contextFactory = ssl.ClientContextFactory()
    
    tunnel = proxy_server.createTunnel(configuration)
    tunnel.connect(factory.address, factory.port, factory, contextFactory)

reactor.callLater(0, start_LOCAL_PROXY_SERVER_1)
reactor.callLater(10, start_LOCAL_PROXY_SERVER_2)
reactor.callLater(15, connect, 80)
reactor.callLater(20, connect, 443)
reactor.callLater(25, stop_LOCAL_PROXY_SERVER_2)
reactor.callLater(30, stop_LOCAL_PROXY_SERVER_1)
reactor.callLater(35, reactor.stop)
reactor.run()