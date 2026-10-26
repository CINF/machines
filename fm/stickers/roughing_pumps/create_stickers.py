"""QR code label generator for roughing pumps

usage: python create_stickers.py --pump_list=<list-of-pumps> --offset=<labels-to-skip>
example: python create_stickers.py --pump_list=1-4,6 --offset=5
Above example generates Pump 1, Pump 2, Pump 3, Pump 4 and Pump 6 starting from the 6th
label.

If there is an error in the output, try adding "--debug=True" to the option list

The script generates a list of numbered pumps as specified from the options. It then
checks if a qr code already exists as qr_codes/pump_X.png. If not, then we connect to
the Wekan board and scan the cards for a match to card title "Pump X -" and generate a
qr code from its URL using qrencode and subprocess. We then modfify the svg template
using sed and subprocess to replace designated elements. Lastly we run inkscape and
subprocess to generate the PDF and hide any unwanted labels.

Template is designed for use with Avery L4773-20, polyester, hvid, 63,5 x 33,9 mm
Product number: 1.100.046 (Lyreco)
https://www.lyreco.com/webshop/DADA/etiketter-avery-l4773-20-polyester-hvid-63-5-x-33-9-mm-pakke-a-480-stk-product-000000000001100046.html

Change printer settings for wetting resistant paper type and A4 thick 1 paper thickness
"""
import datetime
from optparse import OptionParser
from pathlib import Path
import subprocess

wekan_init = False
base_url = 'https://wekan.fysik.dtu.dk/b/4JqGTM98ef39AownK/roughing-pumps/'
def get_wekan_cards():
    from wekan import WekanClient
    import wekan_credentials as creds
    wiccan = WekanClient(
        base_url='https://wekan.fysik.dtu.dk',
        username=creds.username,
        password=creds.password,
        )
    board = wiccan.list_boards(regex_filter='Roughing Pumps')[0]
    lists = board.get_lists()
    all_cards = []
    for l in lists:
        cards = l.get_cards()
        all_cards += cards
    print('Connected')
    return all_cards

parser = OptionParser()
parser.add_option('--pump_list') # (Integer) List of pumps
parser.add_option('--offset') # Offset as integer
parser.add_option('--debug')

# Generate pump array
(options, args) = parser.parse_args()
list_of_pumps = []
offset = 0
if options.offset is not None:
    offset = int(options.offset)
debug = False
if options.debug is not None:
    debug = True
if debug:
    print(options)
for i in options.pump_list.split(','):
    if '-' in i:
        i = i.split('-')
        for i_sub in range(int(i[0]), int(i[1]) + 1):
            list_of_pumps.append(i_sub)
    else:
        list_of_pumps.append(int(i))
if debug:
    print(list_of_pumps)
if len(list_of_pumps) + offset > 24:
    raise ValueError(f'With an offset of {offset} only {24 - offset} stickers are available. You have specified {len(list_of_pumps)} pumps')

# Check for existing QR codes
sed_options = []
error_msg = ''
inkscape_actions = ''
for i in range(offset):
    inkscape_actions += f'template_group_{i+1},'
for i, pump in enumerate(list_of_pumps):
    qr_code = Path(f'qr_codes/pump_{pump}.png')
    if not qr_code.is_file():
        if not wekan_init:
            print('Connecting to Wekan...')
            all_cards = get_wekan_cards()
            wekan_init = True
        found_url = False
        for card in all_cards:
            if card.title.startswith(f'Pump {pump} -'):
                url = base_url + card.id
                subprocess.run(['qrencode', '-o', f'qr_codes/pump_{pump}.png', url])
                found_url = True
                break
        if not found_url:
            error_msg += f'"Pump {pump}" not in Wekan?;'
            continue
    sed_options.append('-e')
    sed_options.append(f"s#__image_qr_{i+1+offset}__#qr_codes/pump_{pump}.png#")
    sed_options.append('-e')
    sed_options.append(f"s/__{i+1+offset}__/{pump}/")
if error_msg:
    raise IOError(42, 'Missing QR code files: ' + error_msg.rstrip(';'))
# Change color of SURFCAT
sed_options.append('-e')
sed_options.append('s/#bb0000/#990000/g')
# Change color of brackets
sed_options.append('-e')
sed_options.append('s/stroke:#000000;stroke-width:1/stroke:#555555;stroke-width:0.4/g')
if debug:
    print(sed_options)

for i in range(1+offset+len(list_of_pumps), 25):
    inkscape_actions += f'template_group_{i},'
if inkscape_actions:
    inkscape_actions = 'select-by-id:' + inkscape_actions.rstrip(',')
inkscape_actions += ';selection-hide;export-area-page'
if debug:
    print(inkscape_actions)

output = subprocess.run(["sed", *sed_options, 'template_roughing_pump_stickers.svg'], capture_output=True)
time = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
with open('temp_qrstickers_roughing_pumps.svg', 'w') as f:
    f.write(output.stdout.decode())

output_file = f'./pdfs/{time}_roughing_pump_stickers.pdf'
output = subprocess.run(["inkscape", '--actions=' + inkscape_actions + '', '-o', output_file, './temp_qrstickers_roughing_pumps.svg'], capture_output=True)
if output.returncode != 0:
    print(output)
print('Generated file: {}'.format(Path(output_file).resolve()))
