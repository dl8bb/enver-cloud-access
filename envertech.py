#!/usr/bin/env python3

import json
import requests

from os.path import expanduser
from influxdb import InfluxDBClient
from suntime import Sun, SunTimeException
from datetime import datetime, date, time, timezone, timedelta

baseUrl = 'https://www.envertecportal.com/ApiStations/getStationInfo'
stationId   = ''

dbHost      = '192.168.188.47'
dbPort      = 8086
dbUser      = 'admin'
dbPasswd    = ''
dbName      = 'enverbridge'
dbToken     = ''
influxTag   = 'envertech'
influxTopic = 'tele/enverbridge/SENSOR'

timePattern = '%H:%M:%S'

latitude = 51.50168571767066
longitude = 9.752889034951595

def readPasswdFromFile(passwdFileName):
    if passwdFileName.startswith('~'):
        passwdFileName = expanduser(passwdFileName)
    pfile = open(passwdFileName, 'r')
    pw = pfile.readline()
    pfile.close()

    return str(pw.rstrip("\n"))

def pprint(data):
  print(json.dumps(
    data,
    sort_keys = True,
    indent = 4,
    separators = (', ', ' : ')
  ))

def get_page_stationInfo(id):
  url = '{base}?stationId={stationid}'.format(
    base = baseUrl,
    stationid = id
  )
  r = requests.post(url, data = {})
  r.raise_for_status()

  return r.json()


def main():

  global stationId
  stationId = readPasswdFromFile("~/.stationId")

  global dbPasswd
  dbPasswd = readPasswdFromFile("~/.db_passwd")

  sun = Sun(latitude, longitude)

  # Get today's sunrise and sunset in UTC
  today_sr = sun.get_local_sunrise_time() - timedelta(hours=0, minutes=15)
  today_ss = sun.get_local_sunset_time() + timedelta(hours=0, minutes=15)

  print('Sun raise - 15min:  {}\nSun set + 15min:    {}'.
      format(today_sr.isoformat(), today_ss.isoformat()))

  now = datetime.now()

  print('Local time:         {}'.format(now.isoformat()))

  afterSunRise = datetime.strptime(today_sr.strftime(timePattern), timePattern) < \
    datetime.strptime(now.strftime(timePattern), timePattern)

  print("After sun rise: ", afterSunRise)

#  now = now - timedelta(hours=0, minutes=30)
#  print('Corrected local time by 30min: {}'.format(now.isoformat()))

  beforeSunSet = datetime.strptime(today_ss.strftime(timePattern), timePattern) > \
    datetime.strptime(now.strftime(timePattern), timePattern)

  print("Before sun set: ", beforeSunSet)

  if afterSunRise and beforeSunSet:

    # precision is in minutes as stated above
    time_precision = 'm'

    client = InfluxDBClient(dbHost, dbPort, dbUser, dbPasswd, dbName)
    #client = InfluxDBClient(dbHost, dbPort, username=None, password=None, headers={"Authorization": dbToken})

    response = get_page_stationInfo(str(stationId))['Data']

    pprint(response)

    response['Power'] = float(response['Power'])
    response['Etoday'] = float(response['Etoday'])

    # "StrCO2" : "0.027 ton",
    response['NumC02'] = float(response['StrCO2'].replace(" ton", ""))

    if (response['StrPeakPower'].endswith(" KW")):
      # "StrPeakPower" : "1.02986 KW",
      response['PeakPower'] = float(response['StrPeakPower'].replace(" KW", "")) * 1000
    else:
      # "StrPeakPower" : "931.68 W",
      response['PeakPower'] = float(response['StrPeakPower'].replace(" W", ""))

    # "UnitEMonth" : "10.05 KWh",
    response['StrUnitEMonth'] = response['UnitEMonth']
    response['UnitEMonth'] = float(response['UnitEMonth'].replace(" KWh", ""))

    # "UnitEToday" : "0.31 KWh",
    response['StrUnitEToday'] = response['UnitEToday']
    if (response['UnitEToday'].endswith(" KKh")):
      response['UnitEToday'] = float(response['UnitEToday'].replace(" KKh", ""))
    else:
      response['UnitEToday'] = float(response['UnitEToday'].replace(" KWh", ""))

    # "UnitETotal" : "26.94 KWh",
    # "UnitETotal" : "1.34 MWh"
    # response['StrUnitETotal'] = response['UnitETotal']
    if (response['UnitETotal'].endswith(" MWh")):
      response['UnitETotal'] = float(response['UnitETotal'].replace(" MWh", "")) * 1000
    else:
      response['UnitETotal'] = float(response['UnitETotal'].replace(" KWh", ""))

    # "UnitEYear" : "26.94 KWh"
    # response['StrUnitEYear'] = response['UnitEYear']
    if (response['UnitEYear'].endswith(" MWh")):
      response['UnitEYear'] = float(response['UnitEYear'].replace(" MWh", "")) * 1000
    else:
      response['UnitEYear'] = float(response['UnitEYear'].replace(" KWh", ""))

    # "UnitCapacity" : "1.2 KWp"
    response['StrUnitCapacity'] = response['UnitCapacity']
    # response['UnitCapacity'] = float(response['UnitCapacity'].replace(" KWp", "")) * 1000

    points = [
      {
        'measurement': dbName, 
        'tags': {
          'host': 'tuya',
          'topic': influxTopic,
          'region': "de"
        },
        'time': datetime.now(timezone.utc).isoformat(),
        'fields': response
      }
    ]

    pprint(points)

    # write the datapoint
    client.write_points(
      points = points,
      time_precision = time_precision
    )
  else:
    print('{} *** Nothing to do!'.format(now.isoformat())) 


if __name__ == "__main__" : main()

