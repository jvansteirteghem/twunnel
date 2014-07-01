# Copyright (c) Jeroen Van Steirteghem
# See LICENSE

from twisted.conch import avatar
from twisted.conch.error import ValidPublicKey
from twisted.conch.ssh import channel, factory, forwarding, keys
from twisted.cred import checkers, credentials, portal
from twisted.cred.error import UnauthorizedLogin
from twisted.internet import defer, interfaces, reactor, tcp
from zope.interface import implements
import twunnel.local_proxy_server
import twunnel.logger
import twunnel.proxy_server

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
            if self.processDataState0():
                return
        if self.dataState == 1:
            if self.processDataState1():
                return
    
    def processDataState0(self):
        twunnel.logger.log(3, "trace: SSHChannel.processDataState0")
        
        return True
        
    def processDataState1(self):
        twunnel.logger.log(3, "trace: SSHChannel.processDataState1")
        
        self.outputProtocol.inputProtocol_dataReceived(self.data)
        
        self.data = ""
        
        return True
        
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
        
        if len(self.configuration["REMOTE_PROXY_SERVER"]["ACCOUNTS"]) == 0:
            return defer.succeed(-1)
        
        i = 0
        while i < len(self.configuration["REMOTE_PROXY_SERVER"]["ACCOUNTS"]):
            if self.configuration["REMOTE_PROXY_SERVER"]["ACCOUNTS"][i]["NAME"] == credentials.username:
                if self.configuration["REMOTE_PROXY_SERVER"]["ACCOUNTS"][i]["PASSWORD"] == credentials.password:
                    return defer.succeed(i)
                
                twunnel.logger.log(1, "ERROR_ACCOUNT_PASSWORD")
                
                return defer.fail(UnauthorizedLogin("ERROR_ACCOUNT_PASSWORD"))
            
            i = i + 1
        
        twunnel.logger.log(1, "ERROR_ACCOUNT_NAME")
        
        return defer.fail(UnauthorizedLogin("ERROR_ACCOUNT_NAME"))

class SSHPrivateKeyCredentialsChecker(object):
    implements(checkers.ICredentialsChecker)
    credentialInterfaces = (credentials.ISSHPrivateKey, )
    
    def __init__(self, configuration):
        twunnel.logger.log(3, "trace: SSHPrivateKeyCredentialsChecker.__init__")
        
        self.configuration = configuration
    
    def requestAvatarId(self, credentials):
        twunnel.logger.log(3, "trace: SSHPrivateKeyCredentialsChecker.requestAvatarId")
        
        if len(self.configuration["REMOTE_PROXY_SERVER"]["ACCOUNTS"]) == 0:
            return defer.succeed(-1)
        
        if not credentials.signature:
            return defer.fail(ValidPublicKey())
        
        i = 0
        while i < len(self.configuration["REMOTE_PROXY_SERVER"]["ACCOUNTS"]):
            if self.configuration["REMOTE_PROXY_SERVER"]["ACCOUNTS"][i]["NAME"] == credentials.username:
                j = 0
                while j < len(self.configuration["REMOTE_PROXY_SERVER"]["ACCOUNTS"][i]["KEYS"]):
                    if self.configuration["REMOTE_PROXY_SERVER"]["ACCOUNTS"][i]["KEYS"][j]["PUBLIC"]["FILE"] != "":
                        key = keys.Key.fromFile(self.configuration["REMOTE_PROXY_SERVER"]["ACCOUNTS"][i]["KEYS"][j]["PUBLIC"]["FILE"], passphrase=str(self.configuration["REMOTE_PROXY_SERVER"]["ACCOUNTS"][i]["KEYS"][j]["PUBLIC"]["PASSPHRASE"]))
                        
                        if key.blob() == credentials.blob:
                            if key.verify(credentials.signature, credentials.sigData):
                                return defer.succeed(i)
                    
                    j = j + 1
                
                twunnel.logger.log(1, "ERROR_ACCOUNT_KEYS_PUBLIC")
                
                return defer.fail(UnauthorizedLogin("ERROR_ACCOUNT_KEYS_PUBLIC"))
            
            i = i + 1
        
        twunnel.logger.log(1, "ERROR_ACCOUNT_NAME")
        
        return defer.fail(UnauthorizedLogin("ERROR_ACCOUNT_NAME"))

class SSHRealm(object):
    implements(portal.IRealm)
    
    def __init__(self, configuration):
        twunnel.logger.log(3, "trace: SSHRealm.__init__")
        
        self.configuration = configuration
        self.connections = {}
        
        i = -1
        self.connections[i] = -1
        
        i = i + 1
        while i < len(self.configuration["REMOTE_PROXY_SERVER"]["ACCOUNTS"]):
            self.connections[i] = 0
            
            i = i + 1
        
    def requestAvatar(self, avatarId, avatarMind, *avatarInterfaces):
        twunnel.logger.log(3, "trace: SSHRealm.requestAvatar")
        
        i = avatarId
        
        if self.configuration["REMOTE_PROXY_SERVER"]["ACCOUNTS"][i]["CONNECTIONS"] != -1:
            if self.configuration["REMOTE_PROXY_SERVER"]["ACCOUNTS"][i]["CONNECTIONS"] == self.connections[i]:
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