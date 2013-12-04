# Copyright (c) Jeroen Van Steirteghem
# See LICENSE

from twisted.conch.ssh import channel, connection, forwarding, keys, transport, userauth
from twisted.internet import base, defer, interfaces, protocol, reactor, ssl, tcp
from twisted.internet.abstract import isIPAddress, isIPv6Address
from zope.interface import implements
import autobahn.websocket
import base64
import json
import OpenSSL
import socket
import struct
import twunnel.logger
import twunnel.proxy_server

def setDefaultConfiguration(configuration, keys):
    twunnel.proxy_server.setDefaultConfiguration(configuration, keys)
    
    if "LOCAL_PROXY_SERVER" in keys:
        configuration.setdefault("LOCAL_PROXY_SERVER", {})
        configuration["LOCAL_PROXY_SERVER"].setdefault("TYPE", "")
        if configuration["LOCAL_PROXY_SERVER"]["TYPE"] == "SOCKS5":
            configuration["LOCAL_PROXY_SERVER"].setdefault("ADDRESS", "")
            configuration["LOCAL_PROXY_SERVER"].setdefault("PORT", 0)
    
    if "REMOTE_PROXY_SERVERS" in keys:
        configuration.setdefault("REMOTE_PROXY_SERVERS", [])
        i = 0
        while i < len(configuration["REMOTE_PROXY_SERVERS"]):
            configuration["REMOTE_PROXY_SERVERS"][i].setdefault("TYPE", "")
            if configuration["REMOTE_PROXY_SERVERS"][i]["TYPE"] == "SSH":
                configuration["REMOTE_PROXY_SERVERS"][i].setdefault("ADDRESS", "")
                configuration["REMOTE_PROXY_SERVERS"][i].setdefault("PORT", 0)
                configuration["REMOTE_PROXY_SERVERS"][i].setdefault("KEY", {})
                configuration["REMOTE_PROXY_SERVERS"][i]["KEY"].setdefault("FINGERPRINT", "")
                configuration["REMOTE_PROXY_SERVERS"][i].setdefault("ACCOUNT", {})
                configuration["REMOTE_PROXY_SERVERS"][i]["ACCOUNT"].setdefault("NAME", "")
                configuration["REMOTE_PROXY_SERVERS"][i]["ACCOUNT"].setdefault("PASSWORD", "")
                configuration["REMOTE_PROXY_SERVERS"][i]["ACCOUNT"].setdefault("KEYS", [])
                j = 0
                while j < len(configuration["REMOTE_PROXY_SERVERS"][i]["ACCOUNT"]["KEYS"]):
                    configuration["REMOTE_PROXY_SERVERS"][i]["ACCOUNT"]["KEYS"][j].setdefault("PUBLIC", {})
                    configuration["REMOTE_PROXY_SERVERS"][i]["ACCOUNT"]["KEYS"][j]["PUBLIC"].setdefault("FILE", "")
                    configuration["REMOTE_PROXY_SERVERS"][i]["ACCOUNT"]["KEYS"][j]["PUBLIC"].setdefault("PASSPHRASE", "")
                    configuration["REMOTE_PROXY_SERVERS"][i]["ACCOUNT"]["KEYS"][j].setdefault("PRIVATE", {})
                    configuration["REMOTE_PROXY_SERVERS"][i]["ACCOUNT"]["KEYS"][j]["PRIVATE"].setdefault("FILE", "")
                    configuration["REMOTE_PROXY_SERVERS"][i]["ACCOUNT"]["KEYS"][j]["PRIVATE"].setdefault("PASSPHRASE", "")
                    j = j + 1
                configuration["REMOTE_PROXY_SERVERS"][i]["ACCOUNT"].setdefault("CONNECTIONS", 0)
            else:
                if configuration["REMOTE_PROXY_SERVERS"][i]["TYPE"] == "WS":
                    configuration["REMOTE_PROXY_SERVERS"][i].setdefault("ADDRESS", "")
                    configuration["REMOTE_PROXY_SERVERS"][i].setdefault("PORT", 0)
                    configuration["REMOTE_PROXY_SERVERS"][i].setdefault("ACCOUNT", {})
                    configuration["REMOTE_PROXY_SERVERS"][i]["ACCOUNT"].setdefault("NAME", "")
                    configuration["REMOTE_PROXY_SERVERS"][i]["ACCOUNT"].setdefault("PASSWORD", "")
                else:
                    if configuration["REMOTE_PROXY_SERVERS"][i]["TYPE"] == "WSS":
                        configuration["REMOTE_PROXY_SERVERS"][i].setdefault("ADDRESS", "")
                        configuration["REMOTE_PROXY_SERVERS"][i].setdefault("PORT", 0)
                        configuration["REMOTE_PROXY_SERVERS"][i].setdefault("CERTIFICATE", {})
                        configuration["REMOTE_PROXY_SERVERS"][i]["CERTIFICATE"].setdefault("AUTHORITY", {})
                        configuration["REMOTE_PROXY_SERVERS"][i]["CERTIFICATE"]["AUTHORITY"].setdefault("FILE", "")
                        configuration["REMOTE_PROXY_SERVERS"][i].setdefault("ACCOUNT", {})
                        configuration["REMOTE_PROXY_SERVERS"][i]["ACCOUNT"].setdefault("NAME", "")
                        configuration["REMOTE_PROXY_SERVERS"][i]["ACCOUNT"].setdefault("PASSWORD", "")
            i = i + 1

