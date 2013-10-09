# Copyright (c) Jeroen Van Steirteghem
# See LICENSE

from zope.interface import implements
from twisted.internet import defer, interfaces, protocol, reactor, tcp
from twisted.conch.ssh import channel, connection, forwarding, keys, transport, userauth
import logging
import twunnel.local

logger = logging.getLogger(__name__)

class SSHChannel(channel.SSHChannel):
    implements(interfaces.IPushProducer)
    name = "direct-tcpip"
    
    def __init__(self, *args, **kw):
        logger.debug("SSHChannel.__init__")
        
        channel.SSHChannel.__init__(self, *args, **kw)
        
        self.inputProtocol = None
        self.connectionState = 0
        
    def channelOpen(self, specificData):
        logger.debug("SSHChannel.channelOpen")
        
        self.connectionState = 1
        
        self.inputProtocol.outputProtocol_connectionMade()

    def openFailed(self, reason):
        logger.debug("SSHChannel.openFailed")
        
        self.connectionState = 2
        
        self.inputProtocol.outputProtocol_connectionFailed(reason)

    def dataReceived(self, data):
        logger.debug("SSHChannel.dataReceived")
        
        self.inputProtocol.outputProtocol_dataReceived(data)
    
    def eofReceived(self):
        logger.debug("SSHChannel.eofReceived")
        
        self.loseConnection()
    
    def closeReceived(self):
        logger.debug("SSHChannel.closeReceived")
        
        self.loseConnection()
            
    def closed(self):
        logger.debug("SSHChannel.closed")
        
        self.connectionState = 2
        
        self.inputProtocol.outputProtocol_connectionLost(None)
        
    def inputProtocol_connectionMade(self):
        logger.debug("SSHChannel.inputProtocol_connectionMade")
        
    def inputProtocol_connectionLost(self, reason):
        logger.debug("SSHChannel.inputProtocol_connectionLost")
        
        if self.connectionState == 1:
            self.loseConnection()
        
    def inputProtocol_dataReceived(self, data):
        logger.debug("SSHChannel.inputProtocol_dataReceived")
        
        if self.connectionState == 1:
            self.write(data)
    
    def pauseProducing(self):
        logger.debug("SSHChannel.pauseProducing")
        
        if self.connectionState == 1:
            self.localWindowSize = 0
    
    def resumeProducing(self):
        logger.debug("SSHChannel.resumeProducing")
        
        if self.connectionState == 1:
            self.localWindowSize = 131072
    
    def stopProducing(self):
        logger.debug("SSHChannel.stopProducing")
        
        if self.connectionState == 1:
            self.localWindowSize = 0
    
    def startWriting(self):
        logger.debug("SSHChannel.startWriting")
        
        self.inputProtocol.resumeProducing()
    
    def stopWriting(self):
        logger.debug("SSHChannel.stopWriting")
        
        self.inputProtocol.pauseProducing()

class SSHClientTransport(transport.SSHClientTransport):
    def __init__(self):
        logger.debug("SSHClientTransport.__init__")
        
        self.configuration = None
        self.i = 0
        
    def verifyHostKey(self, hostKey, fingerprint):
        logger.debug("SSHClientTransport.verifyHostKey")
        logger.debug("SSHClientTransport.verifyHostKey: fingerprint1=" + fingerprint)
        logger.debug("SSHClientTransport.verifyHostKey: fingerprint2=" + self.configuration["REMOTE_PROXY_SERVERS"][self.i]["KEY"]["FINGERPRINT"])
        
        if self.configuration["REMOTE_PROXY_SERVERS"][self.i]["KEY"]["FINGERPRINT"] != "":
            if self.configuration["REMOTE_PROXY_SERVERS"][self.i]["KEY"]["FINGERPRINT"] != fingerprint:
                logger.debug("SSHClientTransport.verifyHostKey: fingerprint1!=fingerprint2")
                
                return defer.fail(0)
        
        return defer.succeed(1)

    def connectionSecure(self):
        logger.debug("SSHClientTransport.connectionSecure")
        
        self.requestService(SSHUserAuthClient(self.configuration, self.i))

class SSHClientTransportFactory(protocol.ReconnectingClientFactory):
    protocol = SSHClientTransport
    
    def __init__(self, configuration, i, output):
        logger.debug("SSHClientTransportFactory.__init__")
        
        self.configuration = configuration
        self.i = i
        self.output = output
        
    def buildProtocol(self, address):
        logger.debug("SSHClientTransportFactory.buildProtocol")
        
        p = protocol.ClientFactory.buildProtocol(self, address)
        p.configuration = self.configuration
        p.i = self.i
        return p
        
    def startFactory(self):
        logger.debug("SSHClientTransportFactory.startFactory")
        
    def stopFactory(self):
        logger.debug("SSHClientTransportFactory.stopFactory")
        
    def startedConnecting(self, connector):
        logger.debug("SSHClientTransportFactory.startedConnecting")
        
        self.output.connectors.append(connector)
        
        protocol.ReconnectingClientFactory.startedConnecting(self, connector)
        
    def clientConnectionFailed(self, connector, reason):
        logger.debug("SSHClientTransportFactory.clientConnectionFailed")
        
        self.output.connectors.remove(connector)
        
        protocol.ReconnectingClientFactory.clientConnectionFailed(self, connector, reason)
        
    def clientConnectionLost(self, connector, reason):
        logger.debug("SSHClientTransportFactory.clientConnectionLost")
        
        self.output.connectors.remove(connector)
        
        protocol.ReconnectingClientFactory.clientConnectionLost(self, connector, reason)
        
