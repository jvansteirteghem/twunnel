# Copyright (c) Jeroen Van Steirteghem
# See LICENSE

def generateKey(configuration):
    from twunnel.generator__ssh import generateKey as _generateKey
    
    _generateKey(configuration)

def generateCertificateAuthority(configuration):
    from twunnel.generator__ssl import generateCertificateAuthority as _generateCertificateAuthority
    
    _generateCertificateAuthority(configuration)
    

def generateCertificate(configuration):
    from twunnel.generator__ssl import generateCertificate as _generateCertificate
    
    _generateCertificate(configuration)