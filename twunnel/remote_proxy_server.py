# Copyright (c) Jeroen Van Steirteghem
# See LICENSE

from twisted.conch import avatar
from twisted.conch.error import ValidPublicKey
from twisted.conch.ssh import channel, factory, forwarding, keys
from twisted.cred import checkers, credentials, portal
from twisted.cred.error import UnauthorizedLogin
from twisted.internet import defer, interfaces, reactor, ssl, tcp
from zope.interface import implements
import autobahn.websocket
import json
import twunnel.local_proxy_server
import twunnel.logger
import twunnel.proxy_server

def setDefaultConfiguration(configuration, keys):
    twunnel.proxy_server.setDefaultConfiguration(configuration, keys)
    
    if "REMOTE_PROXY_SERVER" in keys:
        configuration.setdefault("REMOTE_PROXY_SERVER", {})
        configuration["REMOTE_PROXY_SERVER"].setdefault("TYPE", "")
        if configuration["REMOTE_PROXY_SERVER"]["TYPE"] == "SSH":
            configuration["REMOTE_PROXY_SERVER"].setdefault("ADDRESS", "")
            configuration["REMOTE_PROXY_SERVER"].setdefault("PORT", 0)
            configuration["REMOTE_PROXY_SERVER"].setdefault("KEY", {})
            configuration["REMOTE_PROXY_SERVER"]["KEY"].setdefault("PUBLIC", {})
            configuration["REMOTE_PROXY_SERVER"]["KEY"]["PUBLIC"].setdefault("FILE", "")
            configuration["REMOTE_PROXY_SERVER"]["KEY"]["PUBLIC"].setdefault("PASSPHRASE", "")
            configuration["REMOTE_PROXY_SERVER"]["KEY"].setdefault("PRIVATE", {})
            configuration["REMOTE_PROXY_SERVER"]["KEY"]["PRIVATE"].setdefault("FILE", "")
            configuration["REMOTE_PROXY_SERVER"]["KEY"]["PRIVATE"].setdefault("PASSPHRASE", "")
            configuration["REMOTE_PROXY_SERVER"].setdefault("ACCOUNTS", [])
            i = 0
            while i < len(configuration["REMOTE_PROXY_SERVER"]["ACCOUNTS"]):
                configuration["REMOTE_PROXY_SERVER"]["ACCOUNTS"][i].setdefault("NAME", "")
                configuration["REMOTE_PROXY_SERVER"]["ACCOUNTS"][i].setdefault("PASSWORD", "")
                configuration["REMOTE_PROXY_SERVER"]["ACCOUNTS"][i].setdefault("KEYS", [])
                j = 0
                while j < len(configuration["REMOTE_PROXY_SERVER"]["ACCOUNTS"][i]["KEYS"]):
                    configuration["REMOTE_PROXY_SERVER"]["ACCOUNTS"][i]["KEYS"][j].setdefault("PUBLIC", {})
                    configuration["REMOTE_PROXY_SERVER"]["ACCOUNTS"][i]["KEYS"][j]["PUBLIC"].setdefault("FILE", "")
                    configuration["REMOTE_PROXY_SERVER"]["ACCOUNTS"][i]["KEYS"][j]["PUBLIC"].setdefault("PASSPHRASE", "")
                    j = j + 1
                configuration["REMOTE_PROXY_SERVER"]["ACCOUNTS"][i].setdefault("CONNECTIONS", 0)
                i = i + 1
        else:
            if configuration["REMOTE_PROXY_SERVER"]["TYPE"] == "WS":
                configuration["REMOTE_PROXY_SERVER"].setdefault("ADDRESS", "")
                configuration["REMOTE_PROXY_SERVER"].setdefault("PORT", 0)
                configuration["REMOTE_PROXY_SERVER"].setdefault("ACCOUNTS", [])
                i = 0
                while i < len(configuration["REMOTE_PROXY_SERVER"]["ACCOUNTS"]):
                    configuration["REMOTE_PROXY_SERVER"]["ACCOUNTS"][i].setdefault("NAME", "")
                    configuration["REMOTE_PROXY_SERVER"]["ACCOUNTS"][i].setdefault("PASSWORD", "")
                    i = i + 1
            else:
                if configuration["REMOTE_PROXY_SERVER"]["TYPE"] == "WSS":
                    configuration["REMOTE_PROXY_SERVER"].setdefault("ADDRESS", "")
                    configuration["REMOTE_PROXY_SERVER"].setdefault("PORT", 0)
                    configuration["REMOTE_PROXY_SERVER"].setdefault("CERTIFICATE", {})
                    configuration["REMOTE_PROXY_SERVER"]["CERTIFICATE"].setdefault("FILE", "")
                    configuration["REMOTE_PROXY_SERVER"]["CERTIFICATE"].setdefault("KEY", {})
                    configuration["REMOTE_PROXY_SERVER"]["CERTIFICATE"]["KEY"].setdefault("FILE", "")
                    configuration["REMOTE_PROXY_SERVER"].setdefault("ACCOUNTS", [])
                    i = 0
                    while i < len(configuration["REMOTE_PROXY_SERVER"]["ACCOUNTS"]):
                        configuration["REMOTE_PROXY_SERVER"]["ACCOUNTS"][i].setdefault("NAME", "")
                        configuration["REMOTE_PROXY_SERVER"]["ACCOUNTS"][i].setdefault("PASSWORD", "")
                        i = i + 1

