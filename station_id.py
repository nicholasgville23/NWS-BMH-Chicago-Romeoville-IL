#! /usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import json
import logging
import traceback
from enum import produce_wav_file

log = logging.getLogger("BMH")

# ---------------------------------------------------------------------------
# Station ID Scripts
#
# The different station identification announcements available:
#   - SHORT_STATION_ID:  A brief routine identification used during normal
#                        broadcast hours (e.g., top-of-the-hour station ID).
#   - LONG_STATION_ID:   The full legal station identification, including the
#                        callsign, frequencies, transmitter locations, and
#                        coverage area.
#   - SEVERE_STATION_ID: The announcement used in place of the normal station
#                        ID whenever severe weather is occurring or forecast
#                        for the listening area.
#
# The callsign (STATION_CALLSIGN) is in pronounceable, spaced form so the TTS
# engine reads each letter and digit individually (e.g. "W N G 6 89"). It is
# returned by getStationID() so other modules (such as alert_summary.py) can
# announce the callsign correctly.
# ---------------------------------------------------------------------------

STATION_CALLSIGN = "W N G 6 89"

# Station Identification for WNG689 in Valparaiso, Indiana
# Frequency: 162.450 MHz
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

# Map of variant names to their scripts
STATION_ID_VARIANTS = {
    'short': SHORT_STATION_ID,
    'long': LONG_STATION_ID,
    'severe': SEVERE_STATION_ID,
}

# Map of variant names to their output file names
STATION_ID_FILENAMES = {
    'short': 'ShortStationID.wav',
    'long': 'StationID.wav',
    'severe': 'SevereStationID.wav',
}


def _render_station_id(station_text, output_name):
    """
    Apply the phoneme and replacement dictionaries to the given station ID
    text, wrap it in the VTML volume/speed tags, and produce the WAV file.

    Args:
        station_text (str): The raw station ID text to render.
        output_name (str): The output WAV filename (e.g., 'StationID.wav').
    """
    try:
        config = json.load(open('config.json', encoding='utf-8'))
        phonemeDict = json.load(open('phonemeDB.json', encoding='utf-8'))
        replaceDict = phonemeDict['replace']
        phonemeDict = phonemeDict['phonemes']
        speed = config['ttsSpeed']
        pause = config['endPause']

        # Apply phonemes
        for phoneme in phonemeDict:
            log.debug('[STATIONID PHONEMES] Replacing %s with %s', phoneme, phonemeDict[phoneme])
            station_text = str(station_text).replace(phoneme, f'<vtml_phoneme alphabet="x-cmu" ph="{phonemeDict[phoneme]}"></vtml_phoneme>')

        # Apply replacements
        for word in replaceDict:
            log.debug('[STATIONID PHONEMES] Replacing %s with %s', word, replaceDict[word])
            if '*PAUSE' in replaceDict[word]:
                pauseTime = replaceDict[word].split('*')[1].split('-')[1]
                word_to_find = word.replace(f'*PAUSE-{pauseTime}*', f'<vtml_pause time="{pauseTime}"/>')
                station_text = str(station_text).replace(word_to_find, replaceDict[word])
            else:
                station_text = str(station_text).replace(word, replaceDict[word])

        final_text = f'<vtml_volume value="200"> <vtml_speed value="{speed}"> ' + station_text + f' <vtml_pause time="{pause}"/> </vtml_volume> </vtml_speed>'
        final_text = final_text.replace('\n', ' ').replace('\r', ' ')

        log.debug('[STATIONID] Final Text: %s', final_text)
        produce_wav_file(final_text, output_name)

    except Exception:
        log.error('[STATIONID] %s', traceback.format_exc())
        sys.exit(1)


def getStationID(variant='short'):
    """
    Generate the Station ID audio file for the requested variant.

    Args:
        variant (str): One of 'short', 'long', or 'severe'.
                       Defaults to 'long' (the full legal station ID).

    Returns:
        str: The station callsign in pronounceable, spaced form
             (e.g., 'W N G 6 89') so that callers such as alert_summary.py
             can build correctly-spaced callsign announcements.
             Returns None if an invalid variant is requested.
    """
    variant = str(variant).lower()
    if variant not in STATION_ID_VARIANTS:
        log.error('[STATIONID] Unknown station ID variant: %s', variant)
        return None

    station_text = STATION_ID_VARIANTS[variant]
    output_name = STATION_ID_FILENAMES[variant]
    log.debug('[STATIONID] Generating %s station ID -> %s', variant, output_name)
    _render_station_id(station_text, output_name)
    return STATION_CALLSIGN


def getShortStationID():
    """Generate the short station ID audio file (ShortStationID.wav)."""
    return getStationID('short')


def getLongStationID():
    """Generate the long station ID audio file (StationID.wav)."""
    return getStationID('long')


def getSevereStationID():
    """Generate the severe weather station ID audio file (SevereStationID.wav)."""
    return getStationID('severe')


if __name__ == '__main__':
    print('[STATIONID] This is one of the BMH modules, not a standalone program. Please run main.py to execute the full BMH program.')
