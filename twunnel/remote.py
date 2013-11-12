# Copyright (c) Jeroen Van Steirteghem
# See LICENSE

import logging
import twunnel.remotessh
import twunnel.remotews

logger = logging.getLogger(__name__)

def createPort(configuration):
    configuration.setdefault("REMOTE_PROXY_SERVER", {})
    configuration["REMOTE_PROXY_SERVER"].setdefault("TYPE", "")
    if configuration["REMOTE_PROXY_SERVER"]["TYPE"] == "SSH":
        configuration["REMOTE_PROXY_SERVER"].setdefault("ADDRESS", "")
        configuration["REMOTE_PROXY_SERVER"].setdefault("PORT", 0)
        configuration["REMOTE_PROXY_SERVER"].setdefault("KEY", {})
        configuration["REMOTE_PROXY_SERVER"]["KEY"].setdefault("PUBLIC", {})
        configuration["REMOTE_PROXY_SERVER"]["KEY"]["PUBLIC"].setdefault("FILE", "")
        configuration["REMOTE_PROXY_SERVER"]["KEY"]["PUBLIC"].setdefault("PASSPHRASE", "")
        configuration["REMOTE_PROXY_SERVER"]["KEY"].setdefault("PRIVATE", {})
        configuration["REMOTE_PROXY_SERVER"]["KEY"]["PRIVATE"].setdefault("FILE", "")
        configuration["REMOTE_PROXY_SERVER"]["KEY"]["PRIVATE"].setdefault("PASSPHRASE", "")
        configuration["REMOTE_PROXY_SERVER"].setdefault("ACCOUNT", {})
        configuration["REMOTE_PROXY_SERVER"]["ACCOUNT"].setdefault("NAME", "")
        configuration["REMOTE_PROXY_SERVER"]["ACCOUNT"].setdefault("PASSWORD", "")
        configuration["REMOTE_PROXY_SERVER"]["ACCOUNT"].setdefault("KEYS", [])
        i = 0
        while i < len(configuration["REMOTE_PROXY_SERVER"]["ACCOUNT"]["KEYS"]):
            configuration["REMOTE_PROXY_SERVER"]["ACCOUNT"]["KEYS"][i].setdefault("PUBLIC", {})
            configuration["REMOTE_PROXY_SERVER"]["ACCOUNT"]["KEYS"][i]["PUBLIC"].setdefault("FILE", "")
            configuration["REMOTE_PROXY_SERVER"]["ACCOUNT"]["KEYS"][i]["PUBLIC"].setdefault("PASSPHRASE", "")
            i = i + 1
        configuration["REMOTE_PROXY_SERVER"]["ACCOUNT"].setdefault("CONNECTIONS", 0)
    else:
        if configuration["REMOTE_PROXY_SERVER"]["TYPE"] == "WS":
            configuration["REMOTE_PROXY_SERVER"].setdefault("ADDRESS", "")
            configuration["REMOTE_PROXY_SERVER"].setdefault("PORT", 0)
            configuration["REMOTE_PROXY_SERVER"].setdefault("ACCOUNT", {})
            configuration["REMOTE_PROXY_SERVER"]["ACCOUNT"].setdefault("NAME", "")
            configuration["REMOTE_PROXY_SERVER"]["ACCOUNT"].setdefault("PASSWORD", "")
        else:
            if configuration["REMOTE_PROXY_SERVER"]["TYPE"] == "WSS":
                configuration["REMOTE_PROXY_SERVER"].setdefault("ADDRESS", "")
                configuration["REMOTE_PROXY_SERVER"].setdefault("PORT", 0)
                configuration["REMOTE_PROXY_SERVER"].setdefault("CERTIFICATE", {})
                configuration["REMOTE_PROXY_SERVER"]["CERTIFICATE"].setdefault("FILE", "")
                configuration["REMOTE_PROXY_SERVER"]["CERTIFICATE"].setdefault("KEY", {})
                configuration["REMOTE_PROXY_SERVER"]["CERTIFICATE"]["KEY"].setdefault("FILE", "")
                configuration["REMOTE_PROXY_SERVER"].setdefault("ACCOUNT", {})
                configuration["REMOTE_PROXY_SERVER"]["ACCOUNT"].setdefault("NAME", "")
                configuration["REMOTE_PROXY_SERVER"]["ACCOUNT"].setdefault("PASSWORD", "")
    
    if configuration["REMOTE_PROXY_SERVER"]["TYPE"] == "SSH":
        return twunnel.remotessh.createSSHPort(configuration)
    else:
        if configuration["REMOTE_PROXY_SERVER"]["TYPE"] == "WS":
            return twunnel.remotews.createWSPort(configuration)
        else:
            if configuration["REMOTE_PROXY_SERVER"]["TYPE"] == "WSS":
                return twunnel.remotews.createWSPort(configuration)
            else:
                return None
