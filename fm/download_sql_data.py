#import MySQLdb
from cinfdata import Cinfdata

db = Cinfdata('omicron', use_caching=False) # pylint: disable=invalid-name
query = 'SELECT id, Codename FROM dateplots_descriptions WHERE Codename LIKE %s'
db.cursor.execute(query, ('omicron_dataq_ch8',))
result = db.cursor.fetchall()

write_string = '{},{}\r\n'
# unix_timestamp(time)
#  and time between "2025-02-10 09:21" and "2025-05-21 09:22"
data_query = 'SELECT time, value FROM dateplots_omicron where type = %s and time between "2025-07-31 10:33:26" and "2025-07-31 10:39:25" order by time'
for type_, codename in result:
    print('Fetching: ', codename)
    size = db.cursor.execute(data_query, (type_,))
    data = db.cursor.fetchall()
    print('Writing: ', codename)
    print(size)
    f = open('/home/jejsor/sql_data/' + codename + '.csv', 'w')
    for time, value in data:
        f.write(write_string.format(time, value))
    f.close()
    print('Writing done')
    
print('Done')
