# Copyright (c) Jeroen Van Steirteghem
# See LICENSE

from Crypto.PublicKey import RSA

def generateKey(configuration):
    configuration.setdefault("KEY", {})
    configuration["KEY"].setdefault("FILE", "")
    configuration["KEY"].setdefault("PASSPHRASE", "")
    
    key = RSA.generate(2048)
    
    if configuration["KEY"]["PASSPHRASE"] != "":
        data = key.exportKey("PEM", pkcs=1, passphrase=configuration["KEY"]["PASSPHRASE"])
    else:
        data = key.exportKey("PEM", pkcs=1)
    
    f = open(configuration["KEY"]["FILE"], "wb")
    f.write(data)
    f.close()