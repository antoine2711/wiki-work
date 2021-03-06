import traceback
from urllib import quote
from dateutil.parser import parse
import requests
import pdb
import json
import codecs
import re
import csv

from bs4 import BeautifulSoup

from extract import get_submission_wikicode_link
from extract import get_submission_wikicode

import sys
reload(sys)
sys.setdefaultencoding('utf-8')

time_pattern = re.compile("^\! (\d\d\:\d\d)")
presentation_pattern = re.compile("\[\[(.*)\]\]")
level_pattern = re.compile("\((.*)\)")
session_pattern = re.compile("'''(.*)'''")
#event_pattern = re.compile("presentation|unconference|workshop|keynote|posters|logistics")
event_pattern = re.compile('^\|\s*class\s*="(presentation|unconference|workshop|keynote|posters|logistics)"')
logistics_pattern = re.compile("\{\{TNT\|(.*)\}\}")
comment_pattern = re.compile('^\<\!\-\-(.*)\-\-\>')
breakout_pattern = re.compile("(\w*)([Bb]reakout)(\w*)")

c = {"room ballroomwc" : "Ballroom West", 
        "room ballroome"  : "Ballroom Center", 
        "room drummondw"  : "Drummond West", 
        "room drummondc"  : "Drummond Center",
        "room drummonde"  : "Drummond East",
        "room salon45"    : "Salon 3", 
        "room salon6"     : "Salon 5",  
        "room salon7"     : "Joyce/Jarry",
        "room salon8"     : "Salon 1", 
        "room salon9"     : "Salon 4" } 


def generate_csv(file_name, events):

    headers = ['title', 'description', 'faciliator_array', 'faciliators', 'location', 'pathways', 'schedule-block', 'space', 'start', 'end']

    dummy = ['','','','','','','','','','']
    #dummy = ['0','1','2','3','4','5','6','7','8','9']
    
    with codecs.open(file_name, "wb", encoding="utf-8") as fp:
        writer = csv.writer(fp, delimiter=',', quotechar='"', quoting=csv.QUOTE_ALL)
        writer.writerow(headers)

        for event in events:
            if event[1][0] == "presentation":
                try:
                    writer.writerow(dummy)
                    dummy[0] = event[1][1][1]
                    #writer.writerow(event[1][1][1])
                except:
                    pass
    return

def traverse_schedule(schedule):
    for line in schedule:
        yield line
    raise StopIteration()

def get_time(line):
    answer = time_pattern.search(line)
    if answer:
       return answer.group(1)
    else:
       return None

def get_sessions(schedule):

    def get_session_dates(line):
        i = line.find(":")
        if i != -1:
            times = line[i + 1:].split("-")
        return times[0], times[1]

    def get_them_sessions(schedule, session_number):
        these_sessions = []
        for line in schedule:
            n = line.find("Session")
            if n >= 0:
                break
            if line.find('class="header"'):
                result = session_pattern.search(line)
                if result:
                    these_sessions.append(result.group(1))
        return these_sessions

    gen_schedule = traverse_schedule(schedule)
    sessions = {}
    session_number = 1

    for line in gen_schedule:
        if line.find("Session") != -1:
            start, finish = get_session_dates(line)
            the_sessions = get_them_sessions(gen_schedule, session_number)
            sessions[session_number] = (the_sessions, start, finish)
            session_number += 1

    return sessions        


def get_room(line):

    def get_short_name(line):
        i = line.find("=")
        if i != -1:
            start = line.find('"')
            finish = line.find('"', start + 1)
        return c[line[start + 1:finish]]

    def get_long_name(line):
        i = line.find("|")
        j = line.find("&lt")
        if j != -1:
           room = line[i+1:j-1]
        else:
           room = line[i+1:]
        return room

    def get_level(line):
        level = level_pattern.search(line)
        if level:
            return level.group(1)
        else:
            return None

    short_name = get_short_name(line)
    long_name = get_long_name(line)
    level = get_level(line)
    return short_name, long_name, level

def get_url(url):
    response = requests.get(url)
    return response.content

def get_file(file_name):
    lines = None
    with codecs.open(file_name, encoding="utf-8") as fp:
        lines = [line for line in fp]
    return lines

def get_rooms(schedule):

    def get_them(schedule):
        rooms = []
        for line in schedule:
            if line.find('class=\"time\"') != -1:
                break
            else:
                # okay lets process them
                the_room = get_room(line.strip())
                rooms.append(the_room)
        return rooms

    have_rooms = False
    gen_schedule = traverse_schedule(schedule)

    for line in gen_schedule:
        if have_rooms:
            break
        j = line.find('class="time"')
        if j != -1:
            rooms = get_them(gen_schedule)
            have_rooms = True

    return rooms

def get_time(line):
    result = time_pattern.search(line)
    if result:
        return result.group(1)
    else:
        return None

