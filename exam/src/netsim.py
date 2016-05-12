from pycsp.greenlets import process, Channel, Parallel, poison, shutdown, Spawn, \
    AltSelect, InputGuard
from time import sleep


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
def firewall(whitelist, swear_words, addr, port, client_w, monitor_r):
    """ Firewall layer for the server. All communication should pass through a
    firewall process to reach a server.

    :param whitelist:  list of (ip, port) doubles of allowed clients.
    :param swear_words:  List of words not allowed in messages to a server job.
    :param addr:
    :param port:
    :param conn:
    """
    # Verify IP/Port whitelist
    if (addr, port) in whitelist:
        # Setup as node between client and server.
        client_chan = Channel()
        server_chan = Channel()
        server_r = server_chan.reader()

        Spawn(do_service(server_chan.writer()))
        server_w = server_r()
        client_w(client_chan.writer())
        client_r = client_chan.reader()

        monitor_writer = None;

        while True:
            g, msg = AltSelect(InputGuard(client_r), InputGuard(monitor_r))

            if (g == client_r):
                # Poison channels if client swears.
                for swear in swear_words:
                    if swear in msg:
                        poison(client_w, server_r, client_r, monitor_r)
                        return

                # If no swears, then forward message to server and write response
                # back to client.
                server_w("[SFW] " + msg)
                client_w("[RESP] " + server_r())
                if monitor_writer is not None:
                    monitor_writer(msg)
            else:
                monitor_writer = msg
    else:
        poison(client_w)


def conn_to_id(addr, port):
    return "%s:%s" % (addr, port)


@process
def server(whitelist, swear_words, IP, monitors_r):
    monitor_writers = {}
    while True:
        monitor_chan = Channel()

        p, msg = AltSelect(InputGuard(IP), InputGuard(monitors_r))
        if p == IP:
            (addr, port, conn) = msg
            Spawn(firewall(whitelist, swear_words, addr, port, conn,
                           monitor_chan.reader()))
            monitor_writers[conn_to_id(addr, port)] = (monitor_chan.writer())
        else:
            (id, conn) = msg
            monitor_writers[id](conn)



@process
def client(IP, port):
    """ Process simulating a client

    :param IP:  Writer to server
    :param id:  Id for this process.
    """
    conn = Channel()
    IP(('10.0.0.12', port, conn.writer()))
    inp = conn.reader()
    outp = inp()

    for _ in xrange(10):
        outp('Hello from %d ' % port)
        msg = inp()
        print msg
        sleep(0.1)
    poison(outp)


@process
def monitor(server_w, id):
    conn = Channel()
    server_w((id, conn.writer()))
    inp = conn.reader()

    # Monitor the first three messages an then kill the connection
    for _ in range(3):
        print "[MONITOR] %s" % inp()

    poison(inp)


if __name__ == '__main__':
    swear_words = ["objects", "java", "php", "5"]
    whitelist = [("10.0.0.12", 0),
                 ("10.0.0.12", 1),
                 ("10.0.0.12", 2),
                 ("10.0.0.12", 3),
                 ("10.0.0.12", 4),
                 # ("10.0.0.12", 5),
                 ("10.0.0.12", 6),
                 ("10.0.0.12", 7),
                 ("10.0.0.12", 8),
                 ("10.0.0.12", 9),]
    service = Channel()
    monitor_access = Channel()

    try:
        Parallel(server(whitelist, swear_words, service.reader(),
                        monitor_access.reader()),
                 [client(service.writer(), id) for id in xrange(10)],
                 monitor(monitor_access.writer(), conn_to_id("10.0.0.12", 6))
                 )
    except Exception as ex:
        if str(ex) == 'Deadlock':
            pass  # All simulated clients and servers are shut down... time to terminate
        else:
            raise

    shutdown()
