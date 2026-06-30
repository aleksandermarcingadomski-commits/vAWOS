import tkinter as tk
from tkinter import ttk
import urllib.request
import urllib.parse
import json
import re
import math
import random
import time
import ssl
import threading
import os
import wave
import struct
import webbrowser
import sys
import subprocess
from difflib import SequenceMatcher
from datetime import datetime, timezone, timedelta

# OBSŁUGA REQUESTS (Zgodnie z wymogami VATSIM API)
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

# DZWIEKI
try:
    import winsound
except ImportError:
    winsound = None

try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False

try:
    import webview
    PYWEBVIEW_AVAILABLE = True
except ImportError:
    PYWEBVIEW_AVAILABLE = False
    print("UWAGA: Brak biblioteki 'pywebview'. Mapa otworzy się awaryjnie w przeglądarce.")

# LOTNISKA
AIRPORT_DATA = """
EPWA|CHOPIN|52.17147|20.9467|11:362,15:352,29:346,33:351,|
EPMO|MODLIN|52.45027|20.6415|08:339,26:343,|
EPLL|LUBLINEK|51.71622|19.3721|07:592,25:606,|
EPRA|RADOM|51.38651|21.1977|07:622,25:602,|
EPBC|BABICE|52.27125|20.9021|10R:343,28L:352,|
EPGD|LECH WALESA|54.38106|18.452|11:451,29:488,|
EPBY|SZWEDEROWO|53.09666|17.9777|08:236,26:234,|
EPOK|GDYNIA-OKSYWIE|54.58717|18.5214|08:121,13:144,26:108,31:135,|
EPKK|BALICE|50.07539|19.768|07:791,25:781,|
EPKT|PYRZOWICE|50.4743|19.0546|08:970,26:995,|
EPRZ|JASIONKA|50.11003|22.0134|09:689,27:669,|
EPKP|POBIEDNIK|50.08967|20.20166|09:90,27:270,|
EPPO|LAWICA|52.42495|16.806|10:308,28:289,|
EPWR|STRACHOWICE|51.1088|16.8658|11:404,29:400,|
EPZG|BABIMOST|52.1337|15.782|06:194,24:188,|
EPKS|KRZESINY|52.33715|16.9504|11:272,29:274,|
EPLB|LUBLIN|51.23764|22.6959|07:632,25:626,|
EPSC|GOLENIOW|53.59208|14.8879|13:118,31:154,|
EPSY|MAZURY|53.4712|20.9317|02:438,20:462,|
"""

# KOLORY
BG_COLOR = "#0D1117"
PANEL_BG = "#161E2B"
BOX_BG = "#1F2937"
TEXT_WHITE = "#F8F9FA"  
TEXT_CYAN = "#00FFFF"
TEXT_GREEN = "#55FF55"  
TEXT_YELLOW = "#FFFF00"
TEXT_RED = "#FF5555"    
BTN_DEF_BG = "#3A4A6A"

# ASTRONOMIA I SŁOŃCE
def get_sun_position(lat, lon, utc_time):
    days = (utc_time - datetime(utc_time.year, 1, 1, tzinfo=timezone.utc)).days
    b = (360 / 365.0) * (days - 81)
    eot = 9.87 * math.sin(math.radians(2*b)) - 7.53 * math.cos(math.radians(b)) - 1.5 * math.sin(math.radians(b))
    time_offset = eot + 4 * float(lon)
    tst = utc_time.hour + utc_time.minute/60.0 + utc_time.second/3600.0 + time_offset/60.0
    ha = 15 * (tst - 12)
    declination = 23.45 * math.sin(math.radians((360/365.0)*(days-81)))
    
    lat_r = math.radians(float(lat))
    dec_r = math.radians(declination)
    ha_r = math.radians(ha)
    
    sin_el = math.sin(lat_r)*math.sin(dec_r) + math.cos(lat_r)*math.cos(dec_r)*math.cos(ha_r)
    sin_el = max(-1.0, min(1.0, sin_el)) 
    el_r = math.asin(sin_el)
    el_deg = math.degrees(el_r)
    
    cos_az = (math.sin(dec_r) - math.sin(el_r)*math.sin(lat_r)) / (math.cos(el_r)*math.cos(lat_r) + 0.000001)
    cos_az = max(-1.0, min(1.0, cos_az))
    az_r = math.acos(cos_az)
    az_deg = math.degrees(az_r)
    if ha > 0: az_deg = 360 - az_deg
    
    return el_deg, az_deg

# WINDY (IZOLOWANY SUBPROCESS)
class MapApi:
    def close_map(self):
        os._exit(0)

def launch_windy_webview(w, h, x, y, is_full, lat, lon):
    try:
        import webview
        api = MapApi()
        embed_url = f"https://embed.windy.com/embed2.html?lat={lat}&lon={lon}&zoom=8&level=surface&overlay=wind&menu=&message=&marker=true&calendar=now&pressure=&type=map&location=coordinates&detail=&metricWind=kt&metricTemp=%C2%B0C"
        html_content = f"""
        <!DOCTYPE html><html><head><meta charset="utf-8"><style>
        body, html {{ margin: 0; padding: 0; height: 100%; overflow: hidden; background-color: #0D1117; font-family: Arial, sans-serif; }}
        .top-bar {{ background-color: #161E2B; border-bottom: 1px solid #4A6B9C; display: flex; align-items: center; padding: 0 15px; height: 65px; box-sizing: border-box; user-select: none; }}
        .back-btn {{ background-color: #E6A817; color: black; border: none; padding: 12px 20px; font-size: 14px; font-weight: bold; cursor: pointer; border-radius: 4px; box-shadow: 0 2px 4px rgba(0,0,0,0.3); z-index: 100; transition: 0.2s; }}
        .back-btn:hover {{ background-color: #f0b830; }}
        .title {{ color: #00FFFF; margin-left: 25px; font-size: 18px; font-weight: bold; }}
        iframe {{ width: 100%; height: calc(100% - 65px); border: none; }}
        </style></head><body>
        <div class="top-bar"><button class="back-btn" onclick="pywebview.api.close_map()">◄ POWRÓT DO AWOS</button><div class="title">MAPA POGODOWA (Windy.com)</div></div>
        <iframe src="{embed_url}"></iframe></body></html>
        """
        window = webview.create_window('AWOS - MAPA', html=html_content, width=w, height=h, x=x, y=y, frameless=True, fullscreen=is_full, js_api=api)
        webview.start()
    except Exception as e:
        print("Błąd Webview:", e)

# DEKODER METAR
def decode_weather_phenomena(raw_metar):
    weather_map = {
        'DZ': 'Mżawka', 'RA': 'Deszcz', 'SN': 'Śnieg', 'SG': 'Ziarna śnieżne',
        'GR': 'Grad', 'GS': 'Krupy lodowe', 'PL': 'Ziarna lodowe', 'FG': 'Mgła',
        'FU': 'Dym', 'HZ': 'Zmętnienie', 'BR': 'Zamglenie', 'SA': 'Piasek',
        'DU': 'Pył', 'TS': 'Burza', 'SH': 'Przelotne', 'FZ': 'Marznące'
    }
    found = []
    codes = re.findall(r'\b([+-]?(?:MI|PR|BC|DR|BL|SH|TS|FZ)?(?:DZ|RA|SN|SG|GR|GS|PL|FG|FU|HZ|DU|SA|PY|BR))\b', raw_metar)
    for code in codes:
        decoded_part = []
        if '+' in code: decoded_part.append("Intensywne")
        elif '-' in code: decoded_part.append("Słabe")
        for k, v in weather_map.items():
            if k in code: decoded_part.append(v)
        if decoded_part: found.append(" ".join(decoded_part))
    return " / ".join(found) if found else "Brak istotnych zjawisk"

def format_notam_date(d_str):
    if not d_str: return "UNKNOWN"
    d_str = d_str.upper()
    if d_str in ["PERM", "EST"]: return d_str
    if len(d_str) == 10 and d_str.isdigit():
        return f"{d_str[4:6]}.{d_str[2:4]}.20{d_str[0:2]} {d_str[6:8]}:{d_str[8:10]}"
    return d_str

# DZWIEK ATIS
def create_beep_wav(filename="atis_beep.wav", freq=1200, duration=0.3):
    if os.path.exists(filename): return
    try:
        sample_rate = 44100
        with wave.open(filename, 'w') as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(sample_rate)
            for i in range(int(sample_rate * duration)):
                value = int(16383.0 * math.sin(2.0 * math.pi * freq * i / sample_rate))
                w.writeframesraw(struct.pack('<h', value))
    except Exception: pass

# ZAAWANSOWANY SILNIK POGODY
class WindSim:
    def __init__(self, initial_drift_dir=0, initial_drift_spd=0):
        self.drift_dir = initial_drift_dir
        self.drift_spd = initial_drift_spd
        self.target_drift_dir = random.uniform(-10, 10)
        self.target_drift_spd = random.uniform(-3, 3)

        self.history = []
        self.pub_avg_dir = 0
        self.pub_avg_spd = 0
        self.pub_max_spd = 0
        self.pub_min_dir = 0
        self.pub_max_dir = 0
        self.cur_dir = 0
        self.cur_spd = 0
        
        self.ws_alert = False
        self.is_vrb = False
        self.vrb_target_dir = random.randint(0, 359)
        self.vrb_current_dir = random.randint(0, 359)

    def update_drift(self):
        if self.drift_dir < self.target_drift_dir: self.drift_dir += 0.1
        elif self.drift_dir > self.target_drift_dir: self.drift_dir -= 0.1
        if self.drift_spd < self.target_drift_spd: self.drift_spd += 0.05
        elif self.drift_spd > self.target_drift_spd: self.drift_spd -= 0.05
        
        if abs(self.drift_dir - self.target_drift_dir) < 0.2: 
            self.target_drift_dir = random.uniform(-15, 15)
        if abs(self.drift_spd - self.target_drift_spd) < 0.1: 
            self.target_drift_spd = random.uniform(-4, 4)

    def reset_and_init(self, m_dir, m_spd, m_gust, v_min, v_max):
        self.history = []
        self.tick(m_dir, m_spd, m_gust, v_min, v_max, False, False, 0.0)
        self.publish() 

    def tick(self, m_dir, m_spd, m_gust, v_min, v_max, is_night=False, is_ovc=False, wave_offset=0.0):
        if m_dir is None: m_dir = 0
        if m_spd is None: m_spd = 0
        
        # WIATR ZMIENNY - oscylacja w pełnym zakresie 360 st.
        if self.is_vrb:
            if random.random() < 0.05: 
                self.vrb_target_dir = random.randint(0, 359)
            diff = (self.vrb_target_dir - self.vrb_current_dir + 180) % 360 - 180
            self.vrb_current_dir = (self.vrb_current_dir + diff * 0.05) % 360
            m_dir = self.vrb_current_dir
        
        self.update_drift()
        
        eff_drift_spd = self.drift_spd if m_spd > 4 else self.drift_spd * 0.2
        
        local_base_dir = (m_dir + self.drift_dir) % 360
        local_base_spd = max(0, m_spd + eff_drift_spd)
        local_base_gust = max(0, m_gust + eff_drift_spd) if m_gust > 0 else 0

        thermal_factor = 1.0
        if is_night or is_ovc: 
            thermal_factor = 0.3 
        elif not is_night and not is_ovc: 
            thermal_factor = 1.6

        if random.random() < (0.05 * thermal_factor):
            cdir = int(local_base_dir) + random.randint(30, 80) * random.choice([-1, 1])
        else:
            if v_min is not None and v_max is not None:
                cdir = random.randint(int(v_min + self.drift_dir) - int(22*thermal_factor), int(v_max + self.drift_dir) + int(22*thermal_factor))
            else:
                cdir = int(local_base_dir) + int(random.randint(-28, 28) * thermal_factor)
        
        cdir = cdir % 360

        if local_base_gust > 0: 
            cspd = local_base_spd + wave_offset + random.uniform(-1.0, 1.5) * thermal_factor
        else: 
            cspd = local_base_spd + (wave_offset * 0.5) + random.uniform(-1.0, 1.5) * thermal_factor
                
        self.cur_dir = int(cdir)
        self.cur_spd = int(round(max(0, cspd)))
        self.history.append((self.cur_dir, self.cur_spd))
        
        if len(self.history) > 24: 
            self.history.pop(0)

    def publish(self):
        if not self.history: return
        sum_sin = sum([math.sin(math.radians(d)) for d, s in self.history])
        sum_cos = sum([math.cos(math.radians(d)) for d, s in self.history])
        
        self.pub_avg_spd = round(sum([s for d, s in self.history]) / len(self.history))
        self.pub_max_spd = max([s for d, s in self.history])
        
        if sum_sin == 0 and sum_cos == 0: 
            self.pub_avg_dir = 0
        else:
            deg = (math.degrees(math.atan2(sum_sin, sum_cos)) + 360) % 360
            self.pub_avg_dir = round(deg / 10) * 10
            if self.pub_avg_dir == 360: self.pub_avg_dir = 0
            
        max_dev_pos = max_dev_neg = 0
        for d, _ in self.history:
            diff = (d - self.pub_avg_dir + 180) % 360 - 180
            if diff > max_dev_pos: max_dev_pos = diff
            if diff < max_dev_neg: max_dev_neg = diff
            
        self.pub_min_dir = int((self.pub_avg_dir + max_dev_neg) % 360)
        self.pub_max_dir = int((self.pub_avg_dir + max_dev_pos) % 360)

