import sys
import os
sys.path.insert(0, os.path.abspath(".."))

from twisted.internet import reactor, ssl
import logging
from twunnel import local
from example import example

logging.basicConfig(level=logging.DEBUG)

port_LOCAL_PROXY_SERVER = None

def start_LOCAL_PROXY_SERVER():
    global port_LOCAL_PROXY_SERVER
    
    configuration = \
    {
        "PROXY_SERVERS": [],
        "LOCAL_PROXY_SERVER":
        {
            "ADDRESS": "127.0.0.1",
            "PORT": 1080
        }
    }
    
    port_LOCAL_PROXY_SERVER = local.createPort(configuration)
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
                "TYPE": "SOCKS5",
                "ADDRESS": "127.0.0.1",
                "PORT": 1080,
                "AUTHENTICATION": 
                {
                    "USERNAME": "",
                    "PASSWORD": ""
                }
            }
        ]
    }
    
    contextFactory = None
    if factory.port == 443:
        contextFactory = ssl.ClientContextFactory()
    
    tunnel = local.Tunnel(configuration)
    tunnel.connect(factory.address, factory.port, factory, contextFactory)

reactor.callLater(0, start_LOCAL_PROXY_SERVER)
reactor.callLater(10, connect, 80)
reactor.callLater(15, connect, 443)
reactor.callLater(20, stop_LOCAL_PROXY_SERVER)
reactor.callLater(25, reactor.stop)
reactor.run()