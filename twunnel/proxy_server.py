# Copyright (c) Jeroen Van Steirteghem
# See LICENSE

from twisted.internet import protocol, reactor
from twisted.internet.abstract import isIPAddress, isIPv6Address
import base64
import socket
import struct
import twunnel.logger

def setDefaultConfiguration(configuration, keys):
    if "PROXY_SERVERS" in keys:
        configuration.setdefault("PROXY_SERVERS", [])
        i = 0
        while i < len(configuration["PROXY_SERVERS"]):
            configuration["PROXY_SERVERS"][i].setdefault("TYPE", "")
            if configuration["PROXY_SERVERS"][i]["TYPE"] == "HTTPS":
                configuration["PROXY_SERVERS"][i].setdefault("ADDRESS", "")
                configuration["PROXY_SERVERS"][i].setdefault("PORT", 0)
                configuration["PROXY_SERVERS"][i].setdefault("ACCOUNT", {})
                configuration["PROXY_SERVERS"][i]["ACCOUNT"].setdefault("NAME", "")
                configuration["PROXY_SERVERS"][i]["ACCOUNT"].setdefault("PASSWORD", "")
            else:
                if configuration["PROXY_SERVERS"][i]["TYPE"] == "SOCKS5":
                    configuration["PROXY_SERVERS"][i].setdefault("ADDRESS", "")
                    configuration["PROXY_SERVERS"][i].setdefault("PORT", 0)
                    configuration["PROXY_SERVERS"][i].setdefault("ACCOUNT", {})
                    configuration["PROXY_SERVERS"][i]["ACCOUNT"].setdefault("NAME", "")
                    configuration["PROXY_SERVERS"][i]["ACCOUNT"].setdefault("PASSWORD", "")
            i = i + 1

class TunnelProtocol(protocol.Protocol):
    def __init__(self):
        twunnel.logger.log(3, "trace: TunnelProtocol.__init__")
    
    def connectionMade(self):
        twunnel.logger.log(3, "trace: TunnelProtocol.connectionMade")
        
        self.factory.tunnelOutputProtocolFactory.tunnelProtocol = self
        self.factory.tunnelOutputProtocol = self.factory.tunnelOutputProtocolFactory.buildProtocol(self.transport.getPeer())
        self.factory.tunnelOutputProtocol.makeConnection(self.transport)
    
    def connectionLost(self, reason):
        twunnel.logger.log(3, "trace: TunnelProtocol.connectionLost")
        
        if self.factory.tunnelOutputProtocol is not None:
            self.factory.tunnelOutputProtocol.connectionLost(reason)
        else:
            if self.factory.outputProtocol is not None:
                self.factory.outputProtocol.connectionLost(reason)
    
    def dataReceived(self, data):
        twunnel.logger.log(3, "trace: TunnelProtocol.dataReceived")
        
        if self.factory.tunnelOutputProtocol is not None:
            self.factory.tunnelOutputProtocol.dataReceived(data)
        else:
            if self.factory.outputProtocol is not None:
                self.factory.outputProtocol.dataReceived(data)
    
    def tunnelOutputProtocol_connectionMade(self, data):
        twunnel.logger.log(3, "trace: TunnelProtocol.tunnelOutputProtocol_connectionMade")
        
        self.factory.tunnelOutputProtocol = None
        
        if self.factory.contextFactory is not None:
            self.transport.startTLS(self.factory.contextFactory)
        
        self.factory.outputProtocol = self.factory.outputProtocolFactory.buildProtocol(self.transport.getPeer())
        self.factory.outputProtocol.makeConnection(self.transport)
        
        if len(data) > 0:
            self.factory.outputProtocol.dataReceived(data)

