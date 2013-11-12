import sys
import os
sys.path.insert(0, os.path.abspath(".."))

from twisted.internet import reactor, ssl
import logging
from twunnel import local, remote
from example import example

logging.basicConfig(level=logging.DEBUG)

port_LOCAL_PROXY_SERVER = None
port_REMOTE_PROXY_SERVER = None

def start_LOCAL_PROXY_SERVER():
    global port_LOCAL_PROXY_SERVER
    
    configuration = \
    {
        "PROXY_SERVERS": [],
        "LOCAL_PROXY_SERVER":
        {
            "TYPE": "SOCKS5",
            "ADDRESS": "127.0.0.1",
            "PORT": 1080
        },
        "REMOTE_PROXY_SERVERS":
        [
            {
                "TYPE": "WSS",
                "ADDRESS": "127.0.0.1",
                "PORT": 8443,
                "CERTIFICATE":
                {
                    "AUTHORITY":
                    {
                        "FILE": "example4/CA.pem"
                    }
                },
                "ACCOUNT":
                {
                    "NAME": "1",
                    "PASSWORD": "2"
                }
            }
        ]
    }
    
    port_LOCAL_PROXY_SERVER = local.createPort(configuration)
    port_LOCAL_PROXY_SERVER.startListening()

def stop_LOCAL_PROXY_SERVER():
    global port_LOCAL_PROXY_SERVER
    
    port_LOCAL_PROXY_SERVER.stopListening()

def start_REMOTE_PROXY_SERVER():
    global port_REMOTE_PROXY_SERVER
    
    configuration = \
    {
        "PROXY_SERVERS": [],
        "REMOTE_PROXY_SERVER":
        {
            "TYPE": "WSS",
            "ADDRESS": "127.0.0.1",
            "PORT": 8443,
            "CERTIFICATE":
            {
                "FILE": "example4/C.pem",
                "KEY":
                {
                    "FILE": "example4/CK.pem"
                }
            },
            "ACCOUNTS":
            [
                {
                    "NAME": "1",
                    "PASSWORD": "2"
                }
            ]
        }
    }
    
    port_REMOTE_PROXY_SERVER = remote.createPort(configuration)
    port_REMOTE_PROXY_SERVER.startListening()

def stop_REMOTE_PROXY_SERVER():
    global port_REMOTE_PROXY_SERVER
    
    port_REMOTE_PROXY_SERVER.stopListening()

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
                "ACCOUNT":
                {
                    "NAME": "",
                    "PASSWORD": ""
                }
            }
        ]
    }
    
    contextFactory = None
    if factory.port == 443:
        contextFactory = ssl.ClientContextFactory()
    
    tunnel = local.createTunnel(configuration)
    tunnel.connect(factory.address, factory.port, factory, contextFactory)

reactor.callLater(0, start_REMOTE_PROXY_SERVER)
reactor.callLater(5, start_LOCAL_PROXY_SERVER)
reactor.callLater(10, connect, 80)
reactor.callLater(15, connect, 443)
reactor.callLater(20, stop_LOCAL_PROXY_SERVER)
reactor.callLater(25, stop_REMOTE_PROXY_SERVER)
reactor.callLater(30, reactor.stop)
reactor.run()