def createPort(configuration):
    setDefaultConfiguration(configuration, ["REMOTE_PROXY_SERVER"])
    
    if configuration["REMOTE_PROXY_SERVER"]["TYPE"] == "SSH":
        return createSSHPort(configuration)
    else:
        if configuration["REMOTE_PROXY_SERVER"]["TYPE"] == "WS":
            return createWSPort(configuration)
        else:
            if configuration["REMOTE_PROXY_SERVER"]["TYPE"] == "WSS":
                return createWSPort(configuration)
            else:
                return None

# SSH

class SSHOutputProtocol(twunnel.local_proxy_server.OutputProtocol):
    pass

class SSHOutputProtocolFactory(twunnel.local_proxy_server.OutputProtocolFactory):
    protocol = SSHOutputProtocol

class SSHChannel(channel.SSHChannel):
    implements(interfaces.IPushProducer)
    name = "direct-tcpip"
    
    def __init__(self, *args, **kwargs):
        twunnel.logger.log(3, "trace: SSHChannel.__init__")
        
        channel.SSHChannel.__init__(self, *args, **kwargs)
        
        self.configuration = None
        self.remoteAddress = ""
        self.remotePort = 0
        self.outputProtocol = None
        self.connectionState = 0
        self.data = ""
        self.dataState = 0
        
    def channelOpen(self, specificData):
        twunnel.logger.log(3, "trace: SSHChannel.channelOpen")
        
        self.connectionState = 1
        
        outputProtocolFactory = SSHOutputProtocolFactory(self)
        
        tunnel = twunnel.proxy_server.createTunnel(self.configuration)
        tunnel.connect(self.remoteAddress, self.remotePort, outputProtocolFactory)

    def openFailed(self, reason):
        twunnel.logger.log(3, "trace: SSHChannel.openFailed")
        
        self.connectionState = 2

    def dataReceived(self, data):
        twunnel.logger.log(3, "trace: SSHChannel.dataReceived")
        
        self.data = self.data + data
        if self.dataState == 0:
            self.processDataState0()
            return
        if self.dataState == 1:
            self.processDataState1()
            return
    
    def processDataState0(self):
        twunnel.logger.log(3, "trace: SSHChannel.processDataState0")
        
    def processDataState1(self):
        twunnel.logger.log(3, "trace: SSHChannel.processDataState0")
        
        self.outputProtocol.inputProtocol_dataReceived(self.data)
        
        self.data = ""
        
    def eofReceived(self):
        twunnel.logger.log(3, "trace: SSHChannel.eofReceived")
        
        self.loseConnection()
    
    def closeReceived(self):
        twunnel.logger.log(3, "trace: SSHChannel.closeReceived")
        
        self.loseConnection()
            
    def closed(self):
        twunnel.logger.log(3, "trace: SSHChannel.closed")
        
        self.connectionState = 2
        
        if self.outputProtocol is not None:
            self.outputProtocol.inputProtocol_connectionLost(None)
        
    def outputProtocol_connectionMade(self):
        twunnel.logger.log(3, "trace: SSHChannel.outputProtocol_connectionMade")
        
        if self.connectionState == 1:
            self.outputProtocol.inputProtocol_connectionMade()
            
            if len(self.data) != 0:
                self.outputProtocol.inputProtocol_dataReceived(self.data)
                
                self.data = ""
            
            self.dataState = 1
        else:
            if self.connectionState == 2:
                self.outputProtocol.inputProtocol_connectionLost(None)
        
    def outputProtocol_connectionFailed(self, reason):
        twunnel.logger.log(3, "trace: SSHChannel.outputProtocol_connectionFailed")
        
        if self.connectionState == 1:
            self.loseConnection()
        
    def outputProtocol_connectionLost(self, reason):
        twunnel.logger.log(3, "trace: SSHChannel.outputProtocol_connectionLost")
        
        if self.connectionState == 1:
            self.loseConnection()
        else:
            if self.connectionState == 2:
                self.outputProtocol.inputProtocol_connectionLost(None)
        
    def outputProtocol_dataReceived(self, data):
        twunnel.logger.log(3, "trace: SSHChannel.outputProtocol_dataReceived")
        
        if self.connectionState == 1:
            self.write(data)
        else:
            if self.connectionState == 2:
                self.outputProtocol.inputProtocol_connectionLost(None)
    
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
        
        self.outputProtocol.resumeProducing()
    
    def stopWriting(self):
        twunnel.logger.log(3, "trace: SSHChannel.stopWriting")
        
        self.outputProtocol.pauseProducing()

