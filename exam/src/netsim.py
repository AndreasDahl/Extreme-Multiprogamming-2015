from pycsp.greenlets import process, Channel, Parallel, poison, shutdown, Spawn


@process
def do_service(outp):
    conn = Channel()
    outp(conn.writer())
    inp = conn.reader()

    while True:
        msg = inp()
        outp('Simulated HTTP Server got:  ' + msg)


@process
def firewall(whitelist, addr, port, conn):
    print addr, port, whitelist
    if (addr, port) in whitelist:
        Spawn(do_service(conn))


@process
def server(whitelist, IP):
    while True:  # Only do 10 services then terminate
        addr, port, conn = IP()
        Spawn(firewall(whitelist, addr, port, conn))


@process
def client(IP, id):
    conn = Channel()
    IP(('10.0.0.12', 80, conn.writer()))
    inp = conn.reader()
    outp = inp()

    for _ in xrange(10):
        outp('Hello from %d ' % id)
        msg = inp()
        print msg
    poison(outp)


whitelist = [("10.0.0.12", 80), ("10.0.0.22", 21), ("10.0.0.28", 22)]
service = Channel()

try:
    Parallel(server(whitelist, service.reader()), [client(service.writer(), id) for id in xrange(10)])
except Exception, msg:
    if str(msg) == 'Deadlock':
        pass  # All simulated clients and servers are shut down... time to terminate
    else:
        print 'Unexpected exception: ', msg

shutdown()
