# Copyright (c) Jeroen Van Steirteghem
# See LICENSE

from zope.interface import implements
from twisted.internet import base, interfaces, protocol, reactor, tcp
from twisted.internet.abstract import isIPAddress, isIPv6Address
from twisted.names import cache, client, hosts, resolve
import base64
import struct
import socket
import logging

logger = logging.getLogger(__name__)

class HostsResolver(hosts.Resolver):
    lookupAllRecords = hosts.Resolver.lookupAddress

class ClientResolver(client.Resolver):
    lookupAllRecords = client.Resolver.lookupAddress

def createResolver(configuration):
    resolverFile = configuration["DNS_RESOLVER"]["HOSTS"]["FILE"]
    resolverServers = []
    i = 0
    while i < len(configuration["DNS_RESOLVER"]["SERVERS"]):
        resolverServers.append((configuration["DNS_RESOLVER"]["SERVERS"][i]["ADDRESS"], configuration["DNS_RESOLVER"]["SERVERS"][i]["PORT"]))
        i = i + 1
    
    resolvers = []
    if resolverFile != "":
        resolvers.append(HostsResolver(file=resolverFile))
    if len(resolverServers) != 0:
        resolvers.append(cache.CacheResolver())
        resolvers.append(ClientResolver(servers=resolverServers))
    
    if len(resolvers) != 0:
        return resolve.ResolverChain(resolvers)
    else:
        return base.BlockingResolver()

class TunnelProtocol(protocol.Protocol):
    def __init__(self):
        logger.debug("TunnelProtocol.__init__")
        
        self.tunnelOutputProtocol = None
        self.tunnelOutputProtocolFactory = None
        
    def connectionMade(self):
        logger.debug("TunnelProtocol.connectionMade")
        
        if self.factory.configuration["PROXY_SERVERS"][self.factory.i]["TYPE"] == "HTTP":
            self.tunnelOutputProtocolFactory = HTTPTunnelOutputProtocolFactory(self.factory.i, self.factory.configuration, self.factory.address, self.factory.port, self)
            self.tunnelOutputProtocolFactory.protocol = HTTPTunnelOutputProtocol
        else:
            if self.factory.configuration["PROXY_SERVERS"][self.factory.i]["TYPE"] == "SOCKS5":
                self.tunnelOutputProtocolFactory = SOCKS5TunnelOutputProtocolFactory(self.factory.i, self.factory.configuration, self.factory.address, self.factory.port, self)
                self.tunnelOutputProtocolFactory.protocol = SOCKS5TunnelOutputProtocol
            else:
                self.transport.loseConnection()
                return
        
        self.tunnelOutputProtocol = self.tunnelOutputProtocolFactory.buildProtocol(self.transport.getPeer())
        self.tunnelOutputProtocol.makeConnection(self.transport)
        
    def connectionLost(self, reason):
        logger.debug("TunnelProtocol.connectionLost")
        
        if self.tunnelOutputProtocol is not None:
            self.tunnelOutputProtocol.connectionLost(reason)
        else:
            if self.factory.outputProtocol is not None:
                self.factory.outputProtocol.connectionLost(reason)
    
    def dataReceived(self, data):
        logger.debug("TunnelProtocol.dataReceived")
        
        if self.tunnelOutputProtocol is not None:
            self.tunnelOutputProtocol.dataReceived(data)
        else:
            if self.factory.outputProtocol is not None:
                self.factory.outputProtocol.dataReceived(data)
    
    def tunnelOutputProtocol_connectionMade(self, data):
        logger.debug("TunnelProtocol.tunnelOutputProtocol_connectionMade")
        
        self.tunnelOutputProtocol = None
        
        if self.factory.contextFactory is not None:
            self.transport.startTLS(self.factory.contextFactory)
        
        self.factory.outputProtocol = self.factory.outputProtocolFactory.buildProtocol(self.transport.getPeer())
        self.factory.outputProtocol.makeConnection(self.transport)
        
        if len(data) > 0:
            self.factory.outputProtocol.dataReceived(data)

