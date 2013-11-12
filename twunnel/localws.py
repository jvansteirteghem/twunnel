# Copyright (c) Jeroen Van Steirteghem
# See LICENSE

from zope.interface import implements
from twisted.internet import interfaces, reactor, ssl, tcp
import OpenSSL
import json
import logging
import autobahn.websocket
import twunnel.local

logger = logging.getLogger(__name__)

class WSOutputProtocol(autobahn.websocket.WebSocketClientProtocol):
    implements(interfaces.IPushProducer)
    
    def __init__(self):
        logger.debug("WSOutputProtocol.__init__")
        
        self.configuration = None
        self.i = 0
        self.remoteAddress = ""
        self.remotePort = 0
        self.inputProtocol = None
        self.connectionState = 0
        self.message = ""
        self.messageState = 0
        
    def onOpen(self):
        logger.debug("WSOutputProtocol.onOpen")
        
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
        logger.debug("WSOutputProtocol.onClose")
        
        self.connectionState = 2
        
        self.inputProtocol.outputProtocol_connectionLost(reason)
        
    def onMessage(self, message, binary):
        logger.debug("WSOutputProtocol.onMessage")
        
        self.message = self.message + message
        if self.messageState == 0:
            self.processMessageState0();
            return
        if self.messageState == 1:
            self.processMessageState1();
            return
        
    def processMessageState0(self):
        logger.debug("WSOutputProtocol.processMessageState0")
        
        decoder = json.JSONDecoder()
        response = decoder.decode(self.message)
        
        self.inputProtocol.outputProtocol_connectionMade()
        
        self.message = ""
        self.messageState = 1
        
    def processMessageState1(self):
        logger.debug("WSOutputProtocol.processMessageState1")
        
        if len(self.message) == 0:
            self.inputProtocol.resumeProducing()
            return
        
        self.sendMessage("", True)
        
        self.inputProtocol.outputProtocol_dataReceived(self.message)
        
        self.message = ""
        
    def inputProtocol_connectionMade(self):
        logger.debug("WSOutputProtocol.inputProtocol_connectionMade")
        
    def inputProtocol_connectionLost(self, reason):
        logger.debug("WSOutputProtocol.inputProtocol_connectionLost")
        
        if self.connectionState == 1:
            self.sendClose()
        
    def inputProtocol_dataReceived(self, data):
        logger.debug("WSOutputProtocol.inputProtocol_dataReceived")
        
        self.inputProtocol.pauseProducing()
        
        if self.connectionState == 1:
            self.sendMessage(data, True)
    
    def pauseProducing(self):
        logger.debug("WSOutputProtocol.pauseProducing")
        
        if self.connectionState == 1:
            self.transport.pauseProducing()
    
    def resumeProducing(self):
        logger.debug("WSOutputProtocol.resumeProducing")
        
        if self.connectionState == 1:
            self.transport.resumeProducing()
    
    def stopProducing(self):
        logger.debug("WSOutputProtocol.stopProducing")
        
        if self.connectionState == 1:
            self.transport.stopProducing()

class WSOutputProtocolFactory(autobahn.websocket.WebSocketClientFactory):
    protocol = WSOutputProtocol
    
    def __init__(self, configuration, i, remoteAddress, remotePort, inputProtocol, *args, **kwargs):
        logger.debug("WSOutputProtocolFactory.__init__")
        
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
        logger.debug("WSOutputProtocolFactory.clientConnectionFailed")
        
        self.inputProtocol.outputProtocol_connectionFailed(reason)

class ClientContextFactory(ssl.ClientContextFactory):
    def __init__(self, verify_locations):
        logger.debug("ClientContextFactory.__init__")
        
        self.verify_locations = verify_locations
        
    def getContext(self):
        logger.debug("ClientContextFactory.getContext")
        
        self.method = OpenSSL.SSL.TLSv1_METHOD
        
        context = ssl.ClientContextFactory.getContext(self)
        context.load_verify_locations(self.verify_locations)
        context.set_verify(OpenSSL.SSL.VERIFY_PEER | OpenSSL.SSL.VERIFY_FAIL_IF_NO_PEER_CERT, self.verify)
        
        return context
        
    def verify(self, connection, certificate, errorNumber, errorDepth, certificateOk):
        logger.debug("ClientContextFactory.verify")
        
        if certificateOk:
            logger.debug("ClientContextFactory: certificate ok")
        else:
            logger.debug("ClientContextFactory: certificate not ok")
        
        return certificateOk

class WSOutputProtocolConnection(object):
    def __init__(self, configuration, i):
        logger.debug("WSOutputProtocolConnection.__init__")
        
        self.configuration = configuration
        self.i = i
        
    def connect(self, remoteAddress, remotePort, inputProtocol):
        logger.debug("WSOutputProtocolConnection.connect")
        
        if self.configuration["REMOTE_PROXY_SERVERS"][self.i]["TYPE"] == "WS":
            factory = WSOutputProtocolFactory(self.configuration, self.i, remoteAddress, remotePort, inputProtocol, "ws://" + str(self.configuration["REMOTE_PROXY_SERVERS"][self.i]["ADDRESS"]) + ":" + str(self.configuration["REMOTE_PROXY_SERVERS"][self.i]["PORT"]))
            
            tunnel = twunnel.local.createTunnel(self.configuration)
            tunnel.connect(self.configuration["REMOTE_PROXY_SERVERS"][self.i]["ADDRESS"], self.configuration["REMOTE_PROXY_SERVERS"][self.i]["PORT"], factory)
        else:
            factory = WSOutputProtocolFactory(self.configuration, self.i, remoteAddress, remotePort, inputProtocol, "wss://" + str(self.configuration["REMOTE_PROXY_SERVERS"][self.i]["ADDRESS"]) + ":" + str(self.configuration["REMOTE_PROXY_SERVERS"][self.i]["PORT"]))
            
            if self.configuration["REMOTE_PROXY_SERVERS"][self.i]["CERTIFICATE"]["AUTHORITY"]["FILE"] != "":
                contextFactory = ClientContextFactory(self.configuration["REMOTE_PROXY_SERVERS"][self.i]["CERTIFICATE"]["AUTHORITY"]["FILE"])
            else:
                contextFactory = ssl.ClientContextFactory()
            
            tunnel = twunnel.local.createTunnel(self.configuration)
            tunnel.connect(self.configuration["REMOTE_PROXY_SERVERS"][self.i]["ADDRESS"], self.configuration["REMOTE_PROXY_SERVERS"][self.i]["PORT"], factory, contextFactory)
    
    def startConnection(self):
        logger.debug("WSOutputProtocolConnection.startConnection")
    
    def stopConnection(self):
        logger.debug("WSOutputProtocolConnection.stopConnection")