class TunnelProtocolFactory(protocol.ClientFactory):
    protocol = TunnelProtocol
    
    def __init__(self, outputProtocolFactory, tunnelOutputProtocolFactory, contextFactory=None):
        twunnel.logger.log(3, "trace: TunnelProtocolFactory.__init__")
        
        self.outputProtocol = None
        self.outputProtocolFactory = outputProtocolFactory
        self.tunnelOutputProtocol = None
        self.tunnelOutputProtocolFactory = tunnelOutputProtocolFactory
        self.contextFactory = contextFactory
    
    def startedConnecting(self, connector):
        twunnel.logger.log(3, "trace: TunnelProtocolFactory.startedConnecting")
        
        self.outputProtocolFactory.startedConnecting(connector)
    
    def clientConnectionFailed(self, connector, reason):
        twunnel.logger.log(3, "trace: TunnelProtocolFactory.clientConnectionFailed")
        
        self.outputProtocolFactory.clientConnectionFailed(connector, reason)
    
    def clientConnectionLost(self, connector, reason):
        twunnel.logger.log(3, "trace: TunnelProtocolFactory.clientConnectionLost")
        
        if self.outputProtocol is None:
            self.outputProtocolFactory.clientConnectionFailed(connector, reason)
        else:
            self.outputProtocolFactory.clientConnectionLost(connector, reason)

class Tunnel(object):
    def __init__(self, configuration):
        twunnel.logger.log(3, "trace: Tunnel.__init__")
        
        self.configuration = configuration
    
    def connect(self, address, port, outputProtocolFactory, contextFactory=None, timeout=30, bindAddress=None):
        twunnel.logger.log(3, "trace: Tunnel.connect")
        
        if len(self.configuration["PROXY_SERVERS"]) == 0:
            if contextFactory is None:
                return reactor.connectTCP(address, port, outputProtocolFactory, timeout, bindAddress)
            else:
                return reactor.connectSSL(address, port, outputProtocolFactory, contextFactory, timeout, bindAddress)
        else:
            i = len(self.configuration["PROXY_SERVERS"])
            
            configuration = {}
            configuration["PROXY_SERVER"] = self.configuration["PROXY_SERVERS"][i - 1]
            
            tunnelOutputProtocolFactoryClass = self.getTunnelOutputProtocolFactoryClass(configuration["PROXY_SERVER"]["TYPE"])
            tunnelOutputProtocolFactory = tunnelOutputProtocolFactoryClass(configuration, address, port)
            
            tunnelProtocolFactory = TunnelProtocolFactory(outputProtocolFactory, tunnelOutputProtocolFactory, contextFactory)
            
            i = i - 1
            
            while i > 0:
                configuration = {}
                configuration["PROXY_SERVER"] = self.configuration["PROXY_SERVERS"][i - 1]
                
                tunnelOutputProtocolFactoryClass = self.getTunnelOutputProtocolFactoryClass(configuration["PROXY_SERVER"]["TYPE"])
                tunnelOutputProtocolFactory = tunnelOutputProtocolFactoryClass(configuration, self.configuration["PROXY_SERVERS"][i]["ADDRESS"], self.configuration["PROXY_SERVERS"][i]["PORT"])
                
                tunnelProtocolFactory = TunnelProtocolFactory(tunnelProtocolFactory, tunnelOutputProtocolFactory)
                
                i = i - 1
            
            return reactor.connectTCP(self.configuration["PROXY_SERVERS"][i]["ADDRESS"], self.configuration["PROXY_SERVERS"][i]["PORT"], tunnelProtocolFactory, timeout, bindAddress)
    
    def getTunnelOutputProtocolFactoryClass(self, type):
        twunnel.logger.log(3, "trace: Tunnel.getTunnelOutputProtocolFactoryClass")
        
        if type == "HTTPS":
            return HTTPSTunnelOutputProtocolFactory
        else:
            if type == "SOCKS5":
                return SOCKS5TunnelOutputProtocolFactory
            else:
                return None

defaultTunnelClass = Tunnel

def getDefaultTunnelClass():
    global defaultTunnelClass
    
    return defaultTunnelClass

def setDefaultTunnelClass(tunnelClass):
    global defaultTunnelClass
    
    defaultTunnelClass = tunnelClass

def createTunnel(configuration):
    setDefaultConfiguration(configuration, ["PROXY_SERVERS"])
    
    tunnelClass = getDefaultTunnelClass()
    tunnel = tunnelClass(configuration)
    
    return tunnel

