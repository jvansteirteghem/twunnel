# Copyright (c) Jeroen Van Steirteghem
# See LICENSE

from twisted.internet import reactor
from twisted.names import cache, client, hosts, resolve
import twunnel.logger

def setDefaultConfiguration(configuration, keys):
    if "DNS_RESOLVER" in keys:
        configuration.setdefault("DNS_RESOLVER", {})
        configuration["DNS_RESOLVER"].setdefault("HOSTS", {})
        configuration["DNS_RESOLVER"]["HOSTS"].setdefault("FILE", "")
        configuration["DNS_RESOLVER"].setdefault("SERVERS", [])
        i = 0
        while i < len(configuration["DNS_RESOLVER"]["SERVERS"]):
            configuration["DNS_RESOLVER"]["SERVERS"][i].setdefault("ADDRESS", "")
            configuration["DNS_RESOLVER"]["SERVERS"][i].setdefault("PORT", 0)
            i = i + 1

class HostsResolver(hosts.Resolver):
    lookupAllRecords = hosts.Resolver.lookupAddress

class ClientResolver(client.Resolver):
    lookupAllRecords = client.Resolver.lookupAddress

def createResolver(configuration):
    setDefaultConfiguration(configuration, ["DNS_RESOLVER"])
    
    resolverFile = configuration["DNS_RESOLVER"]["HOSTS"]["FILE"]
    resolverServers = []
    i = 0
    while i < len(configuration["DNS_RESOLVER"]["SERVERS"]):
        resolverServers.append((configuration["DNS_RESOLVER"]["SERVERS"][i]["ADDRESS"], configuration["DNS_RESOLVER"]["SERVERS"][i]["PORT"]))
        i = i + 1
    
    resolvers = []
    if resolverFile != "":
        resolvers.append(HostsResolver(file=resolverFile))
    if len(resolverServers) != 0:
        resolvers.append(cache.CacheResolver())
        resolvers.append(ClientResolver(servers=resolverServers))
    
    if len(resolvers) != 0:
        return resolve.ResolverChain(resolvers)
    else:
        return None

def getDefaultResolver():
    return reactor.resolver

def setDefaultResolver(resolver):
    reactor.resolver = resolver