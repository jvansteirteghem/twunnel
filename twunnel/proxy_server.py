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
                if configuration["PROXY_SERVERS"][i]["TYPE"] == "SOCKS4":
                    configuration["PROXY_SERVERS"][i].setdefault("ADDRESS", "")
                    configuration["PROXY_SERVERS"][i].setdefault("PORT", 0)
                    configuration["PROXY_SERVERS"][i].setdefault("ACCOUNT", {})
                    configuration["PROXY_SERVERS"][i]["ACCOUNT"].setdefault("NAME", "")
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
            if type == "SOCKS4":
                return SOCKS4TunnelOutputProtocolFactory
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
        
        request = "CONNECT "
        
        if isIPv6Address(self.factory.address) == True:
            request = request + "[" + str(self.factory.address) + "]:" + str(self.factory.port)
        else:
            request = request + str(self.factory.address) + ":" + str(self.factory.port)
        
        request = request + " HTTP/1.1\r\n"
        
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
            if self.processDataState0():
                return
    
    def processDataState0(self):
        twunnel.logger.log(3, "trace: HTTPSTunnelOutputProtocol.processDataState0")
        
        data = self.data
        
        i = data.find("\r\n\r\n")
        
        if i == -1:
            return True
            
        i = i + 4
        
        response = data[:i]
        
        data = data[i:]
        
        responseLines = response.split("\r\n")
        responseLine = responseLines[0].split(" ", 2)
        
        if len(responseLine) != 3:
            self.transport.loseConnection()
            
            return True
        
        responseVersion = responseLine[0].upper()
        responseStatus = responseLine[1]
        responseStatusMessage = responseLine[2]
        
        if responseStatus != "200":
            self.transport.loseConnection()
            
            return True
        
        self.factory.tunnelProtocol.tunnelOutputProtocol_connectionMade(data)
        
        self.data = ""
        self.dataState = 1
        
        return True

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

class SOCKS4TunnelOutputProtocol(protocol.Protocol):
    def __init__(self):
        twunnel.logger.log(3, "trace: SOCKS4TunnelOutputProtocol.__init__")
        
        self.data = ""
        self.dataState = 0
    
    def connectionMade(self):
        twunnel.logger.log(3, "trace: SOCKS4TunnelOutputProtocol.connectionMade")
        
        addressType = 0x03
        if isIPAddress(self.factory.address) == True:
            addressType = 0x01
        
        request = struct.pack("!BB", 0x04, 0x01)
        
        port = self.factory.port
        
        request = request + struct.pack("!H", port)
        
        address = 0
        if addressType == 0x01:
            address = self.factory.address
            address = socket.inet_pton(socket.AF_INET, address)
            address, = struct.unpack("!I", address)
        else:
            if addressType == 0x03:
                address = 1
        
        request = request + struct.pack("!I", address)
        
        name = self.factory.configuration["PROXY_SERVER"]["ACCOUNT"]["NAME"]
        name = name + "\x00"
        nameLength = len(name)
        
        request = request + struct.pack("!%ds" % nameLength, name)
        
        if addressType == 0x03:
            address = self.factory.address
            address = address + "\x00"
            addressLength = len(address)
            
            request = request + struct.pack("!%ds" % addressLength, address)
        
        self.transport.write(request)
        
        self.dataState = 0
        
    def connectionLost(self, reason):
        twunnel.logger.log(3, "trace: SOCKS4TunnelOutputProtocol.connectionLost")
    
    def dataReceived(self, data):
        twunnel.logger.log(3, "trace: SOCKS4TunnelOutputProtocol.dataReceived")
        
        self.data = self.data + data
        if self.dataState == 0:
            if self.processDataState0():
                return
    
    def processDataState0(self):
        twunnel.logger.log(3, "trace: SOCKS4TunnelOutputProtocol.processDataState0")
        
        data = self.data
        
        if len(data) < 8:
            return True
        
        status, = struct.unpack("!B", data[1:2])
        
        data = data[8:]
        
        if status != 0x5a:
            self.transport.loseConnection()
            
            return True
        
        self.factory.tunnelProtocol.tunnelOutputProtocol_connectionMade(data)
        
        self.data = ""
        
        return True

class SOCKS4TunnelOutputProtocolFactory(protocol.ClientFactory):
    protocol = SOCKS4TunnelOutputProtocol
    
    def __init__(self, configuration, address, port):
        twunnel.logger.log(3, "trace: SOCKS4TunnelOutputProtocolFactory.__init__")
        
        self.configuration = configuration
        self.address = address
        self.port = port
        self.tunnelProtocol = None
    
    def startedConnecting(self, connector):
        twunnel.logger.log(3, "trace: SOCKS4TunnelOutputProtocolFactory.startedConnecting")
    
    def clientConnectionFailed(self, connector, reason):
        twunnel.logger.log(3, "trace: SOCKS4TunnelOutputProtocolFactory.clientConnectionFailed")
    
    def clientConnectionLost(self, connector, reason):
        twunnel.logger.log(3, "trace: SOCKS4TunnelOutputProtocolFactory.clientConnectionLost")