class OutputProtocol(protocol.Protocol):
    implements(interfaces.IPushProducer)
    
    def __init__(self):
        twunnel.logger.log(3, "trace: OutputProtocol.__init__")
        
        self.inputProtocol = None
        self.connectionState = 0
        
    def connectionMade(self):
        twunnel.logger.log(3, "trace: OutputProtocol.connectionMade")
        
        self.connectionState = 1
        
        self.inputProtocol.outputProtocol_connectionMade()
        
    def connectionLost(self, reason):
        twunnel.logger.log(3, "trace: OutputProtocol.connectionLost")
        
        self.connectionState = 2
        
        self.inputProtocol.outputProtocol_connectionLost(reason)
        
    def dataReceived(self, data):
        twunnel.logger.log(3, "trace: OutputProtocol.dataReceived")
        
        self.inputProtocol.outputProtocol_dataReceived(data)
        
    def inputProtocol_connectionMade(self):
        twunnel.logger.log(3, "trace: OutputProtocol.inputProtocol_connectionMade")
        
        if self.connectionState == 1:
            self.transport.registerProducer(self.inputProtocol, True)
        
    def inputProtocol_connectionLost(self, reason):
        twunnel.logger.log(3, "trace: OutputProtocol.inputProtocol_connectionLost")
        
        if self.connectionState == 1:
            self.transport.unregisterProducer()
            self.transport.loseConnection()
        
    def inputProtocol_dataReceived(self, data):
        twunnel.logger.log(3, "trace: OutputProtocol.inputProtocol_dataReceived")
        
        if self.connectionState == 1:
            self.transport.write(data)
    
    def pauseProducing(self):
        twunnel.logger.log(3, "trace: OutputProtocol.pauseProducing")
        
        if self.connectionState == 1:
            self.transport.pauseProducing()
    
    def resumeProducing(self):
        twunnel.logger.log(3, "trace: OutputProtocol.resumeProducing")
        
        if self.connectionState == 1:
            self.transport.resumeProducing()
    
    def stopProducing(self):
        twunnel.logger.log(3, "trace: OutputProtocol.stopProducing")
        
        if self.connectionState == 1:
            self.transport.stopProducing()

class OutputProtocolFactory(protocol.ClientFactory):
    protocol = OutputProtocol
    
    def __init__(self, inputProtocol):
        twunnel.logger.log(3, "trace: OutputProtocolFactory.__init__")
        
        self.inputProtocol = inputProtocol
        
    def buildProtocol(self, *args, **kw):
        outputProtocol = protocol.ClientFactory.buildProtocol(self, *args, **kw)
        outputProtocol.inputProtocol = self.inputProtocol
        outputProtocol.inputProtocol.outputProtocol = outputProtocol
        return outputProtocol
    
    def clientConnectionFailed(self, connector, reason):
        twunnel.logger.log(3, "trace: OutputProtocolFactory.clientConnectionFailed")
        
        self.inputProtocol.outputProtocol_connectionFailed(reason)

