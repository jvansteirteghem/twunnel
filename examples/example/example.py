from twisted.internet import protocol, reactor
import logging

logger = logging.getLogger(__name__)

class Protocol(protocol.Protocol):
    def __init__(self):
        logger.debug("Protocol.__init__")
        
        self.request = ""
        self.response = ""
        
    def connectionMade(self):
        logger.debug("Protocol.connectionMade")
        
        self.request = "HEAD / HTTP/1.1\r\n"
        
        if self.factory.port == 80 or self.factory.port == 443:
            self.request = self.request + "Host: " + self.factory.address + "\r\n"
        else:
            self.request = self.request + "Host: " + self.factory.address + ":" + str(self.factory.port) + "\r\n"
        
        self.request = self.request + "\r\n"
        
        logger.info("request: " + self.request)
        
        self.transport.write(self.request)
    
    def connectionLost(self, reason):
        logger.debug("Protocol.connectionLost")
        
    def dataReceived(self, data):
        logger.debug("Protocol.dataReceived")
        
        self.response = self.response + data
        
        i = self.response.find("\r\n\r\n")
        
        if i == -1:
            return
        
        logger.info("response: " + self.response)
        
        self.transport.loseConnection()
        
class ProtocolFactory(protocol.ClientFactory):
    protocol = Protocol
    
    def __init__(self):
        logger.debug("ProtocolFactory.__init__")
        
        self.address = ""
        self.port = 0
    
    def startedConnecting(self, connector):
        logger.debug("ProtocolFactory.startedConnecting")
    
    def clientConnectionFailed(self, connector, reason):
        logger.debug("ProtocolFactory.clientConnectionFailed")
    
    def clientConnectionLost(self, connector, reason):
        logger.debug("ProtocolFactory.clientConnectionLost")