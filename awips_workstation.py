#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
AWIPS Text Workstation Module

Implements a full AWIPS (Advanced Weather Interactive Processing System)
Text Workstation for the BMH Emulation system. Provides:

- AWIPS Header Block generation (TTAAii CCCC NNNXXX format)
- Text message composition with validation
- AWIPS Transmit (broadcasts composed messages through BMH)
- AWIPS message database with store/retrieve
- Editor mode for composing new text bulletins

References:
    https://www.weather.gov/media/tg/awips.pdf
    https://www.weather.gov/tg/awipscoding
"""

import os
import re
import sys
import json
import time
import uuid
import logging
import traceback
import threading
import shutil
import subprocess
import tempfile
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Tuple
from enum import Enum

log = logging.getLogger("BMH")

# =============================================================================
# AWIPS Header Block Constants
# =============================================================================

# Product categories (TTAAii)
PRODUCT_CATEGORIES = {
    # AD - Administrative Products
    "ADMN": {"code": "AD", "name": "Administrative", "description": "Administrative products"},
    
    # AF - Area Forecasts
    "FA": {"code": "FA", "name": "Area Forecast", "description": "Area forecasts"},
    "FAA": {"code": "FA", "name": "Area Forecast (Aviation)", "description": "Aviation area forecasts"},
    
    # FP - Public Forecasts
    "FP": {"code": "FP", "name": "Public Forecast", "description": "Public weather forecasts"},
    "FPA": {"code": "FP", "name": "Alaska Public Forecast", "description": "Alaska public forecasts"},
    
    # FW - Fire Weather
    "FW": {"code": "FW", "name": "Fire Weather Forecast", "description": "Fire weather forecasts"},
    
    # GL - Great Lakes
    "GL": {"code": "GL", "name": "Great Lakes", "description": "Great Lakes marine forecasts"},
    
    # HZ - Hurricane
    "HZ": {"code": "HZ", "name": "Hurricane", "description": "Hurricane/tropical products"},
    
    # NS - News
    "NS": {"code": "NS", "name": "News", "description": "News and information"},
    
    # NP - Non-Precipitation
    "NPW": {"code": "NP", "name": "Non-Precipitation Watch/Warn/Advisory", "description": "Non-precipitation warnings"},
    
    # PT - Public Information
    "PTS": {"code": "PT", "name": "Public Information", "description": "Public information statements"},
    
    # RR - Radar
    "RRA": {"code": "RR", "name": "Radar Report", "description": "Radar summary reports"},
    
    # RS - Research
    "RSC": {"code": "RS", "name": "Research", "description": "Research products"},
    
    # SA - Surface Observations
    "SAC": {"code": "SA", "name": "Surface Observation", "description": "Surface weather observations"},
    
    # SE - Severe
    "SVR": {"code": "SE", "name": "Severe Weather", "description": "Severe weather warnings"},
    "TOR": {"code": "SE", "name": "Tornado Warning", "description": "Tornado warnings"},
    "FFW": {"code": "SE", "name": "Flash Flood Warning", "description": "Flash flood warnings"},
    
    # SP - Spot Forecasts
    "SPF": {"code": "SP", "name": "Spot Forecast", "description": "Spot weather forecasts"},
    
    # SV - Service
    "SVC": {"code": "SV", "name": "Service", "description": "Service records"},
    
    # SW - Snow
    "SWO": {"code": "SW", "name": "Snow", "description": "Snow products"},
    
    # US - Upper Air
    "USA": {"code": "US", "name": "Upper Air", "description": "Upper air observations"},
    
    # WA - Watches/Warnings
    "WCN": {"code": "WA", "name": "Watch County Notification", "description": "Watch county notifications"},
    "TOA": {"code": "WA", "name": "Tornado Watch", "description": "Tornado watches"},
    "SVA": {"code": "WA", "name": "Severe Thunderstorm Watch", "description": "Severe thunderstorm watches"},
    
    # WS - Winter
    "WSW": {"code": "WS", "name": "Winter Weather", "description": "Winter storm warnings"},
    
    # WW - Weather
    "WWO": {"code": "WW", "name": "Weather", "description": "Weather summary"},
}

# NWS Office IDs (CCCC)
NWS_OFFICES = {
    "AKQ": "Wakefield, VA",
    "ALY": "Albany, NY",
    "AMA": "Amarillo, TX",
    "APX": "Gaylord, MI",
    "ARX": "La Crosse, WI",
    "BGM": "Binghamton, NY",
    "BIS": "Bismarck, ND",
    "BMX": "Birmingham, AL",
    "BOI": "Boise, ID",
    "BOU": "Denver/Boulder, CO",
    "BOX": "Boston/Norton, MA",
    "BRO": "Brownsville, TX",
    "BTV": "Burlington, VT",
    "BUF": "Buffalo, NY",
    "BYZ": "Billings, MT",
    "CAE": "Columbia, SC",
    "CAR": "Caribou, ME",
    "CHS": "Charleston, SC",
    "CLE": "Cleveland, OH",
    "CRP": "Corpus Christi, TX",
    "CTP": "State College, PA",
    "CYS": "Cheyenne, WY",
    "DDC": "Dodge City, KS",
    "DLH": "Duluth, MN",
    "DMX": "Des Moines, IA",
    "DTX": "Detroit/Pontiac, MI",
    "DVN": "Quad Cities, IA/IL",
    "EAX": "Kansas City/Pleasant Hill, MO",
    "EKA": "Eureka, CA",
    "EPZ": "El Paso, TX/Santa Teresa, NM",
    "EWX": "Austin/San Antonio, TX",
    "FFC": "Peachtree City/Atlanta, GA",
    "FGF": "Grand Forks, ND",
    "FGZ": "Flagstaff, AZ",
    "FWD": "Dallas/Fort Worth, TX",
    "GGW": "Glasgow, MT",
    "GID": "Hastings, NE",
    "GLD": "Goodland, KS",
    "GRB": "Green Bay, WI",
    "GRR": "Grand Rapids, MI",
    "GSP": "Greenville/Spartanburg, SC",
    "GVX": "La Crosse, WI (Experimental)",
    "GYX": "Portland/Gray, ME",
    "HFO": "Honolulu, HI",
    "HGX": "Houston/Galveston, TX",
    "HNX": "Hanford/San Joaquin Valley, CA",
    "ICT": "Wichita, KS",
    "ILM": "Wilmington, NC",
    "ILN": "Wilmington, OH",
    "IND": "Indianapolis, IN",
    "IWX": "Northern Indiana/Syracuse, IN",
    "JAN": "Jackson, MS",
    "JAX": "Jacksonville, FL",
    "JGX": "Atlanta/Peachtree City, GA (Experimental)",
    "JKL": "Jackson, KY",
    "LAF": "Lafayette, IN",
    "LBF": "North Platte, NE",
    "LCH": "Lake Charles, LA",
    "LIX": "New Orleans/Baton Rouge, LA",
    "LKN": "Elko, NV",
    "LOT": "Chicago, IL",
    "LOX": "Los Angeles/Oxnard, CA",
    "LSX": "St. Louis, MO",
    "LUB": "Lubbock, TX",
    "LWX": "Baltimore/Washington DC",
    "LZK": "Little Rock, AR",
    "MAF": "Midland/Odessa, TX",
    "MEG": "Memphis, TN",
    "MFL": "Miami/South Florida, FL",
    "MFR": "Medford, OR",
    "MHX": "Morehead City/Newport, NC",
    "MKX": "Milwaukee/Sullivan, WI",
    "MLB": "Melbourne, FL",
    "MOB": "Mobile, AL",
    "MPX": "Minneapolis/Chanhassen, MN",
    "MQT": "Marquette, MI",
    "MRX": "Morristown/Knoxville, TN",
    "MSO": "Missoula, MT",
    "MTR": "San Francisco/Monterey, CA",
    "OAX": "Omaha/Valley, NE",
    "OHX": "Nashville, TN",
    "OKX": "New York/Upton, NY",
    "OTX": "Spokane, WA",
    "OUN": "Norman/Oklahoma City, OK",
    "PAH": "Paducah, KY",
    "PBZ": "Pittsburgh, PA",
    "PDT": "Pendleton, OR",
    "PHI": "Philadelphia/Mt. Holly, NJ",
    "PIH": "Pocatello, ID",
    "PQR": "Portland, OR",
    "PSR": "Phoenix, AZ",
    "PUB": "Pueblo, CO",
    "RAH": "Raleigh, NC",
    "REV": "Reno, NV",
    "RIW": "Riverton, WY",
    "RLX": "Charleston, WV",
    "RNK": "Blacksburg/Roanoke, VA",
    "RTX": "Portland, OR (Experimental)",
    "SGF": "Springfield, MO",
    "SGX": "San Diego, CA",
    "SHV": "Shreveport, LA",
    "SJT": "San Angelo, TX",
    "SLC": "Salt Lake City, UT",
    "STO": "Sacramento/Stockton, CA",
    "TAE": "Tallahassee, FL",
    "TBW": "Tampa Bay, FL",
    "TFX": "Great Falls, MT",
    "TOP": "Topeka, KS",
    "TSA": "Tulsa, OK",
    "TWC": "Tucson, AZ",
    "UNR": "Rapid City, SD",
    "VEF": "Las Vegas, NV",
}

# AWIPS Product Designators (NNNXXX)
PRODUCT_DESIGNATORS = {
    "SVR": {"nnn": "SVR", "xxx": "SVR", "name": "Severe Weather Watch/Warning"},
    "TOR": {"nnn": "TOR", "xxx": "TOR", "name": "Tornado Warning"},
    "FFW": {"nnn": "FFW", "xxx": "FFW", "name": "Flash Flood Warning"},
    "FFA": {"nnn": "FFA", "xxx": "FFA", "name": "Flash Flood Watch"},
    "FFS": {"nnn": "FFS", "xxx": "FFS", "name": "Flash Flood Statement"},
    "FLW": {"nnn": "FLW", "xxx": "FLW", "name": "Flood Warning"},
    "FLA": {"nnn": "FLA", "xxx": "FLA", "name": "Flood Advisory"},
    "FLS": {"nnn": "FLS", "xxx": "FLS", "name": "Flood Statement"},
    "SVS": {"nnn": "SVS", "xxx": "SVS", "name": "Severe Weather Statement"},
    "WCN": {"nnn": "WCN", "xxx": "WCN", "name": "Watch County Notification"},
    "TOA": {"nnn": "TOA", "xxx": "TOA", "name": "Tornado Watch"},
    "SVA": {"nnn": "SVA", "xxx": "SVA", "name": "Severe Thunderstorm Watch"},
    "BZA": {"nnn": "BZA", "xxx": "BZA", "name": "Blizzard Watch"},
    "BZW": {"nnn": "BZW", "xxx": "BZW", "name": "Blizzard Warning"},
    "WSW": {"nnn": "WSW", "xxx": "WSW", "name": "Winter Storm Warning"},
    "WWW": {"nnn": "WWW", "xxx": "WWW", "name": "Winter Weather Message"},
    "NPW": {"nnn": "NPW", "xxx": "NPW", "name": "Non-Precipitation Warning"},
    "HWW": {"nnn": "HWW", "xxx": "HWW", "name": "High Wind Warning"},
    "SQW": {"nnn": "SQW", "xxx": "SQW", "name": "Snow Squall Warning"},
    "CFW": {"nnn": "CFW", "xxx": "CFW", "name": "Coastal Flood Warning"},
    "RWW": {"nnn": "RWW", "xxx": "RWW", "name": "Red Flag Warning"},
    "FWW": {"nnn": "FWW", "xxx": "FWW", "name": "Fire Weather Watch"},
    "HWO": {"nnn": "HWO", "xxx": "HWO", "name": "Hazardous Weather Outlook"},
    "FP":  {"nnn": "FP",  "xxx": "FP",  "name": "Zone Forecast"},
    "NOW": {"nnn": "NOW", "xxx": "NOW", "name": "Nowcast"},
    "RWR": {"nnn": "RWR", "xxx": "RWR", "name": "Regional Weather Roundup"},
    "CLI": {"nnn": "CLI", "xxx": "CLI", "name": "Climate Report"},
    "PNS": {"nnn": "PNS", "xxx": "PNS", "name": "Public Information Statement"},
    "REC": {"nnn": "REC", "xxx": "REC", "name": "Record Report"},
    "SPS": {"nnn": "SPS", "xxx": "SPS", "name": "Special Weather Statement"},
    "LSR": {"nnn": "LSR", "xxx": "LSR", "name": "Local Storm Report"},
    "MIS": {"nnn": "MIS", "xxx": "MIS", "name": "Miscellaneous Text"},
    "ADM": {"nnn": "ADM", "xxx": "ADM", "name": "Administrative Message"},
    "TEST": {"nnn": "TEST", "xxx": "TEST", "name": "Test Product"},
}


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class AWIPSHeaderBlock:
    """Represents a complete AWIPS header block."""
    # TTAAii - Product category, originating center, index
    category_code: str = "FP"       # TT - Product category
    originating_center: str = "US"  # AA - Originating center (US = NWS)
    index: str = "01"               # ii - Index number (01-99)
    
    # CCCC - Four-character NWS office ID
    office_id: str = "KLOT"         # CCCC - Office ID
    
    # NNNXXX - Product designator
    product_designator: str = "FP"  # NNN - Product category
    product_number: str = "001"     # XXX - Product number
    
    # Additional header fields
    product_name: str = "Zone Forecast"
    issue_time: str = ""            # Automatically set if empty
    expire_time: str = ""           # Optional expire time
    
    def __post_init__(self):
        if not self.issue_time:
            self.issue_time = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    
    def to_awips_header(self) -> str:
        """Generate the full AWIPS header block as a string."""
        return (
            f"{self.category_code}{self.originating_center}{self.index} "
            f"{self.office_id} {self.product_designator}{self.product_number}\n"
            f"{self.product_name}\n"
            f"{self.issue_time}"
            + (f"\n{self.expire_time}" if self.expire_time else "")
        )
    
    def to_bmh_preamble(self) -> str:
        """Generate a spoken preamble from the header."""
        office_name = NWS_OFFICES.get(self.office_id.lstrip('K'), self.office_id)
        return (
            f"The following is a {self.product_name} "
            f"issued by the National Weather Service office in {office_name}. "
        )


@dataclass
class AWIPSMessage:
    """Represents a complete AWIPS text message."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    header: AWIPSHeaderBlock = field(default_factory=AWIPSHeaderBlock)
    body: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    transmitted: bool = False
    transmit_time: Optional[str] = None
    category: str = "General"
    priority: int = 5  # 1-10, 1=highest
    
    def to_full_bulletin(self) -> str:
        """Get the complete bulletin with header."""
        return f"{self.header.to_awips_header()}\n\n{self.body}"
    
    def to_speech_text(self) -> str:
        """Convert to speech-friendly text for BMH broadcast."""
        return self.header.to_bmh_preamble() + self.body


