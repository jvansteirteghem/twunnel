# Copyright (c) Jeroen Van Steirteghem
# See LICENSE

from twisted.internet import error, defer, protocol, reactor
from twisted.names import common, dns, hosts, resolve
from twisted.python import failure
import socket
import twunnel.logger
import twunnel.proxy_server

def setDefaultConfiguration(configuration, keys):
    if "DNS_RESOLVER" in keys:
        configuration.setdefault("DNS_RESOLVER", {})
        configuration["DNS_RESOLVER"].setdefault("FILE", "")
        configuration["DNS_RESOLVER"].setdefault("SERVERS", [])
        i = 0
        while i < len(configuration["DNS_RESOLVER"]["SERVERS"]):
            configuration["DNS_RESOLVER"]["SERVERS"][i].setdefault("ADDRESS", "")
            configuration["DNS_RESOLVER"]["SERVERS"][i].setdefault("PORT", 0)
            i = i + 1

class ResolverBase(common.ResolverBase):
    def __init__(self, configuration):
        twunnel.logger.log(3, "trace: ResolverBase.__init__")
        
        self.configuration = configuration
        
        common.ResolverBase.__init__(self)
    
    def getHostByName(self, name, timeout=None, effort=10):
        twunnel.logger.log(3, "trace: ResolverBase.getHostByName")
        
        deferred = self.lookupAllRecords(name, timeout)
        deferred.addCallback(self._cbRecords, name, timeout, effort)
        return deferred
    
    def _cbRecords(self, records, name, timeout, effort):
        twunnel.logger.log(3, "trace: ResolverBase._cbRecords")
        
        (answers, authority, additional) = records
        
        result = self._extractRecord(answers + authority + additional, name, timeout, effort)
        if not result:
            raise error.DNSLookupError(name)
        return result
    
    def _extractRecord(self, records, name, timeout, effort):
        twunnel.logger.log(3, "trace: ResolverBase._extractRecord")
        
        dnsName = dns.Name(name)
        
        if not effort:
            return None
        for r in records:
            if r.name == dnsName and r.type == dns.A:
                return socket.inet_ntop(socket.AF_INET, r.payload.address)
        for r in records:
            if r.name == dnsName and r.type == dns.A6:
                return socket.inet_ntop(socket.AF_INET6, r.payload.address)
        for r in records:
            if r.name == dnsName and r.type == dns.AAAA:
                return socket.inet_ntop(socket.AF_INET6, r.payload.address)
        for r in records:
            if r.name == dnsName and r.type == dns.CNAME:
                result = self._extractRecord(records, str(r.payload.name), timeout, effort - 1)
                if not result:
                    return self.getHostByName(str(r.payload.name), timeout, effort - 1)
                return result
        for r in records:
            if r.type == dns.NS:
                configuration = {}
                configuration["PROXY_SERVERS"] = self.configuration["PROXY_SERVERS"]
                configuration["DNS_RESOLVER"] = {}
                configuration["DNS_RESOLVER"]["SERVERS"] = []
                configuration["DNS_RESOLVER"]["SERVERS"].append({})
                configuration["DNS_RESOLVER"]["SERVERS"][0]["ADDRESS"] = str(r.payload.name)
                configuration["DNS_RESOLVER"]["SERVERS"][0]["PORT"] = dns.PORT
                
                resolver = ServerResolver(configuration)
                return resolver.getHostByName(name, timeout, effort - 1)

class FileResolver(ResolverBase, hosts.Resolver):
    def __init__(self, configuration, ttl = 60 * 60):
        twunnel.logger.log(3, "trace: FileResolver.__init__")
        
        self.configuration = configuration
        
        ResolverBase.__init__(self, configuration)
        hosts.Resolver.__init__(self, self.configuration["DNS_RESOLVER"]["FILE"], ttl)
    
    def lookupAddress(self, name, timeout=None):
        twunnel.logger.log(3, "trace: FileResolver.lookupAddress")
        
        return hosts.Resolver.lookupAddress(self, name, timeout)
    
    def lookupIPV6Address(self, name, timeout=None):
        twunnel.logger.log(3, "trace: FileResolver.lookupIPV6Address")
        
        return hosts.Resolver.lookupIPV6Address(self, name, timeout)
    
    def _a_aaaaRecords(self, name):
        twunnel.logger.log(3, "trace: FileResolver._a_aaaaRecords")
        
        return self._aRecords(name) + self._aaaaRecords(name)
    
    def lookupAllRecords(self, name, timeout=None):
        twunnel.logger.log(3, "trace: FileResolver.lookupAllRecords")
        
        return self._respond(name, self._a_aaaaRecords(name))

