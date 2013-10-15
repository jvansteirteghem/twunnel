# Copyright (c) Jeroen Van Steirteghem
# See LICENSE

from zope.interface import implements
from twisted.internet import interfaces, reactor, ssl, tcp
import json
import logging
import autobahn.websocket
import twunnel.local

logger = logging.getLogger(__name__)

class WSOutputProtocol(twunnel.local.OutputProtocol):
    pass

class WSOutputProtocolFactory(twunnel.local.OutputProtocolFactory):
    protocol = WSOutputProtocol

class WSInputProtocol(autobahn.websocket.WebSocketServerProtocol):
    implements(interfaces.IPushProducer)
    
    def __init__(self):
        logger.debug("WSInputProtocol.__init__")
        
        self.configuration = None
        self.remoteAddress = ""
        self.remotePort = 0
        self.outputProtocol = None
        self.connectionState = 0
        self.message = ""
        self.messageState = 0
    
    def onOpen(self):
        logger.debug("WSInputProtocol.onOpen")
        
        self.connectionState = 1

    def onClose(self, wasClean, code, reason):
        logger.debug("WSInputProtocol.onClose")
        
        self.connectionState = 2
        
        if self.outputProtocol is not None:
            self.outputProtocol.inputProtocol_connectionLost(reason)
            
    def onMessage(self, message, binary):
        logger.debug("WSInputProtocol.onMessage")
        
        self.message = self.message + message
        if self.messageState == 0:
            self.processMessageState0()
            return
        if self.messageState == 1:
            self.processMessageState1()
            return
    
    def processMessageState0(self):
        logger.debug("WSInputProtocol.processMessageState0")
        
        decoder = json.JSONDecoder()
        request = decoder.decode(self.message)
        
        authorized = False;

        if len(self.configuration["REMOTE_PROXY_SERVER"]["ACCOUNTS"]) == 0:
            authorized = True
        
        if authorized == False:
            i = 0
            while i < len(self.configuration["REMOTE_PROXY_SERVER"]["ACCOUNTS"]):
                if self.configuration["REMOTE_PROXY_SERVER"]["ACCOUNTS"][i]["NAME"] == request["REMOTE_PROXY_SERVER"]["ACCOUNT"]["NAME"] and self.configuration["REMOTE_PROXY_SERVER"]["ACCOUNTS"][i]["PASSWORD"] == request["REMOTE_PROXY_SERVER"]["ACCOUNT"]["PASSWORD"]:
                    authorized = True
                    break
                
                i = i + 1
        
        if authorized == False:
            self.sendClose()
            
            return
        
        self.remoteAddress = request["REMOTE_ADDRESS"]
        self.remotePort = request["REMOTE_PORT"]
        
        logger.debug("WSInputProtocol.remoteAddress: " + self.remoteAddress)
        logger.debug("WSInputProtocol.remotePort: " + str(self.remotePort))
        
        outputProtocolFactory = WSOutputProtocolFactory(self)
        
        tunnelClass = twunnel.local.getDefaultTunnelClass()
        tunnel = tunnelClass(self.configuration)
        tunnel.connect(self.remoteAddress, self.remotePort, outputProtocolFactory)
    
    def processMessageState1(self):
        logger.debug("WSInputProtocol.processMessageState1")
        
        if len(self.message) == 0:
            self.outputProtocol.resumeProducing()
            return
        
        self.sendMessage("", True)
        
        self.outputProtocol.inputProtocol_dataReceived(self.message)
        
        self.message = ""
        
    def outputProtocol_connectionMade(self):
        logger.debug("WSInputProtocol.outputProtocol_connectionMade")
        
        if self.connectionState == 1:
            response = {}
            response["REMOTE_ADDRESS"] = self.remoteAddress
            response["REMOTE_PORT"] = self.remotePort
            
            encoder = json.JSONEncoder()
            message = encoder.encode(response)
            
            self.sendMessage(message, False)
            
            self.outputProtocol.inputProtocol_connectionMade()
            
            self.message = ""
            self.messageState = 1
        else:
            if self.connectionState == 2:
                self.outputProtocol.inputProtocol_connectionLost(None)
        
    def outputProtocol_connectionFailed(self, reason):
        logger.debug("WSInputProtocol.outputProtocol_connectionFailed")
        
        if self.connectionState == 1:
            self.sendClose()
        
    def outputProtocol_connectionLost(self, reason):
        logger.debug("WSInputProtocol.outputProtocol_connectionLost")
        
        if self.connectionState == 1:
            self.sendClose()
        else:
            if self.connectionState == 2:
                self.outputProtocol.inputProtocol_connectionLost(None)
        
    def outputProtocol_dataReceived(self, data):
        logger.debug("WSInputProtocol.outputProtocol_dataReceived")
        
        self.outputProtocol.pauseProducing()
        
        if self.connectionState == 1:
            self.sendMessage(data, True)
        else:
            if self.connectionState == 2:
                self.outputProtocol.inputProtocol_connectionLost(None)
    
    def pauseProducing(self):
        logger.debug("WSInputProtocol.pauseProducing")
        
        if self.connectionState == 1:
            self.transport.pauseProducing()
    
    def resumeProducing(self):
        logger.debug("WSInputProtocol.resumeProducing")
        
        if self.connectionState == 1:
            self.transport.resumeProducing()
    
    def stopProducing(self):
        logger.debug("WSInputProtocol.stopProducing")
        
        if self.connectionState == 1:
            self.transport.stopProducing()

class WSInputProtocolFactory(autobahn.websocket.WebSocketServerFactory):
    protocol = WSInputProtocol
    
    def __init__(self, configuration, *args, **kwargs):
        logger.debug("WSInputProtocolFactory.__init__")
        
        autobahn.websocket.WebSocketServerFactory.__init__(self, *args, **kwargs)
        
        self.configuration = configuration
    
    def buildProtocol(self, *args, **kwargs):
        inputProtocol = autobahn.websocket.WebSocketServerFactory.buildProtocol(self, *args, **kwargs)
        inputProtocol.configuration = self.configuration
        return inputProtocol

def createPort(configuration):
    if configuration["REMOTE_PROXY_SERVER"]["TYPE"] == "WS":
        factory = WSInputProtocolFactory(configuration, "ws://" + str(configuration["REMOTE_PROXY_SERVER"]["ADDRESS"]) + ":" + str(configuration["REMOTE_PROXY_SERVER"]["PORT"]))
        
        return tcp.Port(configuration["REMOTE_PROXY_SERVER"]["PORT"], factory, 50, configuration["REMOTE_PROXY_SERVER"]["ADDRESS"], reactor)
    else:
        factory = WSInputProtocolFactory(configuration, "wss://" + str(configuration["REMOTE_PROXY_SERVER"]["ADDRESS"]) + ":" + str(configuration["REMOTE_PROXY_SERVER"]["PORT"]))
        
        contextFactory = ssl.DefaultOpenSSLContextFactory(configuration["REMOTE_PROXY_SERVER"]["CERTIFICATE"]["KEY"]["FILE"], configuration["REMOTE_PROXY_SERVER"]["CERTIFICATE"]["FILE"])
        
        return ssl.Port(configuration["REMOTE_PROXY_SERVER"]["PORT"], factory, contextFactory, 50, configuration["REMOTE_PROXY_SERVER"]["ADDRESS"], reactor)