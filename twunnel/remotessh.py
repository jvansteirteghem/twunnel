# Copyright (c) Jeroen Van Steirteghem
# See LICENSE

from zope.interface import implements
from twisted.internet import defer, interfaces, reactor, tcp
from twisted.conch import avatar
from twisted.conch.error import ValidPublicKey
from twisted.conch.ssh import channel, factory, forwarding, keys
from twisted.cred import checkers, credentials, portal
from twisted.cred.error import UnauthorizedLogin
import logging
import twunnel.local

logger = logging.getLogger(__name__)

class SSHOutputProtocol(twunnel.local.OutputProtocol):
    pass

class SSHOutputProtocolFactory(twunnel.local.OutputProtocolFactory):
    protocol = SSHOutputProtocol

class SSHChannel(channel.SSHChannel):
    implements(interfaces.IPushProducer)
    name = "direct-tcpip"
    
    def __init__(self, *args, **kw):
        logger.debug("SSHChannel.__init__")
        
        channel.SSHChannel.__init__(self, *args, **kw)
        
        self.configuration = None
        self.remoteAddress = ""
        self.remotePort = 0
        self.outputProtocol = None
        self.connectionState = 0
        self.data = ""
        self.dataState = 0
        
    def channelOpen(self, specificData):
        logger.debug("SSHChannel.channelOpen")
        
        self.connectionState = 1
        
        outputProtocolFactory = SSHOutputProtocolFactory(self)
        
        tunnelClass = twunnel.local.getDefaultTunnelClass()
        tunnel = tunnelClass(self.configuration)
        tunnel.connect(self.remoteAddress, self.remotePort, outputProtocolFactory)

    def openFailed(self, reason):
        logger.debug("SSHChannel.openFailed")
        
        self.connectionState = 2

    def dataReceived(self, data):
        logger.debug("SSHChannel.dataReceived")
        
        self.data = self.data + data
        if self.dataState == 0:
            self.processDataState0()
            return
        if self.dataState == 1:
            self.processDataState1()
            return
    
    def processDataState0(self):
        logger.debug("SSHChannel.processDataState0")
        
    def processDataState1(self):
        logger.debug("SSHChannel.processDataState0")
        
        self.outputProtocol.inputProtocol_dataReceived(self.data)
        
        self.data = ""
        
    def eofReceived(self):
        logger.debug("SSHChannel.eofReceived")
        
        self.loseConnection()
    
    def closeReceived(self):
        logger.debug("SSHChannel.closeReceived")
        
        self.loseConnection()
            
    def closed(self):
        logger.debug("SSHChannel.closed")
        
        self.connectionState = 2
        
        if self.outputProtocol is not None:
            self.outputProtocol.inputProtocol_connectionLost(None)
        
    def outputProtocol_connectionMade(self):
        logger.debug("SSHChannel.outputProtocol_connectionMade")
        
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
        logger.debug("SSHChannel.outputProtocol_connectionFailed")
        
        if self.connectionState == 1:
            self.loseConnection()
        
    def outputProtocol_connectionLost(self, reason):
        logger.debug("SSHChannel.outputProtocol_connectionLost")
        
        if self.connectionState == 1:
            self.loseConnection()
        else:
            if self.connectionState == 2:
                self.outputProtocol.inputProtocol_connectionLost(None)
        
    def outputProtocol_dataReceived(self, data):
        logger.debug("SSHChannel.outputProtocol_dataReceived")
        
        if self.connectionState == 1:
            self.write(data)
        else:
            if self.connectionState == 2:
                self.outputProtocol.inputProtocol_connectionLost(None)
    
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
        
        self.outputProtocol.resumeProducing()
    
    def stopWriting(self):
        logger.debug("SSHChannel.stopWriting")
        
        self.outputProtocol.pauseProducing()

class SSHAvatar(avatar.ConchUser):
    def __init__(self, configuration, i):
        logger.debug("SSHAvatar.__init__")
        
        avatar.ConchUser.__init__(self)
        
        self.configuration = configuration
        self.i = i
        
        self.channelLookup["direct-tcpip"] = self.openSSHChannel
    
    def openSSHChannel(self, remoteWindow, remoteMaxPacket, data, avatar):
        logger.debug("SSHAvatar.openSSHChannel")
        
        remoteAddressPort, localAddressPort = forwarding.unpackOpen_direct_tcpip(data)
        
        sshChannel = SSHChannel(remoteWindow=remoteWindow, remoteMaxPacket=remoteMaxPacket, avatar=avatar)
        sshChannel.configuration = self.configuration
        sshChannel.remoteAddress = remoteAddressPort[0]
        sshChannel.remotePort = remoteAddressPort[1]
        
        return sshChannel
    
    def login(self, avatarMind):
        logger.debug("SSHAvatar.login")
    
    def logout(self, avatarMind):
        logger.debug("SSHAvatar.logout")

