# Copyright (c) Jeroen Van Steirteghem
# See LICENSE

from twisted.internet import interfaces
from zope.interface import implements
import autobahn.twisted.websocket
import json
import twunnel.local_proxy_server__ssl
import twunnel.logger
import twunnel.proxy_server

class WSOutputProtocol(autobahn.twisted.websocket.WebSocketClientProtocol):
    implements(interfaces.IPushProducer)
    
    def __init__(self):
        twunnel.logger.log(3, "trace: WSOutputProtocol.__init__")
        
        self.configuration = None
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
        request["VERSION"] = 0x05
        request["METHODS"] = [0x00, 0x02]
        
        message = self.encodeMessage(request)
        
        self.sendMessage(message, False)
        
        self.messageState = 0
        
    def onClose(self, wasClean, code, reason):
        twunnel.logger.log(3, "trace: WSOutputProtocol.onClose")
        
        self.connectionState = 2
        
        self.inputProtocol.outputProtocol_connectionLost(reason)
        
    def onMessage(self, message, binary):
        twunnel.logger.log(3, "trace: WSOutputProtocol.onMessage")
        
        self.message = message
        if self.messageState == 0:
            if self.processMessageState0():
                return
        if self.messageState == 1:
            if self.processMessageState1():
                return
        if self.messageState == 2:
            if self.processMessageState2():
                return
        if self.messageState == 3:
            if self.processMessageState3():
                return
        if self.messageState == 4:
            if self.processMessageState4():
                return
        
    def processMessageState0(self):
        twunnel.logger.log(3, "trace: WSOutputProtocol.processMessageState0")
        
        response = self.decodeMessage(self.message)
        
        if response["METHOD"] == 0x00:
            self.messageState = 2
            
            return False
        else:
            if response["METHOD"] == 0x02:
                request = {}
                request["VERSION"] = 0x01
                request["NAME"] = self.factory.configuration["REMOTE_PROXY_SERVER"]["ACCOUNT"]["NAME"]
                request["PASSWORD"] = self.factory.configuration["REMOTE_PROXY_SERVER"]["ACCOUNT"]["PASSWORD"]
                
                message = self.encodeMessage(request)
                
                self.sendMessage(message, False)
                
                self.messageState = 1
                
                return True
            else:
                self.sendClose()
                
                return True
        
    def processMessageState1(self):
        twunnel.logger.log(3, "trace: WSOutputProtocol.processMessageState1")
        
        response = self.decodeMessage(self.message)
        
        if response["STATUS"] != 0x00:
            self.sendClose()
            
            return True
        
        self.messageState = 2
        
        return False
        
    def processMessageState2(self):
        twunnel.logger.log(3, "trace: WSOutputProtocol.processMessageState2")
        
        request = {}
        request["VERSION"] = 0x05
        request["METHOD"] = 0x01
        request["ADDRESS"] = self.remoteAddress
        request["PORT"] = self.remotePort
        
        message = self.encodeMessage(request)
        
        self.sendMessage(message, False)
        
        self.messageState = 3
        
        return True
        
    def processMessageState3(self):
        twunnel.logger.log(3, "trace: WSOutputProtocol.processMessageState3")
        
        response = self.decodeMessage(self.message)
        
        if response["STATUS"] != 0x00:
            self.sendClose()
            
            return True
        
        self.inputProtocol.outputProtocol_connectionMade()
        
        self.messageState = 4
        
        return True
        
    def processMessageState4(self):
        twunnel.logger.log(3, "trace: WSOutputProtocol.processMessageState4")
        
        if self.message == "":
            self.inputProtocol.resumeProducing()
            
            return True
        
        self.sendMessage("", True)
        
        self.inputProtocol.outputProtocol_dataReceived(self.message)
        
        return True
        
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
        
    def encodeMessage(self, message):
        encoder = json.JSONEncoder()
        return encoder.encode(message)
        
    def decodeMessage(self, message):
        decoder = json.JSONDecoder()
        return decoder.decode(message)

class WSOutputProtocolFactory(autobahn.twisted.websocket.WebSocketClientFactory):
    protocol = WSOutputProtocol
    
    def __init__(self, configuration, remoteAddress, remotePort, inputProtocol, *args, **kwargs):
        twunnel.logger.log(3, "trace: WSOutputProtocolFactory.__init__")
        
        autobahn.twisted.websocket.WebSocketClientFactory.__init__(self, *args, **kwargs)
        
        self.configuration = configuration
        self.remoteAddress = remoteAddress
        self.remotePort = remotePort
        self.inputProtocol = inputProtocol
        
    def buildProtocol(self, *args, **kwargs):
        twunnel.logger.log(3, "trace: WSOutputProtocolFactory.buildProtocol")
        
        outputProtocol = autobahn.twisted.websocket.WebSocketClientFactory.buildProtocol(self, *args, **kwargs)
        outputProtocol.configuration = self.configuration
        outputProtocol.remoteAddress = self.remoteAddress
        outputProtocol.remotePort = self.remotePort
        outputProtocol.inputProtocol = self.inputProtocol
        outputProtocol.inputProtocol.outputProtocol = outputProtocol
        return outputProtocol
        
    def clientConnectionFailed(self, connector, reason):
        twunnel.logger.log(3, "trace: WSOutputProtocolFactory.clientConnectionFailed")
        
        self.inputProtocol.outputProtocol_connectionFailed(reason)

class WSOutputProtocolConnection(object):
    def __init__(self, configuration):
        twunnel.logger.log(3, "trace: WSOutputProtocolConnection.__init__")
        
        self.configuration = configuration
        
    def connect(self, remoteAddress, remotePort, inputProtocol):
        twunnel.logger.log(3, "trace: WSOutputProtocolConnection.connect")
        
        if self.configuration["REMOTE_PROXY_SERVER"]["TYPE"] == "WS":
            factory = WSOutputProtocolFactory(self.configuration, remoteAddress, remotePort, inputProtocol, "ws://" + str(self.configuration["REMOTE_PROXY_SERVER"]["ADDRESS"]) + ":" + str(self.configuration["REMOTE_PROXY_SERVER"]["PORT"]))
            
            tunnel = twunnel.proxy_server.createTunnel(self.configuration)
            tunnel.connect(self.configuration["REMOTE_PROXY_SERVER"]["ADDRESS"], self.configuration["REMOTE_PROXY_SERVER"]["PORT"], factory)
        else:
            factory = WSOutputProtocolFactory(self.configuration, remoteAddress, remotePort, inputProtocol, "wss://" + str(self.configuration["REMOTE_PROXY_SERVER"]["ADDRESS"]) + ":" + str(self.configuration["REMOTE_PROXY_SERVER"]["PORT"]))
            
            contextFactory = twunnel.local_proxy_server__ssl.SSLClientContextFactory(self.configuration["REMOTE_PROXY_SERVER"]["CERTIFICATE"]["AUTHORITY"]["FILE"])
            
            tunnel = twunnel.proxy_server.createTunnel(self.configuration)
            tunnel.connect(self.configuration["REMOTE_PROXY_SERVER"]["ADDRESS"], self.configuration["REMOTE_PROXY_SERVER"]["PORT"], factory, contextFactory)
    
    def startConnection(self):
        twunnel.logger.log(3, "trace: WSOutputProtocolConnection.startConnection")
    
    def stopConnection(self):
        twunnel.logger.log(3, "trace: WSOutputProtocolConnection.stopConnection")