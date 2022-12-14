#!/usr/bin/env python

from collections import defaultdict
from gc import get_objects

""" This is just the skeleton parts of the memory leak testing routine
suggested by gnibbler  ref 1641280
search stackoverflow 'gnibbler memory leak'
in pi3d the while loop is the Display.loop_running() and print is a p3
type function with braces
"""

str_num = 0
before = defaultdict(int)
after = defaultdict(int)
sample_period = 17
    
# Display scene and rotate shape
def leak_check():
    global str_num, before, after
    
    str_num += 1
    if str_num == sample_period: # large nough number to give it a chance to 'bed in'
        for i in get_objects():
            before[type(i)] += 1
    if (str_num % 50) == sample_period: # same number as above
        print "--------------------"
    for i in after:
        after[i] = 0
    for i in get_objects():
        after[type(i)] += 1
    for i in after:
        if after[i] - before[i]:
            print "{} {}".format(i, after[i] - before[i])
            
