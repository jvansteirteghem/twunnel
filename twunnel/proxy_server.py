# Copyright (c) Jeroen Van Steirteghem
# See LICENSE

from twisted.internet import protocol, reactor
import twunnel.logger

def setDefaultConfiguration(configuration, keys):
    if "PROXY_SERVERS" in keys:
        configuration.setdefault("PROXY_SERVERS", [])
        i = 0
        while i < len(configuration["PROXY_SERVERS"]):
            configuration["PROXY_SERVERS"][i].setdefault("TYPE", "")
            if configuration["PROXY_SERVERS"][i]["TYPE"] == "HTTPS":
                configuration["PROXY_SERVERS"][i].setdefault("ADDRESS", "")
                configuration["PROXY_SERVERS"][i].setdefault("PORT", 0)
                configuration["PROXY_SERVERS"][i].setdefault("ACCOUNT", {})
                configuration["PROXY_SERVERS"][i]["ACCOUNT"].setdefault("NAME", "")
                configuration["PROXY_SERVERS"][i]["ACCOUNT"].setdefault("PASSWORD", "")
            else:
                if configuration["PROXY_SERVERS"][i]["TYPE"] == "SOCKS4":
                    configuration["PROXY_SERVERS"][i].setdefault("ADDRESS", "")
                    configuration["PROXY_SERVERS"][i].setdefault("PORT", 0)
                    configuration["PROXY_SERVERS"][i].setdefault("ACCOUNT", {})
                    configuration["PROXY_SERVERS"][i]["ACCOUNT"].setdefault("NAME", "")
                else:
                    if configuration["PROXY_SERVERS"][i]["TYPE"] == "SOCKS5":
                        configuration["PROXY_SERVERS"][i].setdefault("ADDRESS", "")
                        configuration["PROXY_SERVERS"][i].setdefault("PORT", 0)
                        configuration["PROXY_SERVERS"][i].setdefault("ACCOUNT", {})
                        configuration["PROXY_SERVERS"][i]["ACCOUNT"].setdefault("NAME", "")
                        configuration["PROXY_SERVERS"][i]["ACCOUNT"].setdefault("PASSWORD", "")
            i = i + 1

class TunnelProtocol(protocol.Protocol):
    def __init__(self):
        twunnel.logger.log(3, "trace: TunnelProtocol.__init__")
    
    def connectionMade(self):
        twunnel.logger.log(3, "trace: TunnelProtocol.connectionMade")
        
        self.factory.tunnelOutputProtocolFactory.tunnelProtocol = self
        self.factory.tunnelOutputProtocol = self.factory.tunnelOutputProtocolFactory.buildProtocol(self.transport.getPeer())
        self.factory.tunnelOutputProtocol.makeConnection(self.transport)
    
    def connectionLost(self, reason):
        twunnel.logger.log(3, "trace: TunnelProtocol.connectionLost")
        
        if self.factory.tunnelOutputProtocol is not None:
            self.factory.tunnelOutputProtocol.connectionLost(reason)
        else:
            if self.factory.outputProtocol is not None:
                self.factory.outputProtocol.connectionLost(reason)
    
    def dataReceived(self, data):
        twunnel.logger.log(3, "trace: TunnelProtocol.dataReceived")
        
        if self.factory.tunnelOutputProtocol is not None:
            self.factory.tunnelOutputProtocol.dataReceived(data)
        else:
            if self.factory.outputProtocol is not None:
                self.factory.outputProtocol.dataReceived(data)
    
    def tunnelOutputProtocol_connectionMade(self, data):
        twunnel.logger.log(3, "trace: TunnelProtocol.tunnelOutputProtocol_connectionMade")
        
        self.factory.tunnelOutputProtocol = None
        
        if self.factory.contextFactory is not None:
            self.transport.startTLS(self.factory.contextFactory)
        
        self.factory.outputProtocol = self.factory.outputProtocolFactory.buildProtocol(self.transport.getPeer())
        self.factory.outputProtocol.makeConnection(self.transport)
        
        if len(data) > 0:
            self.factory.outputProtocol.dataReceived(data)

class TunnelProtocolFactory(protocol.ClientFactory):
    protocol = TunnelProtocol
    
    def __init__(self, outputProtocolFactory, tunnelOutputProtocolFactory, contextFactory=None):
        twunnel.logger.log(3, "trace: TunnelProtocolFactory.__init__")
        
        self.outputProtocol = None
        self.outputProtocolFactory = outputProtocolFactory
        self.tunnelOutputProtocol = None
        self.tunnelOutputProtocolFactory = tunnelOutputProtocolFactory
        self.contextFactory = contextFactory
    
    def startedConnecting(self, connector):
        twunnel.logger.log(3, "trace: TunnelProtocolFactory.startedConnecting")
        
        self.outputProtocolFactory.startedConnecting(connector)
    
    def clientConnectionFailed(self, connector, reason):
        twunnel.logger.log(3, "trace: TunnelProtocolFactory.clientConnectionFailed")
        
        self.outputProtocolFactory.clientConnectionFailed(connector, reason)
    
    def clientConnectionLost(self, connector, reason):
        twunnel.logger.log(3, "trace: TunnelProtocolFactory.clientConnectionLost")
        
        if self.outputProtocol is None:
            self.outputProtocolFactory.clientConnectionFailed(connector, reason)
        else:
            self.outputProtocolFactory.clientConnectionLost(connector, reason)