def openSSHChannel(configuration, remoteWindow, remoteMaxPacket, data, avatar):
    twunnel.logger.log(3, "trace: openSSHChannel")
    
    remoteAddressPort, localAddressPort = forwarding.unpackOpen_direct_tcpip(data)
    
    sshChannel = SSHChannel(remoteWindow=remoteWindow, remoteMaxPacket=remoteMaxPacket, avatar=avatar)
    sshChannel.configuration = configuration
    sshChannel.remoteAddress = remoteAddressPort[0]
    sshChannel.remotePort = remoteAddressPort[1]
    
    return sshChannel

class SSHAvatar(avatar.ConchUser):
    def __init__(self, configuration, i):
        twunnel.logger.log(3, "trace: SSHAvatar.__init__")
        
        avatar.ConchUser.__init__(self)
        
        self.configuration = configuration
        self.i = i
        
        self.channelLookup["direct-tcpip"] = lambda remoteWindow, remoteMaxPacket, data, avatar: openSSHChannel(self.configuration, remoteWindow, remoteMaxPacket, data, avatar)
    
    def login(self, avatarMind):
        twunnel.logger.log(3, "trace: SSHAvatar.login")
    
    def logout(self, avatarMind):
        twunnel.logger.log(3, "trace: SSHAvatar.logout")

class SSHUsernamePasswordCredentialsChecker(object):
    implements(checkers.ICredentialsChecker)
    credentialInterfaces = (credentials.IUsernamePassword, )
    
    def __init__(self, configuration):
        twunnel.logger.log(3, "trace: SSHUsernamePasswordCredentialsChecker.__init__")
        
        self.configuration = configuration
    
    def requestAvatarId(self, credentials):
        twunnel.logger.log(3, "trace: SSHUsernamePasswordCredentialsChecker.requestAvatarId")
        
        i = -1
        authorized = False
        
        if len(self.configuration["REMOTE_PROXY_SERVER"]["ACCOUNTS"]) == 0:
            i = -1
            authorized = True
        
        if authorized == False:
            i = 0
            while i < len(self.configuration["REMOTE_PROXY_SERVER"]["ACCOUNTS"]):
                if self.configuration["REMOTE_PROXY_SERVER"]["ACCOUNTS"][i]["NAME"] == credentials.username:
                    if self.configuration["REMOTE_PROXY_SERVER"]["ACCOUNTS"][i]["PASSWORD"] != "":
                        if self.configuration["REMOTE_PROXY_SERVER"]["ACCOUNTS"][i]["PASSWORD"] == credentials.password:
                            authorized = True
                    
                    if authorized == False:
                        twunnel.logger.log(1, "ERROR_ACCOUNT_PASSWORD")
                        
                        return defer.fail(UnauthorizedLogin("ERROR_ACCOUNT_PASSWORD"))
                    
                    break
                
                i = i + 1
            
            if authorized == False:
                twunnel.logger.log(1, "ERROR_ACCOUNT_NAME")
                
                return defer.fail(UnauthorizedLogin("ERROR_ACCOUNT_NAME"))
        
        return defer.succeed(i)

