# Copyright (c) Jeroen Van Steirteghem
# See LICENSE

import twunnel.proxy_server

def setDefaultConfiguration(configuration, keys):
    twunnel.proxy_server.setDefaultConfiguration(configuration, keys)
    
    if "REMOTE_PROXY_SERVER" in keys:
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
            configuration["REMOTE_PROXY_SERVER"].setdefault("ACCOUNTS", [])
            i = 0
            while i < len(configuration["REMOTE_PROXY_SERVER"]["ACCOUNTS"]):
                configuration["REMOTE_PROXY_SERVER"]["ACCOUNTS"][i].setdefault("NAME", "")
                configuration["REMOTE_PROXY_SERVER"]["ACCOUNTS"][i].setdefault("PASSWORD", "")
                configuration["REMOTE_PROXY_SERVER"]["ACCOUNTS"][i].setdefault("KEYS", [])
                j = 0
                while j < len(configuration["REMOTE_PROXY_SERVER"]["ACCOUNTS"][i]["KEYS"]):
                    configuration["REMOTE_PROXY_SERVER"]["ACCOUNTS"][i]["KEYS"][j].setdefault("PUBLIC", {})
                    configuration["REMOTE_PROXY_SERVER"]["ACCOUNTS"][i]["KEYS"][j]["PUBLIC"].setdefault("FILE", "")
                    configuration["REMOTE_PROXY_SERVER"]["ACCOUNTS"][i]["KEYS"][j]["PUBLIC"].setdefault("PASSPHRASE", "")
                    j = j + 1
                configuration["REMOTE_PROXY_SERVER"]["ACCOUNTS"][i].setdefault("CONNECTIONS", 0)
                i = i + 1
        else:
            if configuration["REMOTE_PROXY_SERVER"]["TYPE"] == "SSL":
                configuration["REMOTE_PROXY_SERVER"].setdefault("ADDRESS", "")
                configuration["REMOTE_PROXY_SERVER"].setdefault("PORT", 0)
                configuration["REMOTE_PROXY_SERVER"].setdefault("CERTIFICATE", {})
                configuration["REMOTE_PROXY_SERVER"]["CERTIFICATE"].setdefault("FILE", "")
                configuration["REMOTE_PROXY_SERVER"]["CERTIFICATE"].setdefault("KEY", {})
                configuration["REMOTE_PROXY_SERVER"]["CERTIFICATE"]["KEY"].setdefault("FILE", "")
                configuration["REMOTE_PROXY_SERVER"].setdefault("ACCOUNTS", [])
                i = 0
                while i < len(configuration["REMOTE_PROXY_SERVER"]["ACCOUNTS"]):
                    configuration["REMOTE_PROXY_SERVER"]["ACCOUNTS"][i].setdefault("NAME", "")
                    configuration["REMOTE_PROXY_SERVER"]["ACCOUNTS"][i].setdefault("PASSWORD", "")
                    i = i + 1
            else:
                if configuration["REMOTE_PROXY_SERVER"]["TYPE"] == "WS":
                    configuration["REMOTE_PROXY_SERVER"].setdefault("ADDRESS", "")
                    configuration["REMOTE_PROXY_SERVER"].setdefault("PORT", 0)
                    configuration["REMOTE_PROXY_SERVER"].setdefault("ACCOUNTS", [])
                    i = 0
                    while i < len(configuration["REMOTE_PROXY_SERVER"]["ACCOUNTS"]):
                        configuration["REMOTE_PROXY_SERVER"]["ACCOUNTS"][i].setdefault("NAME", "")
                        configuration["REMOTE_PROXY_SERVER"]["ACCOUNTS"][i].setdefault("PASSWORD", "")
                        i = i + 1
                else:
                    if configuration["REMOTE_PROXY_SERVER"]["TYPE"] == "WSS":
                        configuration["REMOTE_PROXY_SERVER"].setdefault("ADDRESS", "")
                        configuration["REMOTE_PROXY_SERVER"].setdefault("PORT", 0)
                        configuration["REMOTE_PROXY_SERVER"].setdefault("CERTIFICATE", {})
                        configuration["REMOTE_PROXY_SERVER"]["CERTIFICATE"].setdefault("FILE", "")
                        configuration["REMOTE_PROXY_SERVER"]["CERTIFICATE"].setdefault("KEY", {})
                        configuration["REMOTE_PROXY_SERVER"]["CERTIFICATE"]["KEY"].setdefault("FILE", "")
                        configuration["REMOTE_PROXY_SERVER"].setdefault("ACCOUNTS", [])
                        i = 0
                        while i < len(configuration["REMOTE_PROXY_SERVER"]["ACCOUNTS"]):
                            configuration["REMOTE_PROXY_SERVER"]["ACCOUNTS"][i].setdefault("NAME", "")
                            configuration["REMOTE_PROXY_SERVER"]["ACCOUNTS"][i].setdefault("PASSWORD", "")
                            i = i + 1

def createPort(configuration):
    setDefaultConfiguration(configuration, ["PROXY_SERVERS", "REMOTE_PROXY_SERVER"])
    
    if configuration["REMOTE_PROXY_SERVER"]["TYPE"] == "SSH":
        from twunnel.remote_proxy_server__ssh import createSSHPort
        
        return createSSHPort(configuration)
    else:
        if configuration["REMOTE_PROXY_SERVER"]["TYPE"] == "SSL":
            from twunnel.remote_proxy_server__ssl import createSSLPort
            
            return createSSLPort(configuration)
        else:
            if configuration["REMOTE_PROXY_SERVER"]["TYPE"] == "WS":
                from twunnel.remote_proxy_server__ws import createWSPort
                
                return createWSPort(configuration)
            else:
                if configuration["REMOTE_PROXY_SERVER"]["TYPE"] == "WSS":
                    from twunnel.remote_proxy_server__ws import createWSPort
                    
                    return createWSPort(configuration)
                else:
                    return None