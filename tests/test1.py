# -*- coding: utf-8 -*-

import sys
import os
sys.path.insert(0, os.path.abspath(".."))

from twisted.internet import protocol
from twisted.trial import unittest
from twisted.test import proto_helpers
import base64
import struct
import socket
from twunnel import proxy_server

class TestTunnelProtocol(protocol.Protocol):
    def __init__(self):
        pass
        
    def connectionMade(self):
        pass
        
    def connectionLost(self, reason):
        pass
        
    def dataReceived(self, data):
        pass
        
    def tunnelOutputProtocol_connectionMade(self, data):
        pass

class HTTPSTunnelTestCase(unittest.TestCase):
    def setUp(self):
        self.configuration = \
        {
            "PROXY_SERVER": 
            {
                "TYPE": "HTTPS",
                "ADDRESS": "127.0.0.1",
                "PORT": 8080,
                "ACCOUNT": 
                {
                    "NAME": "",
                    "PASSWORD": ""
                }
            }
        }
        self.address = "127.0.0.1"
        self.port = 80
        
        self.tunnelOutputProtocolFactory = proxy_server.HTTPSTunnelOutputProtocolFactory(self.configuration, self.address, self.port)
        self.tunnelOutputProtocolFactory.tunnelProtocol = TestTunnelProtocol()
        self.tunnelOutputProtocol = self.tunnelOutputProtocolFactory.buildProtocol((self.address, self.port))
        self.transport = proto_helpers.StringTransport()
        self.tunnelOutputProtocol.makeConnection(self.transport)
        
    def tearDown(self):
        self.transport.loseConnection()
        
    def test(self):
        value = self.transport.value()
        self.transport.clear()
        
        self.assertEqual(value, "CONNECT %s:%d HTTP/1.1\r\n\r\n" % (self.address, self.port))
        
        self.tunnelOutputProtocol.dataReceived("HTTP/1.1 200 OK\r\n\r\n")

class HTTPSTunnelBasicAuthenticationTestCase(unittest.TestCase):
    def setUp(self):
        self.configuration = \
        {
            "PROXY_SERVER": 
            {
                "TYPE": "HTTPS",
                "ADDRESS": "127.0.0.1",
                "PORT": 8080,
                "ACCOUNT": 
                {
                    "NAME": "1",
                    "PASSWORD": "2"
                }
            }
        }
        self.address = "127.0.0.1"
        self.port = 80
        
        self.tunnelOutputProtocolFactory = proxy_server.HTTPSTunnelOutputProtocolFactory(self.configuration, self.address, self.port)
        self.tunnelOutputProtocolFactory.tunnelProtocol = TestTunnelProtocol()
        self.tunnelOutputProtocol = self.tunnelOutputProtocolFactory.buildProtocol((self.address, self.port))
        self.transport = proto_helpers.StringTransport()
        self.tunnelOutputProtocol.makeConnection(self.transport)
        
    def tearDown(self):
        self.transport.loseConnection()
        
    def test(self):
        value = self.transport.value()
        self.transport.clear()
        
        self.assertEqual(value, "CONNECT %s:%d HTTP/1.1\r\nProxy-Authorization: Basic %s\r\n\r\n" % (self.address, self.port, base64.standard_b64encode("%s:%s" % (self.configuration["PROXY_SERVER"]["ACCOUNT"]["NAME"], self.configuration["PROXY_SERVER"]["ACCOUNT"]["PASSWORD"]))))
        
        self.tunnelOutputProtocol.dataReceived("HTTP/1.1 200 OK\r\n\r\n")

class SOCKS5TunnelIPv4TestCase(unittest.TestCase):
    def setUp(self):
        self.configuration = \
        {
            "PROXY_SERVER": 
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
        }
        self.address = "127.0.0.1"
        self.port = 80
        
        self.tunnelOutputProtocolFactory = proxy_server.SOCKS5TunnelOutputProtocolFactory(self.configuration, self.address, self.port)
        self.tunnelOutputProtocolFactory.tunnelProtocol = TestTunnelProtocol()
        self.tunnelOutputProtocol = self.tunnelOutputProtocolFactory.buildProtocol((self.address, self.port))
        self.transport = proto_helpers.StringTransport()
        self.tunnelOutputProtocol.makeConnection(self.transport)
        
    def tearDown(self):
        self.transport.loseConnection()
        
    def test(self):
        value = self.transport.value()
        self.transport.clear()
        
        version, numberOfMethods, method = struct.unpack("!BBB", value[:3])
        
        self.assertEqual(version, 0x05)
        self.assertEqual(numberOfMethods, 0x01)
        self.assertEqual(method, 0x00)
        
        value = struct.pack("!BB", 0x05, 0x00)
        
        self.tunnelOutputProtocol.dataReceived(value)
        
        value = self.transport.value()
        self.transport.clear()
        
        version, method, reserved, addressType = struct.unpack("!BBBB", value[:4])
        
        self.assertEqual(version, 0x05)
        self.assertEqual(method, 0x01)
        self.assertEqual(reserved, 0x00)
        self.assertEqual(addressType, 0x01)
        
        address, port = struct.unpack("!IH", value[4:10])
        address = socket.inet_ntoa(struct.pack("!I", address))
        
        self.assertEqual(address, self.address)
        self.assertEqual(port, self.port)
        
        value = struct.pack("!BBBBIH", 0x05, 0x00, 0x00, 0x01, 0, 0)
        
        self.tunnelOutputProtocol.dataReceived(value)

class SOCKS5TunnelDNTestCase(unittest.TestCase):
    def setUp(self):
        self.configuration = \
        {
            "PROXY_SERVER": 
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
        }
        self.address = "localhost"
        self.port = 80
        
        self.tunnelOutputProtocolFactory = proxy_server.SOCKS5TunnelOutputProtocolFactory(self.configuration, self.address, self.port)
        self.tunnelOutputProtocolFactory.tunnelProtocol = TestTunnelProtocol()
        self.tunnelOutputProtocol = self.tunnelOutputProtocolFactory.buildProtocol((self.address, self.port))
        self.transport = proto_helpers.StringTransport()
        self.tunnelOutputProtocol.makeConnection(self.transport)
        
    def tearDown(self):
        self.transport.loseConnection()
        
    def test(self):
        value = self.transport.value()
        self.transport.clear()
        
        version, numberOfMethods, method = struct.unpack("!BBB", value[:3])
        
        self.assertEqual(version, 0x05)
        self.assertEqual(numberOfMethods, 0x01)
        self.assertEqual(method, 0x00)
        
        value = struct.pack("!BB", 0x05, 0x00)
        
        self.tunnelOutputProtocol.dataReceived(value)
        
        value = self.transport.value()
        self.transport.clear()
        
        version, method, reserved, addressType = struct.unpack("!BBBB", value[:4])
        
        self.assertEqual(version, 0x05)
        self.assertEqual(method, 0x01)
        self.assertEqual(reserved, 0x00)
        self.assertEqual(addressType, 0x03)
        
        addressLength, = struct.unpack("!B", value[4])
        address, port = struct.unpack("!%dsH" % addressLength, value[5:])
        
        self.assertEqual(address, self.address)
        self.assertEqual(port, self.port)
        
        value = struct.pack("!BBBBIH", 0x05, 0x00, 0x00, 0x01, 0, 0)
        
        self.tunnelOutputProtocol.dataReceived(value)

if __name__ == "__main__":
    unittest.main()