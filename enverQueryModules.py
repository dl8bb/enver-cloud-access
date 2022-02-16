#!/usr/bin/env python3

from twisted.internet.task import react
import treq
import json

from os.path import expanduser
from influxdb import InfluxDBClient
from suntime import Sun, SunTimeException
from datetime import datetime, date, time, timezone, timedelta

from enver_config import CONFIG

dbHost        = '192.168.188.47'
dbPort        = 8086
dbUser        = 'admin'
dbPasswd      = ''
dbName        = 'enverbridge'
dbMeasurement = 'modules'

latitude = 51.50168571767066
longitude = 9.752889034951595

datePattern = "%Y-%m-%dT%H:%M:%S.%f"

url_ = 'https://www.envertecportal.com/ApiStations'
hdrs = [
 'Content-Type: application/x-www-form-urlencoded; charset=UTF-8',
 'Content-Length: 0',
 'Referer: https://www.envertecportal.com/terminal/systemreal',
 'Accept: application/json, text/javascript, */*; q=0.01',
 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_5) AppleWebKit/603.3.8 (KHTML, like Gecko) Version/10.1.2 Safari/603.3.8',
 'Origin: https://www.envertecportal.com',
 'X-Requested-With: XMLHttpRequest',
]
data="""
page=1&perPage=50&orderBy=GATEWAYSN&whereCondition=%7B%22STATIONID%22%3A%22{stationid}%22%7D
"""

stationid = ""

def pprint(data):
    print(json.dumps(
        data,
        sort_keys = True,
        indent = 4,
        separators = (', ', ' : ')
    ))

def readPasswdFromFile(passwdFileName):
    if passwdFileName.startswith('~'):
        passwdFileName = expanduser(passwdFileName)
    pfile = open(passwdFileName, 'r')
    pw = pfile.readline()
    pfile.close()

    return str(pw.rstrip("\n"))

def updateInflux(gwsn, sn, status, timeStamp, data):

    global dbPasswd
    dbPasswd = readPasswdFromFile("~/.db_passwd")

    client = InfluxDBClient(dbHost, dbPort, dbUser, dbPasswd, dbName)

    topic = 'tele/enver_' + gwsn + '_' + sn + '/SENSOR'

    points = [
        {
            'time': timeStamp,
            'measurement': dbMeasurement,
            'tags': {
                'host':  'tuya',
                'topic': topic,
                'sn':    gwsn + '.' + sn,
                'stat':  status
            },
            'fields': data
        }
    ]

    print("updateInflux: ", sn)
    pprint(points)

    # precision is in seconds
    time_precision = 's'

    # write the datapoint
    client.write_points(
        points = points,
        time_precision = time_precision
    )

def mapData(data):
    res = dict()

    res['ACCURRENCY'] = float(data.get('ACCURRENCY'))
    res['ACVOLTAGE'] = float(data.get('ACVOLTAGE'))
    res['DAYENERGY'] = float(data.get('DAYENERGY'))
    res['DCVOLTAGE'] = float(data.get('DCVOLTAGE'))
    res['ENERGY'] = float(data.get('ENERGY'))
    res['FREQUENCY'] = float(data.get('FREQUENCY'))
    res['GATEWAYALIAS'] = data.get('GATEWAYALIAS')
    res['GATEWAYSN'] = data.get('GATEWAYSN')
    res['POWER'] = float(data.get('POWER'))
    res['SITETIME'] = data.get('SITETIME')
    res['SN'] = data.get('SN')
    res['SNALIAS'] = data.get('SNALIAS')
    res['SNID'] = data.get('SNID')
    res['STATIONID'] = stationid     # data.get('STATIONID')
    res['STATUS'] = data.get('STATUS')
    res['TEMPERATURE'] = float(data.get('TEMPERATURE'))

    return res

def update(data):
    for i in data:
        sn = i.get('SN')
        gatewaySn = i.get('GATEWAYSN')
        status = i.get('STATUS')
        influxData = mapData(i)
        updateInflux(gatewaySn, sn, status, datetime.now(timezone.utc).isoformat(), influxData)

        #if status == '1':
        #    updateInflux(gatewaySn, sn, status, datetime.now(timezone.utc).isoformat(), i)
        #else:
        #    print("Status:", gatewaySn, sn, status)

def main(*args):
    global stationid
    hdrs_ = dict(map(str.strip, x.split(':', 1)) for x in hdrs)  # morph headers to dict
    # get stationid from CONFIG
    stationid = CONFIG.get('station_id') or 0
    base = CONFIG.get('current_base_url') or url_
    uri = base + '?' + data.format(stationid=stationid).strip()
    print(uri, hdrs_)
    dfr = treq.post(uri, headers=hdrs_)

    def getQueryModules(r):
        data = r['Data']
        queryResults = data.get("QueryResults")
        return queryResults

    dfr.addCallback(treq.json_content)
    dfr.addCallback(getQueryModules)
    return dfr


def _main(*args):
    dfr = main([])
    dfr.addCallback(update)
    return dfr


if __name__=="__main__":
    react(_main, [])