class MetarData:
    def __init__(self):
        self.raw = ""
        self.var_min = None
        self.var_max = None
        self.temp = "N/A"
        self.dew = "N/A"
        self.qnh = "N/A"
        self.vis = "N/A"
        self.rvr = "///"
        self.clouds = []

# STAN LOTNISKA
class AirportState:
    def __init__(self, icao):
        self.icao = icao
        self.metar = MetarData()
        self.metar_valid = False
        self.target_dir = 0
        self.target_spd = 0
        self.target_gust = 0
        self.target_vis = 9999
        self.base_dir = 0.0
        self.base_spd = 0.0
        self.base_gust = 0.0
        self.base_vis = 9999.0
        self.is_vrb = False
        
        self.phys_sims = {
            'epwa_dep': WindSim(initial_drift_dir=-5, initial_drift_spd=1),
            'epwa_arr': WindSim(initial_drift_dir=5, initial_drift_spd=-1),
            'std_low': WindSim(initial_drift_dir=-4, initial_drift_spd=0.5),
            'std_mid': WindSim(initial_drift_dir=0, initial_drift_spd=0),
            'std_high': WindSim(initial_drift_dir=4, initial_drift_spd=-0.5)
        }
        self.phys_envs = {'epwa_dep': {}, 'epwa_arr': {}, 'std_low': {}, 'std_mid': {}, 'std_high': {}}
        
        self.is_initial_fetch = True
        self.is_initial_metar_fetch = True
        self.is_initial_atis_fetch = True
        
        self.current_notams = []
        self.pending_new_notams = []
        self.pending_removed_notams = []
        self.next_snapshot_notams = []
        
        self.current_taf = ""
        self.pending_new_taf = ""
        self.pending_removed_taf = ""
        self.next_snapshot_taf = ""
        
        self.current_metar_raw = ""
        self.pending_new_metar_raw = ""
        self.pending_removed_metar_raw = ""
        self.next_snapshot_metar_raw = ""
        
        self.taf_changed = False
        self.notam_changed = False
        self.metar_changed_blink = False
        
        self.om_data = None
        self.airport_base_clouds = None
        self.metar_history_raw = []
        
        self.rwy_water_level = 0.0
        self.rwy_snow_level = 0.0
        self.ceilometer_timer = 0
        self.ceilometer_readings = []
        self.mb_timer = 0
        self.mb_qnh_spike = 0
        self.shower_timer = 0
        self.shower_phase = 0
        self.fog_phase = 0.0
        self.gust_wave = [0.0] * 15
        
        self.terrain_profile = {'type': 'FLAT', 'slope_dir': None, 'slope_mag': 0.0, 'valley_axis': None}
        self.tick_counter = 0
        
        self.atis_data_text = {}
        self.atis_data_prev = {}
        self.atis_data_code = {}
        self.atis_change_time = {}
        self.atis_diff_active = {}

