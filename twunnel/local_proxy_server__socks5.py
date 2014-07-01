# Copyright (c) Jeroen Van Steirteghem
# See LICENSE

from twisted.internet import interfaces, protocol, reactor, tcp
from zope.interface import implements
import socket
import struct
import twunnel.logger

class SOCKS5InputProtocol(protocol.Protocol):
    implements(interfaces.IPushProducer)
    
    def __init__(self):
        twunnel.logger.log(3, "trace: SOCKS5InputProtocol.__init__")
        
        self.configuration = None
        self.outputProtocolConnectionManager = None
        self.outputProtocol = None
        self.remoteAddress = ""
        self.remotePort = 0
        self.connectionState = 0
        self.data = ""
        self.dataState = 0
    
    def connectionMade(self):
        twunnel.logger.log(3, "trace: SOCKS5InputProtocol.connectionMade")
        
        self.connectionState = 1
    
    def connectionLost(self, reason):
        twunnel.logger.log(3, "trace: SOCKS5InputProtocol.connectionLost")
        
        self.connectionState = 2
        
        if self.outputProtocol is not None:
            self.outputProtocol.inputProtocol_connectionLost(reason)
    
    def dataReceived(self, data):
        twunnel.logger.log(3, "trace: SOCKS5InputProtocol.dataReceived")
        
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
        twunnel.logger.log(3, "trace: SOCKS5InputProtocol.processDataState0")
        
        data = self.data
        
        if len(data) < 2:
            return True
        
        version, numberOfMethods = struct.unpack("!BB", data[:2])
        
        data = data[2:]
        
        if len(data) < numberOfMethods:
            return True
        
        methods = struct.unpack("!%dB" % numberOfMethods, data[:numberOfMethods])
        
        data = data[numberOfMethods:]
        
        self.data = data
        
        supportedMethods = []
        if len(self.configuration["LOCAL_PROXY_SERVER"]["ACCOUNTS"]) == 0:
            supportedMethods.append(0x00)
        else:
            supportedMethods.append(0x02)
        
        for supportedMethod in supportedMethods:
            if supportedMethod in methods:
                if supportedMethod == 0x00:
                    response = struct.pack("!BB", 0x05, 0x00)
                    
                    self.transport.write(response)
                    
                    self.dataState = 2
                    
                    return False
                else:
                    if supportedMethod == 0x02:
                        response = struct.pack("!BB", 0x05, 0x02)
                        
                        self.transport.write(response)
                        
                        self.dataState = 1
                        
                        return True
        
        response = struct.pack("!BB", 0x05, 0xFF)
        
        self.transport.write(response)
        self.transport.loseConnection()
        
        return True
        
    def processDataState1(self):
        twunnel.logger.log(3, "trace: SOCKS5InputProtocol.processDataState1")
        
        data = self.data
        
        if len(data) < 2:
            return True
        
        version, nameLength = struct.unpack("!BB", data[:2])
        
        data = data[2:]
        
        if len(data) < nameLength:
            return True
        
        name, = struct.unpack("!%ds" % nameLength, data[:nameLength])
        
        data = data[nameLength:]
        
        if len(data) < 1:
            return True
        
        passwordLength, = struct.unpack("!B", data[:1])
        
        data = data[1:]
        
        if len(data) < passwordLength:
            return True
        
        password, = struct.unpack("!%ds" % passwordLength, data[:passwordLength])
        
        data = data[passwordLength:]
        
        self.data = data
        
        i = 0
        while i < len(self.configuration["LOCAL_PROXY_SERVER"]["ACCOUNTS"]):
            if self.configuration["LOCAL_PROXY_SERVER"]["ACCOUNTS"][i]["NAME"] == name:
                if self.configuration["LOCAL_PROXY_SERVER"]["ACCOUNTS"][i]["PASSWORD"] == password:
                    response = struct.pack("!BB", 0x05, 0x00)
                    
                    self.transport.write(response)
                    
                    self.dataState = 2
                    
                    return True
                
                response = struct.pack("!BB", 0x05, 0x01)
                
                self.transport.write(response)
                self.transport.loseConnection()
                
                return True
            
            i = i + 1
        
        response = struct.pack("!BB", 0x05, 0x01)
        
        self.transport.write(response)
        self.transport.loseConnection()
        
        return True
        
    def processDataState2(self):
        twunnel.logger.log(3, "trace: SOCKS5InputProtocol.processDataState2")
        
        data = self.data
        
        if len(data) < 4:
            return True
        
        version, method, reserved, addressType = struct.unpack("!BBBB", data[:4])
        
        data = data[4:]
        
        if addressType == 0x01:
            if len(data) < 4:
                return True
            
            address, = struct.unpack("!I", data[:4])
            address = struct.pack("!I", address)
            address = socket.inet_ntop(socket.AF_INET, address)
            
            self.remoteAddress = address
            
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
                
                self.remoteAddress = address
                
                data = data[addressLength:]
            else:
                if addressType == 0x04:
                    if len(data) < 16:
                        return True
                    
                    address1, address2, address3, address4 = struct.unpack("!IIII", data[:16])
                    address = struct.pack("!IIII", address1, address2, address3, address4)
                    address = socket.inet_ntop(socket.AF_INET6, address)
                    
                    self.remoteAddress = address
                    
                    data = data[16:]
        
        if len(data) < 2:
            return True
        
        port, = struct.unpack("!H", data[:2])
        
        self.remotePort = port
        
        data = data[2:]
        
        self.data = data
        
        twunnel.logger.log(2, "remoteAddress: " + self.remoteAddress)
        twunnel.logger.log(2, "remotePort: " + str(self.remotePort))
        
        if method == 0x01:
            self.outputProtocolConnectionManager.connect(self.remoteAddress, self.remotePort, self)
            
            return True
        else:
            response = struct.pack("!BBBBIH", 0x05, 0x07, 0x00, 0x01, 0, 0)
            
            self.transport.write(response)
            self.transport.loseConnection()
            
            return True
        
    def processDataState3(self):
        twunnel.logger.log(3, "trace: SOCKS5InputProtocol.processDataState3")
        
        self.outputProtocol.inputProtocol_dataReceived(self.data)
        
        self.data = ""
        
        return True
        
    def outputProtocol_connectionMade(self):
        twunnel.logger.log(3, "trace: SOCKS5InputProtocol.outputProtocol_connectionMade")
        
        if self.connectionState == 1:
            self.transport.registerProducer(self.outputProtocol, True)
            
            response = struct.pack("!BBBBIH", 0x05, 0x00, 0x00, 0x01, 0, 0)
            
            self.transport.write(response)
            
            self.outputProtocol.inputProtocol_connectionMade()
            if len(self.data) > 0:
                self.outputProtocol.inputProtocol_dataReceived(self.data)
            
            self.data = ""
            self.dataState = 3
        else:
            if self.connectionState == 2:
                self.outputProtocol.inputProtocol_connectionLost(None)
        
    def outputProtocol_connectionFailed(self, reason):
        twunnel.logger.log(3, "trace: SOCKS5InputProtocol.outputProtocol_connectionFailed")
        
        if self.connectionState == 1:
            response = struct.pack("!BBBBIH", 0x05, 0x05, 0x00, 0x01, 0, 0)
            
            self.transport.write(response)
            self.transport.loseConnection()
        
    def outputProtocol_connectionLost(self, reason):
        twunnel.logger.log(3, "trace: SOCKS5InputProtocol.outputProtocol_connectionLost")
        
        if self.connectionState == 1:
            self.transport.unregisterProducer()
            self.transport.loseConnection()
        else:
            if self.connectionState == 2:
                self.outputProtocol.inputProtocol_connectionLost(None)
        
    def outputProtocol_dataReceived(self, data):
        twunnel.logger.log(3, "trace: SOCKS5InputProtocol.outputProtocol_dataReceived")
        
        if self.connectionState == 1:
            self.transport.write(data)
        else:
            if self.connectionState == 2:
                self.outputProtocol.inputProtocol_connectionLost(None)
    
    def pauseProducing(self):
        twunnel.logger.log(3, "trace: SOCKS5InputProtocol.pauseProducing")
        
        if self.connectionState == 1:
            self.transport.pauseProducing()
    
    def resumeProducing(self):
        twunnel.logger.log(3, "trace: SOCKS5InputProtocol.resumeProducing")
        
        if self.connectionState == 1:
            self.transport.resumeProducing()
    
    def stopProducing(self):
        twunnel.logger.log(3, "trace: SOCKS5InputProtocol.stopProducing")
        
        if self.connectionState == 1:
            self.transport.stopProducing()

