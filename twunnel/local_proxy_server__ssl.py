# Copyright (c) Jeroen Van Steirteghem
# See LICENSE

from twisted.internet import ssl
import OpenSSL
import twunnel.local_proxy_server
import twunnel.logger
import twunnel.proxy_server
import twunnel.proxy_server__socks5

class SSLClientContextFactory(ssl.ContextFactory):
    isClient = 1
    
    def __init__(self, certificateAuthorityFile=""):
        twunnel.logger.log(3, "trace: SSLClientContextFactory.__init__")
        
        self.certificateAuthorityFile = certificateAuthorityFile
        
    def getContext(self):
        twunnel.logger.log(3, "trace: SSLClientContextFactory.getContext")
        
        context = OpenSSL.SSL.Context(OpenSSL.SSL.SSLv23_METHOD)
        context.set_options(OpenSSL.SSL.OP_NO_SSLv2)
        
        if self.certificateAuthorityFile != "":
            context.load_verify_locations(self.certificateAuthorityFile)
        
        context.set_verify(OpenSSL.SSL.VERIFY_PEER | OpenSSL.SSL.VERIFY_FAIL_IF_NO_PEER_CERT, self.verify)
        
        return context
        
    def verify(self, connection, certificate, errorNumber, errorDepth, certificateOk):
        twunnel.logger.log(3, "trace: SSLClientContextFactory.verify")
        
        if certificateOk:
            twunnel.logger.log(2, "certificate: ok")
        else:
            twunnel.logger.log(2, "certificate: not ok")
        
        return certificateOk

class SSLOutputProtocolConnection(object):
    def __init__(self, configuration):
        twunnel.logger.log(3, "trace: SSLOutputProtocolConnection.__init__")
        
        self.configuration = configuration
    
    def connect(self, remoteAddress, remotePort, inputProtocol):
        twunnel.logger.log(3, "trace: SSLOutputProtocolConnection.connect")
        
        configuration = {}
        configuration["PROXY_SERVER"] = {}
        configuration["PROXY_SERVER"]["TYPE"] = "SOCKS5"
        configuration["PROXY_SERVER"]["ADDRESS"] = self.configuration["REMOTE_PROXY_SERVER"]["ADDRESS"]
        configuration["PROXY_SERVER"]["PORT"] = self.configuration["REMOTE_PROXY_SERVER"]["PORT"]
        configuration["PROXY_SERVER"]["ACCOUNT"] = {}
        configuration["PROXY_SERVER"]["ACCOUNT"]["NAME"] = self.configuration["REMOTE_PROXY_SERVER"]["ACCOUNT"]["NAME"]
        configuration["PROXY_SERVER"]["ACCOUNT"]["PASSWORD"] = self.configuration["REMOTE_PROXY_SERVER"]["ACCOUNT"]["PASSWORD"]
        
        outputProtocolFactory = twunnel.local_proxy_server.OutputProtocolFactory(inputProtocol)
        
        tunnelOutputProtocolFactory = twunnel.proxy_server__socks5.SOCKS5TunnelOutputProtocolFactory(configuration, remoteAddress, remotePort)
        tunnelProtocolFactory = twunnel.proxy_server.TunnelProtocolFactory(outputProtocolFactory, tunnelOutputProtocolFactory)
        
        contextFactory = SSLClientContextFactory(self.configuration["REMOTE_PROXY_SERVER"]["CERTIFICATE"]["AUTHORITY"]["FILE"])
        
        tunnel = twunnel.proxy_server.createTunnel(self.configuration)
        tunnel.connect(self.configuration["REMOTE_PROXY_SERVER"]["ADDRESS"], self.configuration["REMOTE_PROXY_SERVER"]["PORT"], tunnelProtocolFactory, contextFactory)
        
    def startConnection(self):
        twunnel.logger.log(3, "trace: SSLOutputProtocolConnection.startConnection")
    
    def stopConnection(self):
        twunnel.logger.log(3, "trace: SSLOutputProtocolConnection.stopConnection")