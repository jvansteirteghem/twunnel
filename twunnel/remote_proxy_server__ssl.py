# Copyright (c) Jeroen Van Steirteghem
# See LICENSE

from twisted.internet import reactor, ssl
import OpenSSL
import twunnel.local_proxy_server
import twunnel.local_proxy_server__socks5
import twunnel.logger

class SSLServerContextFactory(ssl.ContextFactory):
    isClient = 0
    
    def __init__(self, certificateFile, certificateKeyFile):
        twunnel.logger.log(3, "trace: SSLServerContextFactory.__init__")
        
        self.certificateFile = certificateFile
        self.certificateKeyFile = certificateKeyFile
        
    def getContext(self):
        twunnel.logger.log(3, "trace: SSLServerContextFactory.getContext")
        
        context = OpenSSL.SSL.Context(OpenSSL.SSL.SSLv23_METHOD)
        context.set_options(OpenSSL.SSL.OP_NO_SSLv2)
        context.use_certificate_file(self.certificateFile)
        context.use_privatekey_file(self.certificateKeyFile)
        
        return context

class SSLInputProtocolFactory(twunnel.local_proxy_server__socks5.SOCKS5InputProtocolFactory):
    def __init__(self, configuration):
        twunnel.logger.log(3, "trace: SSLInputProtocolFactory.__init__")
        
        self.configuration = configuration
        
        configuration = {}
        configuration["PROXY_SERVERS"] = self.configuration["PROXY_SERVERS"]
        configuration["LOCAL_PROXY_SERVER"] = {}
        configuration["LOCAL_PROXY_SERVER"]["TYPE"] = "SOCKS5"
        configuration["LOCAL_PROXY_SERVER"]["ADDRESS"] = self.configuration["REMOTE_PROXY_SERVER"]["ADDRESS"]
        configuration["LOCAL_PROXY_SERVER"]["PORT"] = self.configuration["REMOTE_PROXY_SERVER"]["PORT"]
        configuration["LOCAL_PROXY_SERVER"]["ACCOUNTS"] = []
        i = 0
        while i < len(self.configuration["REMOTE_PROXY_SERVER"]["ACCOUNTS"]):
            configuration["LOCAL_PROXY_SERVER"]["ACCOUNTS"].append({})
            configuration["LOCAL_PROXY_SERVER"]["ACCOUNTS"][i]["NAME"] = self.configuration["REMOTE_PROXY_SERVER"]["ACCOUNTS"][i]["NAME"]
            configuration["LOCAL_PROXY_SERVER"]["ACCOUNTS"][i]["PASSWORD"] = self.configuration["REMOTE_PROXY_SERVER"]["ACCOUNTS"][i]["PASSWORD"]
            i = i + 1
        configuration["REMOTE_PROXY_SERVERS"] = []
        
        outputProtocolConnectionManager = twunnel.local_proxy_server.OutputProtocolConnectionManager(configuration)
        
        twunnel.local_proxy_server__socks5.SOCKS5InputProtocolFactory.__init__(self, configuration, outputProtocolConnectionManager)

def createSSLPort(configuration):
    factory = SSLInputProtocolFactory(configuration)
    
    contextFactory = SSLServerContextFactory(configuration["REMOTE_PROXY_SERVER"]["CERTIFICATE"]["FILE"], configuration["REMOTE_PROXY_SERVER"]["CERTIFICATE"]["KEY"]["FILE"])
    
    return ssl.Port(configuration["REMOTE_PROXY_SERVER"]["PORT"], factory, contextFactory, 50, configuration["REMOTE_PROXY_SERVER"]["ADDRESS"], reactor)