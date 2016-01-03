import random

from pycsp.parallel import *

capacities = 10
distance_to_first = 5
colours = ['red', 'yellow', 'green']


@process
def producer(chan_out, pause_chan, print_chan):
    ''' Producer and camera
    '''
    pauses = 0
    try:
        # Every iteration in this loop is a "tick" for the whole application
        while True:
            print_chan("produce %s" % pauses)
            # Asyncronusly see if the pause channel has any messages
            c, msg = PriSelect(InputGuard(pause_chan), SkipGuard())
            if c == pause_chan:
                pauses = msg
            print_chan("pauses %s" % pauses)
            if pauses <= 0:
                print_chan("produce something")
                # Produce a ball and send it to the conveyor
                chan_out(random.choice(colours))
            else:
                print_chan("wait %s" % pauses)
                # Do not produce a ball on paused ticks, but decrement the pause counter
                chan_out(None)
                print_chan("after wait")
                pauses -= 1


    except ChannelRetireException:
        print "producer stopping"
    finally:
        print "Producer ended"


@process
def conveyor(chan_in, bins, print_chan):
    ''' Conveyor belt, advances the balls and makes sure they are moved to the
        correct basket
    '''
    length = distance_to_first + 3 * len(colours) - 2
    places = [None] * length

    try:
        while True:
            print_chan("Conveyor")
            # Move everything one. Can be done smarter, but whatever
            for i, v in reversed(list(enumerate(places))):
                if i == len(places) - 1 and v is not None:
                    raise ValueError("Ball ran out of line")
                if i == 0:
                    break
                places[i] = places[i-1]

            places[0] = chan_in()
            print_chan("conveyor ball get %s" % places[0])
            next_bin_loc = distance_to_first
            for i in range(len(bins)):
                if places[next_bin_loc] == colours[i]:
                    bins[i](places[next_bin_loc])
                    places[next_bin_loc] = None
                else:
                    bins[i](None)
                next_bin_loc += 3

    except ChannelRetireException:
        print "conveyor: %s" % places
        retire(chan_in)
        retire(basket_chan)
    finally:
        print "conveyor ended"



@process
def basket(chan_in, pause_chan, capacity, colour, print_chan):
    printer("%s basket initialized" % colour)
    empty_delay = -1
    count = 0
    while True:
        ball = chan_in()
        if ball is not None:
            print_chan("basket %s, %s" % (ball, colour))
            if count >= capacity:
                raise ValueError("BASKET OVERFLOW (%s), empty_delay %s" % (colour, empty_delay))
            if ball != colour:
                raise ValueError("Ball '%s' ended up in wrong basket (%s)" % (ball, colour))
            count += 1
            if count >= capacity:
                print_chan("EMPTYING %s, %s" % (ball, colour))
                count = 0
                pause_chan(5)
    # The basket should not reach this point
    print "BASKET RETIRE"
    retire(chan_in)
    retire(pause_chan)

@process
def printer(chan_in):
    while True:
        msg = chan_in()
        print msg

if __name__ == '__main__':
    print "run"
    producerChan = Channel("producer")
    pauseChan = Channel("pause", len(colours))
    print_chan = Channel("print")
    bin_writers = []

    for colour in colours:
        bin_chan = Channel(colour)
        Spawn(basket(bin_chan.reader(), pauseChan.writer(), capacities, colour, print_chan.writer()))
        bin_writers.append(bin_chan.writer())

    capacities = 10
    Parallel(
        conveyor(producerChan.reader(), bin_writers, print_chan.writer()),
        producer(producerChan.writer(), pauseChan.reader(), print_chan.writer()),
        printer(print_chan.reader()),
    )

    shutdown()
