# Copyright (c) Jeroen Van Steirteghem
# See LICENSE

from twisted.conch.ssh import channel, connection, forwarding, keys, transport, userauth
from twisted.internet import defer, interfaces, protocol
from zope.interface import implements
import twunnel.logger
import twunnel.proxy_server

class SSHChannel(channel.SSHChannel):
    implements(interfaces.IPushProducer)
    name = "direct-tcpip"
    
    def __init__(self, *args, **kwargs):
        twunnel.logger.log(3, "trace: SSHChannel.__init__")
        
        channel.SSHChannel.__init__(self, *args, **kwargs)
        
        self.inputProtocol = None
        self.connectionState = 0
        
    def channelOpen(self, specificData):
        twunnel.logger.log(3, "trace: SSHChannel.channelOpen")
        
        self.connectionState = 1
        
        self.inputProtocol.outputProtocol_connectionMade()

    def openFailed(self, reason):
        twunnel.logger.log(3, "trace: SSHChannel.openFailed")
        
        self.connectionState = 2
        
        self.inputProtocol.outputProtocol_connectionFailed(reason)

    def dataReceived(self, data):
        twunnel.logger.log(3, "trace: SSHChannel.dataReceived")
        
        self.inputProtocol.outputProtocol_dataReceived(data)
    
    def eofReceived(self):
        twunnel.logger.log(3, "trace: SSHChannel.eofReceived")
        
        self.loseConnection()
    
    def closeReceived(self):
        twunnel.logger.log(3, "trace: SSHChannel.closeReceived")
        
        self.loseConnection()
            
    def closed(self):
        twunnel.logger.log(3, "trace: SSHChannel.closed")
        
        self.connectionState = 2
        
        self.inputProtocol.outputProtocol_connectionLost(None)
        
    def inputProtocol_connectionMade(self):
        twunnel.logger.log(3, "trace: SSHChannel.inputProtocol_connectionMade")
        
    def inputProtocol_connectionLost(self, reason):
        twunnel.logger.log(3, "trace: SSHChannel.inputProtocol_connectionLost")
        
        if self.connectionState == 1:
            self.loseConnection()
        
    def inputProtocol_dataReceived(self, data):
        twunnel.logger.log(3, "trace: SSHChannel.inputProtocol_dataReceived")
        
        if self.connectionState == 1:
            self.write(data)
    
    def pauseProducing(self):
        twunnel.logger.log(3, "trace: SSHChannel.pauseProducing")
        
        if self.connectionState == 1:
            self.localWindowSize = 0
    
    def resumeProducing(self):
        twunnel.logger.log(3, "trace: SSHChannel.resumeProducing")
        
        if self.connectionState == 1:
            self.localWindowSize = 131072
    
    def stopProducing(self):
        twunnel.logger.log(3, "trace: SSHChannel.stopProducing")
        
        if self.connectionState == 1:
            self.localWindowSize = 0
    
    def startWriting(self):
        twunnel.logger.log(3, "trace: SSHChannel.startWriting")
        
        self.inputProtocol.resumeProducing()
    
    def stopWriting(self):
        twunnel.logger.log(3, "trace: SSHChannel.stopWriting")
        
        self.inputProtocol.pauseProducing()

class SSHClientTransport(transport.SSHClientTransport):
    def __init__(self):
        twunnel.logger.log(3, "trace: SSHClientTransport.__init__")
        
        self.configuration = None
        
    def verifyHostKey(self, hostKey, fingerprint):
        twunnel.logger.log(3, "trace: SSHClientTransport.verifyHostKey")
        twunnel.logger.log(2, "fingerprint1: " + fingerprint)
        twunnel.logger.log(2, "fingerprint2: " + self.configuration["REMOTE_PROXY_SERVER"]["KEY"]["FINGERPRINT"])
        
        if self.configuration["REMOTE_PROXY_SERVER"]["KEY"]["FINGERPRINT"] != "":
            if self.configuration["REMOTE_PROXY_SERVER"]["KEY"]["FINGERPRINT"] != fingerprint:
                twunnel.logger.log(1, "ERROR_KEY_FINGERPRINT")
                
                return defer.fail(0)
        
        return defer.succeed(1)

    def connectionSecure(self):
        twunnel.logger.log(3, "trace: SSHClientTransport.connectionSecure")
        
        self.requestService(SSHUserAuthClient(self.configuration))

class SSHClientTransportFactory(protocol.ReconnectingClientFactory):
    protocol = SSHClientTransport
    
    def __init__(self, configuration, output):
        twunnel.logger.log(3, "trace: SSHClientTransportFactory.__init__")
        
        self.configuration = configuration
        self.output = output
        
    def buildProtocol(self, address):
        twunnel.logger.log(3, "trace: SSHClientTransportFactory.buildProtocol")
        
        p = protocol.ClientFactory.buildProtocol(self, address)
        p.configuration = self.configuration
        return p
        
    def startFactory(self):
        twunnel.logger.log(3, "trace: SSHClientTransportFactory.startFactory")
        
    def stopFactory(self):
        twunnel.logger.log(3, "trace: SSHClientTransportFactory.stopFactory")
        
    def startedConnecting(self, connector):
        twunnel.logger.log(3, "trace: SSHClientTransportFactory.startedConnecting")
        
        self.output.connectors.append(connector)
        
        protocol.ReconnectingClientFactory.startedConnecting(self, connector)
        
    def clientConnectionFailed(self, connector, reason):
        twunnel.logger.log(3, "trace: SSHClientTransportFactory.clientConnectionFailed")
        
        self.output.connectors.remove(connector)
        
        protocol.ReconnectingClientFactory.clientConnectionFailed(self, connector, reason)
        
    def clientConnectionLost(self, connector, reason):
        twunnel.logger.log(3, "trace: SSHClientTransportFactory.clientConnectionLost")
        
        self.output.connectors.remove(connector)
        
        protocol.ReconnectingClientFactory.clientConnectionLost(self, connector, reason)
        