def get_details(event_type, line):

    details = None

    def get_presentation_details(line):
        answer = presentation_pattern.search(line)
        if answer:
            data = answer.group(1).split("|")
            if len(data) == 1:
                data = [data[0],data[0]]
            return data
        else:
            return None

    def get_keynote_details(line):
        detail = None
        i = line.find("|", 1)
        if i != -1:
            detail = line[i + 1:]
            detail = detail.replace("<br/>","")
            detail = detail.replace("<small>","")
            detail = detail.replace("</small>","")
        return detail

    def get_logistics_details(line):
        global logistics_pattern
        answer = logistics_pattern.search(line)
        if answer:
            return answer.group(1)
        answer = get_presentation_details(line)
        if answer:
           return answer
        else:
            return None

    def get_poster_details(line):
        return get_keynote_details(line)

    def get_unconference_details(line):
        #check for break out
        #answer = breakout_pattern.search(line)
        #if answer:
        #    return answer.group(0)
        details = get_presentation_details(line)
        if details:
            return details
        details = get_logistics_details(line)
        if details:
            return details
        else:
            i = line.find("|",5)
            if i != -1:
                return line[i + 1:].strip()

    def get_workshop_details(line):
        answer = get_presentation_details(line)
        if answer:
            return answer
        answer = get_logistics_details(line)
        if answer:
            return answer
        return None

    if event_type == "presentation":
        details = get_presentation_details(line)
    elif event_type == "logistics":
        details = get_logistics_details(line)
    elif event_type == "keynote":
        details = get_keynote_details(line)
    elif event_type == "posters":
        details = get_poster_details(line)
    elif event_type == "unconference":
        details = get_unconference_details(line)
    elif event_type == "workshop":
        details = get_workshop_details(line)
    else:
        details = "I don't know"

    return event_type, details

def get_events(schedule):

    def get_the_events(schedule):
        the_events = []
        line = schedule.next()
        the_time = get_time(line)

        #if next line is not time, we are not in an event block
        if not the_time:
            return []
       
        # check if this is an event
        while True:
            line = schedule.next()
            result = event_pattern.search(line)
            if result:
                break
            result = comment_pattern.search(line)
            if result:
                continue
            break

        if result:
            details = get_details(result.group(1), line)
            the_events.append((the_time, details))

            # now get the rest of the events
            for line in schedule:
                t = get_time(line)
                if t == "16:00":
                    pass
                #if we see the time again, we are done for that block
                if get_time(line):
                    break
                result = event_pattern.search(line)
                if result:
                   details = get_details(result.group(1), line)
                   the_events.append((the_time, details))

        return the_events

    daily_events = []

    schedule_gen = traverse_schedule(schedule)

    for line in schedule_gen:
        if line.find("|-") != -1:
            events = get_the_events(schedule_gen)
            if len(events) == 0:
                continue
            daily_events = daily_events + events
               
    return daily_events


def get_schedule(html_doc):
    soup = BeautifulSoup(html_doc,"lxml")
    schedule = soup.find("textarea")
    return schedule.get_text().splitlines()
    
def add_rooms(information, presentations):
    i = 0
    modulus = len(information)
    for presentation in presentations:
        print "->", presentation, information[i % modulus]
        i = i + 1
    return

def get_submissions_data(url_prefix, events):
    for event in events:
        try:
            if event[1][0] == "presentation":
                url = get_link(url_prefix, event)
                print url
                #get_submission(url)
            #print event[1][1][0]
        except:
            print "problem with", event
            traceback.print_exc()

def get_submission(url):
    text = None
    result = requests.get(url)
    if result >= 200 and result.status_code < 300:
        text = result.text
    else:
        print "PROBLEM:", result.status_code, url
    return text

def get_link(prefix, event):
    link = event[1][1][1]
    link = link.replace(" ","_")
    return prefix + quote(link.encode('utf-8'))

def check_submissions_links(url_prefix, events):
    for event in events:
        try:
            if event[1][0] == "presentation":
                url = get_link(url_prefix, event)
                response = requests.head(url)
                if response.status_code != 200:
                    print url, response.status_code
                else:
                    print url, "OK"
        except:
            print "problem with", event
            traceback.print_exc()

def test_csv():
    html_doc = get_url("https://wikimania2017.wikimedia.org/w/index.php?title=Programme/Friday&action=edit")
    #html_doc = get_url("https://wikimania2017.wikimedia.org/w/index.php?title=Programme/Saturday&action=edit")
    schedule = get_schedule(html_doc)
    events = get_events(schedule)
    prefix = "https://wikimania2017.wikimedia.org/wiki/Submissions/"
    generate_csv("friday.csv", events)

    #get_submissions_data(prefix, events)
    #rooms = get_rooms(schedule)
    #presentations = get_presentations(schedule)
    #sessions = get_sessions(schedule)

    # now lets add the rooms to the presentations

    #add_rooms(rooms, presentations)

def test_submission_links():
    friday="https://wikimania2017.wikimedia.org/w/index.php?title=Programme/Friday&action=edit"
    #saturday="https://wikimania2017.wikimedia.org/w/index.php?title=Programme/Saturday&action=edit"
    #sunday="https://wikimania2017.wikimedia.org/w/index.php?title=Programme/Sunday&action=edit"
    
    #html_doc = get_url("https://wikimania2017.wikimedia.org/w/index.php?title=Programme/Saturday&action=edit")
    html_doc = get_url(friday)
    schedule = get_schedule(html_doc)
    events = get_events(schedule)
    prefix = "https://wikimania2017.wikimedia.org/wiki/Submissions/"
    check_submissions_links(prefix, events)
    return


def main():
    test_submission_links()
   

if __name__ == "__main__":
    main()