class OutputProtocolConnection(object):
    def __init__(self, configuration, i):
        twunnel.logger.log(3, "trace: OutputProtocolConnection.__init__")
        
        self.configuration = configuration
        self.i = i
    
    def connect(self, remoteAddress, remotePort, inputProtocol):
        twunnel.logger.log(3, "trace: OutputProtocolConnection.connect")
        
        outputProtocolFactory = OutputProtocolFactory(inputProtocol)
        
        tunnel = twunnel.proxy_server.createTunnel(self.configuration)
        tunnel.connect(remoteAddress, remotePort, outputProtocolFactory)
        
    def startConnection(self):
        twunnel.logger.log(3, "trace: OutputProtocolConnection.startConnection")
    
    def stopConnection(self):
        twunnel.logger.log(3, "trace: OutputProtocolConnection.stopConnection")

class OutputProtocolConnectionManager(object):
    def __init__(self, configuration):
        twunnel.logger.log(3, "trace: OutputProtocolConnectionManager.__init__")
        
        self.configuration = configuration
        self.i = -1
        
        self.outputProtocolConnections = []
        
        if len(self.configuration["REMOTE_PROXY_SERVERS"]) == 0:
            outputProtocolConnection = OutputProtocolConnection(self.configuration, 0)
            self.outputProtocolConnections.append(outputProtocolConnection)
        else:
            i = 0
            while i < len(self.configuration["REMOTE_PROXY_SERVERS"]):
                outputProtocolConnectionClass = self.getOutputProtocolConnectionClass(self.configuration["REMOTE_PROXY_SERVERS"][i]["TYPE"])
                
                if outputProtocolConnectionClass is not None:
                    outputProtocolConnection = outputProtocolConnectionClass(self.configuration, i)
                    self.outputProtocolConnections.append(outputProtocolConnection)
                
                i = i + 1
    
    def connect(self, remoteAddress, remotePort, inputProtocol):
        twunnel.logger.log(3, "trace: OutputProtocolConnectionManager.connect")
        
        self.i = self.i + 1
        if self.i >= len(self.outputProtocolConnections):
            self.i = 0
        
        outputProtocolConnection = self.outputProtocolConnections[self.i]
        outputProtocolConnection.connect(remoteAddress, remotePort, inputProtocol)
    
    def startConnectionManager(self):
        twunnel.logger.log(3, "trace: OutputProtocolConnectionManager.startConnectionManager")
        
        i = 0
        while i < len(self.outputProtocolConnections):
            outputProtocolConnection = self.outputProtocolConnections[i]
            outputProtocolConnection.startConnection()
            
            i = i + 1
    
    def stopConnectionManager(self):
        twunnel.logger.log(3, "trace: OutputProtocolConnectionManager.stopConnectionManager")
        
        i = 0
        while i < len(self.outputProtocolConnections):
            outputProtocolConnection = self.outputProtocolConnections[i]
            outputProtocolConnection.stopConnection()
            
            i = i + 1
    
    def getOutputProtocolConnectionClass(self, type):
        twunnel.logger.log(3, "trace: OutputProtocolConnectionManager.getOutputProtocolConnectionClass")
        
        if type == "SSH":
            return SSHOutputProtocolConnection
        else:
            if type == "WS":
                return WSOutputProtocolConnection
            else:
                if type == "WSS":
                    return WSOutputProtocolConnection
                else:
                    return None

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
            self.processDataState0()
            return
        if self.dataState == 1:
            self.processDataState1()
            return
        if self.dataState == 2:
            self.processDataState2()
            return
    
    def processDataState0(self):
        twunnel.logger.log(3, "trace: SOCKS5InputProtocol.processDataState0")
        
        # no authentication
        self.transport.write(struct.pack('!BB', 0x05, 0x00))
        
        self.data = ""
        self.dataState = 1
    
    def processDataState1(self):
        twunnel.logger.log(3, "trace: SOCKS5InputProtocol.processDataState1")
        
        v, c, r, remoteAddressType = struct.unpack('!BBBB', self.data[:4])
        
        # IPv4
        if remoteAddressType == 0x01:
            remoteAddress, self.remotePort = struct.unpack('!IH', self.data[4:10])
            self.remoteAddress = socket.inet_ntoa(struct.pack('!I', remoteAddress))
            self.data = self.data[10:]
        else:
            # DN
            if remoteAddressType == 0x03:
                remoteAddressLength = ord(self.data[4])
                self.remoteAddress, self.remotePort = struct.unpack('!%dsH' % remoteAddressLength, self.data[5:])
                self.data = self.data[7 + remoteAddressLength:]
            # IPv6
            else:
                response = struct.pack('!BBBBIH', 0x05, 0x08, 0x00, 0x01, 0, 0)
                self.transport.write(response)
                self.transport.loseConnection()
                return
        
        twunnel.logger.log(2, "remoteAddress: " + self.remoteAddress)
        twunnel.logger.log(2, "remotePort: " + str(self.remotePort))
        
        # connect
        if c == 0x01:
            self.outputProtocolConnectionManager.connect(self.remoteAddress, self.remotePort, self)
        else:
            response = struct.pack('!BBBBIH', 0x05, 0x07, 0x00, 0x01, 0, 0)
            self.transport.write(response)
            self.transport.loseConnection()
            return
        
    def processDataState2(self):
        twunnel.logger.log(3, "trace: SOCKS5InputProtocol.processDataState2")
        
        self.outputProtocol.inputProtocol_dataReceived(self.data)
        
        self.data = ""
        
    def outputProtocol_connectionMade(self):
        twunnel.logger.log(3, "trace: SOCKS5InputProtocol.outputProtocol_connectionMade")
        
        if self.connectionState == 1:
            self.transport.registerProducer(self.outputProtocol, True)
            
            response = struct.pack('!BBBBIH', 0x05, 0x00, 0x00, 0x01, 0, 0)
            self.transport.write(response)
            
            self.outputProtocol.inputProtocol_connectionMade()
            
            self.data = ""
            self.dataState = 2
        else:
            if self.connectionState == 2:
                self.outputProtocol.inputProtocol_connectionLost(None)
        
    def outputProtocol_connectionFailed(self, reason):
        twunnel.logger.log(3, "trace: SOCKS5InputProtocol.outputProtocol_connectionFailed")
        
        if self.connectionState == 1:
            response = struct.pack('!BBBBIH', 0x05, 0x05, 0x00, 0x01, 0, 0)
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
    
    def buildProtocol(self, *args, **kw):
        inputProtocol = protocol.ClientFactory.buildProtocol(self, *args, **kw)
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

