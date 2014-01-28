import sys
import os
sys.path.insert(0, os.path.abspath("../../.."))

import twunnel.generator

configuration = \
{
    "CERTIFICATE":
    {
        "AUTHORITY":
        {
            "FILE": "CA.pem",
            "KEY":
            {
                "FILE": "CAK.pem",
                "PASSPHRASE": ""
            },
            "SUBJECT":
            {
                "COUNTRY_NAME": "",
                "STATE_OR_PROVINCE_NAME": "",
                "LOCALITY_NAME": "",
                "ORGANISATION_NAME": "",
                "ORGANISATIONAL_UNIT_NAME": "",
                "COMMON_NAME": "CA"
            }
        }
    }
}

twunnel.generator.generateCertificateAuthority(configuration)

configuration = \
{
    "CERTIFICATE":
    {
        "AUTHORITY":
        {
            "FILE": "CA.pem",
            "KEY":
            {
                "FILE": "CAK.pem",
                "PASSPHRASE": ""
            }
        },
        "FILE": "C.pem",
        "KEY":
        {
            "FILE": "CK.pem",
            "PASSPHRASE": ""
        },
        "SUBJECT":
        {
            "COUNTRY_NAME": "",
            "STATE_OR_PROVINCE_NAME": "",
            "LOCALITY_NAME": "",
            "ORGANISATION_NAME": "",
            "ORGANISATIONAL_UNIT_NAME": "",
            "COMMON_NAME": "127.0.0.1",
            "ALTERNATIVE_NAME": "IP: 127.0.0.1, DNS: localhost"
        }
    }
}

twunnel.generator.generateCertificate(configuration)