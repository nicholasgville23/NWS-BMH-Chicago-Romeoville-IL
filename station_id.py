#! /usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import json
import logging
import traceback
from tts_utils import produce_wav_file

log = logging.getLogger("BMH")

STATION_CALLSIGN = "W N G 6 89"

LONG_STATION_ID = (
    "This is NOAA Weather Radio station, W N G 6 89, broadcasting weather "
    "information for Val paraiso, Indiana. Broadcasting on a frequency of "
    "162.400 and 162.450 megahertz, from a transmitter near Porter Township. "
    "This station serves residents and counties of northwest Indiana. "
    "This Broadcasts originates from the National Weather Service Forecast, Office in Romeoville, Illinois. "
    "Visit us on the web at weather, dot, gov, slash, chicago."
)

SHORT_STATION_ID = (
    "Your listening to NOAA Weather Radio, W N G 6 89, Serving Porter Township, Val paraiso, Rensselaer, and Hebron."
)

SEVERE_STATION_ID = (
    "This is NOAA Weather Radio, W N G 6 89 in Porter Township. Severe "
    "Weather is occurring or forecast to occur in the listening area. "
    "Standard broadcasts will be curtailed to bring you the latest severe "
    "weather information. Normal broadcasts will resume when the threat of "
    "severe weather has ended."
)

STATION_ID_VARIANTS = {
    'short': SHORT_STATION_ID,
    'long': LONG_STATION_ID,
    'severe': SEVERE_STATION_ID,
}

STATION_ID_FILENAMES = {
    'short': 'ShortStationID.wav',
    'long': 'StationID.wav',
    'severe': 'SevereStationID.wav',
}

def _render_station_id(station_text, output_name):
    try:
        with open('config.json', encoding='utf-8') as f:
            config = json.load(f)
        with open('phonemeDB.json', encoding='utf-8') as f:
            phonemeDB = json.load(f)
        replaceDict = phonemeDB['replace']
        phonemeDict = phonemeDB['phonemes']
        speed = config['ttsSpeed']
        pause = config['endPause']

        for phoneme, replacement in phonemeDict.items():
            log.debug('[STATIONID PHONEMES] Replacing %s with %s', phoneme, replacement)
            station_text = station_text.replace(phoneme, f'<vtml_phoneme alphabet="x-cmu" ph="{replacement}"></vtml_phoneme>')

        for word, replacement in replaceDict.items():
            log.debug('[STATIONID PHONEMES] Replacing %s with %s', word, replacement)
            if '*PAUSE' in replacement:
                parts = replacement.split('*')
                pauseTime = parts[2].split('-')[1]
                word_to_find = word.replace(f'*PAUSE-{pauseTime}*', f'<vtml_pause time="{pauseTime}"/>')
                station_text = station_text.replace(word_to_find, replacement)
            else:
                station_text = station_text.replace(word, replacement)

        final_text = f'<vtml_volume value="200"> <vtml_speed value="{speed}"> {station_text} <vtml_pause time="{pause}"/> </vtml_volume> </vtml_speed>'
        final_text = final_text.replace('\n', ' ').replace('\r', ' ')

        log.debug('[STATIONID] Final Text: %s', final_text)
        produce_wav_file(final_text, output_name)

    except Exception:
        log.error('[STATIONID] %s', traceback.format_exc())
        sys.exit(1)

def getStationID(variant='short'):
    variant = str(variant).lower()
    if variant not in STATION_ID_VARIANTS:
        log.error('[STATIONID Unknown station ID variant: %s', variant)
        return None

    station_text = STATION_ID_VARIANTS[variant]
    output_name = STATION_ID_FILENAMES[variant]
    log.debug('[STATIONID Generating %s station ID -> %s', variant, output_name)
    _render_station_id(station_text, output_name)
    return STATION_CALLSIGN

def getShortStationID():
    return getStationID('short')

def getLongStationID():
    return getStationID('long')

def getSevereStationID():
    return getStationID('severe')

if __name__ == '__main__':
    print('[STATIONID] This is one of the BMH modules, not a standalone program. Please run main.py to execute the full BMH program.')