class TunnelProtocolFactory(protocol.ClientFactory):
    def __init__(self, i, configuration, address, port, outputProtocolFactory, contextFactory=None, timeout=30, bindAddress=None):
        logger.debug("TunnelProtocolFactory.__init__")
        
        self.i = i
        self.configuration = configuration
        self.address = address
        self.port = port
        self.outputProtocol = None
        self.outputProtocolFactory = outputProtocolFactory
        self.contextFactory = contextFactory
        self.timeout = timeout
        self.bindAddress = bindAddress
    
    def startedConnecting(self, connector):
        logger.debug("TunnelProtocolFactory.startedConnecting")
        
        self.outputProtocolFactory.startedConnecting(connector)
    
    def clientConnectionFailed(self, connector, reason):
        logger.debug("TunnelProtocolFactory.clientConnectionFailed")
        
        self.outputProtocolFactory.clientConnectionFailed(connector, reason)
    
    def clientConnectionLost(self, connector, reason):
        logger.debug("TunnelProtocolFactory.clientConnectionLost")
        
        if self.outputProtocol is None:
            self.outputProtocolFactory.clientConnectionFailed(connector, reason)
        else:
            self.outputProtocolFactory.clientConnectionLost(connector, reason)

class Tunnel(object):
    def __init__(self, configuration):
        logger.debug("Tunnel.__init__")
        
        self.configuration = configuration
    
    def connect(self, address, port, outputProtocolFactory, contextFactory=None, timeout=30, bindAddress=None):
        logger.debug("Tunnel.connect")
        
        if len(self.configuration["PROXY_SERVERS"]) == 0:
            if contextFactory is None:
                return reactor.connectTCP(address, port, outputProtocolFactory, timeout, bindAddress)
            else:
                return reactor.connectSSL(address, port, outputProtocolFactory, contextFactory, timeout, bindAddress)
        else:
            i = len(self.configuration["PROXY_SERVERS"])
            
            tunnelProtocolFactory = TunnelProtocolFactory(i - 1, self.configuration, address, port, outputProtocolFactory, contextFactory, timeout, bindAddress)
            tunnelProtocolFactory.protocol = TunnelProtocol
            
            i = i - 1
            
            while i > 0:
                tunnelProtocolFactory = TunnelProtocolFactory(i - 1, self.configuration, self.configuration["PROXY_SERVERS"][i]["ADDRESS"], self.configuration["PROXY_SERVERS"][i]["PORT"], tunnelProtocolFactory, contextFactory, timeout, bindAddress)
                tunnelProtocolFactory.protocol = TunnelProtocol
                
                i = i - 1
            
            return reactor.connectTCP(self.configuration["PROXY_SERVERS"][i]["ADDRESS"], self.configuration["PROXY_SERVERS"][i]["PORT"], tunnelProtocolFactory, timeout, bindAddress)

class HTTPTunnelOutputProtocol(protocol.Protocol):
    def __init__(self):
        logger.debug("HTTPTunnelOutputProtocol.__init__")
        
        self.data = ""
        self.dataState = 0
        
    def connectionMade(self):
        logger.debug("HTTPTunnelOutputProtocol.connectionMade")
        
        request = "CONNECT " + str(self.factory.address) + ":" + str(self.factory.port) + " HTTP/1.0\r\n"
        
        if self.factory.configuration["PROXY_SERVERS"][self.factory.i]["ACCOUNT"]["NAME"] != "":
            request = request + "Proxy-Authorization: Basic " + base64.standard_b64encode(self.factory.configuration["PROXY_SERVERS"][self.factory.i]["ACCOUNT"]["NAME"] + ":" + self.factory.configuration["PROXY_SERVERS"][self.factory.i]["ACCOUNT"]["PASSWORD"]) + "\r\n"
        
        request = request + "\r\n"
        
        self.transport.write(request)
        
    def connectionLost(self, reason):
        logger.debug("HTTPTunnelOutputProtocol.connectionLost")
    
    def dataReceived(self, data):
        logger.debug("HTTPTunnelOutputProtocol.dataReceived")
        
        self.data = self.data + data
        if self.dataState == 0:
            self.processDataState0()
            return
    
    def processDataState0(self):
        logger.debug("HTTPTunnelOutputProtocol.processDataState0")
        
        i = self.data.find("\r\n\r\n")
        
        if i == -1:
            return
            
        i = i + 4
        
        dataLines = self.data[:i].split("\r\n")
        dataLine0 = dataLines[0]
        dataLine0Values = dataLine0.split(" ", 2)
        
        if len(dataLine0Values) != 3:
            self.transport.loseConnection()
            return
        
        if dataLine0Values[1] != "200":
            self.transport.loseConnection()
            return
        
        self.factory.tunnelProtocol.tunnelOutputProtocol_connectionMade(self.data[i:])
        
        self.data = ""
        self.dataState = 1

