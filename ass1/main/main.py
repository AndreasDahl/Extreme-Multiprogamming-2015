import random

from pycsp.parallel import *


colours = ['red', 'yellow', 'green']


@process
def producer(chan_out, pause_chan):
    ''' Producer and camera
    '''
    pauses = 0
    try:
        # Every iteration in this loop is a "tick" for the whole application
        while True:
            # Asyncronusly see if the pause channel has any messages
            c, msg = PriSelect(InputGuard(pause_chan), SkipGuard())
            if msg is not None:
                pauses = msg
            if pauses <= 0:
                # Produce a ball and send it to the conveyor
                chan_out(random.choice(colours))
            else:
                # Do not produce a ball on paused ticks, but decrement the pause counter
                pauses -= 1

    except ChannelRetireException:
        print "producer stopping"


@process
def conveyor(chan_in, basket_chan):
    ''' Conveyor belt, advances the balls and makes sure they are moved to the
        correct basket

        TODO: Support multiple baskets
        TODO: More flexible belt length
    '''
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
        retire(chan_in)
        retire(basket_chan)



@process
def basket(chan_in, pause_chan, capacity):
    count = 0
    while True:
        ball = chan_in()
        if ball is not None:
            print ball
            count += 1
            if count >= capacity:
                count = 0
                pause_chan(5)  # notify number of ticks the basket require to empty itself
    # The basket should not reach this point
    print "BASKET RETIRE"
    retire(chan_in)
    retire(pause_chan)


@process
def camera(chan_in, chan_out):
    ball = chan_in()
    chan_out(ball)


if __name__ == '__main__':
    print "run"
    producerChan = Channel("producer")
    basketChan = Channel("basket")
    pauseChan = Channel("pause")
    capacities = 10

    Parallel(
        basket(basketChan.reader(), pauseChan.writer(), capacities),
        conveyor(producerChan.reader(), basketChan.writer()),
        producer(producerChan.writer(), pauseChan.reader())
    )

    shutdown()