# =============================================================================
# AWIPS Message Database
# =============================================================================

class AWIPSMessageDB:
    """
    Simple JSON-based database for storing and retrieving AWIPS messages.
    Messages are stored in a JSON file for persistence.
    """
    
    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            db_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "awips_messages.json"
            )
        self.db_path = db_path
        self._messages: Dict[str, dict] = {}
        self._lock = threading.Lock()
        self._load()
    
    def _load(self):
        """Load messages from the JSON file."""
        try:
            if os.path.exists(self.db_path):
                with open(self.db_path, 'r', encoding='utf-8') as f:
                    self._messages = json.load(f)
                log.info("[AWIPS DB] Loaded %d messages from database.", len(self._messages))
        except Exception as e:
            log.warning("[AWIPS DB] Could not load database: %s. Starting fresh.", e)
            self._messages = {}
    
    def _save(self):
        """Save messages to the JSON file."""
        try:
            with open(self.db_path, 'w', encoding='utf-8') as f:
                json.dump(self._messages, f, indent=2)
        except Exception as e:
            log.error("[AWIPS DB] Error saving database: %s", e)
    
    def add_message(self, message: AWIPSMessage) -> str:
        """Add a message to the database."""
        with self._lock:
            msg_dict = {
                "id": message.id,
                "header": {
                    "category_code": message.header.category_code,
                    "originating_center": message.header.originating_center,
                    "index": message.header.index,
                    "office_id": message.header.office_id,
                    "product_designator": message.header.product_designator,
                    "product_number": message.header.product_number,
                    "product_name": message.header.product_name,
                    "issue_time": message.header.issue_time,
                    "expire_time": message.header.expire_time,
                },
                "body": message.body,
                "created_at": message.created_at,
                "transmitted": message.transmitted,
                "transmit_time": message.transmit_time,
                "category": message.category,
                "priority": message.priority,
            }
            self._messages[message.id] = msg_dict
            self._save()
            log.info("[AWIPS DB] Added message %s: %s", message.id, message.header.product_name)
            return message.id
    
    def get_message(self, msg_id: str) -> Optional[AWIPSMessage]:
        """Retrieve a message by ID."""
        with self._lock:
            msg_dict = self._messages.get(msg_id)
            if not msg_dict:
                return None
            
            header = AWIPSHeaderBlock(
                category_code=msg_dict["header"]["category_code"],
                originating_center=msg_dict["header"]["originating_center"],
                index=msg_dict["header"]["index"],
                office_id=msg_dict["header"]["office_id"],
                product_designator=msg_dict["header"]["product_designator"],
                product_number=msg_dict["header"]["product_number"],
                product_name=msg_dict["header"]["product_name"],
                issue_time=msg_dict["header"]["issue_time"],
                expire_time=msg_dict["header"]["expire_time"],
            )
            
            return AWIPSMessage(
                id=msg_dict["id"],
                header=header,
                body=msg_dict["body"],
                created_at=msg_dict["created_at"],
                transmitted=msg_dict["transmitted"],
                transmit_time=msg_dict["transmit_time"],
                category=msg_dict["category"],
                priority=msg_dict["priority"],
            )
    
    def get_all_messages(self) -> List[AWIPSMessage]:
        """Get all messages sorted by creation time (newest first)."""
        with self._lock:
            msgs = []
            for msg_id, msg_dict in self._messages.items():
                header = AWIPSHeaderBlock(
                    category_code=msg_dict["header"]["category_code"],
                    originating_center=msg_dict["header"]["originating_center"],
                    index=msg_dict["header"]["index"],
                    office_id=msg_dict["header"]["office_id"],
                    product_designator=msg_dict["header"]["product_designator"],
                    product_number=msg_dict["header"]["product_number"],
                    product_name=msg_dict["header"]["product_name"],
                    issue_time=msg_dict["header"]["issue_time"],
                    expire_time=msg_dict["header"]["expire_time"],
                )
                msgs.append(AWIPSMessage(
                    id=msg_id,
                    header=header,
                    body=msg_dict["body"],
                    created_at=msg_dict["created_at"],
                    transmitted=msg_dict["transmitted"],
                    transmit_time=msg_dict["transmit_time"],
                    category=msg_dict["category"],
                    priority=msg_dict["priority"],
                ))
            msgs.sort(key=lambda m: m.created_at, reverse=True)
            return msgs
    
    def get_transmitted_messages(self) -> List[AWIPSMessage]:
        """Get all transmitted messages."""
        return [m for m in self.get_all_messages() if m.transmitted]
    
    def get_pending_messages(self) -> List[AWIPSMessage]:
        """Get all pending (not yet transmitted) messages."""
        return [m for m in self.get_all_messages() if not m.transmitted]
    
    def mark_transmitted(self, msg_id: str) -> bool:
        """Mark a message as transmitted."""
        with self._lock:
            if msg_id in self._messages:
                self._messages[msg_id]["transmitted"] = True
                self._messages[msg_id]["transmit_time"] = datetime.now().isoformat()
                self._save()
                log.info("[AWIPS DB] Marked message %s as transmitted.", msg_id)
                return True
            return False
    
    def delete_message(self, msg_id: str) -> bool:
        """Delete a message from the database."""
        with self._lock:
            if msg_id in self._messages:
                del self._messages[msg_id]
                self._save()
                log.info("[AWIPS DB] Deleted message %s.", msg_id)
                return True
            return False
    
    def get_statistics(self) -> dict:
        """Get database statistics."""
        all_msgs = self.get_all_messages()
        return {
            "total": len(all_msgs),
            "transmitted": len([m for m in all_msgs if m.transmitted]),
            "pending": len([m for m in all_msgs if not m.transmitted]),
            "by_category": {cat: len([m for m in all_msgs if m.category == cat])
                           for cat in set(m.category for m in all_msgs)},
        }