def createPort(configuration):
    setDefaultConfiguration(configuration, ["PROXY_SERVERS", "LOCAL_PROXY_SERVER", "REMOTE_PROXY_SERVERS"])
    
    outputProtocolConnectionManager = OutputProtocolConnectionManager(configuration)
    
    if configuration["LOCAL_PROXY_SERVER"]["TYPE"] == "SOCKS5":
        return createSOCKS5Port(configuration, outputProtocolConnectionManager)
    else:
        return None

# SSH

class SSHChannel(channel.SSHChannel):
    implements(interfaces.IPushProducer)
    name = "direct-tcpip"
    
    def __init__(self, *args, **kw):
        twunnel.logger.log(3, "trace: SSHChannel.__init__")
        
        channel.SSHChannel.__init__(self, *args, **kw)
        
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
        self.i = 0
        
    def verifyHostKey(self, hostKey, fingerprint):
        twunnel.logger.log(3, "trace: SSHClientTransport.verifyHostKey")
        twunnel.logger.log(2, "fingerprint1: " + fingerprint)
        twunnel.logger.log(2, "fingerprint2: " + self.configuration["REMOTE_PROXY_SERVERS"][self.i]["KEY"]["FINGERPRINT"])
        
        if self.configuration["REMOTE_PROXY_SERVERS"][self.i]["KEY"]["FINGERPRINT"] != "":
            if self.configuration["REMOTE_PROXY_SERVERS"][self.i]["KEY"]["FINGERPRINT"] != fingerprint:
                twunnel.logger.log(1, "ERROR_KEY_FINGERPRINT")
                
                return defer.fail(0)
        
        return defer.succeed(1)

    def connectionSecure(self):
        twunnel.logger.log(3, "trace: SSHClientTransport.connectionSecure")
        
        self.requestService(SSHUserAuthClient(self.configuration, self.i))