class SOCKS5TunnelOutputProtocol(protocol.Protocol):
    def __init__(self):
        twunnel.logger.log(3, "trace: SOCKS5TunnelOutputProtocol.__init__")
        
        self.data = ""
        self.dataState = 0
    
    def connectionMade(self):
        twunnel.logger.log(3, "trace: SOCKS5TunnelOutputProtocol.connectionMade")
        
        request = struct.pack("!BBBB", 0x05, 0x02, 0x00, 0x02)
        
        self.transport.write(request)
        
        self.dataState = 0
        
    def connectionLost(self, reason):
        twunnel.logger.log(3, "trace: SOCKS5TunnelOutputProtocol.connectionLost")
    
    def dataReceived(self, data):
        twunnel.logger.log(3, "trace: SOCKS5TunnelOutputProtocol.dataReceived")
        
        self.data = self.data + data
        if self.dataState == 0:
            if self.processDataState0():
                return
        if self.dataState == 1:
            if self.processDataState1():
                return
        if self.dataState == 2:
            if self.processDataState2():
                return
        if self.dataState == 3:
            if self.processDataState3():
                return
        
    def processDataState0(self):
        twunnel.logger.log(3, "trace: SOCKS5TunnelOutputProtocol.processDataState0")
        
        data = self.data
        
        if len(data) < 2:
            return True
        
        version, method = struct.unpack("!BB", data[:2])
        
        data = data[2:]
        
        self.data = data
        
        if method == 0x00:
            self.dataState = 2
            
            return False
        else:
            if method == 0x02:
                name = self.factory.configuration["PROXY_SERVER"]["ACCOUNT"]["NAME"]
                nameLength = len(name)
                
                password = self.factory.configuration["PROXY_SERVER"]["ACCOUNT"]["PASSWORD"]
                passwordLength = len(password)
                
                request = struct.pack("!B", 0x01)
                request = request + struct.pack("!B%ds" % nameLength, nameLength, name)
                request = request + struct.pack("!B%ds" % passwordLength, passwordLength, password)
                
                self.transport.write(request)
                
                self.dataState = 1
                
                return True
            else:
                self.transport.loseConnection()
                
                return True
        
    def processDataState1(self):
        twunnel.logger.log(3, "trace: SOCKS5TunnelOutputProtocol.processDataState1")
        
        data = self.data
        
        if len(data) < 2:
            return True
        
        version, status = struct.unpack("!BB", data[:2])
        
        data = data[2:]
        
        self.data = data
        
        if status != 0x00:
            self.transport.loseConnection()
            
            return True
        
        self.dataState = 2
        
        return False
        
    def processDataState2(self):
        twunnel.logger.log(3, "trace: SOCKS5TunnelOutputProtocol.processDataState2")
        
        addressType = 0x03
        if isIPAddress(self.factory.address) == True:
            addressType = 0x01
        else:
            if isIPv6Address(self.factory.address) == True:
                addressType = 0x04
        
        request = struct.pack("!BBB", 0x05, 0x01, 0x00)
        
        if addressType == 0x01:
            address = self.factory.address
            address = socket.inet_pton(socket.AF_INET, address)
            address, = struct.unpack("!I", address)
            
            request = request + struct.pack("!BI", 0x01, address)
        else:
            if addressType == 0x03:
                address = self.factory.address
                addressLength = len(address)
                
                request = request + struct.pack("!BB%ds" % addressLength, 0x03, addressLength, address)
            else:
                if addressType == 0x04:
                    address = self.factory.address
                    address = socket.inet_pton(socket.AF_INET6, address)
                    address1, address2, address3, address4 = struct.unpack("!IIII", address)
                    
                    request = request + struct.pack("!BIIII", 0x04, address1, address2, address3, address4)
        
        port = self.factory.port
        
        request = request + struct.pack("!H", port)
        
        self.transport.write(request)
        
        self.dataState = 3
        
        return True
    
    def processDataState3(self):
        twunnel.logger.log(3, "trace: SOCKS5TunnelOutputProtocol.processDataState3")
        
        data = self.data
        
        if len(data) < 4:
            return True
        
        version, status, reserved, addressType = struct.unpack("!BBBB", data[:4])
        
        data = data[4:]
        
        if status != 0x00:
            self.transport.loseConnection()
            
            return True
        
        if addressType == 0x01:
            if len(data) < 4:
                return True
            
            address, = struct.unpack("!I", data[:4])
            address = struct.pack("!I", address)
            address = socket.inet_ntop(socket.AF_INET, address)
            
            data = data[4:]
        else:
            if addressType == 0x03:
                if len(data) < 1:
                    return True
                
                addressLength, = struct.unpack("!B", data[:1])
                
                data = data[1:]
                
                if len(data) < addressLength:
                    return True
                
                address, = struct.unpack("!%ds" % addressLength, data[:addressLength])
                
                data = data[addressLength:]
            else:
                if addressType == 0x04:
                    if len(data) < 16:
                        return True
                    
                    address1, address2, address3, address4 = struct.unpack("!IIII", data[:16])
                    address = struct.pack("!IIII", address1, address2, address3, address4)
                    address = socket.inet_ntop(socket.AF_INET6, address)
                    
                    data = data[16:]
        
        if len(data) < 2:
            return True
        
        port, = struct.unpack("!H", data[:2])
        
        data = data[2:]
        
        self.factory.tunnelProtocol.tunnelOutputProtocol_connectionMade(data)
        
        self.data = ""
        
        return True

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