class SOCKS5InputProtocolFactory(protocol.ClientFactory):
    protocol = SOCKS5InputProtocol
    
    def __init__(self, configuration, outputProtocolConnectionManager):
        twunnel.logger.log(3, "trace: SOCKS5InputProtocolFactory.__init__")
        
        self.configuration = configuration
        self.outputProtocolConnectionManager = outputProtocolConnectionManager
    
    def buildProtocol(self, *args, **kwargs):
        twunnel.logger.log(3, "trace: SOCKS5InputProtocolFactory.buildProtocol")
        
        inputProtocol = protocol.ClientFactory.buildProtocol(self, *args, **kwargs)
        inputProtocol.configuration = self.configuration
        inputProtocol.outputProtocolConnectionManager = self.outputProtocolConnectionManager
        return inputProtocol
    
    def startFactory(self):
        twunnel.logger.log(3, "trace: SOCKS5InputProtocolFactory.startFactory")
        
        self.outputProtocolConnectionManager.startConnectionManager()
    
    def stopFactory(self):
        twunnel.logger.log(3, "trace: SOCKS5InputProtocolFactory.stopFactory")
        
        self.outputProtocolConnectionManager.stopConnectionManager()

def createSOCKS5Port(configuration, outputProtocolConnectionManager):
    factory = SOCKS5InputProtocolFactory(configuration, outputProtocolConnectionManager)
    
    return tcp.Port(configuration["LOCAL_PROXY_SERVER"]["PORT"], factory, 50, configuration["LOCAL_PROXY_SERVER"]["ADDRESS"], reactor)