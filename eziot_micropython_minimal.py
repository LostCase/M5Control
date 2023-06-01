# Software Development Kit (SDK) for the EZIoT.link Application Programmer Interface (API).
# In other words, the SDK for the EZIoT API.
# This is designed to work for Micropython1.10+ only.

#----------------------------------------------
# IMPORTANT
#----------------------------------------------

print('EZIoT MINI - MicroPython ONLY')

# This is the minimal version of the EZIoT SDK.
# This ONLY works with MicroPython.
# This DOES NOT have the credentials functions.
# The wifi functions are COMMENTED OUT below.

#----------------------------------------------
# user variables
#----------------------------------------------

# the default key and secret "EXAMPLE" is a user
# that everybody can use to test things out

# you will need to use get_creds() to get your
# own account (unless you just like sharing)

api_key = 'N7KY8XR4RLKGCQOY'
api_secret = 'MRTJU4N536TH69ES'
api_version = 1.0

#----------------------------------------------
# general variables
#----------------------------------------------

api_base_path = 'https://eziot.link/api'

#----------------------------------------------
# micropython-only imports
#----------------------------------------------

import usys
import time
import urequests as requests
import ujson as json
from urandom import randint
upython = True

#----------------------------------------------
# data functions
#----------------------------------------------

# get stats for data table
def stats():
##    '''Get the current state of your data.
##    RETURN: dict of item:value pairs'''

    # make request
    code,jdata = _make_request('stats')

    # error
    _check_error(code,jdata)

    # return dict
    return jdata.get('stats',{})

# a meta function to watch for updates
# this uses get_data() in an economical way
def watch(startrows=10,update=10,group=None,device=None):

    # tracking variables
    last_rowid = 0
    if upython:
        update = int(update*1000)
        next_loop = time.ticks_ms()
    else:
        next_loop = int(time.time())

    # infinite loop
    while 1:

        # wait until time
        if upython:
            while time.ticks_diff(time.ticks_ms(),next_loop) < 0:
                time.sleep_ms(int(update/100))
            next_loop = time.ticks_add(next_loop,update)
        else:
            while time.time() < next_loop:
                time.sleep(update/100)
            next_loop += update

        # get rows
        if not last_rowid:
            rows = get_data(startrows,0,group,device)
        else:
            rows = get_data(0,last_rowid,group,device)

        # print oldest first (not the way it comes)
        rows.sort()

        # print
        # row = [rowid,epoch,gmt,ip,group,device,data1,date2,data3,data4]
        for row in rows:
            last_rowid = row[0]
            print('ROW:',row)

        #print('---',next_loop)

# insert a row of data, return rowid of insert
def post_data(group=None,device=None,data1=None,data2=None,data3=None,data4=None):
##    '''Insert a row of data. No values are required.
##    RETURN: rowid (id number) if inserted data'''

    # build data
    # only send non-None values
    data = {}

    # check general data types and string lengths
    # this is a pre-check, the server also checks
    for name,value,length in (('group',group,32),
                              ('device',device,32),
                              ('data1',data1,32),
                              ('data2',data2,32),
                              ('data3',data3,32),
                              ('data4',data4,256)):
        if value != None:
            if type(value) == str:
                assert len(value) <= length
            else:
                assert type(value) in (int,float)
            data[name] = value

    # make request
    code,jdata = _make_request('data/post',data)

    # error
    _check_error(code,jdata)

    # return rowid
    return jdata.get('rowid',0)

# get rows of data
def get_data(count=1,after=None,group=None,device=None):
##    '''Get the "count" most-recent rows of data.
##    Limit return using "after", "group", "device".
##    count = 1-1024 (how many rows to return)
##    after = rowid (only rows after this rowid)
##    group = "groupname" (only rows with this group name)
##    device = "devicename" (only rows with this device name)
##    RETURN: list of data row lists [[row],[row],...]
##    row = [rowid,epoch,gmt,ip,group,device,data1,date2,data3,data4]
##    '''

    # build data
    # only send non-None values
    data = {}

    # count
    assert type(count) == int
    data['count'] = count

    # check general data types and string lengths
    for name,value in (('group',group),('device',device)):
        if value != None:
            if type(value) == str:
                assert len(value) <= 32
            else:
                assert type(value) in (int,float)
            data[name] = value

    # after
    if after != None:
        assert type(after) == int
        data['after'] = after

    # make request
    code,jdata = _make_request('data/get',data)

    # error
    _check_error(code,jdata)

    # return rowid
    return jdata.get('rows',[])

# delete rows of data, return count of rows deleted
def delete_data(rowids=[],before=None,xall=False):
##    '''Delete rows of data. !!!This is PERMANENT!!!
##    rowids = int or list (a rowid of a list of rowids)
##    before = rowid (delete all rowids before this rowid)
##    xall = True|False (delete all rows)
##    RETURN: count of deleted rows
##    '''

    # build data
    # only send non-None values
    data = {}

    # rowids
    if rowids:
        assert type(rowids) in (int,list,tuple)
        if type(rowids) == int:
            data['rowids'] = [rowids]
        else:
            data['rowids'] = [int(x) for x in rowids]

    # before
    if before != None:
        assert type(before) == int
        data['before'] = before

    # xall
    if xall:
        data['xall'] = True

    # make request
    code,jdata = _make_request('data/delete',data)

    # error
    _check_error(code,jdata)

    # return rowid count
    return jdata.get('rows',0)