class SSHUsernamePasswordCredentialsChecker(object):
    implements(checkers.ICredentialsChecker)
    credentialInterfaces = (credentials.IUsernamePassword, )
    
    def __init__(self, configuration):
        logger.debug("SSHUsernamePasswordCredentialsChecker.__init__")
        
        self.configuration = configuration
    
    def requestAvatarId(self, credentials):
        logger.debug("SSHUsernamePasswordCredentialsChecker.requestAvatarId")
        
        i = 0
        authorized = False
        
        if len(self.configuration["REMOTE_PROXY_SERVER"]["ACCOUNTS"]) == 0:
            i = 0
            authorized = True
        
        if authorized == False:
            i = 0
            while i < len(self.configuration["REMOTE_PROXY_SERVER"]["ACCOUNTS"]):
                if self.configuration["REMOTE_PROXY_SERVER"]["ACCOUNTS"][i]["NAME"] == credentials.username:
                    if self.configuration["REMOTE_PROXY_SERVER"]["ACCOUNTS"][i]["PASSWORD"] != "":
                        if self.configuration["REMOTE_PROXY_SERVER"]["ACCOUNTS"][i]["PASSWORD"] == credentials.password:
                            authorized = True
                    
                    if authorized == False:
                        logger.debug("SSHUsernamePasswordCredentialsChecker.requestAvatarId: ERROR_ACCOUNT_PASSWORD")
                        
                        return defer.fail(UnauthorizedLogin("ERROR_ACCOUNT_PASSWORD"))
                    
                    break
                
                i = i + 1
            
            if authorized == False:
                logger.debug("SSHUsernamePasswordCredentialsChecker.requestAvatarId: ERROR_ACCOUNT_NAME")
                
                return defer.fail(UnauthorizedLogin("ERROR_ACCOUNT_NAME"))
        
        return defer.succeed(i)

class SSHPrivateKeyCredentialsChecker(object):
    implements(checkers.ICredentialsChecker)
    credentialInterfaces = (credentials.ISSHPrivateKey, )
    
    def __init__(self, configuration):
        logger.debug("SSHPrivateKeyCredentialsChecker.__init__")
        
        self.configuration = configuration
    
    def requestAvatarId(self, credentials):
        logger.debug("SSHPrivateKeyCredentialsChecker.requestAvatarId")
        
        i = 0
        authorized = False
        
        if len(self.configuration["REMOTE_PROXY_SERVER"]["ACCOUNTS"]) == 0:
            i = 0
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
                        logger.debug("SSHPrivateKeyCredentialsChecker.requestAvatarId: ERROR_ACCOUNT_KEYS_PUBLIC")
                        
                        return defer.fail(UnauthorizedLogin("ERROR_ACCOUNT_KEYS_PUBLIC"))
                    
                    break
                
                i = i + 1
            
            if authorized == False:
                logger.debug("SSHPrivateKeyCredentialsChecker.requestAvatarId: ERROR_ACCOUNT_NAME")
                
                return defer.fail(UnauthorizedLogin("ERROR_ACCOUNT_NAME"))
        
        return defer.succeed(i)

class SSHRealm(object):
    implements(portal.IRealm)
    
    def __init__(self, configuration):
        logger.debug("SSHRealm.__init__")
        
        self.configuration = configuration
        self.connections = {}
        
        i = 0
        while i < len(self.configuration["REMOTE_PROXY_SERVER"]["ACCOUNTS"]):
            self.connections[i] = 0
            
            i = i + 1
        
    def requestAvatar(self, avatarId, avatarMind, *avatarInterfaces):
        logger.debug("SSHRealm.requestAvatar")
        
        i = avatarId
        authorized = False
        
        if len(self.configuration["REMOTE_PROXY_SERVER"]["ACCOUNTS"]) != 0:
            if self.configuration["REMOTE_PROXY_SERVER"]["ACCOUNTS"][i]["CONNECTIONS"] > self.connections[i]:
                authorized = True
        
        if authorized == False:
            logger.debug("SSHRealm.requestAvatar: ERROR_ACCOUNT_CONNECTIONS")
            
            return defer.fail(UnauthorizedLogin("ERROR_ACCOUNT_CONNECTIONS"))
        
        avatar = SSHAvatar(self.configuration, i)
        
        self.login(avatar, avatarMind)
        
        return defer.succeed((avatarInterfaces[0], avatar, lambda: self.logout(avatar, avatarMind)))
    
    def login(self, avatar, avatarMind):
        logger.debug("SSHRealm.login")
        
        self.connections[avatar.i] = self.connections[avatar.i] + 1
        
        avatar.login(avatarMind)
    
    def logout(self, avatar, avatarMind):
        logger.debug("SSHRealm.logout")
        
        avatar.logout(avatarMind)
        
        self.connections[avatar.i] = self.connections[avatar.i] - 1
    
class SSHInputProtocolFactory(factory.SSHFactory):
    def __init__(self, configuration):
        logger.debug("SSHInputProtocolFactory.__init__")
        
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
        
        logger.debug("SSHInputProtocolFactory.__init__: fingerprint=" + str(key.fingerprint()))
        
        key = keys.Key.fromFile(self.configuration["REMOTE_PROXY_SERVER"]["KEY"]["PRIVATE"]["FILE"], passphrase=str(self.configuration["REMOTE_PROXY_SERVER"]["KEY"]["PRIVATE"]["PASSPHRASE"]))
        self.privateKeys = {
            key.sshType(): key
        }

def createPort(configuration):
    factory = SSHInputProtocolFactory(configuration)
    
    return tcp.Port(configuration["REMOTE_PROXY_SERVER"]["PORT"], factory, 50, configuration["REMOTE_PROXY_SERVER"]["ADDRESS"], reactor)