from flask import Flask
import json
import requests
import time

app = Flask(__name__)

globus_url = "https://transfer.api.globus.org/v0.10/private/web_stats"
"""
Example:
  {
    "new": {
      "bytes": 1955402227052862012,
      "files": 209318008246,
      "time": "2023-04-22 22:47:02.125357"
    },
    "old": {
      "bytes": 1955398391739215761,
      "files": 209317930020,
      "time": "2023-04-22 22:42:01.610209"
    }
  }
"""

def get_data(url):
    response = requests.get(url)

    data = response.json()
    json_data = json.dumps(data, indent=2)
    data = json.loads(json_data)

    bytes_value = int(data['new']['bytes'])
    bytes_to_show = bytes_value/(10 ** 9)
    bytes_to_show %= 10 ** 7
    bytes_to_show = int(bytes_to_show)
    print(f'\nGlobus bytes: {bytes_to_show} from {bytes_value}')
    return(bytes_to_show)
  
cache = {}
cache['last_value']    = get_data(globus_url)
cache['last_time']     = int(time.time())
cache['earlier_value'] = cache['last_value'] - 1
cache['earlier_time']  = cache['last_time'] - 1
cache['index']         = 0
cache['scale_factor']  = 0.5

# If Globus web counter value hasn't changed, then estimate it to be
#     <time since last reading> * <counter change rate>
# Where:
#     <counter change rate> = <recent change in value> / <recent change in seconds>
#                           = (last_value - earlier_value)/ (last_time - earlier_time))
#
# The web counter can stay the same for a while, so this can result in estimates getting ahead of reports. 
# If so, then switch to increasing by just 1 at a time.

@app.route('/')
def hello_world():
    this_value    = get_data(globus_url)
    this_time     = int(time.time())
    last_value    = cache['last_value']
    last_time     = cache['last_time']
    earlier_value = cache['earlier_value']
    earlier_time  = cache['earlier_time']
    index         = cache['index']
    
    # print(f'== Round {cache["index"]}:')
    # print(f'    Old : {earlier_value} at {earlier_time}') 
    # print(f'    Last: {last_value} at {last_time}') 
    # print(f'    New : {this_value} at {this_time}') 
    
    if this_value == last_value:  # If no change in web counter
        # Set increment as above
        increment = int( ((this_time - last_time)*(last_value - earlier_value)/(last_time - earlier_time)) * cache['scale_factor'] )
        if increment < 1:
            increment = 1
        print(f"{index}: No change, so increase by {increment} to {this_value+increment}; scale-factor={cache['scale_factor']}")
        cache['scale_factor']  /= 2 # Scale back in case repeated instances 
        this_value += increment
    elif this_value > last_value:
        cache['earlier_value'] = last_value
        cache['earlier_time']  = last_time
        cache['scale_factor']  = 0.5
        print(f'{index}: Increase by {this_value-last_value} to {this_value}')
    else:  # this_value < last_value, which means that we increased by too much last time
        this_value = last_value + 1
        print(f'{index}: Ahead, so increment by 1 to  {this_value}')

    cache['last_value']    = this_value
    cache['last_time']     = this_time
    cache['index']         = cache['index'] + 1
    
    rv = f'{{"number": {this_value}}}'
    return rv