class SSHClientTransportFactory(protocol.ReconnectingClientFactory):
    protocol = SSHClientTransport
    
    def __init__(self, configuration, i, output):
        twunnel.logger.log(3, "trace: SSHClientTransportFactory.__init__")
        
        self.configuration = configuration
        self.i = i
        self.output = output
        
    def buildProtocol(self, address):
        twunnel.logger.log(3, "trace: SSHClientTransportFactory.buildProtocol")
        
        p = protocol.ClientFactory.buildProtocol(self, address)
        p.configuration = self.configuration
        p.i = self.i
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
    def __init__(self, configuration, i):
        twunnel.logger.log(3, "trace: SSHUserAuthClient.__init__")
        
        self.configuration = configuration
        self.i = i
        self.j = -1
        
        userauth.SSHUserAuthClient.__init__(self, str(self.configuration["REMOTE_PROXY_SERVERS"][self.i]["ACCOUNT"]["NAME"]), SSHConnection())
        
    def getPassword(self):
        twunnel.logger.log(3, "trace: SSHUserAuthClient.getPassword")
        
        return defer.succeed(str(self.configuration["REMOTE_PROXY_SERVERS"][self.i]["ACCOUNT"]["PASSWORD"]))
        
    def getPublicKey(self):
        twunnel.logger.log(3, "trace: SSHUserAuthClient.getPublicKey")
        
        if self.configuration["REMOTE_PROXY_SERVERS"][self.i]["ACCOUNT"]["PASSWORD"] != "":
            return None
        
        self.j = self.j + 1
        if self.j == len(self.configuration["REMOTE_PROXY_SERVERS"][self.i]["ACCOUNT"]["KEYS"]):
            return None
        
        return keys.Key.fromFile(self.configuration["REMOTE_PROXY_SERVERS"][self.i]["ACCOUNT"]["KEYS"][self.j]["PUBLIC"]["FILE"], passphrase=str(self.configuration["REMOTE_PROXY_SERVERS"][self.i]["ACCOUNT"]["KEYS"][self.j]["PUBLIC"]["PASSPHRASE"])).blob()

    def getPrivateKey(self):
        twunnel.logger.log(3, "trace: SSHUserAuthClient.getPrivateKey")
        
        return defer.succeed(keys.Key.fromFile(self.configuration["REMOTE_PROXY_SERVERS"][self.i]["ACCOUNT"]["KEYS"][self.j]["PRIVATE"]["FILE"], passphrase=str(self.configuration["REMOTE_PROXY_SERVERS"][self.i]["ACCOUNT"]["KEYS"][self.j]["PRIVATE"]["PASSPHRASE"])).keyObject)

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
    def __init__(self, configuration, i):
        twunnel.logger.log(3, "trace: SSHOutputProtocolConnection.__init__")
        
        self.configuration = configuration
        self.i = i
        self.j = -1
        
        self.connections = []
        self.connectors = []
        self.factory = None
    
    def connect(self, remoteAddress, remotePort, inputProtocol):
        twunnel.logger.log(3, "trace: SSHOutputProtocolConnection.connect")
        
        if len(self.connections) == 0:
            return
        
        self.j = self.j + 1
        if self.j >= len(self.connections):
            self.j = 0
        
        connection = self.connections[self.j]
        
        inputProtocol.outputProtocol = SSHChannel(conn = connection)
        inputProtocol.outputProtocol.inputProtocol = inputProtocol
        data = forwarding.packOpen_direct_tcpip((remoteAddress, remotePort), (self.configuration["LOCAL_PROXY_SERVER"]["ADDRESS"], self.configuration["LOCAL_PROXY_SERVER"]["PORT"]))
        connection.openChannel(inputProtocol.outputProtocol, data)
    
    def startConnection(self):
        twunnel.logger.log(3, "trace: SSHOutputProtocolConnection.startConnection")
        
        self.factory = SSHClientTransportFactory(self.configuration, self.i, self)
        
        i = 0
        while i < self.configuration["REMOTE_PROXY_SERVERS"][self.i]["ACCOUNT"]["CONNECTIONS"]:
            tunnel = twunnel.proxy_server.createTunnel(self.configuration)
            tunnel.connect(self.configuration["REMOTE_PROXY_SERVERS"][self.i]["ADDRESS"], self.configuration["REMOTE_PROXY_SERVERS"][self.i]["PORT"], self.factory)
            
            i = i + 1
    
    def stopConnection(self):
        twunnel.logger.log(3, "trace: SSHOutputProtocolConnection.stopConnection")
        
        self.factory.stopTrying()
        
        i = 0
        while i < len(self.connectors):
            connector = self.connectors[i]
            connector.disconnect()
            
            i = i + 1

# WS