class SSHPrivateKeyCredentialsChecker(object):
    implements(checkers.ICredentialsChecker)
    credentialInterfaces = (credentials.ISSHPrivateKey, )
    
    def __init__(self, configuration):
        twunnel.logger.log(3, "trace: SSHPrivateKeyCredentialsChecker.__init__")
        
        self.configuration = configuration
    
    def requestAvatarId(self, credentials):
        twunnel.logger.log(3, "trace: SSHPrivateKeyCredentialsChecker.requestAvatarId")
        
        i = -1
        authorized = False
        
        if len(self.configuration["REMOTE_PROXY_SERVER"]["ACCOUNTS"]) == 0:
            i = -1
            authorized = True
        
        if authorized == False:
            i = 0
            while i < len(self.configuration["REMOTE_PROXY_SERVER"]["ACCOUNTS"]):
                if self.configuration["REMOTE_PROXY_SERVER"]["ACCOUNTS"][i]["NAME"] == credentials.username:
                    j = 0
                    while j < len(self.configuration["REMOTE_PROXY_SERVER"]["ACCOUNTS"][i]["KEYS"]):
                        if self.configuration["REMOTE_PROXY_SERVER"]["ACCOUNTS"][i]["KEYS"][j]["PUBLIC"]["FILE"] != "":
                            key = keys.Key.fromFile(self.configuration["REMOTE_PROXY_SERVER"]["ACCOUNTS"][i]["KEYS"][j]["PUBLIC"]["FILE"], passphrase=str(self.configuration["REMOTE_PROXY_SERVER"]["ACCOUNTS"][i]["KEYS"][j]["PUBLIC"]["PASSPHRASE"]))
                            
                            if key.blob() == credentials.blob:
                                if credentials.signature:
                                    if key.verify(credentials.signature, credentials.sigData):
                                        authorized = True
                                else:
                                    return defer.fail(ValidPublicKey())
                                
                                break
                        
                        j = j + 1
                    
                    if authorized == False:
                        twunnel.logger.log(1, "ERROR_ACCOUNT_KEYS_PUBLIC")
                        
                        return defer.fail(UnauthorizedLogin("ERROR_ACCOUNT_KEYS_PUBLIC"))
                    
                    break
                
                i = i + 1
            
            if authorized == False:
                twunnel.logger.log(1, "ERROR_ACCOUNT_NAME")
                
                return defer.fail(UnauthorizedLogin("ERROR_ACCOUNT_NAME"))
        
        return defer.succeed(i)

class SSHRealm(object):
    implements(portal.IRealm)
    
    def __init__(self, configuration):
        twunnel.logger.log(3, "trace: SSHRealm.__init__")
        
        self.configuration = configuration
        self.connections = {}
        
        i = -1
        self.connections[i] = 0
        
        i = i + 1
        while i < len(self.configuration["REMOTE_PROXY_SERVER"]["ACCOUNTS"]):
            self.connections[i] = 0
            
            i = i + 1
        
    def requestAvatar(self, avatarId, avatarMind, *avatarInterfaces):
        twunnel.logger.log(3, "trace: SSHRealm.requestAvatar")
        
        i = avatarId
        authorized = False
        
        if len(self.configuration["REMOTE_PROXY_SERVER"]["ACCOUNTS"]) == 0:
            authorized = True
        
        if authorized == False:
            if self.configuration["REMOTE_PROXY_SERVER"]["ACCOUNTS"][i]["CONNECTIONS"] > self.connections[i]:
                authorized = True
            
            if authorized == False:
                twunnel.logger.log(1, "ERROR_ACCOUNT_CONNECTIONS")
                
                return defer.fail(UnauthorizedLogin("ERROR_ACCOUNT_CONNECTIONS"))
        
        avatar = SSHAvatar(self.configuration, i)
        
        self.login(avatar, avatarMind)
        
        return defer.succeed((avatarInterfaces[0], avatar, lambda: self.logout(avatar, avatarMind)))
    
    def login(self, avatar, avatarMind):
        twunnel.logger.log(3, "trace: SSHRealm.login")
        
        self.connections[avatar.i] = self.connections[avatar.i] + 1
        
        avatar.login(avatarMind)
    
    def logout(self, avatar, avatarMind):
        twunnel.logger.log(3, "trace: SSHRealm.logout")
        
        avatar.logout(avatarMind)
        
        self.connections[avatar.i] = self.connections[avatar.i] - 1
    
class SSHInputProtocolFactory(factory.SSHFactory):
    def __init__(self, configuration):
        twunnel.logger.log(3, "trace: SSHInputProtocolFactory.__init__")
        
        self.configuration = configuration
        
        realm = SSHRealm(self.configuration)
        
        checkers = [
            SSHUsernamePasswordCredentialsChecker(self.configuration),
            SSHPrivateKeyCredentialsChecker(self.configuration)
        ]
        
        self.portal = portal.Portal(realm, checkers)
        
        key = keys.Key.fromFile(self.configuration["REMOTE_PROXY_SERVER"]["KEY"]["PUBLIC"]["FILE"], passphrase=str(self.configuration["REMOTE_PROXY_SERVER"]["KEY"]["PUBLIC"]["PASSPHRASE"]))
        self.publicKeys = {
            key.sshType(): key
        }
        
        twunnel.logger.log(2, "fingerprint: " + str(key.fingerprint()))
        
        key = keys.Key.fromFile(self.configuration["REMOTE_PROXY_SERVER"]["KEY"]["PRIVATE"]["FILE"], passphrase=str(self.configuration["REMOTE_PROXY_SERVER"]["KEY"]["PRIVATE"]["PASSPHRASE"]))
        self.privateKeys = {
            key.sshType(): key
        }