class SSHUserAuthClient(userauth.SSHUserAuthClient):
    def __init__(self, configuration, i):
        logger.debug("SSHUserAuthClient.__init__")
        
        self.configuration = configuration
        self.i = i
        self.j = -1
        
        userauth.SSHUserAuthClient.__init__(self, str(self.configuration["REMOTE_PROXY_SERVERS"][self.i]["ACCOUNT"]["NAME"]), SSHConnection())
        
    def getPassword(self):
        logger.debug("SSHUserAuthClient.getPassword")
        
        return defer.succeed(str(self.configuration["REMOTE_PROXY_SERVERS"][self.i]["ACCOUNT"]["PASSWORD"]))
        
    def getPublicKey(self):
        logger.debug("SSHUserAuthClient.getPublicKey")
        
        if self.configuration["REMOTE_PROXY_SERVERS"][self.i]["ACCOUNT"]["PASSWORD"] != "":
            return None
        
        self.j = self.j + 1
        if self.j == len(self.configuration["REMOTE_PROXY_SERVERS"][self.i]["ACCOUNT"]["KEYS"]):
            return None
        
        return keys.Key.fromFile(self.configuration["REMOTE_PROXY_SERVERS"][self.i]["ACCOUNT"]["KEYS"][self.j]["PUBLIC"]["FILE"], passphrase=str(self.configuration["REMOTE_PROXY_SERVERS"][self.i]["ACCOUNT"]["KEYS"][self.j]["PUBLIC"]["PASSPHRASE"])).blob()

    def getPrivateKey(self):
        logger.debug("SSHUserAuthClient.getPrivateKey")
        
        return defer.succeed(keys.Key.fromFile(self.configuration["REMOTE_PROXY_SERVERS"][self.i]["ACCOUNT"]["KEYS"][self.j]["PRIVATE"]["FILE"], passphrase=str(self.configuration["REMOTE_PROXY_SERVERS"][self.i]["ACCOUNT"]["KEYS"][self.j]["PRIVATE"]["PASSPHRASE"])).keyObject)

class SSHConnection(connection.SSHConnection):
    def serviceStarted(self):
        logger.debug("SSHConnection.serviceStarted")
        
        connection.SSHConnection.serviceStarted(self)
        
        self.transport.factory.output.connections.append(self)
        
        logger.debug("SSHConnection.serviceStarted: connections=" + str(len(self.transport.factory.output.connections)))
        
    def serviceStopped(self):
        logger.debug("SSHConnection.serviceStopped")
        
        connection.SSHConnection.serviceStopped(self)
        
        self.transport.factory.output.connections.remove(self)
        
        logger.debug("SSHConnection.serviceStopped: connections=" + str(len(self.transport.factory.output.connections)))

class SSHOutput(object):
    def __init__(self, configuration, i):
        logger.debug("SSHOutput.__init__")
        
        self.configuration = configuration
        self.i = i
        self.j = 0
        
        self.connections = []
        self.connectors = []
        self.factory = None
    
    def connect(self, remoteAddress, remotePort, inputProtocol):
        logger.debug("SSHOutput.connect")
        
        connection = self.connections[self.j]
        
        self.j = self.j + 1
        if self.j == len(self.connections):
            self.j = 0
        
        inputProtocol.outputProtocol = SSHChannel(conn = connection)
        inputProtocol.outputProtocol.inputProtocol = inputProtocol
        data = forwarding.packOpen_direct_tcpip((remoteAddress, remotePort), (self.configuration["LOCAL_PROXY_SERVER"]["ADDRESS"], self.configuration["LOCAL_PROXY_SERVER"]["PORT"]))
        connection.openChannel(inputProtocol.outputProtocol, data)
    
    def startOutput(self):
        logger.debug("SSHOutput.startOutput")
        
        self.factory = SSHClientTransportFactory(self.configuration, self.i, self)
        
        i = 0
        while i < self.configuration["REMOTE_PROXY_SERVERS"][self.i]["ACCOUNT"]["CONNECTIONS"]:
            tunnel = twunnel.local.Tunnel(self.configuration)
            tunnel.connect(self.configuration["REMOTE_PROXY_SERVERS"][self.i]["ADDRESS"], self.configuration["REMOTE_PROXY_SERVERS"][self.i]["PORT"], self.factory)
            
            i = i + 1
    
    def stopOutput(self):
        logger.debug("SSHOutput.stopOutput")
        
        self.factory.stopTrying()
        
        i = 0
        while i < len(self.connectors):
            connector = self.connectors[i]
            connector.disconnect()
            
            i = i + 1