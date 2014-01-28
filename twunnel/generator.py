# Copyright (c) Jeroen Van Steirteghem
# See LICENSE

from Crypto.PublicKey import RSA

import OpenSSL
import time

def generateKey(configuration):
    configuration.setdefault("KEY", {})
    configuration["KEY"].setdefault("FILE", "")
    configuration["KEY"].setdefault("PASSPHRASE", "")
    
    key = RSA.generate(2048)
    
    if configuration["KEY"]["PASSPHRASE"] != "":
        data = key.exportKey("PEM", pkcs=1, passphrase=configuration["KEY"]["PASSPHRASE"])
    else:
        data = key.exportKey("PEM", pkcs=1)
    
    open(configuration["KEY"]["FILE"], "wb").write(data)

def generateCertificateAuthority(configuration):
    configuration.setdefault("CERTIFICATE", {})
    configuration["CERTIFICATE"].setdefault("AUTHORITY", {})
    configuration["CERTIFICATE"]["AUTHORITY"].setdefault("FILE", "")
    configuration["CERTIFICATE"]["AUTHORITY"].setdefault("KEY", {})
    configuration["CERTIFICATE"]["AUTHORITY"]["KEY"].setdefault("FILE", "")
    configuration["CERTIFICATE"]["AUTHORITY"]["KEY"].setdefault("PASSPHRASE", "")
    configuration["CERTIFICATE"]["AUTHORITY"].setdefault("SUBJECT", {})
    configuration["CERTIFICATE"]["AUTHORITY"]["SUBJECT"].setdefault("COUNTRY_NAME", "")
    configuration["CERTIFICATE"]["AUTHORITY"]["SUBJECT"].setdefault("STATE_OR_PROVINCE_NAME", "")
    configuration["CERTIFICATE"]["AUTHORITY"]["SUBJECT"].setdefault("LOCALITY_NAME", "")
    configuration["CERTIFICATE"]["AUTHORITY"]["SUBJECT"].setdefault("ORGANISATION_NAME", "")
    configuration["CERTIFICATE"]["AUTHORITY"]["SUBJECT"].setdefault("ORGANISATIONAL_UNIT_NAME", "")
    configuration["CERTIFICATE"]["AUTHORITY"]["SUBJECT"].setdefault("COMMON_NAME", "")
    
    ca_key = OpenSSL.crypto.PKey()
    ca_key.generate_key(OpenSSL.crypto.TYPE_RSA, 2048)

    ca = OpenSSL.crypto.X509()
    ca.set_version(3)
    ca.set_serial_number(int(time.time() * 10000))
    if configuration["CERTIFICATE"]["AUTHORITY"]["SUBJECT"]["COUNTRY_NAME"] != "":
        ca.get_subject().C = configuration["CERTIFICATE"]["AUTHORITY"]["SUBJECT"]["COUNTRY_NAME"]
    if configuration["CERTIFICATE"]["AUTHORITY"]["SUBJECT"]["STATE_OR_PROVINCE_NAME"] != "":
        ca.get_subject().ST = configuration["CERTIFICATE"]["AUTHORITY"]["SUBJECT"]["STATE_OR_PROVINCE_NAME"]
    if configuration["CERTIFICATE"]["AUTHORITY"]["SUBJECT"]["LOCALITY_NAME"] != "":
        ca.get_subject().L = configuration["CERTIFICATE"]["AUTHORITY"]["SUBJECT"]["LOCALITY_NAME"]
    if configuration["CERTIFICATE"]["AUTHORITY"]["SUBJECT"]["ORGANISATION_NAME"] != "":
        ca.get_subject().O = configuration["CERTIFICATE"]["AUTHORITY"]["SUBJECT"]["ORGANISATION_NAME"]
    if configuration["CERTIFICATE"]["AUTHORITY"]["SUBJECT"]["ORGANISATIONAL_UNIT_NAME"] != "":
        ca.get_subject().OU = configuration["CERTIFICATE"]["AUTHORITY"]["SUBJECT"]["ORGANISATIONAL_UNIT_NAME"]
    ca.get_subject().CN = configuration["CERTIFICATE"]["AUTHORITY"]["SUBJECT"]["COMMON_NAME"]
    ca.gmtime_adj_notBefore(0)
    ca.gmtime_adj_notAfter(5 * 365 * 24 * 60 * 60)
    ca.set_issuer(ca.get_subject())
    ca.set_pubkey(ca_key)
    ca.add_extensions([OpenSSL.crypto.X509Extension("basicConstraints", True, "CA:TRUE")])
    ca.add_extensions([OpenSSL.crypto.X509Extension("subjectKeyIdentifier", False, "hash", subject=ca)])
    ca.add_extensions([OpenSSL.crypto.X509Extension("authorityKeyIdentifier", False, "keyid:always", issuer=ca)])
    ca.sign(ca_key, "sha1")
    
    data = OpenSSL.crypto.dump_certificate(OpenSSL.crypto.FILETYPE_PEM, ca)
    
    open(configuration["CERTIFICATE"]["AUTHORITY"]["FILE"], "wb").write(data)
    
    if configuration["CERTIFICATE"]["AUTHORITY"]["KEY"]["PASSPHRASE"] != "":
        data = OpenSSL.crypto.dump_privatekey(OpenSSL.crypto.FILETYPE_PEM, ca_key, "aes-256-cbc", configuration["CERTIFICATE"]["AUTHORITY"]["KEY"]["PASSPHRASE"])
    else:
        data = OpenSSL.crypto.dump_privatekey(OpenSSL.crypto.FILETYPE_PEM, ca_key)
    
    open(configuration["CERTIFICATE"]["AUTHORITY"]["KEY"]["FILE"], "wb").write(data)