# =============================================================================
# AWIPS Transmit System
# =============================================================================

class AWIPSTransmitQueue:
    """
    Handles the transmission (broadcast) of AWIPS messages through the BMH system.
    Composed messages are converted to BMH audio and added to the broadcast cycle.
    """
    
    def __init__(self):
        self.queue: List[AWIPSMessage] = []
        self._lock = threading.Lock()
        self.db = AWIPSMessageDB()
        self._transmit_thread = None
        self._running = False
    
    def enqueue(self, message: AWIPSMessage) -> str:
        """Add a message to the transmit queue."""
        with self._lock:
            # Save to database first
            self.db.add_message(message)
            self.queue.append(message)
            log.info("[AWIPS TX] Enqueued message %s for transmission: %s",
                    message.id, message.header.product_name)
            return message.id
    
    def get_next_pending(self) -> Optional[AWIPSMessage]:
        """Get the next pending message from the queue."""
        with self._lock:
            for msg in self.queue:
                if not msg.transmitted:
                    return msg
            return None
    
    def transmit_message(self, message: AWIPSMessage) -> bool:
        """
        Transmit (broadcast) a single AWIPS message through the BMH system.
        This generates a WAV file that can be included in the BMH broadcast cycle.
        """
        try:
            from enum import produce_wav_file
            
            config = json.load(open('config.json', encoding='utf-8'))
            speed = config.get('ttsSpeed', '110')
            pause = config.get('endPause', '1300')
            
            speech_text = message.to_speech_text()
            
            # Prepare the text for BMH broadcast
            broadcast_text = (
                f'<vtml_volume value="200"> <vtml_speed value="{speed}"> '
                f'{speech_text}'
                f'<vtml_pause time="{pause}"/> </vtml_volume> </vtml_speed>'
            )
            
            # Generate the WAV file
            produce_wav_file(broadcast_text, 'AWIPS_Message.wav')
            
            # If the BMH main loop is running, the AWIPS_Message.wav will be
            # picked up in the next cycle if configured.
            
            # Mark as transmitted in database
            self.db.mark_transmitted(message.id)
            message.transmitted = True
            message.transmit_time = datetime.now().isoformat()
            
            log.info("[AWIPS TX] Successfully transmitted message %s as audio.",
                    message.id)
            return True
            
        except Exception as e:
            log.error("[AWIPS TX] Error transmitting message %s: %s",
                     message.id, traceback.format_exc())
            return False
    
    def transmit_pending_all(self) -> int:
        """Transmit all pending messages. Returns count of transmitted messages."""
        count = 0
        pending = self.db.get_pending_messages()
        for msg in pending:
            if self.transmit_message(msg):
                count += 1
        log.info("[AWIPS TX] Transmitted %d pending messages.", count)
        return count
    
    def get_queue_status(self) -> dict:
        """Get the current queue status."""
        with self._lock:
            pending = len([m for m in self.queue if not m.transmitted])
            return {
                "queue_size": len(self.queue),
                "pending": pending,
                "transmitted": len(self.queue) - pending,
                "db_stats": self.db.get_statistics(),
            }


