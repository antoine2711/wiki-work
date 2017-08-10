import traceback
from urllib import quote
from dateutil.parser import parse
from datetime import timedelta
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


comment = '^\<\!\-\-(.*)\-\-\>'
p = "\[\[(.*)\]\]"
s = "'''(.*)'''"
events = '^\|.*class\s*="(presentation|unconference|workshop|keynote|posters|logistics)"'
l = "\{\{TNT\|(.*)\}\}"
b = "(\w*[Bb]reakout\w*)"

data =  s + "|" + p + "|" + l + "|" + b

event_pattern = re.compile(events)
data_pattern = re.compile(data)
comment_pattern = re.compile(comment)
#section_pattern = re.compile('\|\- style\="vertical\-align: top\;"')
section_pattern = re.compile('\|\-')

def traverse_schedule(schedule):
    for line in schedule:
        yield line
    raise StopIteration()

def get_url(url):
    response = requests.get(url)
    return response.content


def get_schedule(html_doc):
    soup = BeautifulSoup(html_doc,"lxml")
    schedule = soup.find("textarea")
    return schedule.get_text().splitlines()

def get_data(line):
    columns = line.split("|")
    return columns[:-1]


def get_section(program):
    #we are in a section
    book_end = program.next()
    print "this is the book_end", book_end
    for line in program:
        if line == book_end:
            break
        print "->", line
    print "---"
    return

def test_patterns():
    program = ["https://wikimania2017.wikimedia.org/w/index.php?title=Programme/Friday&action=edit",
               "https://wikimania2017.wikimedia.org/w/index.php?title=Programme/Saturday&action=edit",
               "https://wikimania2017.wikimedia.org/w/index.php?title=Programme/Sunday&action=edit"]
    process_programme(program[0])

def process_programme(url):
    html_doc = get_url(url)
    schedule = get_schedule(html_doc)

    program = traverse_schedule(schedule)

    for line in program:

        # ignore comments
        comment_result = comment_pattern.search(line)
        if comment_result:
            continue

        section_result = section_pattern.search(line)
        if section_result:
            get_section(program)

        """
        event_result = event_pattern.search(line)
        if event_result:
            event_type = event_result.group(1) 
            data_result = data_pattern.search(line)
            if data_result:
                print event_type, data_result.group(0)
        """
        

def main():
    test_patterns()
   

if __name__ == "__main__":
    main()