class HTTPTunnelOutputProtocolFactory(protocol.ClientFactory):
    def __init__(self, i, configuration, address, port, tunnelProtocol):
        logger.debug("HTTPTunnelOutputProtocolFactory.__init__")
        
        self.i = i
        self.configuration = configuration
        self.address = address
        self.port = port
        self.tunnelProtocol = tunnelProtocol
    
    def startedConnecting(self, connector):
        logger.debug("HTTPTunnelOutputProtocolFactory.startedConnecting")
    
    def clientConnectionFailed(self, connector, reason):
        logger.debug("HTTPTunnelOutputProtocolFactory.clientConnectionFailed")
    
    def clientConnectionLost(self, connector, reason):
        logger.debug("HTTPTunnelOutputProtocolFactory.clientConnectionLost")

class SOCKS5TunnelOutputProtocol(protocol.Protocol):
    def __init__(self):
        logger.debug("SOCKS5TunnelOutputProtocol.__init__")
        
        self.data = ""
        self.dataState = 0
    
    def connectionMade(self):
        logger.debug("SOCKS5TunnelOutputProtocol.connectionMade")
        
        request = struct.pack("!BBB", 0x05, 0x01, 0x00)
        
        self.transport.write(request)
    
    def connectionLost(self, reason):
        logger.debug("SOCKS5TunnelOutputProtocol.connectionLost")
    
    def dataReceived(self, data):
        logger.debug("SOCKS5TunnelOutputProtocol.dataReceived")
        
        self.data = self.data + data
        if self.dataState == 0:
            self.processDataState0()
            return
        
        if self.dataState == 1:
            self.processDataState1()
            return
    
    def processDataState0(self):
        logger.debug("SOCKS5TunnelOutputProtocol.processDataState0")
        
        if len(self.data) < 2:
            return
        
        if ord(self.data[0]) != 0x05:
            self.transport.loseConnection()
            return
        
        addressType = 0x03
        if isIPAddress(self.factory.address) == True:
            addressType = 0x01
        else:
            if isIPv6Address(self.factory.address) == True:
                addressType = 0x04
        
        request = struct.pack("!BBB", 0x05, 0x01, 0x00)
        
        if addressType == 0x01:
            address = struct.unpack("!I", socket.inet_aton(self.factory.address))[0]
            request = request + struct.pack("!BI", 0x01, address)
        else:
            if addressType == 0x03:
                address = str(self.factory.address)
                addressLength = len(address)
                request = request + struct.pack("!BB%ds" % addressLength, 0x03, addressLength, address)
            else:
                self.transport.loseConnection()
                return
        
        request = request + struct.pack("!H", self.factory.port)
        
        self.transport.write(request)
        
        self.data = ""
        self.dataState = 1
    
    def processDataState1(self):
        logger.debug("SOCKS5TunnelOutputProtocol.processDataState1")
        
        if len(self.data) < 10:
            return
        
        if ord(self.data[0]) != 0x05:
            self.transport.loseConnection()
            return
        
        if ord(self.data[1]) != 0x00:
            self.transport.loseConnection()
            return
        
        self.factory.tunnelProtocol.tunnelOutputProtocol_connectionMade(self.data[10:])
        
        self.data = ""
        self.dataState = 2

