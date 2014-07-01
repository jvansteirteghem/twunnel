# Copyright (c) Jeroen Van Steirteghem
# See LICENSE

from twisted.internet import interfaces, protocol, reactor, tcp
from zope.interface import implements
import twunnel.logger

class HTTPSInputProtocol(protocol.Protocol):
    implements(interfaces.IPushProducer)
    
    def __init__(self):
        twunnel.logger.log(3, "trace: HTTPSInputProtocol.__init__")
        
        self.configuration = None
        self.outputProtocolConnectionManager = None
        self.outputProtocol = None
        self.remoteAddress = ""
        self.remotePort = 0
        self.connectionState = 0
        self.data = ""
        self.dataState = 0
    
    def connectionMade(self):
        twunnel.logger.log(3, "trace: HTTPSInputProtocol.connectionMade")
        
        self.connectionState = 1
    
    def connectionLost(self, reason):
        twunnel.logger.log(3, "trace: HTTPSInputProtocol.connectionLost")
        
        self.connectionState = 2
        
        if self.outputProtocol is not None:
            self.outputProtocol.inputProtocol_connectionLost(reason)
    
    def dataReceived(self, data):
        twunnel.logger.log(3, "trace: HTTPSInputProtocol.dataReceived")
        
        self.data = self.data + data
        if self.dataState == 0:
            if self.processDataState0():
                return
        if self.dataState == 1:
            if self.processDataState1():
                return
    
    def processDataState0(self):
        twunnel.logger.log(3, "trace: HTTPSInputProtocol.processDataState0")
        
        data = self.data
        
        i = data.find("\r\n\r\n")
        
        if i == -1:
            return True
        
        i = i + 4
        
        request = data[:i]
        
        data = data[i:]
        
        self.data = data
        
        requestLines = request.split("\r\n")
        requestLine = requestLines[0].split(" ", 2)
        
        if len(requestLine) != 3:
            response = "HTTP/1.1 400 Bad Request\r\n"
            response = response + "\r\n"
            
            self.transport.write(response)
            self.transport.loseConnection()
            
            return True
        
        requestMethod = requestLine[0].upper()
        requestURI = requestLine[1]
        requestVersion = requestLine[2].upper()
        
        if requestMethod == "CONNECT":
            address = ""
            port = 0
            
            i1 = requestURI.find("[")
            i2 = requestURI.find("]")
            i3 = requestURI.rfind(":")
            
            if i3 > i2:
                address = requestURI[:i3]
                port = int(requestURI[i3 + 1:])
            else:
                address = requestURI
                port = 443
            
            if i2 > i1:
                address = address[i1 + 1:i2]
            
            self.remoteAddress = address
            self.remotePort = port
            
            twunnel.logger.log(2, "remoteAddress: " + self.remoteAddress)
            twunnel.logger.log(2, "remotePort: " + str(self.remotePort))
            
            self.outputProtocolConnectionManager.connect(self.remoteAddress, self.remotePort, self)
            
            return True
        else:
            response = "HTTP/1.1 405 Method Not Allowed\r\n"
            response = response + "Allow: CONNECT\r\n"
            response = response + "\r\n"
            
            self.transport.write(response)
            self.transport.loseConnection()
            
            return True
        
    def processDataState1(self):
        twunnel.logger.log(3, "trace: HTTPSInputProtocol.processDataState1")
        
        self.outputProtocol.inputProtocol_dataReceived(self.data)
        
        self.data = ""
        
        return True
        
    def outputProtocol_connectionMade(self):
        twunnel.logger.log(3, "trace: HTTPSInputProtocol.outputProtocol_connectionMade")
        
        if self.connectionState == 1:
            self.transport.registerProducer(self.outputProtocol, True)
            
            response = "HTTP/1.1 200 OK\r\n"
            response = response + "\r\n"
            
            self.transport.write(response)
            
            self.outputProtocol.inputProtocol_connectionMade()
            if len(self.data) > 0:
                self.outputProtocol.inputProtocol_dataReceived(self.data)
            
            self.data = ""
            self.dataState = 1
        else:
            if self.connectionState == 2:
                self.outputProtocol.inputProtocol_connectionLost(None)
        
    def outputProtocol_connectionFailed(self, reason):
        twunnel.logger.log(3, "trace: HTTPSInputProtocol.outputProtocol_connectionFailed")
        
        if self.connectionState == 1:
            response = "HTTP/1.1 404 Not Found\r\n"
            response = response + "\r\n"
            
            self.transport.write(response)
            self.transport.loseConnection()
        
    def outputProtocol_connectionLost(self, reason):
        twunnel.logger.log(3, "trace: HTTPSInputProtocol.outputProtocol_connectionLost")
        
        if self.connectionState == 1:
            self.transport.unregisterProducer()
            self.transport.loseConnection()
        else:
            if self.connectionState == 2:
                self.outputProtocol.inputProtocol_connectionLost(None)
        
    def outputProtocol_dataReceived(self, data):
        twunnel.logger.log(3, "trace: HTTPSInputProtocol.outputProtocol_dataReceived")
        
        if self.connectionState == 1:
            self.transport.write(data)
        else:
            if self.connectionState == 2:
                self.outputProtocol.inputProtocol_connectionLost(None)
    
    def pauseProducing(self):
        twunnel.logger.log(3, "trace: HTTPSInputProtocol.pauseProducing")
        
        if self.connectionState == 1:
            self.transport.pauseProducing()
    
    def resumeProducing(self):
        twunnel.logger.log(3, "trace: HTTPSInputProtocol.resumeProducing")
        
        if self.connectionState == 1:
            self.transport.resumeProducing()
    
    def stopProducing(self):
        twunnel.logger.log(3, "trace: HTTPSInputProtocol.stopProducing")
        
        if self.connectionState == 1:
            self.transport.stopProducing()

class HTTPSInputProtocolFactory(protocol.ClientFactory):
    protocol = HTTPSInputProtocol
    
    def __init__(self, configuration, outputProtocolConnectionManager):
        twunnel.logger.log(3, "trace: HTTPSInputProtocolFactory.__init__")
        
        self.configuration = configuration
        self.outputProtocolConnectionManager = outputProtocolConnectionManager
    
    def buildProtocol(self, *args, **kwargs):
        twunnel.logger.log(3, "trace: HTTPSInputProtocolFactory.buildProtocol")
        
        inputProtocol = protocol.ClientFactory.buildProtocol(self, *args, **kwargs)
        inputProtocol.configuration = self.configuration
        inputProtocol.outputProtocolConnectionManager = self.outputProtocolConnectionManager
        return inputProtocol
    
    def startFactory(self):
        twunnel.logger.log(3, "trace: HTTPSInputProtocolFactory.startFactory")
        
        self.outputProtocolConnectionManager.startConnectionManager()
    
    def stopFactory(self):
        twunnel.logger.log(3, "trace: HTTPSInputProtocolFactory.stopFactory")
        
        self.outputProtocolConnectionManager.stopConnectionManager()

def createHTTPSPort(configuration, outputProtocolConnectionManager):
    factory = HTTPSInputProtocolFactory(configuration, outputProtocolConnectionManager)
    
    return tcp.Port(configuration["LOCAL_PROXY_SERVER"]["PORT"], factory, 50, configuration["LOCAL_PROXY_SERVER"]["ADDRESS"], reactor)