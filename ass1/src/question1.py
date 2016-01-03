import random

from pycsp.parallel import *


@process
def producer(chan_out, pause_chan, print_chan):
    ''' Producer and camera
    '''
    colours = ['red', 'yellow', 'green']
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
                print_chan("produce somthing")
                # Produce a ball and send it to the conveyor
                chan_out(random.choice(colours))
            else:
                print_chan("wait %s" % pauses)
                # Do not produce a ball on paused ticks, but decrement the pause counter
                chan_out(None)
                pauses -= 1


    except ChannelRetireException:
        print "producer stopping"
    finally:
        print "Producer ended"


@process
def conveyor(chan_in, red_chan, yellow_chan, green_chan, print_chan):
    ''' Conveyor belt, advances the balls and makes sure they are moved to the
        correct basket
    '''
    length = 11
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
            print_chan("conveyor ball get")
            if places[4] == "red":
                red_chan(places[4])
                places[4] = None
            if places[7] == "yellow":
                yellow_chan(places[7])
                places[7] = None
            if places[10] == "green":
                green_chan(places[10])
                places[10] = None

    except ChannelRetireException:
        print "conveyor: %s" % places
        retire(chan_in)
        retire(basket_chan)
    finally:
        print "conveyor ended"



@process
def basket(chan_in, pause_chan, capacity, colour, print_chan):
    print colour, "basket initialized"
    count = 0
    while True:
        ball = chan_in()
        if ball is not None:
            print_chan("basket %s, %s" % (ball, colour))
            if count >= capacity:
                raise ValueError("BASKET OVERFLOW (%s)" % colour)
            if ball != colour:
                raise ValueError("Ball '%s' ended up in wrong basket (%s)" % (ball, colour))
            count += 1
            if count >= capacity:
                print_chan("EMPTYING %s, %s" % (ball, colour))
                count = 0
                pause_chan(5)  # notify number of ticks the basket require to empty itself
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
    red_chan = Channel("red")
    yellow_chan = Channel("yellow")
    green_chan = Channel("green")
    pauseChan = Channel("pause")
    print_chan = Channel("print")
    capacities = 10
    Parallel(
        basket(red_chan.reader(), pauseChan.writer(), capacities, "red", print_chan.writer()),
        basket(yellow_chan.reader(), pauseChan.writer(), capacities, "yellow", print_chan.writer()),
        basket(green_chan.reader(), pauseChan.writer(), capacities, "green", print_chan.writer()),
        conveyor(producerChan.reader(), red_chan.writer(), yellow_chan.writer(), green_chan.writer(), print_chan.writer()),
        producer(producerChan.writer(), pauseChan.reader(), print_chan.writer()),
        printer(print_chan.reader()),
    )

    shutdown()