class SOCKS5TunnelOutputProtocolFactory(protocol.ClientFactory):
    def __init__(self, i, configuration, address, port, tunnelProtocol):
        logger.debug("SOCKS5TunnelOutputProtocolFactory.__init__")
        
        self.i = i
        self.configuration = configuration
        self.address = address
        self.port = port
        self.tunnelProtocol = tunnelProtocol
    
    def startedConnecting(self, connector):
        logger.debug("SOCKS5TunnelOutputProtocolFactory.startedConnecting")
    
    def clientConnectionFailed(self, connector, reason):
        logger.debug("SOCKS5TunnelOutputProtocolFactory.clientConnectionFailed")
    
    def clientConnectionLost(self, connector, reason):
        logger.debug("SOCKS5TunnelOutputProtocolFactory.clientConnectionLost")

class OutputProtocol(protocol.Protocol):
    implements(interfaces.IPushProducer)
    
    def __init__(self):
        logger.debug("OutputProtocol.__init__")
        
        self.inputProtocol = None
        self.connectionState = 0
        
    def connectionMade(self):
        logger.debug("OutputProtocol.connectionMade")
        
        self.connectionState = 1
        
        self.inputProtocol.outputProtocol_connectionMade()
        
    def connectionLost(self, reason):
        logger.debug("OutputProtocol.connectionLost")
        
        self.connectionState = 2
        
        self.inputProtocol.outputProtocol_connectionLost(reason)
        
    def dataReceived(self, data):
        logger.debug("OutputProtocol.dataReceived")
        
        self.inputProtocol.outputProtocol_dataReceived(data)
        
    def inputProtocol_connectionMade(self):
        logger.debug("OutputProtocol.inputProtocol_connectionMade")
        
        if self.connectionState == 1:
            self.transport.registerProducer(self.inputProtocol, True)
        
    def inputProtocol_connectionLost(self, reason):
        logger.debug("OutputProtocol.inputProtocol_connectionLost")
        
        if self.connectionState == 1:
            self.transport.unregisterProducer()
            self.transport.loseConnection()
        
    def inputProtocol_dataReceived(self, data):
        logger.debug("OutputProtocol.inputProtocol_dataReceived")
        
        if self.connectionState == 1:
            self.transport.write(data)
    
    def pauseProducing(self):
        logger.debug("OutputProtocol.pauseProducing")
        
        if self.connectionState == 1:
            self.transport.pauseProducing()
    
    def resumeProducing(self):
        logger.debug("OutputProtocol.resumeProducing")
        
        if self.connectionState == 1:
            self.transport.resumeProducing()
    
    def stopProducing(self):
        logger.debug("OutputProtocol.stopProducing")
        
        if self.connectionState == 1:
            self.transport.stopProducing()

class OutputProtocolFactory(protocol.ClientFactory):
    protocol = OutputProtocol
    
    def __init__(self, inputProtocol):
        logger.debug("OutputProtocolFactory.__init__")
        
        self.inputProtocol = inputProtocol
        
    def buildProtocol(self, *args, **kw):
        outputProtocol = protocol.ClientFactory.buildProtocol(self, *args, **kw)
        outputProtocol.inputProtocol = self.inputProtocol
        outputProtocol.inputProtocol.outputProtocol = outputProtocol
        return outputProtocol
    
    def clientConnectionFailed(self, connector, reason):
        logger.debug("OutputProtocolFactory.clientConnectionFailed")
        
        self.inputProtocol.outputProtocol_connectionFailed(reason)

class Output(object):
    def __init__(self, configuration):
        logger.debug("Output.__init__")
        
        self.configuration = configuration
    
    def connect(self, remoteAddress, remotePort, inputProtocol):
        logger.debug("Output.connect")
        
        outputProtocolFactory = OutputProtocolFactory(inputProtocol)
        
        tunnel = Tunnel(self.configuration)
        tunnel.connect(remoteAddress, remotePort, outputProtocolFactory)
        
    def startOutput(self):
        logger.debug("Output.startOutput")
    
    def stopOutput(self):
        logger.debug("Output.stopOutput")

