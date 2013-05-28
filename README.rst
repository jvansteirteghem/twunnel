Twunnel
=======

A HTTP/SOCKS5 tunnel for Twisted.

Supports:

- HTTP
- HTTP + Basic authentication
- SOCKS5

Usage
-----

.. code:: python

    import twunnel

    protocolFactory = ..

    configuration = {
        "PROXY_SERVER": {
            "TYPE": "HTTP",
            "ADDRESS": "127.0.0.1",
            "PORT": 8080,
            "AUTHENTICATION": {
                "USERNAME": "1",
                "PASSWORD": "2"
            }
        }
    }

    tunnel = twunnel.Tunnel(configuration)
    tunnel.connect("www.google.com", 80, protocolFactory)

.. code:: python

    import twunnel

    protocolFactory = ..

    configuration = {
        "PROXY_SERVER": {
            "TYPE": "SOCKS5",
            "ADDRESS": "127.0.0.1",
            "PORT": 1080
        }
    }

    tunnel = twunnel.Tunnel(configuration)
    tunnel.connect("www.google.com", 443, protocolFactory)

License
-------

Uses the `MIT`_ license.


.. _MIT: http://opensource.org/licenses/MIT
