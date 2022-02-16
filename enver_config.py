
from os.path import expanduser

def readPasswdFromFile(passwdFileName):
    if passwdFileName.startswith('~'):
        passwdFileName = expanduser(passwdFileName)
    pfile = open(passwdFileName, 'r')
    pw = pfile.readline()
    pfile.close()

    return str(pw.rstrip("\n"))

CONFIG = {
    'station_id': readPasswdFromFile("~/.stationId"),

#    'current_base_url': 'https://www.envertecportal.com/ApiStations',
    'current_base_url': 'https://www.envertecportal.com/ApiInverters/QueryTerminalReal',  # adjust this if API changes
}