class WSOutputProtocol(autobahn.websocket.WebSocketClientProtocol):
    implements(interfaces.IPushProducer)
    
    def __init__(self):
        twunnel.logger.log(3, "trace: WSOutputProtocol.__init__")
        
        self.configuration = None
        self.i = 0
        self.remoteAddress = ""
        self.remotePort = 0
        self.inputProtocol = None
        self.connectionState = 0
        self.message = ""
        self.messageState = 0
        
    def onOpen(self):
        twunnel.logger.log(3, "trace: WSOutputProtocol.onOpen")
        
        self.connectionState = 1
        
        request = {}
        request["REMOTE_PROXY_SERVER"] = {}
        request["REMOTE_PROXY_SERVER"]["ACCOUNT"] = {}
        request["REMOTE_PROXY_SERVER"]["ACCOUNT"]["NAME"] = str(self.configuration["REMOTE_PROXY_SERVERS"][self.i]["ACCOUNT"]["NAME"])
        request["REMOTE_PROXY_SERVER"]["ACCOUNT"]["PASSWORD"] = str(self.configuration["REMOTE_PROXY_SERVERS"][self.i]["ACCOUNT"]["PASSWORD"])
        request["REMOTE_ADDRESS"] = str(self.remoteAddress)
        request["REMOTE_PORT"] = self.remotePort
        
        encoder = json.JSONEncoder()
        message = encoder.encode(request)
        
        self.sendMessage(message, False)
        
        self.message = ""
        self.messageState = 0

    def onClose(self, wasClean, code, reason):
        twunnel.logger.log(3, "trace: WSOutputProtocol.onClose")
        
        self.connectionState = 2
        
        self.inputProtocol.outputProtocol_connectionLost(reason)
        
    def onMessage(self, message, binary):
        twunnel.logger.log(3, "trace: WSOutputProtocol.onMessage")
        
        self.message = self.message + message
        if self.messageState == 0:
            self.processMessageState0();
            return
        if self.messageState == 1:
            self.processMessageState1();
            return
        
    def processMessageState0(self):
        twunnel.logger.log(3, "trace: WSOutputProtocol.processMessageState0")
        
        decoder = json.JSONDecoder()
        response = decoder.decode(self.message)
        
        self.inputProtocol.outputProtocol_connectionMade()
        
        self.message = ""
        self.messageState = 1
        
    def processMessageState1(self):
        twunnel.logger.log(3, "trace: WSOutputProtocol.processMessageState1")
        
        if len(self.message) == 0:
            self.inputProtocol.resumeProducing()
            return
        
        self.sendMessage("", True)
        
        self.inputProtocol.outputProtocol_dataReceived(self.message)
        
        self.message = ""
        
    def inputProtocol_connectionMade(self):
        twunnel.logger.log(3, "trace: WSOutputProtocol.inputProtocol_connectionMade")
        
    def inputProtocol_connectionLost(self, reason):
        twunnel.logger.log(3, "trace: WSOutputProtocol.inputProtocol_connectionLost")
        
        if self.connectionState == 1:
            self.sendClose()
        
    def inputProtocol_dataReceived(self, data):
        twunnel.logger.log(3, "trace: WSOutputProtocol.inputProtocol_dataReceived")
        
        self.inputProtocol.pauseProducing()
        
        if self.connectionState == 1:
            self.sendMessage(data, True)
    
    def pauseProducing(self):
        twunnel.logger.log(3, "trace: WSOutputProtocol.pauseProducing")
        
        if self.connectionState == 1:
            self.transport.pauseProducing()
    
    def resumeProducing(self):
        twunnel.logger.log(3, "trace: WSOutputProtocol.resumeProducing")
        
        if self.connectionState == 1:
            self.transport.resumeProducing()
    
    def stopProducing(self):
        twunnel.logger.log(3, "trace: WSOutputProtocol.stopProducing")
        
        if self.connectionState == 1:
            self.transport.stopProducing()

