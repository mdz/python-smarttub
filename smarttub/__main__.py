import datetime
import logging
from pprint import pprint
import sys

from . import SmartTub

logging.basicConfig(level=logging.DEBUG)

st = SmartTub()
st.login(*sys.argv[1:])
account = st.get_account()
print(account)
spas = account.get_spas()
print(spas)
for spa in spas:
    pprint(spa.get_status())
    for pump in spa.get_pumps():
        print(pump)
    for light in spa.get_lights():
        print(light)
    errors = spa.get_errors()
    pprint(errors)
    for reminder in spa.get_reminders():
        print(reminder)
    debug_status = spa.get_debug_status()
    pprint(debug_status)
    energy_usage_day = spa.get_energy_usage('DAY', end_date=datetime.date.today(), start_date=datetime.date.today() - datetime.timedelta(days=7))
    pprint(energy_usage_day)