def generateCertificate(configuration):
    configuration.setdefault("CERTIFICATE", {})
    configuration["CERTIFICATE"].setdefault("AUTHORITY", {})
    configuration["CERTIFICATE"]["AUTHORITY"].setdefault("FILE", "")
    configuration["CERTIFICATE"]["AUTHORITY"].setdefault("KEY", {})
    configuration["CERTIFICATE"]["AUTHORITY"]["KEY"].setdefault("FILE", "")
    configuration["CERTIFICATE"]["AUTHORITY"]["KEY"].setdefault("PASSPHRASE", "")
    configuration["CERTIFICATE"].setdefault("FILE", "")
    configuration["CERTIFICATE"].setdefault("KEY", {})
    configuration["CERTIFICATE"]["KEY"].setdefault("FILE", "")
    configuration["CERTIFICATE"]["KEY"].setdefault("PASSPHRASE", "")
    configuration["CERTIFICATE"].setdefault("SUBJECT", {})
    configuration["CERTIFICATE"]["SUBJECT"].setdefault("COUNTRY_NAME", "")
    configuration["CERTIFICATE"]["SUBJECT"].setdefault("STATE_OR_PROVINCE_NAME", "")
    configuration["CERTIFICATE"]["SUBJECT"].setdefault("LOCALITY_NAME", "")
    configuration["CERTIFICATE"]["SUBJECT"].setdefault("ORGANISATION_NAME", "")
    configuration["CERTIFICATE"]["SUBJECT"].setdefault("ORGANISATIONAL_UNIT_NAME", "")
    configuration["CERTIFICATE"]["SUBJECT"].setdefault("COMMON_NAME", "")
    configuration["CERTIFICATE"]["SUBJECT"].setdefault("ALTERNATIVE_NAME", "")
    
    data = open(configuration["CERTIFICATE"]["AUTHORITY"]["FILE"], "rb").read()
    
    ca = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, data)
    
    data = open(configuration["CERTIFICATE"]["AUTHORITY"]["KEY"]["FILE"], "rb").read()
    
    if configuration["CERTIFICATE"]["AUTHORITY"]["KEY"]["PASSPHRASE"] != "":
        ca_key = OpenSSL.crypto.load_privatekey(OpenSSL.crypto.FILETYPE_PEM, data, configuration["CERTIFICATE"]["AUTHORITY"]["KEY"]["PASSPHRASE"])
    else:
        ca_key = OpenSSL.crypto.load_privatekey(OpenSSL.crypto.FILETYPE_PEM, data)
    
    c_key = OpenSSL.crypto.PKey()
    c_key.generate_key(OpenSSL.crypto.TYPE_RSA, 2048)

    c = OpenSSL.crypto.X509()
    c.set_version(3)
    c.set_serial_number(int(time.time() * 10000))
    if configuration["CERTIFICATE"]["SUBJECT"]["COUNTRY_NAME"] != "":
        c.get_subject().C = configuration["CERTIFICATE"]["SUBJECT"]["COUNTRY_NAME"]
    if configuration["CERTIFICATE"]["SUBJECT"]["STATE_OR_PROVINCE_NAME"] != "":
        c.get_subject().ST = configuration["CERTIFICATE"]["SUBJECT"]["STATE_OR_PROVINCE_NAME"]
    if configuration["CERTIFICATE"]["SUBJECT"]["LOCALITY_NAME"] != "":
        c.get_subject().L = configuration["CERTIFICATE"]["SUBJECT"]["LOCALITY_NAME"]
    if configuration["CERTIFICATE"]["SUBJECT"]["ORGANISATION_NAME"] != "":
        c.get_subject().O = configuration["CERTIFICATE"]["SUBJECT"]["ORGANISATION_NAME"]
    if configuration["CERTIFICATE"]["SUBJECT"]["ORGANISATIONAL_UNIT_NAME"] != "":
        c.get_subject().OU = configuration["CERTIFICATE"]["SUBJECT"]["ORGANISATIONAL_UNIT_NAME"]
    c.get_subject().CN = configuration["CERTIFICATE"]["SUBJECT"]["COMMON_NAME"]
    c.gmtime_adj_notBefore(0)
    c.gmtime_adj_notAfter(5 * 365 * 24 * 60 * 60)
    c.set_issuer(ca.get_subject())
    c.set_pubkey(c_key)
    c.add_extensions([OpenSSL.crypto.X509Extension("basicConstraints", True, "CA:FALSE")])
    c.add_extensions([OpenSSL.crypto.X509Extension("subjectKeyIdentifier", False, "hash", subject=c)])
    c.add_extensions([OpenSSL.crypto.X509Extension("authorityKeyIdentifier", False, "keyid:always", subject=ca, issuer=ca)])
    if configuration["CERTIFICATE"]["SUBJECT"]["ALTERNATIVE_NAME"] != "":
        c.add_extensions([OpenSSL.crypto.X509Extension("subjectAltName", False, configuration["CERTIFICATE"]["SUBJECT"]["ALTERNATIVE_NAME"])])
    c.sign(ca_key, "sha1")
    
    data = OpenSSL.crypto.dump_certificate(OpenSSL.crypto.FILETYPE_PEM, c)
    
    open(configuration["CERTIFICATE"]["FILE"], "wb").write(data)
    
    if configuration["CERTIFICATE"]["KEY"]["PASSPHRASE"] != "":
        data = OpenSSL.crypto.dump_privatekey(OpenSSL.crypto.FILETYPE_PEM, c_key, "aes-256-cbc", configuration["CERTIFICATE"]["KEY"]["PASSPHRASE"])
    else:
        data = OpenSSL.crypto.dump_privatekey(OpenSSL.crypto.FILETYPE_PEM, c_key)
    
    open(configuration["CERTIFICATE"]["KEY"]["FILE"], "wb").write(data)