def createSSHPort(configuration):
    factory = SSHInputProtocolFactory(configuration)
    
    return tcp.Port(configuration["REMOTE_PROXY_SERVER"]["PORT"], factory, 50, configuration["REMOTE_PROXY_SERVER"]["ADDRESS"], reactor)

# WS

class WSOutputProtocol(twunnel.local_proxy_server.OutputProtocol):
    pass

class WSOutputProtocolFactory(twunnel.local_proxy_server.OutputProtocolFactory):
    protocol = WSOutputProtocol

class WSInputProtocol(autobahn.websocket.WebSocketServerProtocol):
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
        
        self.message = self.message + message
        if self.messageState == 0:
            self.processMessageState0()
            return
        if self.messageState == 1:
            self.processMessageState1()
            return
    
    def processMessageState0(self):
        twunnel.logger.log(3, "trace: WSInputProtocol.processMessageState0")
        
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
        
        twunnel.logger.log(2, "remoteAddress: " + self.remoteAddress)
        twunnel.logger.log(2, "remotePort: " + str(self.remotePort))
        
        outputProtocolFactory = WSOutputProtocolFactory(self)
        
        tunnel = twunnel.proxy_server.createTunnel(self.configuration)
        tunnel.connect(self.remoteAddress, self.remotePort, outputProtocolFactory)
    
    def processMessageState1(self):
        twunnel.logger.log(3, "trace: WSInputProtocol.processMessageState1")
        
        if len(self.message) == 0:
            self.outputProtocol.resumeProducing()
            return
        
        self.sendMessage("", True)
        
        self.outputProtocol.inputProtocol_dataReceived(self.message)
        
        self.message = ""
        
    def outputProtocol_connectionMade(self):
        twunnel.logger.log(3, "trace: WSInputProtocol.outputProtocol_connectionMade")
        
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
        twunnel.logger.log(3, "trace: WSInputProtocol.outputProtocol_connectionFailed")
        
        if self.connectionState == 1:
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

class WSInputProtocolFactory(autobahn.websocket.WebSocketServerFactory):
    protocol = WSInputProtocol
    
    def __init__(self, configuration, *args, **kwargs):
        twunnel.logger.log(3, "trace: WSInputProtocolFactory.__init__")
        
        autobahn.websocket.WebSocketServerFactory.__init__(self, *args, **kwargs)
        
        self.configuration = configuration
    
    def buildProtocol(self, *args, **kwargs):
        inputProtocol = autobahn.websocket.WebSocketServerFactory.buildProtocol(self, *args, **kwargs)
        inputProtocol.configuration = self.configuration
        return inputProtocol

def createWSPort(configuration):
    if configuration["REMOTE_PROXY_SERVER"]["TYPE"] == "WS":
        factory = WSInputProtocolFactory(configuration, "ws://" + str(configuration["REMOTE_PROXY_SERVER"]["ADDRESS"]) + ":" + str(configuration["REMOTE_PROXY_SERVER"]["PORT"]))
        
        return tcp.Port(configuration["REMOTE_PROXY_SERVER"]["PORT"], factory, 50, configuration["REMOTE_PROXY_SERVER"]["ADDRESS"], reactor)
    else:
        factory = WSInputProtocolFactory(configuration, "wss://" + str(configuration["REMOTE_PROXY_SERVER"]["ADDRESS"]) + ":" + str(configuration["REMOTE_PROXY_SERVER"]["PORT"]))
        
        contextFactory = ssl.DefaultOpenSSLContextFactory(configuration["REMOTE_PROXY_SERVER"]["CERTIFICATE"]["KEY"]["FILE"], configuration["REMOTE_PROXY_SERVER"]["CERTIFICATE"]["FILE"])
        
        return ssl.Port(configuration["REMOTE_PROXY_SERVER"]["PORT"], factory, contextFactory, 50, configuration["REMOTE_PROXY_SERVER"]["ADDRESS"], reactor)