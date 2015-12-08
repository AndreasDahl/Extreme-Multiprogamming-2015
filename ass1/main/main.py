import random

from pycsp.parallel import *


colours = ['red', 'yellow', 'green']


@process
def producer(chan_out):
    for _ in range(10):
        chan_out(random.choice(colours))
    retire(chan_out)


@process
def conveyor(chan_in, basket_chan):
    places = [None] * 3

    try:
        while True:
            # Move everything one. Can be done smarter, but whatever
            for i, v in reversed(list(enumerate(places))):
                if i == len(places) - 1 and v is not None:
                    raise ValueError("Ball ran out of line")
                if i == 0:
                    break
                places[i] = places[i-1]

            places[0] = chan_in()
            basket_chan(places[2])
            places[2] = None
    except ChannelRetireException:
        print "conveyor: %s" % places
        retire(basket_chan)


@process
def basket(chan_in):
    count = 0
    while True:
        ball = chan_in()
        print ball
        count += 1


@process
def camera(chan_in, chan_out):
    ball = chan_in()
    chan_out(ball)


if __name__ == '__main__':
    producerChan = Channel("producer")
    basketChan = Channel("basket")

    Parallel(
        basket(basketChan.reader()),
        conveyor(producerChan.reader(), basketChan.writer()),
        producer(producerChan.writer())
    )

    shutdown()

