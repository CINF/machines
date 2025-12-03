import sys
from html.parser import HTMLParser

class Parser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_table = False
        self.c0 = False
        self.c1 = False
        self.c2 = False
        self.id = 0
        self.data = {}
        self.current = ''
        
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'table' and 'id' in attrs and 'dbw.table' in attrs['id']:
            self.in_table = True
        if self.in_table and tag == 'tr':
            self.data[self.id] = {}
        if self.in_table and tag == 'td' and 'class' in attrs:
            if 'column0' in attrs['class']:
                self.c0 = True
            if 'column1' in attrs['class']:
                self.c1 = True
            if 'column2' in attrs['class']:
                self.c2 = True
        
    def handle_endtag(self, tag):
        if tag == 'table':
            self.in_table = False
        if tag == 'td':
            if self.c0:
                self.data[self.id]['user'] = self.current
                self.c0 = False
            if self.c1:
                self.c1 = False
                self.data[self.id]['email'] = self.current
            if self.c2:
                self.c2 = False
                self.data[self.id]['group'] = self.current
            self.current = ''
        if tag == 'tr':
            self.id += 1

    def handle_data(self, data):
        data = data.strip()
        if self.in_table:
            self.current += data

filename = sys.argv[1]
with open(filename, 'r') as f:
    lines = f.readlines()
raw = ''.join(lines)

parser = Parser()
parser.feed(raw)
m0 = max([len(parser.data[s]['user']) for s in parser.data])
m1 = max([len(parser.data[s]['email']) for s in parser.data])
m2 = max([len(parser.data[s]['group']) for s in parser.data])

string = '| {:<{}} | {:<{}} | {:<{}} |'
spacer = f'+{"-"*(m0+2)}+{"-"*(m1+2)}+{"-"*(m2+2)}+'

def all_users():
    print(spacer)
    array = []
    for i in parser.data:
        if i == 0:
            continue
        user = parser.data[i]['user']
        email = parser.data[i]['email']
        group = parser.data[i]['group']
        array.append([user.upper(), user, email, group])
    array.sort()
    for USER, user, email, group in array:
        print(string.format(user, m0, email, m1, group, m2))
        print(spacer)

def active_users():
    print(spacer)
    array = []
    for i in parser.data:
        if i == 0:
            continue
        user = parser.data[i]['user']
        email = parser.data[i]['email']
        group = parser.data[i]['group']
        if '(disabled)' in user:
            continue
        array.append([user.upper(), user, email, group])
    array.sort()
    for USER, user, email, group in array:
        print(string.format(user, m0, email, m1, group, m2))
        print(spacer)

def disabled_users():
    print(spacer)
    array = []
    for i in parser.data:
        if i == 0:
            continue
        user = parser.data[i]['user']
        email = parser.data[i]['email']
        group = parser.data[i]['group']
        if not '(disabled)' in user:
            continue
        array.append([user.upper(), user, email, group])
    array.sort()
    for USER, user, email, group in array:
        print(string.format(user, m0, email, m1, group, m2))
        print(spacer)

def disabled_users_in_groups():
    print(spacer)
    array = []
    for i in parser.data:
        if i == 0:
            continue
        user = parser.data[i]['user']
        email = parser.data[i]['email']
        group = parser.data[i]['group']
        if not '(disabled)' in user:
            continue
        if group == '':
            continue
        array.append([user.upper(), user, email, group])
    array.sort()
    for USER, user, email, group in array:
        print(string.format(user, m0, email, m1, group, m2))
        print(spacer)


msg = """Options:
    1) show all users
    2) show active users
    3) show disabled users
    4) show disabled users still in a group
    0) exit
"""

while True:
    choice = input(msg)

    if choice == '0':
        sys.exit()
    elif choice == '1':
        all_users()
    elif choice == '2':
        active_users()
    elif choice == '3':
        disabled_users()
    elif choice == '4':
        disabled_users_in_groups()