# =============================================================================
# AWIPS Editor Engine
# =============================================================================

class AWIPSEditorEngine:
    """
    Provides the core editing functionality for composing AWIPS text messages.
    Handles validation, formatting, and header generation.
    """
    
    @staticmethod
    def generate_awips_header(
        category_code: str = "FP",
        office_id: str = "KLOT",
        product_designator: str = "FP",
        product_name: str = "Zone Forecast",
        index: str = "01",
        product_number: str = "001",
    ) -> AWIPSHeaderBlock:
        """Generate a new AWIPS header block with default values."""
        return AWIPSHeaderBlock(
            category_code=category_code,
            originating_center="US",
            index=index,
            office_id=office_id,
            product_designator=product_designator,
            product_number=product_number,
            product_name=product_name,
            issue_time=datetime.utcnow().strftime("%Y%m%d%H%M%S"),
        )
    
    @staticmethod
    def validate_body_text(body: str) -> Tuple[bool, List[str]]:
        """
        Validate the body text for AWIPS compliance.
        Returns (is_valid, list_of_issues).
        """
        issues = []
        
        if not body or not body.strip():
            issues.append("Body text is empty.")
            return False, issues
        
        # Check length (max ~2000 chars for most products)
        if len(body) > 50000:
            issues.append("Body text exceeds maximum length (50,000 chars).")
        
        # Check for common issues
        lines = body.strip().split('\n')
        
        # AWIPS requires proper line formatting
        for i, line in enumerate(lines):
            if len(line) > 80:
                issues.append(f"Line {i+1} exceeds 80 characters (AWIPS convention).")
        
        # Check for encoding issues
        try:
            body.encode('ascii')
        except UnicodeEncodeError:
            issues.append("Body contains non-ASCII characters. Consider using plain ASCII.")
        
        is_valid = len(issues) == 0
        return is_valid, issues
    
    @staticmethod
    def compose_message(
        header: AWIPSHeaderBlock,
        body: str,
        category: str = "General",
        priority: int = 5,
    ) -> AWIPSMessage:
        """Compose a complete AWIPS message from header and body."""
        return AWIPSMessage(
            header=header,
            body=body.strip(),
            category=category,
            priority=priority,
        )
    
    @staticmethod
    def format_body_for_nws(body: str) -> str:
        """Format body text according to NWS/AWIPS style guidelines."""
        # Remove excessive whitespace
        lines = body.strip().split('\n')
        formatted_lines = []
        
        for line in lines:
            line = line.strip()
            if line:
                # Ensure proper sentence capitalization
                if line[0].islower() and len(line) > 3:
                    line = line[0].upper() + line[1:]
                formatted_lines.append(line)
            else:
                formatted_lines.append('')
        
        return '\n'.join(formatted_lines)