# PANEL POJEDYNCZY
class AWOSPanel(tk.Frame):
    def __init__(self, parent, app, default_icao="", is_dual=False):
        super().__init__(parent, bg=BG_COLOR)
        self.app = app
        self.is_dual = is_dual
        self.current_icao = tk.StringVar(value=default_icao)
        self.active_rwy_dep = tk.StringVar(value="")
        self.active_rwy_arr = tk.StringVar(value="")
        self.active_rwy_common = tk.StringVar(value="")
        self.is_epwa_mode = False
        self.active_cols = []
        self.atis_cols = []
        self.showing_history = False
        
        self.awos_frame = tk.Frame(self, bg=BG_COLOR)
        self.detail_frame = tk.Frame(self, bg=BG_COLOR)
        
        self.create_awos_layout()
        self.awos_frame.pack(fill=tk.BOTH, expand=True)

        if default_icao:
            self.on_icao_change(force_icao=default_icao)

    def create_awos_layout(self):
        # KONFIGURACJA CZCIONEK ZALEŻNIE OD TRYBU
        font_sz_title = 12 if self.is_dual else 14
        font_sz_lbl_top = 13 if self.is_dual else 15
        font_sz_lbl_bot = 10 if self.is_dual else 12
        font_sz_val = 11 if self.is_dual else 14
        font_sz_atis_txt = 9 if self.is_dual else 10
        font_sz_atis_lbl = 14 if self.is_dual else 18
        
        # MARGINESY
        bot_pady = (5, 5) if self.is_dual else (20, 10)
        bot_ipady = 2 if self.is_dual else 5
        self.env_pady = 2 if self.is_dual else 12

        self.awos_frame.rowconfigure(0, weight=0)
        self.awos_frame.rowconfigure(1, weight=1)
        self.awos_frame.rowconfigure(2, weight=0)
        self.awos_frame.columnconfigure(0, weight=1)
        
        top = tk.Frame(self.awos_frame, bg=BG_COLOR, bd=1, relief=tk.SOLID)
        top.grid(row=0, column=0, sticky="ew", padx=10, pady=5)
        
        self.center_frame = tk.Frame(self.awos_frame, bg=BG_COLOR)
        self.center_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=2)
        self.center_frame.rowconfigure(0, weight=1)
        for i in range(4): 
            self.center_frame.columnconfigure(i, weight=1, uniform="col")

        bot = tk.Frame(self.awos_frame, bg=BG_COLOR, bd=1, relief=tk.SOLID)
        bot.grid(row=2, column=0, sticky="ew", padx=10, pady=bot_pady, ipady=bot_ipady)

        tk.Label(top, text="WYBÓR ICAO:", bg=BG_COLOR, fg=TEXT_WHITE, font=("Arial", font_sz_title, "bold")).pack(side=tk.LEFT, padx=10)
        self.icao_cb = ttk.Combobox(top, values=list(self.app.airports.keys()), width=8, font=("Arial", font_sz_title, "bold"))
        self.icao_cb.pack(side=tk.LEFT, padx=5)
        self.icao_cb.bind('<<ComboboxSelected>>', self.on_icao_change)
        
        self.lbl_time = tk.Label(top, text="--:--:-- UTC", bg=BOX_BG, fg=TEXT_CYAN, font=("Consolas", font_sz_lbl_top, "bold"), width=15, relief=tk.SUNKEN, bd=1)
        self.lbl_time.pack(side=tk.LEFT, padx=40)
        self.lbl_top_qnh = tk.Label(top, text="QNH: ---", bg=BOX_BG, fg=TEXT_WHITE, font=("Consolas", font_sz_lbl_top, "bold"), width=16, relief=tk.SUNKEN, bd=1)
        self.lbl_top_qnh.pack(side=tk.LEFT, padx=40)
        self.lbl_vmc = tk.Label(top, text="---", bg=BOX_BG, fg=TEXT_WHITE, font=("Arial", font_sz_lbl_top, "bold"), width=10, relief=tk.SUNKEN, bd=1)
        self.lbl_vmc.pack(side=tk.RIGHT, padx=10)
        
        self.lbl_lvp = tk.Label(top, text="LVP", bg=BOX_BG, fg="#444444", font=("Arial", font_sz_lbl_top, "bold"), width=6, relief=tk.SUNKEN, bd=1, cursor="arrow")
        self.lbl_lvp.pack(side=tk.RIGHT, padx=10)
        self.lbl_lvp.bind("<Button-1>", lambda e: self.app.toggle_split_screen())

        btn_container = tk.Frame(bot, bg=BG_COLOR)
        btn_container.pack(side=tk.RIGHT, fill=tk.Y, padx=5, pady=2)

        self.btn_map = tk.Button(btn_container, text="MAP", bg="#006699", fg=TEXT_WHITE, font=("Arial", font_sz_lbl_bot, "bold"), width=8, command=self.open_map_action)
        self.btn_map.pack(side=tk.RIGHT, padx=4, ipady=4)

        self.btn_notam = tk.Button(btn_container, text="NOTAM", bg=BTN_DEF_BG, fg=TEXT_WHITE, font=("Arial", font_sz_lbl_bot, "bold"), width=8, command=lambda: self.open_detail_view("NOTAM"))
        self.btn_notam.pack(side=tk.RIGHT, padx=4, ipady=4)
        
        self.btn_taf = tk.Button(btn_container, text="TAF", bg=BTN_DEF_BG, fg=TEXT_WHITE, font=("Arial", font_sz_lbl_bot, "bold"), width=8, command=lambda: self.open_detail_view("TAF"))
        self.btn_taf.pack(side=tk.RIGHT, padx=4, ipady=4)
        
        self.btn_metar = tk.Button(btn_container, text="METAR", bg=BTN_DEF_BG, fg=TEXT_WHITE, font=("Arial", font_sz_lbl_bot, "bold"), width=8, command=lambda: self.open_detail_view("METAR"))
        self.btn_metar.pack(side=tk.RIGHT, padx=4, ipady=4)

        lbl_container = tk.Frame(bot, bg=BG_COLOR)
        lbl_container.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=2)

        def make_bot_label(parent, text, w=20):
            lbl = tk.Label(parent, text=text, bg=BOX_BG, fg=TEXT_CYAN, font=("Consolas", font_sz_val, "bold"), width=w, relief=tk.SUNKEN, bd=1)
            lbl.pack(side=tk.LEFT, padx=5, ipady=3)
            return lbl

        self.lbl_bot_wind = make_bot_label(lbl_container, "WIND: ---", 24)
        self.lbl_bot_temp = make_bot_label(lbl_container, "TEMP: ---", 12)
        self.lbl_bot_dew = make_bot_label(lbl_container, "DEW: ---", 12)
        self.lbl_bot_qnh = make_bot_label(lbl_container, "QNH: ---", 13)
        self.lbl_bot_vis = make_bot_label(lbl_container, "VISIBILITY: ---", 30)

        # CZCIONKI 
        self.font_sz_title = font_sz_title
        self.font_sz_lbl_bot = font_sz_lbl_bot
        self.font_sz_val = font_sz_val
        self.font_sz_atis_txt = font_sz_atis_txt
        self.font_sz_atis_lbl = font_sz_atis_lbl

    def update_static_ui(self):
        try:
            icao = self.current_icao.get()
            state = self.app.airport_states.get(icao)
            if not state: return

            # Bezpieczne parsowanie QNH
            try:
                qnh_val = state.metar.qnh
                if qnh_val != "N/A" and qnh_val.isdigit():
                    lat, lon = self.app.get_coords(icao)
                    tide = 0
                    if lon:
                        now = datetime.now(timezone.utc)
                        local_hour = (now.hour + now.minute/60.0 + float(lon)/15.0) % 24
                        tide = math.cos(4 * math.pi * (local_hour - 10) / 24) * 1.5
                    qnh_val = str(int(qnh_val) + getattr(state, 'mb_qnh_spike', 0) + int(round(tide)))
                    
                self.lbl_top_qnh.config(text=f"QNH: {qnh_val}")
                self.lbl_bot_qnh.config(text=f"QNH: {qnh_val} hPa")
            except Exception: 
                pass

            # Temperatura
            try:
                self.lbl_bot_temp.config(text=f"TEMP: {state.metar.temp} °C")
                self.lbl_bot_dew.config(text=f"DEW: {state.metar.dew} °C")
            except Exception:
                pass
                
            # Widzialność
            try:
                vis_text = "> 10km (CAVOK)" if state.metar.vis == "9999" else f"{state.metar.vis} m"
                self.lbl_bot_vis.config(text=f"VISIBILITY: {vis_text}")
            except Exception:
                pass
                
            # VMC / IMC
            try:
                if state.metar.vis != "N/A" and state.metar.vis != "///":
                    if int(state.metar.vis) >= 5000: self.lbl_vmc.config(text="VMC", bg="#004400", fg=TEXT_GREEN)
                    else: self.lbl_vmc.config(text="IMC", bg="#660000", fg=TEXT_RED)
                else: self.lbl_vmc.config(text="VMC", bg="#004400", fg=TEXT_GREEN)
            except Exception: 
                self.lbl_vmc.config(text="VMC", bg="#004400", fg=TEXT_GREEN)

            # LVP
            is_lvp = False
            try:
                if state.metar.vis != "N/A" and state.metar.vis != "///" and int(state.metar.vis) < 800: is_lvp = True
            except Exception: 
                pass
                
            try:
                if state.metar.rvr != "///":
                    rvr_num_str = re.search(r'\d{4}', state.metar.rvr)
                    if rvr_num_str and int(rvr_num_str.group()) < 600: is_lvp = True
            except Exception: 
                pass

            if is_lvp: self.lbl_lvp.config(bg="#E6A817", fg="#000000") 
            else: self.lbl_lvp.config(bg=BOX_BG, fg="#444444") 

            # Wiatr na dolnym pasku
            try:
                raw_wind = re.search(r'\b(\d{3}|VRB)(\d{2,3})(?:G(\d{2,3}))?KT\b(?:\s+\d{3}V\d{3})?', state.metar.raw)
                met_str = raw_wind.group(0) if raw_wind else "N/A"
                self.lbl_bot_wind.config(text=f"WIND: {met_str}")
            except Exception:
                pass
        except Exception as e:
            pass

    def open_map_action(self):
        if getattr(self, 'map_loading', False): return
            
        if PYWEBVIEW_AVAILABLE:
            self.map_loading = True
            orig_bg = self.btn_map.cget("bg")
            self.btn_map.config(text="ŁADUJE", bg="#DAA520")
            self.update_idletasks()
            
            # Wymuszamy pobranie rozdzielczości całego ekranu dla mapy
            w = self.app.winfo_screenwidth()
            h = self.app.winfo_screenheight()
            x = 0
            y = 0
            is_full = "True"
            
            icao = self.current_icao.get()
            lat, lon = self.app.get_coords(icao)
            
            if not lat or not lon:
                lat, lon = "52.0", "19.0" 
                
            self.after(3000, lambda: [self.btn_map.config(text="MAP", bg=orig_bg), setattr(self, 'map_loading', False)])

            if getattr(sys, 'frozen', False):
                cmd = [sys.executable, "MAP_MODE", str(w), str(h), str(x), str(y), is_full, str(lat), str(lon)]
            else:
                cmd = [sys.executable, sys.argv[0], "MAP_MODE", str(w), str(h), str(x), str(y), is_full, str(lat), str(lon)]
            
            subprocess.Popen(cmd)
        else:
            webbrowser.open("https://www.windy.com")

    def build_center_layout(self, icao):
        self.is_epwa_mode = (icao == "EPWA")
        for w in self.center_frame.winfo_children(): w.destroy()
            
        state = self.app.airport_states.get(icao)
        
        if state: sims = state.phys_sims
        else:
            sims = {
                'epwa_dep': WindSim(), 'epwa_arr': WindSim(),
                'std_low': WindSim(), 'std_mid': WindSim(), 'std_high': WindSim()
            }

        if self.is_epwa_mode:
            self.col_dep = self.create_wind_column(self.center_frame, "DEP", 0, self.active_rwy_dep)
            self.col_arr = self.create_wind_column(self.center_frame, "ARR", 1, self.active_rwy_arr)
            self.col_atis_dep = self.create_atis_column(self.center_frame, "DEP ATIS", 2)
            self.col_atis_arr = self.create_atis_column(self.center_frame, "ARR ATIS", 3)
            self.active_cols = [("dep", self.col_dep, sims['epwa_dep']), ("arr", self.col_arr, sims['epwa_arr'])]
            self.atis_cols = [("dep", self.col_atis_dep), ("arr", self.col_atis_arr)]
        else:
            self.col_tdz = self.create_wind_column(self.center_frame, "TDZ", 0, self.active_rwy_common)
            self.col_mid = self.create_wind_column(self.center_frame, "MID", 1, self.active_rwy_common)
            self.col_end = self.create_wind_column(self.center_frame, "END", 2, self.active_rwy_common)
            self.col_atis = self.create_atis_column(self.center_frame, "ATIS", 3)
            self.active_cols = [("tdz", self.col_tdz, sims['std_low']), ("mid", self.col_mid, sims['std_mid']), ("end", self.col_end, sims['std_high'])]
            self.atis_cols = [("atis", self.col_atis)]
            
        for mode, col in self.atis_cols:
            self.update_single_atis_ui(mode)

    def create_wind_column(self, parent, title, col_idx, rwy_var):
        frame = tk.Frame(parent, bg=PANEL_BG, bd=2, relief=tk.RIDGE)
        frame.grid(row=0, column=col_idx, sticky="nsew", padx=3)
        
        rwy_frame = tk.Frame(frame, bg=PANEL_BG)
        rwy_frame.pack(fill=tk.X, pady=2)
        setattr(self, f"rwy_frame_{title.lower()}", rwy_frame)
        tk.Label(frame, text=title, bg=BOX_BG, fg=TEXT_WHITE, font=("Arial", self.font_sz_title, "bold"), relief=tk.RAISED, bd=1, width=8).pack(anchor="w", padx=5, pady=1)
        
        cvs_size = 150 if self.is_dual else 250
        canvas = tk.Canvas(frame, width=cvs_size, height=cvs_size, bg=PANEL_BG, highlightthickness=0)
        canvas.pack(pady=2 if self.is_dual else 10)
        
        rvr_lbl = tk.Label(frame, text="RVR: ///", bg=BOX_BG, fg=TEXT_WHITE, font=("Consolas", self.font_sz_lbl_bot, "bold"), width=16, relief=tk.SUNKEN, bd=1)
        rvr_lbl.pack(anchor="e", padx=10, pady=1)
        
        cur_wind_lbl = tk.Label(frame, text="INSTANT WIND: ---/--", bg=BOX_BG, fg=TEXT_YELLOW, font=("Consolas", self.font_sz_lbl_bot, "bold"), relief=tk.SUNKEN, bd=1, width=22)
        cur_wind_lbl.pack(anchor="w", padx=5, pady=1)

        # KOMPONENTY WIATRU (HW/XW)
        hw_xw_lbl = tk.Label(frame, text="HW: --kt | XW: --kt", bg=BOX_BG, fg=TEXT_CYAN, font=("Consolas", self.font_sz_lbl_bot, "bold"), relief=tk.SUNKEN, bd=1, width=22)
        hw_xw_lbl.pack(anchor="w", padx=5, pady=1)
        
        env_frame = tk.Frame(frame, bg=PANEL_BG)
        env_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=1)
        
        vis_lbl = tk.Label(env_frame, text="VISIBILITY: ---- m", bg=PANEL_BG, fg=TEXT_WHITE, font=("Consolas", self.font_sz_val, "bold"), anchor="w")
        vis_lbl.pack(fill=tk.X, pady=self.env_pady)
        
        clouds_lbl = tk.Label(env_frame, text="CLOUDS BASE:\n - L1: ---- ft\n - L2: ---- ft", bg=PANEL_BG, fg=TEXT_WHITE, font=("Consolas", self.font_sz_lbl_bot), justify=tk.LEFT, anchor="w")
        clouds_lbl.pack(fill=tk.X, pady=self.env_pady)
        
        grf_lbl = tk.Label(env_frame, text="GRF: 6/6/6 DRY", bg=PANEL_BG, fg=TEXT_GREEN, font=("Consolas", self.font_sz_val, "bold"), anchor="w", relief=tk.FLAT, bd=0)
        grf_lbl.pack(fill=tk.X, pady=self.env_pady)

        temp_lbl = tk.Label(env_frame, text="TEMPERATURE: --.- °C", bg=PANEL_BG, fg=TEXT_CYAN, font=("Consolas", self.font_sz_val, "bold"), anchor="w")
        temp_lbl.pack(fill=tk.X, pady=self.env_pady)
        
        return {"canvas": canvas, "cur_lbl": cur_wind_lbl, "hw_xw_lbl": hw_xw_lbl, "vis_lbl": vis_lbl, "rvr_lbl": rvr_lbl, "clouds_lbl": clouds_lbl, "grf_lbl": grf_lbl, "temp_lbl": temp_lbl, "rwy_var": rwy_var, "rwy_frame": rwy_frame}

    def create_atis_column(self, parent, title, col_idx):
        frame = tk.Frame(parent, bg=PANEL_BG, bd=2, relief=tk.RIDGE)
        frame.grid(row=0, column=col_idx, sticky="nsew", padx=3)
        
        top_bar = tk.Frame(frame, bg=PANEL_BG)
        top_bar.pack(fill=tk.X, padx=3, pady=3)
        tk.Label(top_bar, text=title, bg=BOX_BG, fg=TEXT_GREEN, font=("Arial", self.font_sz_val, "bold"), relief=tk.RAISED, width=10).pack(side=tk.LEFT)
        
        info_lbl = tk.Label(top_bar, text="-", bg=BOX_BG, fg=TEXT_WHITE, font=("Arial", self.font_sz_atis_lbl, "bold"), relief=tk.RAISED, width=3)
        info_lbl.pack(side=tk.RIGHT)
        
        txt = tk.Text(frame, bg="#0A0F18", fg=TEXT_WHITE, font=("Consolas", self.font_sz_atis_txt), bd=0, wrap=tk.WORD)
        txt.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        return {"text": txt, "info_lbl": info_lbl}

    def on_icao_change(self, event=None, force_icao=None):
        new_icao = force_icao if force_icao else self.icao_cb.get()
        old_icao = self.current_icao.get()
        
        if new_icao != old_icao or force_icao:
            if old_icao and old_icao != new_icao:
                self.app.saved_runways[old_icao] = {
                    'dep': self.active_rwy_dep.get(),
                    'arr': self.active_rwy_arr.get(),
                    'common': self.active_rwy_common.get()
                }

            self.current_icao.set(new_icao)
            self.icao_cb.set(new_icao)
            icao = new_icao
            
            if icao not in self.app.airport_states:
                self.app.airport_states[icao] = AirportState(icao)
                threading.Thread(target=self.app.bg_fetch_all_initial, args=(icao,), daemon=True).start()
                
            self.is_epwa_mode = (icao == "EPWA")
            self.build_center_layout(icao)
            self.update_runway_buttons(icao)
            self.close_detail_view(clear_diffs=False)
            
            # ATIS INSTANT LOAD z GLOBAL CACHE
            self.app.process_vatsim_atis_from_global(icao)
            
            state = self.app.airport_states.get(icao)
            if state and state.metar_valid:
                self.update_static_ui()
                self.refresh_env_ui()
                for mode, col in self.atis_cols:
                    self.update_single_atis_ui(mode)

    def update_runway_buttons(self, icao):
        runways = self.app.airports.get(icao, [])
        saved = self.app.saved_runways.get(icao, {})
        
        if self.is_epwa_mode:
            def_dep = runways[0] if runways else ""
            def_arr = runways[-1] if len(runways)>1 else (runways[0] if runways else "")
            
            val_dep = saved.get('dep') if saved.get('dep') in runways else def_dep
            val_arr = saved.get('arr') if saved.get('arr') in runways else def_arr
            
            self.active_rwy_dep.set(val_dep)
            self.active_rwy_arr.set(val_arr)
            
            for col in [self.col_dep, self.col_arr]:
                for w in col["rwy_frame"].winfo_children(): w.destroy()
                for rwy in runways:
                    tk.Radiobutton(col["rwy_frame"], text=f"{rwy}", variable=col["rwy_var"], value=rwy, indicatoron=0, bg="#2A3B5C", fg=TEXT_WHITE, selectcolor="#4A6B9C", font=("Arial", 8, "bold"), width=4).pack(side=tk.LEFT, padx=1)
        else:
            def_com = runways[0] if runways else ""
            val_com = saved.get('common') if saved.get('common') in runways else def_com
            
            self.active_rwy_common.set(val_com)
            
            for col in [self.col_tdz, self.col_mid, self.col_end]:
                for w in col["rwy_frame"].winfo_children(): w.destroy()
            
            for rwy in runways:
                tk.Radiobutton(self.col_tdz["rwy_frame"], text=f"{rwy}", variable=self.active_rwy_common, value=rwy, indicatoron=0, bg="#2A3B5C", fg=TEXT_WHITE, selectcolor="#4A6B9C", font=("Arial", 8, "bold"), width=4).pack(side=tk.LEFT, padx=1)

    def generate_decoded_metar(self, state):
        out = "ODKODOWANE DANE METAR:\n\n"
        if state.is_vrb: 
            out += f"Kierunek Wiatru:   Zmienny (VRB)\n"
        else: 
            out += f"Kierunek Wiatru:   {state.target_dir:03d}°\n"
            
        out += f"Prędkość Wiatru:   {state.target_spd} kt\n"
        if state.target_gust > 0: 
            out += f"Porywy (Gusts):    {state.target_gust} kt\n"
            
        if state.metar.var_min is not None and state.metar.var_max is not None:
            out += f"Zmienność kier.:   od {state.metar.var_min:03d}° do {state.metar.var_max:03d}°\n"
            
        vis_str = "> 10 km (CAVOK)" if state.metar.vis == "9999" else f"{state.metar.vis} m"
        out += f"Widzialność:       {vis_str}\n"
        
        if state.metar.rvr != "///": 
            out += f"RVR na pasie:      {state.metar.rvr}\n"
            
        cloud_dict = {"FEW": "Nieliczne (FEW)", "SCT": "Rozproszone (SCT)", "BKN": "Znaczne (BKN)", "OVC": "Całkowite (OVC)", "VV": "Widz. pionowa (VV)"}
        
        if "CAVOK" in state.metar.raw: 
            out += "Chmury:            CAVOK (Brak chmur poniżej 5000ft)\n"
        elif "NSC" in state.metar.raw: 
            out += "Chmury:            NSC (Brak istotnych chmur)\n"
        elif "NCD" in state.metar.raw: 
            out += "Chmury:            NCD (Brak wykrytych chmur)\n"
        elif not state.metar.clouds: 
            out += "Chmury:            Brak danych\n"
        else:
            out += "Chmury:\n"
            for c in state.metar.clouds:
                ctype, alt_str, cb_tcu = c
                alt_ft = int(alt_str) * 100
                desc = cloud_dict.get(ctype, ctype)
                extra = f" [{cb_tcu}]" if cb_tcu else ""
                out += f"  - {desc} na {alt_ft} ft{extra}\n"
                
        weather_desc = decode_weather_phenomena(state.metar.raw)
        out += f"\nZjawiska pogodowe: {weather_desc}\n"
                
        out += f"\nTemperatura:       {state.metar.temp} °C\n"
        out += f"Punkt Rosy:        {state.metar.dew} °C\n"
        out += f"Ciśnienie QNH:     {state.metar.qnh} hPa\n"
        
        return out

    def add_detail_block(self, text_val, text_color, overstrike=False):
        block_frame = tk.Frame(self.scrollable_frame, bg="#0A0F18")
        block_frame.pack(fill=tk.X, pady=10)
        font_style = ("Consolas", 12, "overstrike") if overstrike else ("Consolas", 12)
        lbl = tk.Label(block_frame, text=text_val, bg="#0A0F18", fg=text_color, font=font_style, justify=tk.LEFT, anchor="w")
        lbl.pack(fill=tk.X, padx=20)
        lbl.bind('<Configure>', lambda e: lbl.config(wraplength=lbl.winfo_width()))
        
        sep = tk.Label(self.scrollable_frame, text="━"*150, bg="#0A0F18", fg="#3A4A6A", font=("Arial", 8))
        sep.pack(fill=tk.X, pady=5)

    def render_notam_view(self, state):
        state.notam_changed = False 
        self.btn_notam.config(bg=BTN_DEF_BG)
        if not state.current_notams and not state.pending_removed_notams and not state.pending_new_notams:
            self.add_detail_block("Brak danych lub brak aktywnych NOTAM dla wybranego lotniska.", TEXT_WHITE)
        else:
            for n in state.pending_removed_notams: 
                self.add_detail_block(n, TEXT_RED, overstrike=True)
            for n in state.pending_new_notams: 
                self.add_detail_block(n, TEXT_GREEN)
                
            std_notams = [n for n in state.current_notams if n not in state.pending_new_notams]
            for n in std_notams: 
                self.add_detail_block(n, TEXT_WHITE)

    def render_taf_view(self, state):
        state.taf_changed = False 
        self.btn_taf.config(bg=BTN_DEF_BG)
        if state.pending_removed_taf: 
            self.add_detail_block("POPRZEDNI (WYGASŁY) TAF:\n\n" + state.pending_removed_taf, TEXT_RED, overstrike=True)
        if state.pending_new_taf: 
            self.add_detail_block("NOWY (ZAKTUALIZOWANY) TAF:\n\n" + state.pending_new_taf, TEXT_GREEN)
        else:
            if state.current_taf: 
                self.add_detail_block(state.current_taf, TEXT_WHITE)
            else: 
                self.add_detail_block("Brak danych TAF dla wybranego lotniska.", TEXT_WHITE)

    def render_metar_view(self, state):
        for w in self.scrollable_frame.winfo_children(): 
            w.destroy()
        
        state.metar_changed_blink = False 
        self.btn_metar.config(bg=BTN_DEF_BG)
        if state.pending_removed_metar_raw: 
            self.add_detail_block("POPRZEDNI (WYGASŁY) METAR:\n\n" + state.pending_removed_metar_raw, TEXT_RED, overstrike=True)
            
        if state.pending_new_metar_raw:
            self.add_detail_block("NOWY (ZAKTUALIZOWANY) METAR:\n\n" + state.pending_new_metar_raw, TEXT_GREEN)
            self.add_detail_block(self.generate_decoded_metar(state), TEXT_WHITE)
        else:
            if state.current_metar_raw:
                self.add_detail_block("AKTUALNY METAR:\n\n" + state.current_metar_raw, TEXT_WHITE)
                self.add_detail_block(self.generate_decoded_metar(state), TEXT_WHITE)
            else: 
                self.add_detail_block("Brak danych METAR dla wybranego lotniska.", TEXT_WHITE)
            
        self.scrollable_frame.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def render_metar_history(self, state):
        for w in self.scrollable_frame.winfo_children(): 
            w.destroy()
            
        self.add_detail_block("HISTORIA METAR (Z ostatnich 3 godzin):", TEXT_YELLOW)
        
        if not state.metar_history_raw:
            self.add_detail_block("Brak historii METAR dla tego lotniska.", TEXT_WHITE)
        else:
            for m in reversed(state.metar_history_raw):
                self.add_detail_block(m, TEXT_WHITE)
                
        self.scrollable_frame.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def toggle_metar_history(self):
        icao = self.current_icao.get()
        state = self.app.airport_states.get(icao)
        if not state: return
        
        if getattr(self, 'showing_history', False):
            self.showing_history = False
            self.btn_prev.config(text="PREVIOUS METAR")
            self.render_metar_view(state)
        else:
            self.showing_history = True
            self.btn_prev.config(text="CURRENT METAR")
            self.render_metar_history(state)

    def open_detail_view(self, view_type):
        icao = self.current_icao.get()
        if not icao: return
        state = self.app.airport_states.get(icao)
        if not state: return
        
        self.awos_frame.pack_forget()
        for w in self.detail_frame.winfo_children(): 
            w.destroy()
            
        top_bar = tk.Frame(self.detail_frame, bg=PANEL_BG, bd=1, relief=tk.SOLID)
        top_bar.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)
        
        btn_back = tk.Button(top_bar, text="◄ POWRÓT DO AWOS", bg="#E6A817", fg="#000000", font=("Arial", 14, "bold"), command=lambda: self.close_detail_view(clear_diffs=True))
        btn_back.pack(side=tk.LEFT, padx=10, pady=10)
        lbl_title = tk.Label(top_bar, text=f"{view_type} - {icao}", bg=PANEL_BG, fg=TEXT_CYAN, font=("Arial", 16, "bold"))
        lbl_title.pack(side=tk.LEFT, padx=20)
        
        if view_type == "METAR":
            self.showing_history = False
            bot_bar = tk.Frame(self.detail_frame, bg=PANEL_BG)
            bot_bar.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=10)
            self.btn_prev = tk.Button(bot_bar, text="PREVIOUS METAR", bg="#006699", fg=TEXT_WHITE, font=("Arial", 12, "bold"), width=20, command=self.toggle_metar_history)
            self.btn_prev.pack(side=tk.RIGHT, padx=20)
        
        txt_frame = tk.Frame(self.detail_frame, bg="#0A0F18")
        txt_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.canvas = tk.Canvas(txt_frame, bg="#0A0F18", highlightthickness=0)
        scrollbar = tk.Scrollbar(txt_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg="#0A0F18")
        
        self.scrollable_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        
        def configure_canvas(event):
            self.canvas.itemconfig(canvas_window, width=event.width)
        self.canvas.bind("<Configure>", configure_canvas)
        
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        self.bind_all("<MouseWheel>", lambda e: self.canvas.yview_scroll(int(-1*(e.delta/120)), "units"))

        if view_type == "NOTAM":
            self.render_notam_view(state)
        elif view_type == "TAF":
            self.render_taf_view(state)
        elif view_type == "METAR":
            self.render_metar_view(state)
                    
        self.detail_frame.pack(fill=tk.BOTH, expand=True)

    def close_detail_view(self, clear_diffs=True):
        self.unbind_all("<MouseWheel>") 
        icao = self.current_icao.get()
        state = self.app.airport_states.get(icao)
        
        if clear_diffs and state:
            if state.next_snapshot_notams: 
                state.current_notams = list(state.next_snapshot_notams)
                self.app.notams_cache[icao] = list(state.next_snapshot_notams)
                self.app.save_notams_cache()
            
            if state.next_snapshot_taf: 
                state.current_taf = state.next_snapshot_taf
            if state.next_snapshot_metar_raw: 
                state.current_metar_raw = state.next_snapshot_metar_raw
                
            state.pending_new_notams.clear()
            state.pending_removed_notams.clear()
            state.pending_new_taf = ""
            state.pending_removed_taf = ""
            state.pending_new_metar_raw = ""
            state.pending_removed_metar_raw = ""
            
        self.detail_frame.pack_forget()
        self.awos_frame.pack(fill=tk.BOTH, expand=True)

    def update_single_atis_ui(self, mode):
        icao = self.current_icao.get()
        state = self.app.airport_states.get(icao)
        if not state: return
        key = f"{icao}_{mode}"
        
        col = None
        if self.is_epwa_mode:
            if mode == "dep": col = getattr(self, "col_atis_dep", None)
            elif mode == "arr": col = getattr(self, "col_atis_arr", None)
        else:
            if mode == "atis": col = getattr(self, "col_atis", None)
            
        if not col or "text" not in col: return
        txt_widget = col["text"]
        lbl_widget = col["info_lbl"]
        
        new_text = state.atis_data_text.get(key, "Brak danych ATIS w sieci VATSIM.")
        old_text = state.atis_data_prev.get(key, new_text)
        new_code = state.atis_data_code.get(key, "-")
        
        lbl_widget.config(text=new_code)
        txt_widget.config(state=tk.NORMAL)
        txt_widget.delete("1.0", tk.END)
        txt_widget.tag_configure("diff", background="#997A00", foreground=TEXT_WHITE)
        txt_widget.tag_configure("normal", background="#0A0F18", foreground=TEXT_WHITE)
        
        elapsed = time.time() - state.atis_change_time.get(key, 0)
        if 0 < elapsed <= 300: 
            state.atis_diff_active[key] = True
            old_words = [w for w in re.split(r'(\s+)', old_text) if w]
            new_words = [w for w in re.split(r'(\s+)', new_text) if w]
            
            matcher = SequenceMatcher(None, old_words, new_words)
            for tag, i1, i2, j1, j2 in matcher.get_opcodes():
                chunk = "".join(new_words[j1:j2])
                if tag in ('replace', 'insert'): txt_widget.insert(tk.END, chunk, "diff")
                elif tag == 'equal': txt_widget.insert(tk.END, chunk, "normal")
        else:
            state.atis_diff_active[key] = False
            txt_widget.insert(tk.END, new_text, "normal")
            
        txt_widget.config(state=tk.DISABLED)

    def refresh_wind_ui(self):
        state = self.app.airport_states.get(self.current_icao.get())
        if state and state.metar_valid:
            for sim in state.phys_sims.values(): 
                sim.publish()
            
            same_rwy = False
            if self.active_rwy_dep.get() != "":
                same_rwy = (self.active_rwy_dep.get() == self.active_rwy_arr.get())
            
            if self.is_epwa_mode and same_rwy:
                s_dep, s_arr = state.phys_sims['epwa_dep'], state.phys_sims['epwa_arr']
                s_arr.pub_avg_dir = s_dep.pub_avg_dir
                s_arr.pub_avg_spd = s_dep.pub_avg_spd
                s_arr.pub_max_spd = s_dep.pub_max_spd
                s_arr.pub_min_dir = s_dep.pub_min_dir
                s_arr.pub_max_dir = s_dep.pub_max_dir

            if self.is_epwa_mode:
                self.update_wind_ui(self.col_dep, state.phys_sims['epwa_dep'])
                self.update_wind_ui(self.col_arr, state.phys_sims['epwa_arr'])
            else:
                rwy_str = self.active_rwy_common.get()
                hdg = 0
                if rwy_str != "":
                    try: 
                        hdg = int(re.sub(r'[A-Z]', '', rwy_str)) * 10
                    except ValueError: 
                        pass
                if hdg < 180:
                    self.update_wind_ui(self.col_tdz, state.phys_sims['std_low'])
                    self.update_wind_ui(self.col_end, state.phys_sims['std_high'])
                else:
                    self.update_wind_ui(self.col_tdz, state.phys_sims['std_high'])
                    self.update_wind_ui(self.col_end, state.phys_sims['std_low'])
                self.update_wind_ui(self.col_mid, state.phys_sims['std_mid'])

    def refresh_env_ui(self):
        state = self.app.airport_states.get(self.current_icao.get())
        if not state: return
        
        if self.is_epwa_mode:
            self.update_col_env(self.col_dep, state.phys_envs['epwa_dep'])
            self.update_col_env(self.col_arr, state.phys_envs['epwa_arr'])
        else:
            rwy_str = self.active_rwy_common.get()
            hdg = 0
            if rwy_str != "":
                try: 
                    hdg = int(re.sub(r'[A-Z]', '', rwy_str)) * 10
                except ValueError: pass
                
            if hdg < 180:
                self.update_col_env(self.col_tdz, state.phys_envs['std_low'])
                self.update_col_env(self.col_end, state.phys_envs['std_high'])
            else:
                self.update_col_env(self.col_tdz, state.phys_envs['std_high'])
                self.update_col_env(self.col_end, state.phys_envs['std_low'])
                
            self.update_col_env(self.col_mid, state.phys_envs['std_mid'])

    def update_wind_ui(self, col_data, sim):
        canvas = col_data["canvas"]
        rwy_str = col_data["rwy_var"].get()
        
        col_data["cur_lbl"].config(text=f"INSTANT WIND: {sim.cur_dir:03d}/{sim.cur_spd:02d}kt")
        
        # HW / XW KALKULATOR POD INSTANT WIND
        hw_xw_lbl = col_data.get("hw_xw_lbl")
        if hw_xw_lbl:
            if rwy_str and re.sub(r'[A-Z]', '', str(rwy_str)).isdigit():
                try:
                    rwy_hdg = int(re.sub(r'[A-Z]', '', str(rwy_str))) * 10
                    angle_diff = math.radians(sim.cur_dir - rwy_hdg)
                    hw = sim.cur_spd * math.cos(angle_diff)
                    xw = sim.cur_spd * math.sin(angle_diff)
                    
                    hw_val = int(round(hw))
                    xw_val = int(round(abs(xw)))
                    
                    if xw_val == 0:
                        xw_dir = ""
                    else:
                        xw_dir = "R" if xw > 0 else "L"
                    
                    hw_str = f"HW:{hw_val}kt" if hw_val >= 0 else f"TW:{abs(hw_val)}kt"
                    xw_str = f"{xw_val}{xw_dir}kt"
                    
                    hw_xw_lbl.config(text=f"{hw_str} | XW:{xw_str}")
                except ValueError:
                    hw_xw_lbl.config(text="HW: --kt | XW: --kt")
            else:
                hw_xw_lbl.config(text="HW: --kt | XW: --kt")

        canvas.delete("all")
        
        cvs_size = 150 if self.is_dual else 250
        cx = cy = cvs_size // 2
        r_out = 65 if self.is_dual else 105
        r_in = 35 if self.is_dual else 60

        canvas.create_oval(cx-r_out, cy-r_out, cx+r_out, cy+r_out, outline="#4A6B9C", width=2)
        for i in range(0, 360, 10):
            angle = math.radians(i - 90)
            length = 4 if i % 30 != 0 else 8
            x1 = cx + (r_out - length) * math.cos(angle)
            y1 = cy + (r_out - length) * math.sin(angle)
            x2 = cx + r_out * math.cos(angle)
            y2 = cy + r_out * math.sin(angle)
            canvas.create_line(x1, y1, x2, y2, fill="#4A6B9C", width=2 if i % 30 == 0 else 1)

        canvas.create_oval(cx-r_in, cy-r_in, cx+r_in, cy+r_in, outline="#2A3B5C", width=2)
        
        extent = (sim.pub_max_dir - sim.pub_min_dir) % 360
        if extent < 2: 
            extent = 2 
        start_angle = (90 - sim.pub_max_dir) % 360
        
        arc_color = TEXT_YELLOW if (sim.pub_max_spd - sim.pub_avg_spd) > 5 else TEXT_WHITE
        canvas.create_arc(cx-r_in, cy-r_in, cx+r_in, cy+r_in, start=start_angle, extent=extent, style=tk.ARC, outline=arc_color, width=4)

        if str(rwy_str) != "":
            try: 
                rwy_hdg = int(re.sub(r'[A-Z]', '', str(rwy_str))) * 10
            except ValueError: 
                rwy_hdg = 0
                
            rwy_rad = math.radians(rwy_hdg - 90)
            r_line_len = r_out - 15
            rwy_dx = r_line_len * math.cos(rwy_rad)
            rwy_dy = r_line_len * math.sin(rwy_rad)
            canvas.create_line(cx - rwy_dx, cy - rwy_dy, cx + rwy_dx, cy + rwy_dy, fill="#6B7280", width=10, capstyle=tk.BUTT)

        dev_angle = math.radians(sim.cur_dir - 90)
        dev_x = cx + r_out * math.cos(dev_angle)
        dev_y = cy + r_out * math.sin(dev_angle)
        
        marker_color = TEXT_YELLOW if (sim.cur_spd - sim.pub_avg_spd) > 5 else TEXT_WHITE
        canvas.create_oval(dev_x-5, dev_y-5, dev_x+5, dev_y+5, fill=marker_color, outline=marker_color)

        if getattr(sim, 'ws_alert', False) and self.app.blink_state:
            canvas.create_text(cx, cy - 25, text="WS WRNG", fill=TEXT_RED, font=("Consolas", 12, "bold"))

        canvas.create_text(cx, cy - 10, text=f"{sim.pub_avg_dir:03d}°", fill=TEXT_WHITE, font=("Consolas", 13 if self.is_dual else 20, "bold"))
        canvas.create_text(cx, cy + 12, text=f"{sim.pub_avg_spd:02d}kt", fill=TEXT_WHITE, font=("Consolas", 10 if self.is_dual else 16, "bold"))

    def update_col_env(self, col, env):
        if not env: return
        c_vis = env['vis']
        c_rvr = env['rvr']
        
        if c_vis < 9999:
            col["vis_lbl"].config(text=f"VISIBILITY: {int(c_vis)} m")
            col["rvr_lbl"].config(text=f"RVR: {int(c_rvr)} m")
        else:
            col["vis_lbl"].config(text="VISIBILITY: > 10 km")
            col["rvr_lbl"].config(text=f"RVR: > {int(c_rvr)} m")
            
        cloud_txt = "CLOUDS BASE:\n" + "\n".join([f" - L{i+1}: {int(alt)} ft" for i, alt in enumerate(env['clouds'])])
        col["clouds_lbl"].config(text=cloud_txt)
        col["temp_lbl"].config(text=f"TEMPERATURE: {env['temp']:.1f} °C")
        
        if 'grf' in env:
            col["grf_lbl"].config(text=f"GRF: {env['grf']}", bg=PANEL_BG, fg=env.get('grf_color', TEXT_WHITE))

