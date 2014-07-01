# Copyright (c) Jeroen Van Steirteghem
# See LICENSE

from twisted.internet import protocol
from twisted.internet.abstract import isIPv6Address
import base64
import twunnel.logger

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