class Tunnel(object):
    def __init__(self, configuration):
        twunnel.logger.log(3, "trace: Tunnel.__init__")
        
        self.configuration = configuration
    
    def connect(self, address, port, outputProtocolFactory, contextFactory=None, timeout=30, bindAddress=None):
        twunnel.logger.log(3, "trace: Tunnel.connect")
        
        if len(self.configuration["PROXY_SERVERS"]) == 0:
            if contextFactory is None:
                return reactor.connectTCP(address, port, outputProtocolFactory, timeout, bindAddress)
            else:
                return reactor.connectSSL(address, port, outputProtocolFactory, contextFactory, timeout, bindAddress)
        else:
            i = len(self.configuration["PROXY_SERVERS"])
            
            configuration = {}
            configuration["PROXY_SERVER"] = self.configuration["PROXY_SERVERS"][i - 1]
            
            tunnelOutputProtocolFactoryClass = self.getTunnelOutputProtocolFactoryClass(configuration["PROXY_SERVER"]["TYPE"])
            tunnelOutputProtocolFactory = tunnelOutputProtocolFactoryClass(configuration, address, port)
            
            tunnelProtocolFactory = TunnelProtocolFactory(outputProtocolFactory, tunnelOutputProtocolFactory, contextFactory)
            
            i = i - 1
            
            while i > 0:
                configuration = {}
                configuration["PROXY_SERVER"] = self.configuration["PROXY_SERVERS"][i - 1]
                
                tunnelOutputProtocolFactoryClass = self.getTunnelOutputProtocolFactoryClass(configuration["PROXY_SERVER"]["TYPE"])
                tunnelOutputProtocolFactory = tunnelOutputProtocolFactoryClass(configuration, self.configuration["PROXY_SERVERS"][i]["ADDRESS"], self.configuration["PROXY_SERVERS"][i]["PORT"])
                
                tunnelProtocolFactory = TunnelProtocolFactory(tunnelProtocolFactory, tunnelOutputProtocolFactory)
                
                i = i - 1
            
            return reactor.connectTCP(self.configuration["PROXY_SERVERS"][i]["ADDRESS"], self.configuration["PROXY_SERVERS"][i]["PORT"], tunnelProtocolFactory, timeout, bindAddress)
    
    def getTunnelOutputProtocolFactoryClass(self, type):
        twunnel.logger.log(3, "trace: Tunnel.getTunnelOutputProtocolFactoryClass")
        
        if type == "HTTPS":
            from twunnel.proxy_server__https import HTTPSTunnelOutputProtocolFactory
            
            return HTTPSTunnelOutputProtocolFactory
        else:
            if type == "SOCKS4":
                from twunnel.proxy_server__socks4 import SOCKS4TunnelOutputProtocolFactory
                
                return SOCKS4TunnelOutputProtocolFactory
            else:
                if type == "SOCKS5":
                    from twunnel.proxy_server__socks5 import SOCKS5TunnelOutputProtocolFactory
                    
                    return SOCKS5TunnelOutputProtocolFactory
                else:
                    return None

defaultTunnelClass = Tunnel

def getDefaultTunnelClass():
    global defaultTunnelClass
    
    return defaultTunnelClass

def setDefaultTunnelClass(tunnelClass):
    global defaultTunnelClass
    
    defaultTunnelClass = tunnelClass

def createTunnel(configuration):
    setDefaultConfiguration(configuration, ["PROXY_SERVERS"])
    
    tunnelClass = getDefaultTunnelClass()
    tunnel = tunnelClass(configuration)
    
    return tunnel

class TunnelReactor(object):
    def __init__(self, tunnel):
        twunnel.logger.log(3, "trace: TunnelReactor.__init__")
        
        self.tunnel = tunnel
    
    def connectTCP(self, host, port, factory, timeout=30, bindAddress=None):
        twunnel.logger.log(3, "trace: TunnelReactor.connectTCP")
        
        self.tunnel.connect(host, port, factory, None, timeout, bindAddress)
    
    def connectSSL(self, host, port, factory, contextFactory, timeout=30, bindAddress=None):
        twunnel.logger.log(3, "trace: TunnelReactor.connectSSL")
        
        self.tunnel.connect(host, port, factory, contextFactory, timeout, bindAddress)
    
    def __getattr__(self, attr):
        twunnel.logger.log(3, "trace: TunnelReactor.__getattr__")
        
        return getattr(reactor, attr)

def createTunnelReactor(configuration):
    tunnel = createTunnel(configuration)
    
    tunnelReactor = TunnelReactor(tunnel)
    
    return tunnelReactor