class DNSProtocolClientFactory(protocol.ClientFactory):
    def __init__(self, controller):
        twunnel.logger.log(3, "trace: DNSProtocolClientFactory.__init__")
        
        self.controller = controller
    
    def clientConnectionLost(self, connector, reason):
        twunnel.logger.log(3, "trace: DNSProtocolClientFactory.clientConnectionLost")
    
    def clientConnectionFailed(self, connector, reason):
        twunnel.logger.log(3, "trace: DNSProtocolClientFactory.clientConnectionFailed")
        
        deferreds = self.controller.deferreds[:]
        del self.controller.deferreds[:]
        for deferred, name, type, cls, timeout in deferreds:
            deferred.errback(reason)
    
    def buildProtocol(self, addr):
        twunnel.logger.log(3, "trace: DNSProtocolClientFactory.buildProtocol")
        
        p = dns.DNSProtocol(self.controller)
        p.factory = self
        return p

class ServerResolver(ResolverBase):
    def __init__(self, configuration):
        twunnel.logger.log(3, "trace: ServerResolver.__init__")
        
        ResolverBase.__init__(self, configuration)
        
        self.configuration = configuration
        self.i = 0
        self.connections = []
        self.deferreds = []
        self.factory = DNSProtocolClientFactory(self)
    
    def connectionMade(self, connection):
        twunnel.logger.log(3, "trace: ServerResolver.connectionMade")
        
        self.connections.append(connection)
        
        deferreds = self.deferreds[:]
        del self.deferreds[:]
        for (deferred, name, type, cls, timeout) in deferreds:
            self._lookup(name, cls, type, timeout).chainDeferred(deferred)
    
    def connectionLost(self, connection):
        twunnel.logger.log(3, "trace: ServerResolver.connectionLost")
        
        self.connections.remove(connection)
    
    def messageReceived(self, message, protocol, address=None):
        twunnel.logger.log(3, "trace: ServerResolver.messageReceived")
    
    def _lookup(self, name, cls, type, timeout=None):
        twunnel.logger.log(3, "trace: ServerResolver._lookup")
        
        if not len(self.connections):
            self.i = self.i + 1
            if self.i >= len(self.configuration["DNS_RESOLVER"]["SERVERS"]):
                self.i = 0
            
            tunnel = twunnel.proxy_server.createTunnel(self.configuration)
            tunnel.connect(self.configuration["DNS_RESOLVER"]["SERVERS"][self.i]["ADDRESS"], self.configuration["DNS_RESOLVER"]["SERVERS"][self.i]["PORT"], self.factory)
            
            deferred = defer.Deferred()
            self.deferreds.append((deferred, name, type, cls, timeout))
            return deferred
        else:
            deferred = self.connections[0].query([dns.Query(name, type, cls)])
            deferred.addCallback(self._cbMessage)
            return deferred
    
    def _cbMessage(self, message):
        twunnel.logger.log(3, "trace: ServerResolver._cbMessage")
        
        if message.rCode != dns.OK:
            return failure.Failure(self.exceptionForCode(message.rCode)(message))
        
        return (message.answers, message.authority, message.additional)

class Resolver(ResolverBase, resolve.ResolverChain):
    def __init__(self, configuration):
        twunnel.logger.log(3, "trace: Resolver.__init__")
        
        resolvers = []
        if configuration["DNS_RESOLVER"]["FILE"] != "":
            resolvers.append(FileResolver(configuration))
        if len(configuration["DNS_RESOLVER"]["SERVERS"]) != 0:
            resolvers.append(ServerResolver(configuration))
        
        ResolverBase.__init__(self, configuration)
        resolve.ResolverChain.__init__(self, resolvers)
    
    def _lookup(self, name, cls, type, timeout):
        twunnel.logger.log(3, "trace: Resolver._lookup")
        
        return resolve.ResolverChain._lookup(self, name, cls, type, timeout)

def createResolver(configuration):
    setDefaultConfiguration(configuration, ["DNS_RESOLVER"])
    
    if configuration["DNS_RESOLVER"]["FILE"] != "" or len(configuration["DNS_RESOLVER"]["SERVERS"]) != 0:
        return Resolver(configuration)
    else:
        return None

def getDefaultResolver():
    return reactor.resolver

def setDefaultResolver(resolver):
    reactor.resolver = resolver