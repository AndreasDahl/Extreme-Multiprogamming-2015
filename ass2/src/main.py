
import re
from pycsp.parallel import *


def look():
    """ The 'look' command string
    """
    return 'look'

def take():
    """ The 'take' command string
    """
    return 'take'

def leave():
    """ The 'leave' command string
    """
    return 'leave'

def index_to_direction(i):
    if i == 0:
        return 'N'
    if i == 1:
        return 'E'
    if i == 2:
        return 'S'
    return 'W'

def direction_to_index(d):
    if d.lower() == 'n':
        return 0
    if d.lower() == 'e':
        return 1
    if d.lower() == 's':
        return 2
    return 3

def is_direction(s):
    return (s.lower() == 'n' or
         s.lower() == 'e' or
         s.lower() == 's' or
         s.lower() == 'w')

@process
def room(agent_reader, room_writer, description, objects, adjacent):
    """

    adjacent    -- Four-list with adjacent rooms [North, East, South, West]
    description -- Description of room
    objects     -- Objects contained in the room
    """
    while True:
        request = agent_reader()
        if request == look():
            obj_list = ''
            if objects:
                obj_list = 'In the room you see\n'
                for obj in objects:
                    obj_list += '- %s\n' % obj
            adj_list = ''
            for i in range(len(adjacent)):
                if not adjacent[i] is None:
                    adj_list += "To the %s there is a door\n" \
                                % index_to_direction(i)
            room_writer(description + '\n' + adj_list + obj_list)
        elif re.match(take(), request):
            taken = request[4:].strip()
            if taken in objects:
                objects.remove(taken)
                room_writer("took %s" % taken)
            else:
                room_writer("nothing")
        elif re.match(leave(), request):
            objects.append(request[5:].strip())
        elif is_direction(request):
            room_writer(adjacent[direction_to_index(request)])

        else:
            raise ValueError("UNKNOWN ROOM COMMAND")


@process
def agent(chan_in, room_reader, room_writer, print_writer, inventory):
    while True:
        command = chan_in()
        if command == look():               # Look
            room_writer(command)
            response = room_reader()
            if inventory:
                response = response + "You are holding\n"
                for item in inventory:
                    response += "- %s\n" % item
            print_writer(response)
        elif re.match(take(), command):     # Take
            room_writer(command)
            response = room_reader()
            if re.match("took", response):
                got = response[4:].strip()
                inventory.append(got)
                print_writer("You picked up %s\n" % got)
            else:
                print_writer("You are not able to pick up %s\n" \
                        % command[4:].strip())
        elif re.match(leave(), command):    # Leave
            obj = command[5:].strip()
            if obj in inventory:
                inventory.remove(obj)
                room_writer('leave %s' % obj)
                print_writer("you left '%s' in the room\n" % obj)
            else:
                print_writer("You do not have '%s' in your possession\n" % obj)
        elif is_direction(command):
            room_writer(command)
            response = room_reader()
            if response is None:
                print_writer("It is not possible to move '%s' from here\n" \
                        % command)
            else:
                room_writer = response
                print_writer("You moved '%s'\n" % command)
        else:
            print_writer("Invalid Command\n")

@process
def terminal(chan_in, chan_out):
    print("Welcome to xmpMUD")
    while True:
        command = raw_input(">> ")
        if command == 'exit':
            poison(chan_out)
            poison(chan_in)
            break

        chan_out(command)
        print(chan_in()),


if __name__ == '__main__':
    command_chan = Channel()
    print_chan = Channel()
    agent_response_chan = Channel()
    s_chan = Channel()
    n_chan = Channel()
    Parallel(
        terminal(print_chan.reader(), command_chan.writer()),
        agent(command_chan.reader(), agent_response_chan.reader(),
                s_chan.writer(), print_chan.writer(), []),
        room(s_chan.reader(), agent_response_chan.writer(),
                "You find yourself in a slimy treasure room", ['gold', 'slime'],
                [n_chan.writer(), None, None, None]),
        room(n_chan.reader(), agent_response_chan.writer(), "Northen room",
                ['tooth'], [None, None, s_chan.writer(), None])
    )

    shutdown()