class WSOutputProtocolFactory(autobahn.websocket.WebSocketClientFactory):
    protocol = WSOutputProtocol
    
    def __init__(self, configuration, i, remoteAddress, remotePort, inputProtocol, *args, **kwargs):
        twunnel.logger.log(3, "trace: WSOutputProtocolFactory.__init__")
        
        autobahn.websocket.WebSocketClientFactory.__init__(self, *args, **kwargs)
        
        self.configuration = configuration
        self.i = i
        self.remoteAddress = remoteAddress
        self.remotePort = remotePort
        self.inputProtocol = inputProtocol
        
    def buildProtocol(self, *args, **kwargs):
        outputProtocol = autobahn.websocket.WebSocketClientFactory.buildProtocol(self, *args, **kwargs)
        outputProtocol.configuration = self.configuration
        outputProtocol.i = self.i
        outputProtocol.remoteAddress = self.remoteAddress
        outputProtocol.remotePort = self.remotePort
        outputProtocol.inputProtocol = self.inputProtocol
        outputProtocol.inputProtocol.outputProtocol = outputProtocol
        return outputProtocol
        
    def clientConnectionFailed(self, connector, reason):
        twunnel.logger.log(3, "trace: WSOutputProtocolFactory.clientConnectionFailed")
        
        self.inputProtocol.outputProtocol_connectionFailed(reason)

class ClientContextFactory(ssl.ClientContextFactory):
    def __init__(self, verify_locations):
        twunnel.logger.log(3, "trace: ClientContextFactory.__init__")
        
        self.verify_locations = verify_locations
        
    def getContext(self):
        twunnel.logger.log(3, "trace: ClientContextFactory.getContext")
        
        self.method = OpenSSL.SSL.TLSv1_METHOD
        
        context = ssl.ClientContextFactory.getContext(self)
        context.load_verify_locations(self.verify_locations)
        context.set_verify(OpenSSL.SSL.VERIFY_PEER | OpenSSL.SSL.VERIFY_FAIL_IF_NO_PEER_CERT, self.verify)
        
        return context
        
    def verify(self, connection, certificate, errorNumber, errorDepth, certificateOk):
        twunnel.logger.log(3, "trace: ClientContextFactory.verify")
        
        if certificateOk:
            twunnel.logger.log(2, "certificate: ok")
        else:
            twunnel.logger.log(2, "certificate: not ok")
        
        return certificateOk

class WSOutputProtocolConnection(object):
    def __init__(self, configuration, i):
        twunnel.logger.log(3, "trace: WSOutputProtocolConnection.__init__")
        
        self.configuration = configuration
        self.i = i
        
    def connect(self, remoteAddress, remotePort, inputProtocol):
        twunnel.logger.log(3, "trace: WSOutputProtocolConnection.connect")
        
        if self.configuration["REMOTE_PROXY_SERVERS"][self.i]["TYPE"] == "WS":
            factory = WSOutputProtocolFactory(self.configuration, self.i, remoteAddress, remotePort, inputProtocol, "ws://" + str(self.configuration["REMOTE_PROXY_SERVERS"][self.i]["ADDRESS"]) + ":" + str(self.configuration["REMOTE_PROXY_SERVERS"][self.i]["PORT"]))
            
            tunnel = twunnel.proxy_server.createTunnel(self.configuration)
            tunnel.connect(self.configuration["REMOTE_PROXY_SERVERS"][self.i]["ADDRESS"], self.configuration["REMOTE_PROXY_SERVERS"][self.i]["PORT"], factory)
        else:
            factory = WSOutputProtocolFactory(self.configuration, self.i, remoteAddress, remotePort, inputProtocol, "wss://" + str(self.configuration["REMOTE_PROXY_SERVERS"][self.i]["ADDRESS"]) + ":" + str(self.configuration["REMOTE_PROXY_SERVERS"][self.i]["PORT"]))
            
            if self.configuration["REMOTE_PROXY_SERVERS"][self.i]["CERTIFICATE"]["AUTHORITY"]["FILE"] != "":
                contextFactory = ClientContextFactory(self.configuration["REMOTE_PROXY_SERVERS"][self.i]["CERTIFICATE"]["AUTHORITY"]["FILE"])
            else:
                contextFactory = ssl.ClientContextFactory()
            
            tunnel = twunnel.proxy_server.createTunnel(self.configuration)
            tunnel.connect(self.configuration["REMOTE_PROXY_SERVERS"][self.i]["ADDRESS"], self.configuration["REMOTE_PROXY_SERVERS"][self.i]["PORT"], factory, contextFactory)
    
    def startConnection(self):
        twunnel.logger.log(3, "trace: WSOutputProtocolConnection.startConnection")
    
    def stopConnection(self):
        twunnel.logger.log(3, "trace: WSOutputProtocolConnection.stopConnection")