class SSHUserAuthClient(userauth.SSHUserAuthClient):
    def __init__(self, configuration):
        twunnel.logger.log(3, "trace: SSHUserAuthClient.__init__")
        
        self.configuration = configuration
        self.i = -1
        
        userauth.SSHUserAuthClient.__init__(self, str(self.configuration["REMOTE_PROXY_SERVER"]["ACCOUNT"]["NAME"]), SSHConnection())
        
    def getPassword(self):
        twunnel.logger.log(3, "trace: SSHUserAuthClient.getPassword")
        
        return defer.succeed(str(self.configuration["REMOTE_PROXY_SERVER"]["ACCOUNT"]["PASSWORD"]))
        
    def getPublicKey(self):
        twunnel.logger.log(3, "trace: SSHUserAuthClient.getPublicKey")
        
        if self.configuration["REMOTE_PROXY_SERVER"]["ACCOUNT"]["PASSWORD"] != "":
            return None
        
        self.i = self.i + 1
        if self.i == len(self.configuration["REMOTE_PROXY_SERVER"]["ACCOUNT"]["KEYS"]):
            return None
        
        return keys.Key.fromFile(self.configuration["REMOTE_PROXY_SERVER"]["ACCOUNT"]["KEYS"][self.i]["PUBLIC"]["FILE"], passphrase=str(self.configuration["REMOTE_PROXY_SERVER"]["ACCOUNT"]["KEYS"][self.i]["PUBLIC"]["PASSPHRASE"])).blob()

    def getPrivateKey(self):
        twunnel.logger.log(3, "trace: SSHUserAuthClient.getPrivateKey")
        
        return defer.succeed(keys.Key.fromFile(self.configuration["REMOTE_PROXY_SERVER"]["ACCOUNT"]["KEYS"][self.i]["PRIVATE"]["FILE"], passphrase=str(self.configuration["REMOTE_PROXY_SERVER"]["ACCOUNT"]["KEYS"][self.i]["PRIVATE"]["PASSPHRASE"])).keyObject)

class SSHConnection(connection.SSHConnection):
    def serviceStarted(self):
        twunnel.logger.log(3, "trace: SSHConnection.serviceStarted")
        
        connection.SSHConnection.serviceStarted(self)
        
        self.transport.factory.output.connections.append(self)
        
        twunnel.logger.log(2, "connections=" + str(len(self.transport.factory.output.connections)))
        
    def serviceStopped(self):
        twunnel.logger.log(3, "trace: SSHConnection.serviceStopped")
        
        connection.SSHConnection.serviceStopped(self)
        
        self.transport.factory.output.connections.remove(self)
        
        twunnel.logger.log(2, "connections=" + str(len(self.transport.factory.output.connections)))

class SSHOutputProtocolConnection(object):
    def __init__(self, configuration):
        twunnel.logger.log(3, "trace: SSHOutputProtocolConnection.__init__")
        
        self.configuration = configuration
        self.i = -1
        
        self.connections = []
        self.connectors = []
        self.factory = None
    
    def connect(self, remoteAddress, remotePort, inputProtocol):
        twunnel.logger.log(3, "trace: SSHOutputProtocolConnection.connect")
        
        if len(self.connections) == 0:
            return
        
        self.i = self.i + 1
        if self.i >= len(self.connections):
            self.i = 0
        
        connection = self.connections[self.i]
        
        inputProtocol.outputProtocol = SSHChannel(conn = connection)
        inputProtocol.outputProtocol.inputProtocol = inputProtocol
        data = forwarding.packOpen_direct_tcpip((remoteAddress, remotePort), (self.configuration["LOCAL_PROXY_SERVER"]["ADDRESS"], self.configuration["LOCAL_PROXY_SERVER"]["PORT"]))
        connection.openChannel(inputProtocol.outputProtocol, data)
    
    def startConnection(self):
        twunnel.logger.log(3, "trace: SSHOutputProtocolConnection.startConnection")
        
        self.factory = SSHClientTransportFactory(self.configuration, self)
        
        i = 0
        while i < self.configuration["REMOTE_PROXY_SERVER"]["ACCOUNT"]["CONNECTIONS"]:
            tunnel = twunnel.proxy_server.createTunnel(self.configuration)
            tunnel.connect(self.configuration["REMOTE_PROXY_SERVER"]["ADDRESS"], self.configuration["REMOTE_PROXY_SERVER"]["PORT"], self.factory)
            
            i = i + 1
    
    def stopConnection(self):
        twunnel.logger.log(3, "trace: SSHOutputProtocolConnection.stopConnection")
        
        self.factory.stopTrying()
        
        i = 0
        while i < len(self.connectors):
            connector = self.connectors[i]
            connector.disconnect()
            
            i = i + 1