#----------------------------------------------
# dns functions
#----------------------------------------------

# get dnsid,redirect_url, and hit count
def get_dns():
##    '''Get current dnsid,link,url,hitcount.
##    RETURN: (dnsid,link,url,hits) or (None,None,0)'''

    # make request
    code,jdata = _make_request('dns/get',{})

    # error
    _check_error(code,jdata)

    # make link
    dnsid,url,hits = jdata.get('dns',(None,None,0))
    if dnsid:
        link = 'http://eziot.link/dns/{}'.format(dnsid)
    else:
        link = None

    # done
    return dnsid,link,url,hits

# set dns, return actual dnsid
def set_dns(https=False,port=None,plus=None,dnsid=None):
##    '''Create a DNS entry, based on current IP, given port, and suggested DNSID.
##    RETURN: the actual 'dnsid' value (may have numbers appended to make it unique).
##    The 301 redirect IP will be "http{s}://{ip}:{port}/{plus}"'''

    # build data
    # only send non-None values
    data = {}

    # check general data types and string lengths
    # this is a pre-check, the server also checks
    https = not not https
    for name,value,check in (('https',https,bool),
                              ('port',port,int),
                              ('plus',plus,64),
                              ('dnsid',dnsid,29)):
        if value != None:
            if type(value) == str:
                assert len(value) <= check
            else:
                assert type(value) == check
            data[name] = value

    # make request
    code,jdata = _make_request('dns/set',data)

    # error
    _check_error(code,jdata)

    # return dnsid
    return jdata.get('dnsid',None)

# unset dns, return True|False
def unset_dns():
##    '''Set DNS "url" to None. Preserve current "dnsid" value.
##    Use this to stop DNS service but keep your current ID.
##    RETURN: True'''

    # make request
    code,jdata = _make_request('dns/unset',{})

    # error
    _check_error(code,jdata)

    # return dnsid
    return jdata.get('success',False)

# delete dns entry, return True|False
def delete_dns():
##    '''Delete DNS entry. Delete current "dnsid" value.
##    If you use this function, you might lose your current DNS ID.
##    RETURN: True'''

    # make request
    code,jdata = _make_request('dns/delete',{})

    # error
    _check_error(code,jdata)

    # return dnsid
    return jdata.get('success',False)

#----------------------------------------------
# network functions
#----------------------------------------------

# not a user function
def _check_error(code,jdata):

    # error
    if code != 200 or not jdata.get('success',False):
        message = 'Request error: code: {}, detail: {}'.format(code,jdata.get('message','unknown reason'))
        raise Exception(message)

    # okay
    return True

# not a user function
def _make_request(route,data={},timeout=10):

    # make path
    route = '{}/v{}/{}'.format(api_base_path,float(api_version),route)

    # set up auth
    key,secret,n = None,None,randint(-16,32)
    if api_key:
        key = ''.join((chr(ord(c)+n) for c in api_key))
    if api_secret:
        secret = ''.join((chr(ord(c)+n) for c in api_secret))
    auth = [key,secret,n]

    # make packet
    assert type(data) == dict
    data['auth'] = auth
    packet = json.dumps(data)

    # request
    resp = requests.post(route,data=packet,headers={'Content-Type':'application/json'})

    # build return
    code = resp.status_code
    try:
        jdata = resp.json()
    except:
        jdata = {'json_parse_error':resp.text}

    # done
    return code,jdata

# wifi optional functions

import network
from ubinascii import hexlify

# upython only wifi scan
def wifi_scan():
    if not upython:
        return
    wlan = network.WLAN(network.STA_IF)
    state = wlan.active() # save current state
    wlan.active(True) # set state active
    for ssid,bssid,channel,RSSI,authmode,hidden in wlan.scan():
        ssid = ssid.decode('ascii')
        bssid = hexlify(bssid).decode('ascii')
        if len(bssid) == 12:
            bssid = ':'.join([bssid[x:x+2] for x in range(0,12,2)])
        authmode = ('OPEN','WEP','WPA-PSK','WPA2-PSK','WPA/WPA2-PSK')[min(4,max(0,authmode))]
        if hidden:
            hidden = True
        else:
            False
        print('Network AP:',[ssid,bssid,channel,RSSI,authmode,hidden])
    wlan.active(state) # return to pervious state

# upython-only wifi connect
def wifi_connect(essid,password,timeout=15):
    if not upython:
        return False
    print('Network Connect:',essid)
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        wlan.connect(essid,password)
        time.sleep_ms(100)
        for x in range(timeout):
            if wlan.isconnected():
                break
            time.sleep_ms(500)
    return_value = wlan.isconnected()
    print('Network Connect:',essid,return_value)
    return return_value

# upython-only wifi connect
def wifi_disconnect(timeout=15):
    if not upython:
        return False
    print('Network Disconnect')
    wlan = network.WLAN(network.STA_IF)
    return_value = True
    if wlan.active():
        if wlan.isconnected():
            wlan.disconnect()
            time.sleep_ms(100)
            for x in range(timeout):
                if not wlan.isconnected():
                    break
                time.sleep_ms(1000)
            return_value = not wlan.isconnected()
    wlan.active(False)
    print('Network Disonnect:',return_value)
    return return_value

#----------------------------------------------
# end
#----------------------------------------------