# GŁÓWNA KLASA KONTROLERA APLIKACJI
class VirtualAWOS(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("AWOS - Automated Weather Observing System")
        self.geometry("1280x750")  
        self.configure(bg=BG_COLOR)
        
        try:
            icon_img = tk.PhotoImage(file="awos_icon.png")
            self.iconphoto(False, icon_img)
        except Exception: pass
        
        self.is_fullscreen = True
        self.attributes("-fullscreen", True)
        self.bind("<F11>", self.toggle_fullscreen)
        self.bind("<Escape>", self.exit_fullscreen)
        
        self.atis_sound = None
        if PYGAME_AVAILABLE:
            try:
                pygame.mixer.init()
                create_beep_wav()
                self.atis_sound = pygame.mixer.Sound("atis_beep.wav")
            except Exception: pass
        
        self.airports = self.parse_airport_data()
        self.saved_runways = {}
        self.notams_cache = self.load_notams_cache()
        self.airport_states = {}
        
        self.dual_mode = False
        self.panels = []
        self.blink_state = False
        self.saved_dual_icao = ""
        self.global_atis_data = [] # Globalny Cache ATIS
        
        self.main_container = tk.Frame(self, bg=BG_COLOR)
        self.main_container.pack(fill=tk.BOTH, expand=True)
        
        # Inicjalizacja lotnisk
        self.airport_states["EPWA"] = AirportState("EPWA")
        self.airport_states["EPMO"] = AirportState("EPMO")
        
        self.setup_screen_layout(initial=True)
        
        self.update_clock()
        self.periodic_metar_fetch()
        self.periodic_taf_notam_fetch()
        self.periodic_open_meteo_fetch()
        self.periodic_vatsim_atis_fetch()
        self.check_atis_timers()
        self.blink_loop()
        self.wind_simulation_tick()

    def toggle_split_screen(self):
        self.dual_mode = not self.dual_mode
        self.setup_screen_layout()

    def setup_screen_layout(self, initial=False):
        top_icao = "EPWA"
        bot_icao = "EPMO"
        
        if not initial and self.panels:
            top_icao = self.panels[0].current_icao.get()
            if self.dual_mode:
                bot_icao = self.saved_dual_icao if self.saved_dual_icao else "EPMO"
            else:
                if len(self.panels) > 1:
                    self.saved_dual_icao = self.panels[1].current_icao.get()

        # Uratowanie pasów startowych przed usunięciem paneli
        for p in self.panels:
            icao = p.current_icao.get()
            if icao:
                self.saved_runways[icao] = {
                    'dep': p.active_rwy_dep.get(),
                    'arr': p.active_rwy_arr.get(),
                    'common': p.active_rwy_common.get()
                }
            p.destroy()
            
        self.panels.clear()
        
        if not self.dual_mode:
            p1 = AWOSPanel(self.main_container, self, top_icao, is_dual=False)
            p1.pack(fill=tk.BOTH, expand=True)
            self.panels.append(p1)
        else:
            p1 = AWOSPanel(self.main_container, self, top_icao, is_dual=True)
            p1.pack(fill=tk.BOTH, expand=True, side=tk.TOP, pady=(0, 2))
            p2 = AWOSPanel(self.main_container, self, bot_icao, is_dual=True)
            p2.pack(fill=tk.BOTH, expand=True, side=tk.TOP, pady=(2, 0))
            self.panels.extend([p1, p2])

        for p in self.panels:
            # Szybko sprawdź czy to lotnisko już zaciągnęło dane ATIS i METAR, w przeciwnym razie wyślij pobieranie
            state = self.airport_states.get(p.current_icao.get())
            if state and state.metar_valid:
                p.update_static_ui()
                p.refresh_env_ui()
            threading.Thread(target=self.bg_fetch_all_initial, args=(p.current_icao.get(),), daemon=True).start()

    def load_notams_cache(self):
        try:
            if os.path.exists("awos_notams_cache.json"):
                with open("awos_notams_cache.json", "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception: pass
        return {}

    def save_notams_cache(self):
        try:
            with open("awos_notams_cache.json", "w", encoding="utf-8") as f:
                json.dump(self.notams_cache, f, ensure_ascii=False, indent=2)
        except Exception: pass

    def toggle_fullscreen(self, event=None):
        self.is_fullscreen = not self.is_fullscreen
        self.attributes("-fullscreen", self.is_fullscreen)
        return "break"

    def exit_fullscreen(self, event=None):
        self.is_fullscreen = False
        self.attributes("-fullscreen", False)
        return "break"

    def play_atis_alert(self):
        def beep_task():
            if self.atis_sound:
                self.atis_sound.play()
                time.sleep(0.4)
                self.atis_sound.play()
            elif winsound:
                winsound.Beep(1200, 300)
                time.sleep(0.1)
                winsound.Beep(1200, 300)
        threading.Thread(target=beep_task, daemon=True).start()

    def extract_atis_letter(self, text, fallback_code):
        phonetics = {
            "ALPHA": "A", "ALFA": "A", "BRAVO": "B", "CHARLIE": "C", "DELTA": "D", "ECHO": "E",
            "FOXTROT": "F", "GOLF": "G", "HOTEL": "H", "INDIA": "I", "JULIETT": "J", "JULIET": "J",
            "KILO": "K", "LIMA": "L", "MIKE": "M", "NOVEMBER": "N", "OSCAR": "O", "PAPA": "P",
            "QUEBEC": "Q", "ROMEO": "R", "SIERRA": "S", "TANGO": "T", "UNIFORM": "U",
            "VICTOR": "V", "WHISKEY": "W", "XRAY": "X", "X-RAY": "X", "YANKEE": "Y", "ZULU": "Z"
        }
        match = re.search(r'\bINFORMATION\s+([A-Z\-]+)\b', text.upper())
        if match:
            word = match.group(1)
            if word in phonetics:
                return phonetics[word]
        return fallback_code

    def parse_airport_data(self):
        db = {}
        for line in AIRPORT_DATA.strip().split('\n'):
            parts = line.split('|')
            if len(parts) >= 5: 
                db[parts[0]] = [r.split(':')[0] for r in parts[4].split(',') if ':' in r]
        return db

    def get_coords(self, icao):
        for line in AIRPORT_DATA.strip().split('\n'):
            parts = line.split('|')
            if len(parts) >= 4 and parts[0] == icao:
                return parts[2].replace(',', '.'), parts[3].replace(',', '.')
        return None, None

    def bg_fetch_elevation_grid(self, icao):
        state = self.airport_states.get(icao)
        if not state: return
        lat_str, lon_str = self.get_coords(icao)
        if not lat_str or not lon_str: return
        
        try:
            lat = float(lat_str)
            lon = float(lon_str)
            d = 0.05 
            lats = f"{lat},{lat+d},{lat-d},{lat},{lat}"
            lons = f"{lon},{lon},{lon},{lon+d},{lon-d}"
            
            url = f"https://api.open-meteo.com/v1/elevation?latitude={lats}&longitude={lons}"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                elevs = data.get('elevation', [])
                if len(elevs) == 5:
                    c, n, s, e, w = elevs
                    
                    dy = n - s
                    dx = e - w
                    mag = math.sqrt(dx**2 + dy**2)
                    
                    slope_dir = None
                    if mag > 15: 
                        slope_dir = (math.degrees(math.atan2(dx, dy)) + 360) % 360
                        
                    is_ew_valley = (n - c > 30) and (s - c > 30)
                    is_ns_valley = (e - c > 30) and (w - c > 30)
                    
                    v_axis = None
                    if is_ew_valley: v_axis = 90
                    elif is_ns_valley: v_axis = 0
                    
                    t_type = 'FLAT'
                    if v_axis is not None: t_type = 'VALLEY'
                    elif mag > 25: t_type = 'SLOPE'
                    
                    state.terrain_profile = {
                        'type': t_type,
                        'slope_dir': slope_dir,
                        'slope_mag': mag,
                        'valley_axis': v_axis
                    }
        except Exception: pass

    def download_metar_history(self, icao, hours=3):
        target_icao = icao
        if icao == "EPBC": target_icao = "EPWA"
        elif icao == "EPKS": target_icao = "EPPO"
        elif icao == "EPOK": target_icao = "EPGD"
        elif icao == "EPKP": target_icao = "EPKK"
        
        try:
            req = urllib.request.Request(f"https://aviationweather.gov/api/data/metar?ids={target_icao}&hours={hours}", headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = resp.read().decode('utf-8').strip()
                if data:
                    lines = [line.strip() for line in data.split('\n') if line.strip()]
                    return lines[::-1] 
        except Exception: pass
        return []

    def calculate_initial_rwy_state(self, state, history):
        water = 0.0
        snow = 0.0
        for metar_str in history:
            spd = 0
            wnd_match = re.search(r'\b(?:\d{3}|VRB)(\d{2,3})(?:G\d{2,3})?KT\b', metar_str)
            if wnd_match: spd = int(wnd_match.group(1))
            
            temp = 15.0
            temp_match = re.search(r'\b(M?\d{2})/(M?\d{2})\b', metar_str)
            if temp_match:
                temp = float(temp_match.group(1).replace('M', '-'))
                
            has_rain = bool(re.search(r'\b[+-]?(?:SH|TS)?(?:RA|DZ)\b', metar_str))
            has_snow = bool(re.search(r'\b[+-]?(?:SH|TS)?(?:SN|SG)\b', metar_str))
            has_ice = bool(re.search(r'\b[+-]?(?:FZ[A-Z]*|PL|GS|GR)\b', metar_str))
            
            drying_step = (0.001 + spd * 0.0001) * 360
            
            if has_rain:
                water = min(1.0, water + 0.5)
                snow = max(0.0, snow - 0.2)
            elif has_snow:
                snow = min(1.0, snow + 0.5)
            elif has_ice:
                water = min(1.0, water + 0.5)
                
            if not has_rain and not has_ice:
                water = max(0.0, water - drying_step)
                
            if not has_snow and temp > 0 and snow > 0:
                melt_rate = drying_step * temp * 0.2
                melted = min(snow, melt_rate)
                snow -= melted
                water = min(1.0, water + melted)
                
        state.rwy_water_level = water
        state.rwy_snow_level = snow

    def bg_fetch_all_initial(self, icao):
        state = self.airport_states.get(icao)
        if not state: return
        
        threading.Thread(target=self.bg_fetch_open_meteo, args=(icao,), daemon=True).start()
        threading.Thread(target=self.bg_fetch_elevation_grid, args=(icao,), daemon=True).start()
        
        history = self.download_metar_history(icao, hours=3)
        if history:
            state.metar_history_raw = list(history)
            self.calculate_initial_rwy_state(state, history)
        else:
            state.metar_history_raw = []
            
        m_raw = self.download_metar(icao)
        self.after(0, self.process_metar_result, m_raw, True, icao)
        t_raw = self.download_taf(icao)
        n_raw = self.download_notam(icao)
        self.after(0, self.process_taf_notam_result, t_raw, n_raw, icao)

    def periodic_metar_fetch(self):
        for icao in list(self.airport_states.keys()):
            threading.Thread(target=self.bg_fetch_metar, args=(icao,), daemon=True).start()
        self.after(60000, self.periodic_metar_fetch) 

    def get_fallback_metar(self, icao):
        try:
            req = urllib.request.Request(f"https://api.checkwx.com/metar/{icao}", headers={'X-API-Key': '12c75a4095594b2f8a4cd39908'})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                if data and 'data' in data and len(data['data']) > 0:
                    return data['data'][0]
        except Exception: pass
        return None

    def bg_fetch_metar(self, icao):
        m_raw = self.download_metar(icao)
        if m_raw is None:
            if icao == "EPBC": m_raw = self.download_metar("EPWA")
            elif icao == "EPKS": m_raw = self.download_metar("EPPO")
            elif icao == "EPOK": m_raw = self.download_metar("EPGD")
            elif icao == "EPKP": m_raw = self.download_metar("EPKK")
            else: m_raw = self.get_fallback_metar(icao)
        self.after(0, self.process_metar_result, m_raw, False, icao)

    def periodic_taf_notam_fetch(self):
        for icao in list(self.airport_states.keys()):
            threading.Thread(target=self.bg_fetch_taf_notam, args=(icao,), daemon=True).start()
        self.after(900000, self.periodic_taf_notam_fetch) 

    def get_fallback_taf(self, icao):
        try:
            req = urllib.request.Request(f"https://api.checkwx.com/taf/{icao}", headers={'X-API-Key': '12c75a4095594b2f8a4cd39908'})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                if data and 'data' in data and len(data['data']) > 0:
                    return data['data'][0]
        except Exception: pass
        return None

    def bg_fetch_taf_notam(self, icao):
        t_raw = self.download_taf(icao)
        if t_raw is None:
            t_raw = self.get_fallback_taf(icao)
            
        n_raw = self.download_notam(icao)
        self.after(0, self.process_taf_notam_result, t_raw, n_raw, icao)

    def download_metar(self, icao):
        target_icao = icao
        if icao == "EPBC": target_icao = "EPWA"
        elif icao == "EPKS": target_icao = "EPPO"
        elif icao == "EPOK": target_icao = "EPGD"
        elif icao == "EPKP": target_icao = "EPKK"
        
        try:
            req = urllib.request.Request(f"https://aviationweather.gov/api/data/metar?ids={target_icao}", headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=4) as resp:
                data = resp.read().decode('utf-8').strip()
                if data: return data.split('\n')[0]
        except Exception: pass

        try:
            req = urllib.request.Request(f"https://metar.vatsim.net/{target_icao}", headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=4) as resp:
                data = resp.read().decode('utf-8').strip()
                if data and len(data) > 10 and "Unrecognized" not in data:
                    return data
        except Exception: pass
        
        try:
            req = urllib.request.Request(f"https://api.checkwx.com/metar/{target_icao}", headers={'X-API-Key': '12c75a4095594b2f8a4cd39908'})
            with urllib.request.urlopen(req, timeout=4) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                if data and 'data' in data and len(data['data']) > 0:
                    return data['data'][0]
        except Exception: pass
        
        return None

    def download_taf(self, icao):
        try:
            req = urllib.request.Request(f"https://aviationweather.gov/api/data/taf?ids={icao}", headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=4) as resp:
                data = resp.read().decode('utf-8').strip()
                return data if data else None
        except Exception: pass
        return None

    def download_notam(self, icao):
        try:
            url = "https://notams.aim.faa.gov/notamSearch/search"
            payload = urllib.parse.urlencode({'searchType': '0', 'designatorsForLocation': icao}).encode('utf-8')
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            headers = {
                'User-Agent': 'Mozilla/5.0',
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'X-Requested-With': 'XMLHttpRequest'
            }
            req = urllib.request.Request(url, data=payload, headers=headers)
            with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
                json_data = json.loads(resp.read().decode('utf-8'))
                notams = []
                if "notamList" in json_data and len(json_data["notamList"]) > 0:
                    for item in json_data["notamList"]:
                        msg = item.get("icaoMessage", "")
                        if not msg or str(msg).strip() == "": msg = item.get("traditionalMessage", "")
                        if not msg or str(msg).strip() == "": msg = item.get("message", "")
                        if not msg or str(msg).strip() == "":
                            if item.get("notamNumber") and item.get("cdata"): msg = f"{item['notamNumber']}\n{item['cdata']}"
                        msg = str(msg).strip()
                        if msg:
                            b_m = re.search(r'\bB\)\s*(\d{10})', msg)
                            c_m = re.search(r'\bC\)\s*(\d{10}|PERM|EST)', msg)
                            if b_m or c_m:
                                eff_from = format_notam_date(b_m.group(1)) if b_m else "UNKNOWN"
                                eff_to = format_notam_date(c_m.group(1)) if c_m else "UNKNOWN"
                                msg = f"Effective from {eff_from}    Effective to {eff_to}\n" + msg
                            notams.append(msg.replace("<br>", "\n").replace("</br>", "\n"))
                return notams
        except Exception: pass
        return None

    def periodic_open_meteo_fetch(self):
        for icao in list(self.airport_states.keys()):
            threading.Thread(target=self.bg_fetch_open_meteo, args=(icao,), daemon=True).start()
        self.after(900000, self.periodic_open_meteo_fetch)

    def bg_fetch_open_meteo(self, icao):
        state = self.airport_states.get(icao)
        if not state: return
        lat, lon = self.get_coords(icao)
        if not lat or not lon: return
        
        try:
            url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&hourly=wind_speed_10m,wind_direction_10m,wind_gusts_10m,visibility&wind_speed_unit=kn&timezone=UTC&forecast_days=2"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                state.om_data = data
        except Exception: pass

    def periodic_vatsim_atis_fetch(self):
        threading.Thread(target=self.bg_fetch_vatsim_atis, daemon=True).start()
        self.after(60000, self.periodic_vatsim_atis_fetch)

    def bg_fetch_vatsim_atis(self):
        try:
            url = "https://data.vatsim.net/v3/afv-atis-data.json"
            if REQUESTS_AVAILABLE:
                headers = {'Accept': 'application/json'}
                response = requests.request("GET", url, headers=headers, timeout=10)
                try:
                    data = response.json()
                except:
                    data = json.loads(response.text)
            else:
                req = urllib.request.Request(url, headers={'Accept': 'application/json'})
                with urllib.request.urlopen(req, timeout=10) as response:
                    data = json.loads(response.read().decode('utf-8'))
                    
            if isinstance(data, list):
                self.global_atis_data = data
            elif isinstance(data, dict):
                self.global_atis_data = data.get("atis", [])
                
            for icao in list(self.airport_states.keys()):
                self.process_vatsim_atis_from_global(icao)
        except Exception as e:
            pass

    def process_vatsim_atis_from_global(self, icao):
        if not getattr(self, 'global_atis_data', None): return
        
        results = {"dep": None, "arr": None, "atis": None}
        for item in self.global_atis_data:
            callsign = str(item.get("callsign", ""))
            if icao in callsign and "ATIS" in callsign:
                t = item.get("text_atis", item.get("text", ""))
                if isinstance(t, list): t = "\n".join(t)
                if not t: t = f"ATIS dostępny tylko głosowo na freq: {item.get('freq', '---')}"
                
                raw_code = item.get("atis_code", "-")
                if not raw_code: raw_code = "-"
                code = self.extract_atis_letter(t, raw_code)
                
                if "_D_" in callsign: results["dep"] = {"code": code, "text": t}
                elif "_A_" in callsign: results["arr"] = {"code": code, "text": t}
                else: results["atis"] = {"code": code, "text": t}
                
        if not results["dep"] and results["atis"]: results["dep"] = results["atis"]
        if not results["arr"] and results["atis"]: results["arr"] = results["atis"]
        if not results["atis"] and results["dep"]: results["atis"] = results["dep"]
        
        self.after(0, self.apply_atis_results, results, icao)

    def apply_atis_results(self, results, req_icao):
        state = self.airport_states.get(req_icao)
        if not state: return
        
        should_beep = False
        modes_to_update = ["dep", "arr"] if req_icao == "EPWA" else ["atis"]
        
        for mode in modes_to_update:
            key = f"{req_icao}_{mode}"
            
            if results.get(mode):
                new_text = results[mode]["text"]
                new_code = results[mode]["code"]
            else:
                new_text = "Brak danych ATIS w sieci VATSIM."
                new_code = "-"
                
            old_text = state.atis_data_text.get(key, "Brak danych ATIS w sieci VATSIM.")
            
            if new_text != old_text:
                if state.is_initial_atis_fetch:
                    state.atis_data_prev[key] = new_text
                    state.atis_change_time[key] = 0
                else:
                    state.atis_data_prev[key] = old_text
                    state.atis_change_time[key] = time.time()
                    if new_code != "-": 
                        should_beep = True
                    
            state.atis_data_text[key] = new_text
            state.atis_data_code[key] = new_code
            
            for p in self.panels:
                if p.current_icao.get() == req_icao:
                    p.update_single_atis_ui(mode)
            
        state.is_initial_atis_fetch = False
        if should_beep:
            for p in self.panels:
                if p.current_icao.get() == req_icao:
                    self.play_atis_alert()
                    break

    def check_atis_timers(self):
        for p in self.panels:
            icao = p.current_icao.get()
            if icao:
                state = self.airport_states.get(icao)
                if state:
                    modes = ["dep", "arr"] if icao == "EPWA" else ["atis"]
                    for mode in modes:
                        key = f"{icao}_{mode}"
                        if time.time() - state.atis_change_time.get(key, 0) > 300 and state.atis_diff_active.get(key, False):
                            p.update_single_atis_ui(mode)
        self.after(5000, self.check_atis_timers)

    def parse_metar_regex(self, state, metar_str):
        state.target_dir, state.target_spd, state.target_gust = 0, 0, 0
        state.target_vis = 9999
        state.metar.var_min, state.metar.var_max = None, None
        state.metar.clouds = []
        
        # LOGIKA VRB DETEKCJA
        wnd_match = re.search(r'\b(\d{3}|VRB)(\d{2,3})(?:G(\d{2,3}))?KT\b', metar_str)
        if wnd_match:
            d = wnd_match.group(1)
            state.is_vrb = (d == 'VRB')
            state.target_dir = 0 if state.is_vrb else int(d)
            state.target_spd = int(wnd_match.group(2))
            state.target_gust = int(wnd_match.group(3)) if wnd_match.group(3) else 0
            
        var_match = re.search(r'\b(\d{3})V(\d{3})\b', metar_str)
        if var_match:
            state.metar.var_min = int(var_match.group(1))
            state.metar.var_max = int(var_match.group(2))
            
        state.metar.clouds = re.findall(r'\b(FEW|SCT|BKN|OVC|VV)(\d{3})(CB|TCU)?\b', metar_str)
            
        temp_match = re.search(r'\b(M?\d{2})/(M?\d{2})\b', metar_str)
        if temp_match:
            state.metar.temp = temp_match.group(1).replace('M', '-')
            state.metar.dew = temp_match.group(2).replace('M', '-')
            
        qnh_match = re.search(r'\bQ(\d{4})\b', metar_str)
        state.metar.qnh = qnh_match.group(1) if qnh_match else "N/A"
        
        vis_match = re.search(r'\s(\d{4})\s', metar_str + " ")
        if vis_match: state.target_vis = int(vis_match.group(1))
        if "CAVOK" in metar_str: state.target_vis = 9999
        state.metar.vis = str(state.target_vis) if state.target_vis < 9999 else "9999"
        
        rvr_match = re.search(r'\bR\d{2}[LRC]?/([MP]?\d{4}[UDV]?)\b', metar_str)
        state.metar.rvr = rvr_match.group(1) if rvr_match else "///"

    def process_metar_result(self, raw_metar, snap_immediately, req_icao):
        state = self.airport_states.get(req_icao)
        if not state: return
        
        if raw_metar:
            state.metar.raw = raw_metar
            self.parse_metar_regex(state, raw_metar)
            state.metar_valid = True 
            
            if state.is_initial_metar_fetch or snap_immediately:
                state.current_metar_raw = raw_metar
                state.next_snapshot_metar_raw = raw_metar
                state.is_initial_metar_fetch = False
                state.airport_base_clouds = None
                
                if raw_metar not in state.metar_history_raw:
                    state.metar_history_raw.append(raw_metar)
                
                state.base_dir = float(state.target_dir)
                state.base_spd = float(state.target_spd)
                state.base_gust = float(state.target_gust)
                state.base_vis = float(state.target_vis)
                for key, sim in state.phys_sims.items():
                    sim.reset_and_init(state.base_dir, state.base_spd, state.base_gust, state.metar.var_min, state.metar.var_max)
                
                state.tick_counter = 0
            else:
                if raw_metar != state.current_metar_raw and "UNAVAILABLE" not in raw_metar:
                    state.pending_removed_metar_raw = state.current_metar_raw
                    state.pending_new_metar_raw = raw_metar
                    state.next_snapshot_metar_raw = raw_metar
                    state.metar_changed_blink = False 
                    state.airport_base_clouds = None
                    
                    if raw_metar not in state.metar_history_raw:
                        state.metar_history_raw.append(raw_metar)
        else:
            state.metar.raw = f"{req_icao} METAR UNAVAILABLE"
            state.metar_valid = False 
            
        for p in self.panels:
            if p.current_icao.get() == req_icao:
                p.update_static_ui()

    def process_taf_notam_result(self, t_raw, n_raw, req_icao):
        state = self.airport_states.get(req_icao)
        if not state: return
        
        # TAF
        if state.is_initial_fetch:
            if t_raw is not None: 
                state.current_taf = t_raw
                state.next_snapshot_taf = t_raw
        else:
            if t_raw is not None and t_raw != state.current_taf:
                state.pending_removed_taf = state.current_taf
                state.pending_new_taf = t_raw
                state.next_snapshot_taf = t_raw
                state.taf_changed = True
                
        # NOTAM
        if n_raw is not None:
            cached_notams = self.notams_cache.get(req_icao)
            
            if state.is_initial_fetch and cached_notams is not None:
                state.current_notams = list(cached_notams)
                
            f_set = set(n_raw)
            c_set = set(state.current_notams)
            
            if state.is_initial_fetch and cached_notams is None:
                state.current_notams = list(n_raw)
                state.next_snapshot_notams = list(n_raw)
                self.notams_cache[req_icao] = list(n_raw)
                self.save_notams_cache()
            else:
                added = list(f_set - c_set)
                removed = list(c_set - f_set)
                if added or removed:
                    for n in added:
                        if n in state.pending_removed_notams: state.pending_removed_notams.remove(n)
                        elif n not in state.pending_new_notams: state.pending_new_notams.append(n)
                    for n in removed:
                        if n in state.pending_new_notams: state.pending_new_notams.remove(n)
                        elif n not in state.pending_removed_notams: state.pending_removed_notams.append(n)
                    state.next_snapshot_notams = list(n_raw)
                    state.notam_changed = True
                else:
                    if state.is_initial_fetch:
                        state.next_snapshot_notams = list(n_raw)
                        
        state.is_initial_fetch = False

    # GŁÓWNA PĘTLA SYMULACJI
    def wind_simulation_tick(self):
        for icao, state in list(self.airport_states.items()):
            try:
                self.simulate_single_airport(state)
            except Exception as e:
                pass

        # Odśwież UI tylko dla aktywnych paneli
        for p in self.panels:
            p.refresh_wind_ui()

        self.after(5000, self.wind_simulation_tick)

    # MATEMATYKA POJEDYNCZEGO LOTNISKA
    def simulate_single_airport(self, state):
        if not state.metar_valid: return
        
        b_dir = state.target_dir
        b_spd = state.target_spd
        b_gust = state.target_gust
        b_vis = state.target_vis
        
        # ZABEZPIECZENIE: CZY JEST CALM WIND?
        is_calm = (state.target_spd <= 4)
        
        lat, lon = self.get_coords(state.icao)
        is_night = False
        sun_az = 0
        sun_el = 0
        
        if lat and lon:
            try:
                now = datetime.now(timezone.utc)
                sun_el, sun_az = get_sun_position(lat, lon, now)
                is_night = sun_el < 0
            except: pass
            
        is_ovc = "OVC" in state.metar.raw or "BKN" in state.metar.raw

        tp = state.terrain_profile
        
        # OROGRAFIA DZIAŁA TYLKO GDY WIATR NIE JEST CALM I NIE JEST VRB
        if not is_calm and not getattr(state, 'is_vrb', False):
            if tp['type'] == 'VALLEY' and tp['valley_axis'] is not None:
                diff_to_axis = (b_dir - tp['valley_axis'] + 180) % 360 - 180
                if abs(diff_to_axis) < 60:
                    b_dir = (b_dir - diff_to_axis * 0.3) % 360 
                    b_spd *= 1.2 
                elif abs((b_dir - (tp['valley_axis']+180)) % 360 - 180) < 60:
                    diff_to_axis_opp = (b_dir - (tp['valley_axis']+180) + 180) % 360 - 180
                    b_dir = (b_dir - diff_to_axis_opp * 0.3) % 360
                    b_spd *= 1.2
            
            elif tp['type'] == 'SLOPE' and tp['slope_dir'] is not None:
                if is_night and b_spd < 5 and not is_ovc:
                    b_dir = tp['slope_dir']
                    b_spd = max(3.0, b_spd + (tp['slope_mag'] * 0.1))
                elif not is_night and not is_ovc:
                    diff_sun_slope = abs((sun_az - tp['slope_dir'] + 180) % 360 - 180)
                    if diff_sun_slope < 60 and sun_el > 20:
                        b_dir = (tp['slope_dir'] + 180) % 360 
                        b_spd = max(b_spd, 5.0 + (tp['slope_mag'] * 0.1))
                        
                diff_lee = abs((b_dir - (tp['slope_dir']+180)) % 360 - 180)
                if diff_lee < 45 and b_spd > 10:
                    b_spd *= 0.6 
                    b_gust = max(b_gust, b_spd + 15) 

        is_convective = ("TS" in state.metar.raw or "CB" in state.metar.raw)
        trend = None
        om_trend = None
        
        try:
            now = datetime.now(timezone.utc)
            if state.om_data:
                times = state.om_data['hourly']['time']
                current_time_str = now.strftime("%Y-%m-%dT%H:00")
                if current_time_str in times:
                    idx = times.index(current_time_str)
                    if idx + 1 < len(times):
                        om_trend = {
                            'dir': state.om_data['hourly']['wind_direction_10m'][idx+1],
                            'spd': state.om_data['hourly']['wind_speed_10m'][idx+1],
                            'gust': state.om_data['hourly']['wind_gusts_10m'][idx+1],
                            'vis': state.om_data['hourly'].get('visibility', [9999]*len(times))[idx+1]
                        }
        except Exception: pass

        if state.current_taf:
            try:
                cur_d = now.day
                cur_h = now.hour + now.minute / 60.0
                def hd_diff(d1, h1, d2, h2):
                    days = d2 - d1
                    if days < -15: days += 30
                    elif days > 15: days -= 30
                    return days * 24 + (h2 - h1)
                best_weight = 0.0
                target = {}
                for match in re.finditer(r'BECMG\s+(\d{2})(\d{2})/(\d{2})(\d{2})\s+((?:(?!BECMG|FM|TEMPO|PROB).)*)', state.current_taf, re.DOTALL):
                    d1, h1, d2, h2, wx = match.groups()
                    sd = hd_diff(cur_d, cur_h, int(d1), int(h1))
                    ed = hd_diff(cur_d, cur_h, int(d2), int(h2))
                    w = 0.0
                    if sd <= 0 and ed >= 0:
                        dur = hd_diff(int(d1), int(h1), int(d2), int(h2))
                        w = abs(sd) / dur if dur > 0 else 1.0
                        w = min(0.65, w) 
                    elif 0 < sd <= 1.5:
                        w = 0.1 + (1.5 - sd) * 0.3
                        w = min(0.65, w)
                    if w > best_weight:
                        best_weight = w
                        target['wx'] = wx
                for match in re.finditer(r'FM\s*(\d{2})(\d{2})(\d{2})\s+((?:(?!BECMG|FM|TEMPO|PROB).)*)', state.current_taf, re.DOTALL):
                    d1, h1, m1, wx = match.groups()
                    h1_val = int(h1) + int(m1)/60.0
                    diff = hd_diff(cur_d, cur_h, int(d1), h1_val)
                    w = 0.0
                    if 0 < diff <= 1.5:
                        w = 0.65 - (diff / 1.5) * 0.65
                    elif -2.0 < diff <= 0:
                        w = 0.65 
                    if w > best_weight:
                        best_weight = w
                        target['wx'] = wx
                if best_weight > 0 and 'wx' in target:
                    wx = target['wx']
                    res = {'weight': best_weight}
                    w_match = re.search(r'\b(\d{3})(\d{2,3})(?:G(\d{2,3}))?KT\b', wx)
                    if w_match:
                        res['dir'] = 0 if w_match.group(1) == 'VRB' else int(w_match.group(1))
                        res['spd'] = int(w_match.group(2))
                        res['gust'] = int(w_match.group(3)) if w_match.group(3) else 0
                    v_match = re.search(r'\s(\d{4})\s', wx + " ")
                    if v_match and int(v_match.group(1)) <= 9999:
                        res['vis'] = int(v_match.group(1))
                    elif "CAVOK" in wx:
                        res['vis'] = 9999
                    trend = res
            except Exception: pass

        if trend and 'wx' in trend and ("TS" in trend['wx'] or "CB" in trend['wx']):
            is_convective = True

        if om_trend and om_trend.get('dir') is not None and om_trend.get('spd') is not None:
            if is_convective and abs((om_trend['dir'] - b_dir + 180) % 360 - 180) > 40:
                b_spd += 5.0
                if random.random() < 0.1:
                    b_dir = om_trend['dir']

            if not is_calm and not getattr(state, 'is_vrb', False):
                diff_om = (om_trend['dir'] - b_dir + 180) % 360 - 180
                b_dir = (b_dir + diff_om * 0.03) % 360  
                b_spd = b_spd * 0.95 + om_trend['spd'] * 0.05
                
                if om_trend.get('gust') is not None:
                    b_gust = b_gust * 0.95 + om_trend['gust'] * 0.05
                    
            if om_trend.get('vis') is not None:
                b_vis = b_vis * 0.95 + min(9999, om_trend['vis']) * 0.05
        
        if trend and trend.get('weight', 0) > 0:
            w = trend['weight']
            if 'dir' in trend and not is_calm and not getattr(state, 'is_vrb', False):
                diff = (trend['dir'] - b_dir + 180) % 360 - 180
                b_dir = (b_dir + diff * w) % 360
                b_spd = b_spd * (1 - w) + trend['spd'] * w
                b_gust = b_gust * (1 - w) + trend['gust'] * w
            if 'vis' in trend:
                b_vis = b_vis * (1 - w) + trend['vis'] * w

        diff_dir = (b_dir - state.base_dir + 180) % 360 - 180
        if abs(diff_dir) > 1.0: 
            state.base_dir = (state.base_dir + math.copysign(1.0, abs(diff_dir))) % 360
        else: 
            state.base_dir = b_dir
            
        if state.base_spd < b_spd: state.base_spd += 0.2
        elif state.base_spd > b_spd: state.base_spd -= 0.2
        
        if state.base_gust < b_gust: state.base_gust += 0.2
        elif state.base_gust > b_gust: state.base_gust -= 0.2
        
        if state.base_vis < b_vis: state.base_vis += 20
        elif state.base_vis > b_vis: state.base_vis -= 20

        has_ts_cb = ("TS" in state.metar.raw or "CB" in state.metar.raw)
        if has_ts_cb and state.mb_timer == 0 and random.random() < 0.03: 
            state.mb_timer = random.randint(12, 24) 
            
        if state.mb_timer > 0:
            state.mb_timer -= 1
            state.mb_qnh_spike = 2
            for p in self.panels:
                if p.current_icao.get() == state.icao: p.update_static_ui()
        else:
            if state.mb_qnh_spike > 0:
                state.mb_qnh_spike = 0
                for p in self.panels:
                    if p.current_icao.get() == state.icao: p.update_static_ui()

        wave_val = 0.0
        if state.base_gust > 0:
            if random.random() < 0.2: 
                wave_val = random.uniform(0, state.base_gust + 3)
            else:
                wave_val = state.gust_wave[-1] * 0.8 
        else:
            wave_val = random.uniform(-1, 1)
            
        state.gust_wave.append(wave_val)
        state.gust_wave.pop(0)

        upper_wind = b_spd
        if om_trend and om_trend.get('spd') is not None:
            upper_wind = om_trend['spd']
            
        for sim in state.phys_sims.values():
            sim.ws_alert = has_ts_cb or (abs(sim.pub_avg_spd - upper_wind) >= 15.0) or (state.mb_timer > 0)
            sim.is_vrb = getattr(state, 'is_vrb', False)

        same_rwy = False
        for p in self.panels:
            if p.current_icao.get() == state.icao:
                if p.active_rwy_dep.get() != "":
                    same_rwy = (p.active_rwy_dep.get() == p.active_rwy_arr.get())
        
        if state.icao == "EPWA":
            state.phys_sims['epwa_dep'].tick(state.base_dir, state.base_spd, state.base_gust, state.metar.var_min, state.metar.var_max, is_night, is_ovc, state.gust_wave[-1])
            if same_rwy:
                s_dep = state.phys_sims['epwa_dep']
                s_arr = state.phys_sims['epwa_arr']
                s_arr.drift_dir = s_dep.drift_dir
                s_arr.drift_spd = s_dep.drift_spd
                s_arr.target_drift_dir = s_dep.target_drift_dir
                s_arr.target_drift_spd = s_dep.target_drift_spd
                s_arr.history = list(s_dep.history)
                s_arr.cur_dir = s_dep.cur_dir
                s_arr.cur_spd = s_dep.cur_spd
            else:
                state.phys_sims['epwa_arr'].tick(state.base_dir, state.base_spd, state.base_gust, state.metar.var_min, state.metar.var_max, is_night, is_ovc, state.gust_wave[-6])
            
            if state.mb_timer > 0:
                state.phys_sims['epwa_dep'].cur_spd += 25
                state.phys_sims['epwa_arr'].cur_dir = (state.phys_sims['epwa_arr'].cur_dir + 180) % 360
                state.phys_sims['epwa_arr'].cur_spd += 15
        else:
            state.phys_sims['std_low'].tick(state.base_dir, state.base_spd, state.base_gust, state.metar.var_min, state.metar.var_max, is_night, is_ovc, state.gust_wave[-1])
            state.phys_sims['std_mid'].tick(state.base_dir, state.base_spd, state.base_gust, state.metar.var_min, state.metar.var_max, is_night, is_ovc, state.gust_wave[-5])
            state.phys_sims['std_high'].tick(state.base_dir, state.base_spd, state.base_gust, state.metar.var_min, state.metar.var_max, is_night, is_ovc, state.gust_wave[-10])
            
            if state.mb_timer > 0:
                state.phys_sims['std_low'].cur_spd += 25
                state.phys_sims['std_high'].cur_dir = (state.phys_sims['std_high'].cur_dir + 180) % 360
                state.phys_sims['std_high'].cur_spd += 15

        state.tick_counter += 1
        
        # AKTUALIZACJA ŚRODOWISKA (WODA, CHMURY, WIDZIALNOŚĆ) W TLE
        wx_str = state.metar.raw
        is_cavok_or_few = False
        
        if "CAVOK" in wx_str: 
            is_cavok_or_few = True
        elif state.metar.clouds:
            if all(c[0] == "FEW" for c in state.metar.clouds): 
                is_cavok_or_few = True
                
        target_layers = 2 if is_cavok_or_few else 3

        if state.airport_base_clouds is None:
            layers = []
            for c in state.metar.clouds:
                try: 
                    layers.append(int(c[1])*100)
                except ValueError: 
                    pass
                    
            if not layers:
                if is_cavok_or_few:
                    layers = [random.randint(5500, 7500), random.randint(9500, 15000)]
                else:
                    layers = [random.randint(800, 1500), random.randint(2000, 3000), random.randint(4000, 8000)]
                    
            while len(layers) < target_layers:
                last = layers[-1] if layers else 1000
                layers.append(last + random.randint(1500, 4000))
                
            state.airport_base_clouds = layers[:target_layers]
        else:
            new_base = []
            for alt in state.airport_base_clouds:
                new_base.append(max(100, alt + random.choice([-20, 0, 20])))
            state.airport_base_clouds = new_base

        if not state.ceilometer_readings or len(state.ceilometer_readings) != len(state.airport_base_clouds):
            state.ceilometer_readings = list(state.airport_base_clouds)

        state.ceilometer_timer += 1
        if state.ceilometer_timer >= 6:
            state.ceilometer_timer = 0
            for i in range(len(state.airport_base_clouds)):
                jitter = random.randint(-20, 20) * 10
                state.ceilometer_readings[i] = max(100, state.airport_base_clouds[i] + jitter)

        try:
            base_temp = float(state.metar.temp.replace('M', '-')) if 'M' in state.metar.temp or state.metar.temp.replace('-','').isdigit() else 15.0
            d_val = float(state.metar.dew.replace('M', '-')) if 'M' in state.metar.dew or state.metar.dew.replace('-','').isdigit() else 10.0
            
            if trend and 'wx' in trend and ('RA' in trend['wx'] or 'SH' in trend['wx']):
                if 'RA' not in wx_str and 'SH' not in wx_str and 'DZ' not in wx_str:
                    spread = base_temp - d_val
                    if spread > 2.0:
                        base_temp -= min(4.0, spread * 0.6)
                        
            spread = base_temp - d_val
            if spread <= 1.5 and state.base_vis > 200:
                state.base_vis = max(200.0, state.base_vis - 100.0)
        except Exception: 
            base_temp = 15.0

        is_shower = bool(re.search(r'\b([+-]?SH[A-Z]*|TS[A-Z]*)\b', wx_str))
        if is_shower:
            state.shower_timer += 1
            if state.shower_timer > 20:
                state.shower_phase = (state.shower_phase + 1) % 3
                state.shower_timer = 0
        else:
            state.shower_phase = 0
            state.shower_timer = 0
        
        has_rain = bool(re.search(r'\b[+-]?(?:SH|TS)?(?:RA|DZ)\b', wx_str))
        has_snow = bool(re.search(r'\b[+-]?(?:SH|TS)?(?:SN|SG)\b', wx_str))
        has_ice = bool(re.search(r'\b[+-]?(?:FZ[A-Z]*|PL|GS|GR)\b', wx_str))

        if has_rain:
            state.rwy_water_level = min(1.0, state.rwy_water_level + 0.1)
            state.rwy_snow_level = max(0.0, state.rwy_snow_level - 0.1) 
        elif has_snow:
            state.rwy_snow_level = min(1.0, state.rwy_snow_level + 0.1)
        elif has_ice:
            state.rwy_water_level = min(1.0, state.rwy_water_level + 0.1)
            
        drying_factor = 0.001 + (state.base_spd * 0.0001) 
        
        if not has_rain and not has_ice:
            state.rwy_water_level = max(0.0, state.rwy_water_level - drying_factor)
            
        if not has_snow and base_temp > 0 and state.rwy_snow_level > 0:
            melt_rate = drying_factor * base_temp * 0.1
            melted_snow = min(state.rwy_snow_level, melt_rate)
            state.rwy_snow_level -= melted_snow
            state.rwy_water_level = min(1.0, state.rwy_water_level + melted_snow)

        grf_status = "6/6/6 DRY"
        grf_color = TEXT_GREEN

        if has_ice or (state.rwy_water_level > 0.05 and base_temp <= 0.0):
            grf_status = "2/2/2 POOR (ICE)"
            grf_color = TEXT_RED
        elif state.rwy_snow_level > 0.1:
            grf_status = "3/3/3 SNOW"
            grf_color = TEXT_WHITE
        elif state.rwy_water_level > 0.05:
            grf_status = "5/5/5 WET"
            grf_color = TEXT_CYAN

        if state.mb_timer > 0:
            base_temp -= 5.0

        master_vis = state.base_vis
        if state.shower_phase == 1:
            master_vis = min(master_vis, 1200)
            state.rwy_water_level = min(1.0, state.rwy_water_level + 0.3)
        elif state.shower_phase == 2:
            master_vis = min(master_vis, 4000)

        if state.rwy_snow_level > 0.05 and state.base_spd > 15.0:
            blsn_penalty = (state.base_spd - 15.0) * 80 
            master_vis = max(400.0, master_vis - blsn_penalty)

        if state.metar.rvr != "///":
            try:
                master_rvr_target = int(re.search(r'\d{4}', state.metar.rvr).group())
                if master_vis < float(state.target_vis) - 500: 
                    master_rvr = master_vis * 0.85
                else:
                    master_rvr = master_rvr_target
            except Exception: 
                master_rvr = master_vis * 0.85
        else:
            master_rvr = master_vis * 0.85

        if is_night and master_rvr < 2000:
            master_rvr = min(2000.0, master_rvr * 1.5)

        state.fog_phase += 0.1
        tdz_vis_offset = math.sin(state.fog_phase) * 300 if master_vis < 3000 else 0
        mid_vis_offset = math.sin(state.fog_phase - 1.5) * 300 if master_vis < 3000 else 0
        end_vis_offset = math.sin(state.fog_phase - 3.0) * 300 if master_vis < 3000 else 0

        offsets = [tdz_vis_offset, mid_vis_offset, end_vis_offset]
        keys_to_update = ['epwa_dep', 'epwa_arr'] if state.icao == "EPWA" else ['std_low', 'std_mid', 'std_high']

        for i, phys_key in enumerate(keys_to_update):
            env = state.phys_envs[phys_key]
            sim = state.phys_sims[phys_key]
            current_offset = offsets[i % 3]
            
            if state.icao == "EPWA" and phys_key == 'epwa_arr' and same_rwy:
                env.update(state.phys_envs['epwa_dep'])
                continue

            if master_vis >= 9999:
                env['vis'] = 9999
                env['rvr'] = 2000 + random.randint(0, 40)
            else:
                env['vis'] = max(100, min(9999, master_vis + current_offset + random.randint(-50, 50)))
                env['rvr'] = max(50, min(2000, master_rvr + current_offset + random.randint(-30, 30)))

            mode_clouds = []
            for alt in state.ceilometer_readings:
                offset = random.randint(-4, 4) * 10 
                mode_clouds.append(max(100, alt + offset))
            env['clouds'] = mode_clouds

            target_temp = base_temp - (0.022 * sim.cur_spd)
            env['temp'] = env.get('temp', base_temp) + 0.015 * (target_temp - env.get('temp', base_temp))
            env['grf'] = grf_status
            env['grf_color'] = grf_color
            
        for p in self.panels:
            if p.current_icao.get() == state.icao:
                p.refresh_env_ui()

    def blink_loop(self):
        self.blink_state = not self.blink_state
        for p in self.panels:
            st = self.airport_states.get(p.current_icao.get())
            if st:
                p.btn_taf.config(bg=TEXT_RED if st.taf_changed and self.blink_state else BTN_DEF_BG)
                p.btn_notam.config(bg=TEXT_RED if st.notam_changed and self.blink_state else BTN_DEF_BG)
                p.btn_metar.config(bg=BTN_DEF_BG)
                for m, col in p.atis_cols:
                    key = f"{st.icao}_{m}"
                    t = st.atis_change_time.get(key, 0)
                    if t > 0 and (time.time() - t) <= 120:
                        col["info_lbl"].config(bg="#DAA520" if self.blink_state else BOX_BG, fg=TEXT_WHITE)
                    else:
                        col["info_lbl"].config(bg=BOX_BG, fg=TEXT_WHITE)
                        
                for _, cd, sim in p.active_cols:
                    if getattr(sim, 'ws_alert', False): p.update_wind_ui(cd, sim)

        self.after(500, self.blink_loop)

    def update_clock(self):
        t = datetime.now(timezone.utc).strftime("%H:%M:%S UTC")
        for p in self.panels:
            p.lbl_time.config(text=t)
        self.after(1000, self.update_clock)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "MAP_MODE":
        try: launch_windy_webview(int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5]), sys.argv[6] == "True", sys.argv[7], sys.argv[8])
        except Exception: pass
        sys.exit(0)
    app = VirtualAWOS()
    app.mainloop()