# Copyright (c) Jeroen Van Steirteghem
# See LICENSE

from twisted.internet import protocol
from twisted.internet.abstract import isIPAddress, isIPv6Address
import socket
import struct
import twunnel.logger

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