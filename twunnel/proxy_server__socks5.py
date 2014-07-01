# Copyright (c) Jeroen Van Steirteghem
# See LICENSE

from twisted.internet import protocol
from twisted.internet.abstract import isIPAddress, isIPv6Address
import socket
import struct
import twunnel.logger

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