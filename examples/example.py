from twisted.internet import protocol, reactor
import twunnel.logger

class Protocol(protocol.Protocol):
    def __init__(self):
        twunnel.logger.log(3, "trace: Protocol.__init__")
        
        self.request = ""
        self.response = ""
        
    def connectionMade(self):
        twunnel.logger.log(3, "trace: Protocol.connectionMade")
        
        self.request = "HEAD / HTTP/1.1\r\n"
        
        if self.factory.port == 80 or self.factory.port == 443:
            self.request = self.request + "Host: " + self.factory.address + "\r\n"
        else:
            self.request = self.request + "Host: " + self.factory.address + ":" + str(self.factory.port) + "\r\n"
        
        self.request = self.request + "\r\n"
        
        twunnel.logger.log(2, "request: " + self.request)
        
        self.transport.write(self.request)
    
    def connectionLost(self, reason):
        twunnel.logger.log(3, "trace: Protocol.connectionLost")
        
    def dataReceived(self, data):
        twunnel.logger.log(3, "trace: Protocol.dataReceived")
        
        self.response = self.response + data
        
        i = self.response.find("\r\n\r\n")
        
        if i == -1:
            return
        
        twunnel.logger.log(2, "response: " + self.response)
        
        self.transport.loseConnection()
        
class ProtocolFactory(protocol.ClientFactory):
    protocol = Protocol
    
    def __init__(self):
        twunnel.logger.log(3, "trace: ProtocolFactory.__init__")
        
        self.address = ""
        self.port = 0
    
    def startedConnecting(self, connector):
        twunnel.logger.log(3, "trace: ProtocolFactory.startedConnecting")
    
    def clientConnectionFailed(self, connector, reason):
        twunnel.logger.log(3, "trace: ProtocolFactory.clientConnectionFailed")
    
    def clientConnectionLost(self, connector, reason):
        twunnel.logger.log(3, "trace: ProtocolFactory.clientConnectionLost")