class HTTPSTunnelOutputProtocol(protocol.Protocol):
    def __init__(self):
        twunnel.logger.log(3, "trace: HTTPSTunnelOutputProtocol.__init__")
        
        self.data = ""
        self.dataState = 0
        
    def connectionMade(self):
        twunnel.logger.log(3, "trace: HTTPSTunnelOutputProtocol.connectionMade")
        
        request = "CONNECT " + str(self.factory.address) + ":" + str(self.factory.port) + " HTTP/1.1\r\n"
        
        if self.factory.configuration["PROXY_SERVER"]["ACCOUNT"]["NAME"] != "":
            request = request + "Proxy-Authorization: Basic " + base64.standard_b64encode(self.factory.configuration["PROXY_SERVER"]["ACCOUNT"]["NAME"] + ":" + self.factory.configuration["PROXY_SERVER"]["ACCOUNT"]["PASSWORD"]) + "\r\n"
        
        request = request + "\r\n"
        
        self.transport.write(request)
        
    def connectionLost(self, reason):
        twunnel.logger.log(3, "trace: HTTPSTunnelOutputProtocol.connectionLost")
    
    def dataReceived(self, data):
        twunnel.logger.log(3, "trace: HTTPSTunnelOutputProtocol.dataReceived")
        
        self.data = self.data + data
        if self.dataState == 0:
            self.processDataState0()
            return
    
    def processDataState0(self):
        twunnel.logger.log(3, "trace: HTTPSTunnelOutputProtocol.processDataState0")
        
        i = self.data.find("\r\n\r\n")
        
        if i == -1:
            return
            
        i = i + 4
        
        response = self.data[:i]
        
        self.data = self.data[i:]
        
        responseLines = response.split("\r\n")
        responseLine = responseLines[0].split(" ", 2)
        
        if len(responseLine) != 3:
            self.transport.loseConnection()
            return
        
        responseVersion = responseLine[0].upper()
        responseStatus = responseLine[1]
        responseStatusMessage = responseLine[2]
        
        if responseStatus != "200":
            self.transport.loseConnection()
            return
        
        self.factory.tunnelProtocol.tunnelOutputProtocol_connectionMade(self.data)
        
        self.data = ""
        self.dataState = 1

class HTTPSTunnelOutputProtocolFactory(protocol.ClientFactory):
    protocol = HTTPSTunnelOutputProtocol
    
    def __init__(self, configuration, address, port):
        twunnel.logger.log(3, "trace: HTTPSTunnelOutputProtocolFactory.__init__")
        
        self.configuration = configuration
        self.address = address
        self.port = port
        self.tunnelProtocol = None
    
    def startedConnecting(self, connector):
        twunnel.logger.log(3, "trace: HTTPSTunnelOutputProtocolFactory.startedConnecting")
    
    def clientConnectionFailed(self, connector, reason):
        twunnel.logger.log(3, "trace: HTTPSTunnelOutputProtocolFactory.clientConnectionFailed")
    
    def clientConnectionLost(self, connector, reason):
        twunnel.logger.log(3, "trace: HTTPSTunnelOutputProtocolFactory.clientConnectionLost")

