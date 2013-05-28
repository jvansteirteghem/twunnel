# -*- coding: utf-8 -*-

from test import twunnel

from twisted.internet import protocol
from twisted.trial import unittest
from twisted.test import proto_helpers

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

class HTTPTunnelTestCase(unittest.TestCase):
    def setUp(self):
        self.configuration = {
            "PROXY_SERVER": {
                "TYPE": "HTTP",
                "ADDRESS": "127.0.0.1",
                "PORT": 8080,
                "AUTHENTICATION": {
                    "USERNAME": "",
                    "PASSWORD": ""
                }
            }
        }
        self.address = "127.0.0.1"
        self.port = 80
        
        self.protocolFactory = twunnel.HTTPTunnelOutputProtocolFactory(self.configuration, self.address, self.port, TestTunnelProtocol())
        self.protocolFactory.protocol = twunnel.HTTPTunnelOutputProtocol
        self.protocol = self.protocolFactory.buildProtocol((self.address, self.port))
        self.transport = proto_helpers.StringTransport()
        self.protocol.makeConnection(self.transport)

    def test_response_200(self):
        self.assertEqual(self.transport.value(), "CONNECT %s:%d HTTP/1.0\r\n\r\n" % (self.address, self.port))
        
        self.transport.clear()
        self.protocol.dataReceived("HTTP/1.0 200 OK\r\n\r\n")
        
        self.assertEqual(self.transport.disconnecting, False)
    
    def test_response_401(self):
        self.assertEqual(self.transport.value(), "CONNECT %s:%d HTTP/1.0\r\n\r\n" % (self.address, self.port))
        
        self.transport.clear()
        self.protocol.dataReceived("HTTP/1.0 401 Unauthorized\r\n\r\n")
        
        self.assertEqual(self.transport.disconnecting, True)

class HTTPTunnelWithBasicAuthenticationTestCase(unittest.TestCase):
    def setUp(self):
        self.configuration = {
            "PROXY_SERVER": {
                "TYPE": "HTTP",
                "ADDRESS": "127.0.0.1",
                "PORT": 8080,
                "AUTHENTICATION": {
                    "USERNAME": "1",
                    "PASSWORD": "2"
                }
            }
        }
        self.address = "127.0.0.1"
        self.port = 80
        
        self.protocolFactory = twunnel.HTTPTunnelOutputProtocolFactory(self.configuration, self.address, self.port, TestTunnelProtocol())
        self.protocolFactory.protocol = twunnel.HTTPTunnelOutputProtocol
        self.protocol = self.protocolFactory.buildProtocol((self.address, self.port))
        self.transport = proto_helpers.StringTransport()
        self.protocol.makeConnection(self.transport)

    def test_response_200(self):
        self.assertEqual(self.transport.value(), "CONNECT %s:%d HTTP/1.0\r\nProxy-Authorization: Basic MToy\r\n\r\n" % (self.address, self.port))
        
        self.transport.clear()
        self.protocol.dataReceived("HTTP/1.0 200 OK\r\n\r\n")
        
        self.assertEqual(self.transport.disconnecting, False)
    
    def test_response_401(self):
        self.assertEqual(self.transport.value(), "CONNECT %s:%d HTTP/1.0\r\nProxy-Authorization: Basic MToy\r\n\r\n" % (self.address, self.port))
        
        self.transport.clear()
        self.protocol.dataReceived("HTTP/1.0 401 Unauthorized\r\n\r\n")
        
        self.assertEqual(self.transport.disconnecting, True)

if __name__ == "__main__":
    unittest.main()
