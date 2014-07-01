# Copyright (c) Jeroen Van Steirteghem
# See LICENSE

from twisted.internet import interfaces, reactor, ssl, tcp
from zope.interface import implements
import autobahn.twisted.websocket
import json
import twunnel.local_proxy_server
import twunnel.logger
import twunnel.proxy_server
import twunnel.remote_proxy_server__ssl

class WSOutputProtocol(twunnel.local_proxy_server.OutputProtocol):
    pass

class WSOutputProtocolFactory(twunnel.local_proxy_server.OutputProtocolFactory):
    protocol = WSOutputProtocol

class WSInputProtocol(autobahn.twisted.websocket.WebSocketServerProtocol):
    implements(interfaces.IPushProducer)
    
    def __init__(self):
        twunnel.logger.log(3, "trace: WSInputProtocol.__init__")
        
        self.configuration = None
        self.remoteAddress = ""
        self.remotePort = 0
        self.outputProtocol = None
        self.connectionState = 0
        self.message = ""
        self.messageState = 0
        
    def onOpen(self):
        twunnel.logger.log(3, "trace: WSInputProtocol.onOpen")
        
        self.connectionState = 1
        
    def onClose(self, wasClean, code, reason):
        twunnel.logger.log(3, "trace: WSInputProtocol.onClose")
        
        self.connectionState = 2
        
        if self.outputProtocol is not None:
            self.outputProtocol.inputProtocol_connectionLost(reason)
        
    def onMessage(self, message, binary):
        twunnel.logger.log(3, "trace: WSInputProtocol.onMessage")
        
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
        
    def processMessageState0(self):
        twunnel.logger.log(3, "trace: WSInputProtocol.processMessageState0")
        
        request = self.decodeMessage(self.message)
        
        supportedMethods = []
        if len(self.configuration["REMOTE_PROXY_SERVER"]["ACCOUNTS"]) == 0:
            supportedMethods.append(0x00)
        else:
            supportedMethods.append(0x02)
        
        for supportedMethod in supportedMethods:
            if supportedMethod in request["METHODS"]:
                if supportedMethod == 0x00:
                    response = {}
                    response["VERSION"] = 0x05
                    response["METHOD"] = 0x00
                    
                    message = self.encodeMessage(response)
                    
                    self.sendMessage(message, False)
                    
                    self.messageState = 2
                    
                    return True
                else:
                    if supportedMethod == 0x02:
                        response = {}
                        response["VERSION"] = 0x05
                        response["METHOD"] = 0x02
                        
                        message = self.encodeMessage(response)
                        
                        self.sendMessage(message, False)
                        
                        self.messageState = 1
                        
                        return True
        
        response = {}
        response["VERSION"] = 0x05
        response["METHOD"] = 0xFF
        
        message = self.encodeMessage(response)
        
        self.sendMessage(message, False)
        self.sendClose()
        
        return True
        
    def processMessageState1(self):
        twunnel.logger.log(3, "trace: WSInputProtocol.processMessageState1")
        
        request = self.decodeMessage(self.message)
        
        i = 0
        while i < len(self.configuration["REMOTE_PROXY_SERVER"]["ACCOUNTS"]):
            if self.configuration["REMOTE_PROXY_SERVER"]["ACCOUNTS"][i]["NAME"] == request["NAME"]:
                if self.configuration["REMOTE_PROXY_SERVER"]["ACCOUNTS"][i]["PASSWORD"] == request["PASSWORD"]:
                    response = {}
                    response["VERSION"] = 0x05
                    response["STATUS"] = 0x00
                    
                    message = self.encodeMessage(response)
                    
                    self.sendMessage(message, False)
                    
                    self.messageState = 2
                    
                    return True
                
                response = {}
                response["VERSION"] = 0x05
                response["STATUS"] = 0x01
                
                message = self.encodeMessage(response)
                
                self.sendMessage(message, False)
                self.sendClose()
                
                return True
            
            i = i + 1
        
        response = {}
        response["VERSION"] = 0x05
        response["STATUS"] = 0x01
        
        message = self.encodeMessage(response)
        
        self.sendMessage(message, False)
        self.sendClose()
        
        return True
        
    def processMessageState2(self):
        twunnel.logger.log(3, "trace: WSInputProtocol.processMessageState2")
        
        request = self.decodeMessage(self.message)
        
        self.remoteAddress = request["ADDRESS"]
        self.remotePort = request["PORT"]
        
        twunnel.logger.log(2, "remoteAddress: " + self.remoteAddress)
        twunnel.logger.log(2, "remotePort: " + str(self.remotePort))
        
        if request["METHOD"] == 0x01:
            outputProtocolFactory = WSOutputProtocolFactory(self)
            
            tunnel = twunnel.proxy_server.createTunnel(self.configuration)
            tunnel.connect(self.remoteAddress, self.remotePort, outputProtocolFactory)
            
            return True
        else:
            response = {}
            response["VERSION"] = 0x05
            response["STATUS"] = 0x07
            response["ADDRESS"] = 0
            response["PORT"] = 0
            
            message = self.encodeMessage(response)
            
            self.sendMessage(message, False)
            self.sendClose()
            
            return True
        
    def processMessageState3(self):
        twunnel.logger.log(3, "trace: WSInputProtocol.processMessageState3")
        
        if self.message == "":
            self.outputProtocol.resumeProducing()
            
            return True
        
        self.sendMessage("", True)
        
        self.outputProtocol.inputProtocol_dataReceived(self.message)
        
        return True
        
    def outputProtocol_connectionMade(self):
        twunnel.logger.log(3, "trace: WSInputProtocol.outputProtocol_connectionMade")
        
        if self.connectionState == 1:
            response = {}
            response["VERSION"] = 0x05
            response["STATUS"] = 0x00
            response["ADDRESS"] = 0
            response["PORT"] = 0
            
            message = self.encodeMessage(response)
            
            self.sendMessage(message, False)
            
            self.outputProtocol.inputProtocol_connectionMade()
            
            self.messageState = 3
        else:
            if self.connectionState == 2:
                self.outputProtocol.inputProtocol_connectionLost(None)
        
    def outputProtocol_connectionFailed(self, reason):
        twunnel.logger.log(3, "trace: WSInputProtocol.outputProtocol_connectionFailed")
        
        if self.connectionState == 1:
            response = {}
            response["VERSION"] = 0x05
            response["STATUS"] = 0x05
            response["ADDRESS"] = 0
            response["PORT"] = 0
            
            message = self.encodeMessage(response)
            
            self.sendMessage(message, False)
            self.sendClose()
        
    def outputProtocol_connectionLost(self, reason):
        twunnel.logger.log(3, "trace: WSInputProtocol.outputProtocol_connectionLost")
        
        if self.connectionState == 1:
            self.sendClose()
        else:
            if self.connectionState == 2:
                self.outputProtocol.inputProtocol_connectionLost(None)
        
    def outputProtocol_dataReceived(self, data):
        twunnel.logger.log(3, "trace: WSInputProtocol.outputProtocol_dataReceived")
        
        self.outputProtocol.pauseProducing()
        
        if self.connectionState == 1:
            self.sendMessage(data, True)
        else:
            if self.connectionState == 2:
                self.outputProtocol.inputProtocol_connectionLost(None)
        
    def pauseProducing(self):
        twunnel.logger.log(3, "trace: WSInputProtocol.pauseProducing")
        
        if self.connectionState == 1:
            self.transport.pauseProducing()
        
    def resumeProducing(self):
        twunnel.logger.log(3, "trace: WSInputProtocol.resumeProducing")
        
        if self.connectionState == 1:
            self.transport.resumeProducing()
    
    def stopProducing(self):
        twunnel.logger.log(3, "trace: WSInputProtocol.stopProducing")
        
        if self.connectionState == 1:
            self.transport.stopProducing()
        
    def encodeMessage(self, message):
        encoder = json.JSONEncoder()
        return encoder.encode(message)
        
    def decodeMessage(self, message):
        decoder = json.JSONDecoder()
        return decoder.decode(message)