# =============================================================================
# Global Singleton Instances
# =============================================================================

# Global transmit queue (used by main.py and gui.py)
_transmit_queue = None
_editor_engine = None
_message_db = None

def get_transmit_queue() -> AWIPSTransmitQueue:
    """Get or create the global transmit queue instance."""
    global _transmit_queue
    if _transmit_queue is None:
        _transmit_queue = AWIPSTransmitQueue()
    return _transmit_queue

def get_editor_engine() -> AWIPSEditorEngine:
    """Get or create the global editor engine instance."""
    global _editor_engine
    if _editor_engine is None:
        _editor_engine = AWIPSEditorEngine()
    return _editor_engine

def get_message_db() -> AWIPSMessageDB:
    """Get or create the global message database instance."""
    global _message_db
    if _message_db is None:
        _message_db = AWIPSMessageDB()
    return _message_db


# =============================================================================
# Utility: Generate AWIPS Audio Product for BMH
# =============================================================================

def getAWIPSTransmit():
    """
    Product generator function for BMH integration.
    Checks the transmit queue and broadcasts any pending messages.
    This is called by the BMH main loop through products.py.
    """
    try:
        tx_queue = get_transmit_queue()
        pending = tx_queue.db.get_pending_messages()
        
        if not pending:
            log.debug("[AWIPS TX] No pending AWIPS messages to transmit.")
            return
        
        # Transmit the highest priority (lowest number) message
        pending.sort(key=lambda m: (m.priority, m.created_at))
        next_msg = pending[0]
        
        log.info("[AWIPS TX] Broadcasting pending AWIPS message: %s - %s",
                next_msg.id, next_msg.header.product_name)
        
        tx_queue.transmit_message(next_msg)
        
    except Exception as e:
        log.error("[AWIPS TX] Error in AWIPS transmit product: %s",
                 traceback.format_exc())


# =============================================================================
# Main entry for testing
# =============================================================================

if __name__ == '__main__':
    print("[AWIPS] AWIPS Text Workstation Module")
    print("[AWIPS] Use this module through gui.py or main.py")
    
    # Quick test
    engine = get_editor_engine()
    header = engine.generate_awips_header(
        office_id="KLOT",
        product_designator="SPS",
        product_name="Special Weather Statement"
    )
    print(f"\nTest Header:\n{header.to_awips_header()}")
    
    body = "A line of strong thunderstorms will affect the area through this evening."
    msg = engine.compose_message(header, body, category="Weather", priority=3)
    print(f"\nTest Message ID: {msg.id}")
    print(f"Full Bulletin:\n{msg.to_full_bulletin()}")
    print(f"\nSpeech Text: {msg.to_speech_text()}")