class SOCKS5TunnelOutputProtocol(protocol.Protocol):
    def __init__(self):
        twunnel.logger.log(3, "trace: SOCKS5TunnelOutputProtocol.__init__")
        
        self.data = ""
        self.dataState = 0
    
    def connectionMade(self):
        twunnel.logger.log(3, "trace: SOCKS5TunnelOutputProtocol.connectionMade")
        
        if self.factory.configuration["PROXY_SERVER"]["ACCOUNT"]["NAME"] != "":
            request = struct.pack("!BBB", 0x05, 0x01, 0x02)
            self.transport.write(request)
            
            self.dataState = 0
        else:
            request = struct.pack("!BBB", 0x05, 0x01, 0x00)
            self.transport.write(request)
            
            self.dataState = 1
    
    def connectionLost(self, reason):
        twunnel.logger.log(3, "trace: SOCKS5TunnelOutputProtocol.connectionLost")
    
    def dataReceived(self, data):
        twunnel.logger.log(3, "trace: SOCKS5TunnelOutputProtocol.dataReceived")
        
        self.data = self.data + data
        if self.dataState == 0:
            self.processDataState0()
            return
        if self.dataState == 1:
            self.processDataState1()
            return
        if self.dataState == 2:
            self.processDataState2()
            return
    
    def processDataState0(self):
        twunnel.logger.log(3, "trace: SOCKS5TunnelOutputProtocol.processDataState0")
        
        if len(self.data) < 2:
            return
        
        version, method = struct.unpack("!BB", self.data[:2])
        
        self.data = self.data[2:]
        
        if method != 0x02:
            self.transport.loseConnection()
            return
        
        name = self.factory.configuration["PROXY_SERVER"]["ACCOUNT"]["NAME"]
        nameLength = len(name)
        password = self.factory.configuration["PROXY_SERVER"]["ACCOUNT"]["PASSWORD"]
        passwordLength = len(password)
        
        response = struct.pack("!B", 0x01)
        response = response + struct.pack("!B%ds" % nameLength, nameLength, name)
        response = response + struct.pack("!B%ds" % passwordLength, passwordLength, password)
        self.transport.write(response)
        
        self.dataState = 1
    
    def processDataState1(self):
        twunnel.logger.log(3, "trace: SOCKS5TunnelOutputProtocol.processDataState1")
        
        if len(self.data) < 2:
            return
        
        version, status = struct.unpack("!BB", self.data[:2])
        
        self.data = self.data[2:]
        
        if status != 0x00:
            self.transport.loseConnection()
            return
        
        addressType = 0x03
        if isIPAddress(self.factory.address) == True:
            addressType = 0x01
        else:
            if isIPv6Address(self.factory.address) == True:
                addressType = 0x04
        
        request = struct.pack("!BBB", 0x05, 0x01, 0x00)
        
        if addressType == 0x01:
            address, = struct.unpack("!I", socket.inet_aton(self.factory.address))
            request = request + struct.pack("!BI", 0x01, address)
        else:
            if addressType == 0x03:
                address = str(self.factory.address)
                addressLength = len(address)
                request = request + struct.pack("!BB%ds" % addressLength, 0x03, addressLength, address)
            else:
                self.transport.loseConnection()
                return
        
        request = request + struct.pack("!H", self.factory.port)
        self.transport.write(request)
        
        self.dataState = 2
    
    def processDataState2(self):
        twunnel.logger.log(3, "trace: SOCKS5TunnelOutputProtocol.processDataState2")
        
        if len(self.data) < 4:
            return
        
        version, status, reserved, addressType = struct.unpack("!BBBB", self.data[:4])
        
        if status != 0x00:
            self.transport.loseConnection()
            return
        
        if addressType == 0x01:
            if len(self.data) < 10:
                return
            
            address, port = struct.unpack("!IH", self.data[4:10])
            address = socket.inet_ntoa(struct.pack("!I", address))
            
            self.data = self.data[10:]
        else:
            if addressType == 0x03:
                if len(self.data) < 5:
                    return
                
                addressLength, = struct.unpack("!B", self.data[4])
                
                if len(self.data) < 7 + addressLength:
                    return
                
                address, port = struct.unpack("!%dsH" % addressLength, self.data[5:])
                
                self.data = self.data[7 + addressLength:]
            else:
                self.transport.loseConnection()
                return
        
        self.factory.tunnelProtocol.tunnelOutputProtocol_connectionMade(self.data)
        
        self.data = ""
        self.dataState = 3

class SOCKS5TunnelOutputProtocolFactory(protocol.ClientFactory):
    protocol = SOCKS5TunnelOutputProtocol
    
    def __init__(self, configuration, address, port):
        twunnel.logger.log(3, "trace: SOCKS5TunnelOutputProtocolFactory.__init__")
        
        self.configuration = configuration
        self.address = address
        self.port = port
        self.tunnelProtocol = None
    
    def startedConnecting(self, connector):
        twunnel.logger.log(3, "trace: SOCKS5TunnelOutputProtocolFactory.startedConnecting")
    
    def clientConnectionFailed(self, connector, reason):
        twunnel.logger.log(3, "trace: SOCKS5TunnelOutputProtocolFactory.clientConnectionFailed")
    
    def clientConnectionLost(self, connector, reason):
        twunnel.logger.log(3, "trace: SOCKS5TunnelOutputProtocolFactory.clientConnectionLost")