class WSInputProtocolFactory(autobahn.twisted.websocket.WebSocketServerFactory):
    protocol = WSInputProtocol
    
    def __init__(self, configuration, *args, **kwargs):
        twunnel.logger.log(3, "trace: WSInputProtocolFactory.__init__")
        
        autobahn.twisted.websocket.WebSocketServerFactory.__init__(self, *args, **kwargs)
        
        self.configuration = configuration
    
    def buildProtocol(self, *args, **kwargs):
        twunnel.logger.log(3, "trace: WSInputProtocolFactory.buildProtocol")
        
        inputProtocol = autobahn.twisted.websocket.WebSocketServerFactory.buildProtocol(self, *args, **kwargs)
        inputProtocol.configuration = self.configuration
        return inputProtocol

def createWSPort(configuration):
    if configuration["REMOTE_PROXY_SERVER"]["TYPE"] == "WS":
        factory = WSInputProtocolFactory(configuration, "ws://" + str(configuration["REMOTE_PROXY_SERVER"]["ADDRESS"]) + ":" + str(configuration["REMOTE_PROXY_SERVER"]["PORT"]))
        
        return tcp.Port(configuration["REMOTE_PROXY_SERVER"]["PORT"], factory, 50, configuration["REMOTE_PROXY_SERVER"]["ADDRESS"], reactor)
    else:
        factory = WSInputProtocolFactory(configuration, "wss://" + str(configuration["REMOTE_PROXY_SERVER"]["ADDRESS"]) + ":" + str(configuration["REMOTE_PROXY_SERVER"]["PORT"]))
        
        contextFactory = twunnel.remote_proxy_server__ssl.SSLServerContextFactory(configuration["REMOTE_PROXY_SERVER"]["CERTIFICATE"]["FILE"], configuration["REMOTE_PROXY_SERVER"]["CERTIFICATE"]["KEY"]["FILE"])
        
        return ssl.Port(configuration["REMOTE_PROXY_SERVER"]["PORT"], factory, contextFactory, 50, configuration["REMOTE_PROXY_SERVER"]["ADDRESS"], reactor)