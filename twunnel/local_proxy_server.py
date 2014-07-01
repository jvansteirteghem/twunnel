# Copyright (c) Jeroen Van Steirteghem
# See LICENSE

from twisted.internet import interfaces, protocol, reactor
from zope.interface import implements
import twunnel.logger
import twunnel.proxy_server

def setDefaultConfiguration(configuration, keys):
    twunnel.proxy_server.setDefaultConfiguration(configuration, keys)
    
    if "LOCAL_PROXY_SERVER" in keys:
        configuration.setdefault("LOCAL_PROXY_SERVER", {})
        configuration["LOCAL_PROXY_SERVER"].setdefault("TYPE", "")
        if configuration["LOCAL_PROXY_SERVER"]["TYPE"] == "HTTPS":
            configuration["LOCAL_PROXY_SERVER"].setdefault("ADDRESS", "")
            configuration["LOCAL_PROXY_SERVER"].setdefault("PORT", 0)
        else:
            if configuration["LOCAL_PROXY_SERVER"]["TYPE"] == "SOCKS4":
                configuration["LOCAL_PROXY_SERVER"].setdefault("ADDRESS", "")
                configuration["LOCAL_PROXY_SERVER"].setdefault("PORT", 0)
            else:
                if configuration["LOCAL_PROXY_SERVER"]["TYPE"] == "SOCKS5":
                    configuration["LOCAL_PROXY_SERVER"].setdefault("ADDRESS", "")
                    configuration["LOCAL_PROXY_SERVER"].setdefault("PORT", 0)
                    configuration["LOCAL_PROXY_SERVER"].setdefault("ACCOUNTS", [])
                    i = 0
                    while i < len(configuration["LOCAL_PROXY_SERVER"]["ACCOUNTS"]):
                        configuration["LOCAL_PROXY_SERVER"]["ACCOUNTS"][i].setdefault("NAME", "")
                        configuration["LOCAL_PROXY_SERVER"]["ACCOUNTS"][i].setdefault("PASSWORD", "")
                        i = i + 1
    
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
                if configuration["REMOTE_PROXY_SERVERS"][i]["TYPE"] == "SSL":
                    configuration["REMOTE_PROXY_SERVERS"][i].setdefault("ADDRESS", "")
                    configuration["REMOTE_PROXY_SERVERS"][i].setdefault("PORT", 0)
                    configuration["REMOTE_PROXY_SERVERS"][i].setdefault("CERTIFICATE", {})
                    configuration["REMOTE_PROXY_SERVERS"][i]["CERTIFICATE"].setdefault("AUTHORITY", {})
                    configuration["REMOTE_PROXY_SERVERS"][i]["CERTIFICATE"]["AUTHORITY"].setdefault("FILE", "")
                    configuration["REMOTE_PROXY_SERVERS"][i].setdefault("ACCOUNT", {})
                    configuration["REMOTE_PROXY_SERVERS"][i]["ACCOUNT"].setdefault("NAME", "")
                    configuration["REMOTE_PROXY_SERVERS"][i]["ACCOUNT"].setdefault("PASSWORD", "")
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
        
    def buildProtocol(self, *args, **kwargs):
        twunnel.logger.log(3, "trace: OutputProtocolFactory.buildProtocol")
        
        outputProtocol = protocol.ClientFactory.buildProtocol(self, *args, **kwargs)
        outputProtocol.inputProtocol = self.inputProtocol
        outputProtocol.inputProtocol.outputProtocol = outputProtocol
        return outputProtocol
    
    def clientConnectionFailed(self, connector, reason):
        twunnel.logger.log(3, "trace: OutputProtocolFactory.clientConnectionFailed")
        
        self.inputProtocol.outputProtocol_connectionFailed(reason)

class OutputProtocolConnection(object):
    def __init__(self, configuration):
        twunnel.logger.log(3, "trace: OutputProtocolConnection.__init__")
        
        self.configuration = configuration
    
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
            configuration = {}
            configuration["PROXY_SERVERS"] = self.configuration["PROXY_SERVERS"]
            configuration["LOCAL_PROXY_SERVER"] = self.configuration["LOCAL_PROXY_SERVER"]
            
            outputProtocolConnection = OutputProtocolConnection(configuration)
            self.outputProtocolConnections.append(outputProtocolConnection)
        else:
            i = 0
            while i < len(self.configuration["REMOTE_PROXY_SERVERS"]):
                configuration = {}
                configuration["PROXY_SERVERS"] = self.configuration["PROXY_SERVERS"]
                configuration["LOCAL_PROXY_SERVER"] = self.configuration["LOCAL_PROXY_SERVER"]
                configuration["REMOTE_PROXY_SERVER"] = self.configuration["REMOTE_PROXY_SERVERS"][i]
                
                outputProtocolConnectionClass = self.getOutputProtocolConnectionClass(configuration["REMOTE_PROXY_SERVER"]["TYPE"])
                
                if outputProtocolConnectionClass is not None:
                    outputProtocolConnection = outputProtocolConnectionClass(configuration)
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
            from twunnel.local_proxy_server__ssh import SSHOutputProtocolConnection
            
            return SSHOutputProtocolConnection
        else:
            if type == "SSL":
                from twunnel.local_proxy_server__ssl import SSLOutputProtocolConnection
                
                return SSLOutputProtocolConnection
            else:
                if type == "WS":
                    from twunnel.local_proxy_server__ws import WSOutputProtocolConnection
                    
                    return WSOutputProtocolConnection
                else:
                    if type == "WSS":
                        from twunnel.local_proxy_server__ws import WSOutputProtocolConnection
                        
                        return WSOutputProtocolConnection
                    else:
                        return None

def createPort(configuration):
    setDefaultConfiguration(configuration, ["PROXY_SERVERS", "LOCAL_PROXY_SERVER", "REMOTE_PROXY_SERVERS"])
    
    outputProtocolConnectionManager = OutputProtocolConnectionManager(configuration)
    
    if configuration["LOCAL_PROXY_SERVER"]["TYPE"] == "HTTPS":
        from twunnel.local_proxy_server__https import createHTTPSPort
        
        return createHTTPSPort(configuration, outputProtocolConnectionManager)
    else:
        if configuration["LOCAL_PROXY_SERVER"]["TYPE"] == "SOCKS4":
            from twunnel.local_proxy_server__socks4 import createSOCKS4Port
            
            return createSOCKS4Port(configuration, outputProtocolConnectionManager)
        else:
            if configuration["LOCAL_PROXY_SERVER"]["TYPE"] == "SOCKS5":
                from twunnel.local_proxy_server__socks5 import createSOCKS5Port
                
                return createSOCKS5Port(configuration, outputProtocolConnectionManager)
            else:
                return None