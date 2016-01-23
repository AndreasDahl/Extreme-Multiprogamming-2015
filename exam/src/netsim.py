from pycsp.greenlets import process, Channel, Parallel, poison, shutdown, Spawn


@process
def do_service(outp):
    """ job process initiated by the server. Handles communication with the
    client after connection has been established

    :param outp:  Writer to connected client
    """
    conn = Channel()
    outp(conn.writer())
    inp = conn.reader()

    while True:
        msg = inp()
        outp('Simulated HTTP Server got:  ' + msg)


@process
def firewall(whitelist, swears, addr, port, client_w):
    """ Firewall layer for the server. All communication should pass through a
    firewall process to reach a server.

    :param whitelist:  list of (ip, port) doubles of allowed clients.
    :param swears:  List of words not allowed in messages to a server job.
    :param addr:
    :param port:
    :param conn:
    """
    # Verify IP/Port whitelist
    if (addr, port) in whitelist:
        client_chan = Channel()
        server_chan = Channel()
        server_r = server_chan.reader()

        Spawn(do_service(server_chan.writer()))
        server_w = server_r()
        client_w(client_chan.writer())
        client_r = client_chan.reader()

        while True:
            msg = client_r()
            for swear in swears:
                if swear in msg:
                    poison(client_w)
                    return
            server_w("[SFW] " + msg)
            client_w("[RESP] " + server_r())
    else:
        poison(client_w)


@process
def server(whitelist, swears, IP):
    while True:  # Only do 10 services then terminate
        addr, port, conn = IP()
        Spawn(firewall(whitelist, swears, addr, port, conn))


@process
def client(IP, id):
    """ Process simulating a client

    :param IP:  Writer to server
    :param id:  Id for this process.
    """
    conn = Channel()
    IP(('10.0.0.12', 80, conn.writer()))
    inp = conn.reader()
    outp = inp()

    for _ in xrange(10):
        outp('Hello from %d ' % id)
        msg = inp()
        print msg
    poison(outp)


if __name__ == '__main__':
    swears = ["objects", "java", "php"]
    whitelist = [("10.0.0.12", 80), ("10.0.0.22", 21), ("10.0.0.28", 22)]
    service = Channel()

    try:
        Parallel(server(whitelist, swears, service.reader()), [client(service.writer(), id) for id in xrange(10)])
    except Exception, msg:
        if str(msg) == 'Deadlock':
            pass  # All simulated clients and servers are shut down... time to terminate
        else:
            print 'Unexpected exception: ', msg

    shutdown()
