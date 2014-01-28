import sys
import os
sys.path.insert(0, os.path.abspath("../../.."))

import twunnel.generator

configuration = \
{
    "KEY":
    {
        "FILE": "KP.pem",
        "PASSPHRASE": ""
    }
}

twunnel.generator.generateKey(configuration)