class InputProtocol(protocol.Protocol):
    implements(interfaces.IPushProducer)
    
    def __init__(self):
        logger.debug("InputProtocol.__init__")
        
        self.configuration = None
        self.output = None
        self.outputProtocol = None
        self.remoteAddress = ""
        self.remotePort = 0
        self.connectionState = 0
        self.data = ""
        self.dataState = 0
    
    def connectionMade(self):
        logger.debug("InputProtocol.connectionMade")
        
        self.connectionState = 1
    
    def connectionLost(self, reason):
        logger.debug("InputProtocol.connectionLost")
        
        self.connectionState = 2
        
        if self.outputProtocol is not None:
            self.outputProtocol.inputProtocol_connectionLost(reason)
    
    def dataReceived(self, data):
        logger.debug("InputProtocol.dataReceived")
        
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
        logger.debug("InputProtocol.processDataState0")
        
        # no authentication
        self.transport.write(struct.pack('!BB', 0x05, 0x00))
        
        self.data = ""
        self.dataState = 1
    
    def processDataState1(self):
        logger.debug("InputProtocol.processDataState1")
        
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
        
        logger.debug("InputProtocol.remoteAddress: " + self.remoteAddress)
        logger.debug("InputProtocol.remotePort: " + str(self.remotePort))
        
        # connect
        if c == 0x01:
            self.output.connect(self.remoteAddress, self.remotePort, self)
        else:
            response = struct.pack('!BBBBIH', 0x05, 0x07, 0x00, 0x01, 0, 0)
            self.transport.write(response)
            self.transport.loseConnection()
            return
        
    def processDataState2(self):
        logger.debug("InputProtocol.processDataState2")
        
        self.outputProtocol.inputProtocol_dataReceived(self.data)
        
        self.data = ""
        
    def outputProtocol_connectionMade(self):
        logger.debug("InputProtocol.outputProtocol_connectionMade")
        
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
        logger.debug("InputProtocol.outputProtocol_connectionFailed")
        
        if self.connectionState == 1:
            response = struct.pack('!BBBBIH', 0x05, 0x05, 0x00, 0x01, 0, 0)
            self.transport.write(response)
            self.transport.loseConnection()
        
    def outputProtocol_connectionLost(self, reason):
        logger.debug("InputProtocol.outputProtocol_connectionLost")
        
        if self.connectionState == 1:
            self.transport.unregisterProducer()
            self.transport.loseConnection()
        else:
            if self.connectionState == 2:
                self.outputProtocol.inputProtocol_connectionLost(None)
        
    def outputProtocol_dataReceived(self, data):
        logger.debug("InputProtocol.outputProtocol_dataReceived")
        
        if self.connectionState == 1:
            self.transport.write(data)
        else:
            if self.connectionState == 2:
                self.outputProtocol.inputProtocol_connectionLost(None)
    
    def pauseProducing(self):
        logger.debug("InputProtocol.pauseProducing")
        
        if self.connectionState == 1:
            self.transport.pauseProducing()
    
    def resumeProducing(self):
        logger.debug("InputProtocol.resumeProducing")
        
        if self.connectionState == 1:
            self.transport.resumeProducing()
    
    def stopProducing(self):
        logger.debug("InputProtocol.stopProducing")
        
        if self.connectionState == 1:
            self.transport.stopProducing()
        
class InputProtocolFactory(protocol.ClientFactory):
    protocol = InputProtocol
    
    def __init__(self, configuration, output):
        logger.debug("InputProtocolFactory.__init__")
        
        self.configuration = configuration
        self.output = output
    
    def buildProtocol(self, *args, **kw):
        inputProtocol = protocol.ClientFactory.buildProtocol(self, *args, **kw)
        inputProtocol.configuration = self.configuration
        inputProtocol.output = self.output
        return inputProtocol
    
    def startFactory(self):
        logger.debug("InputProtocolFactory.startFactory")
        
        self.output.startOutput()
    
    def stopFactory(self):
        logger.debug("InputProtocolFactory.stopFactory")
        
        self.output.stopOutput()

def createPort(configuration, output=None):
    if output is None:
        output = Output(configuration)
    
    factory = InputProtocolFactory(configuration, output)
    
    return tcp.Port(configuration["LOCAL_PROXY_SERVER"]["PORT"], factory, 50, configuration["LOCAL_PROXY_SERVER"]["ADDRESS"], reactor)