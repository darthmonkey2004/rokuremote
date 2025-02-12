#!/usr/bin/env python3


import socket
from http.client import HTTPResponse
from io import BytesIO
import PySimpleGUI as sg
import subprocess
import shutil
import xmltojson
import pickle
import json
import xmldict
import os
import requests
from difflib import SequenceMatcher
from urllib.parse import quote
import time
from threading import Thread
from queue import Queue
#from discovery2 import RokuDiscoverer

def getKeys():
	keys = {}
	keys['a'] = 38
	keys['b'] = 56
	keys['c'] = 54
	keys['d'] = 40
	keys['e'] = 26
	keys['f'] = 41
	keys['g'] = 42
	keys['h'] = 43
	keys['i'] = 31
	keys['j'] = 44
	keys['k'] = 45
	keys['l'] = 46
	keys['m'] = 58
	keys['n'] = 57
	keys['o'] = 32
	keys['p'] = 33
	keys['q'] = 24
	keys['r'] = 27
	keys['s'] = 39
	keys['t'] = 28
	keys['u'] = 30
	keys['v'] = 55
	keys['w'] = 25
	keys['x'] = 53
	keys['y'] = 29
	keys['z'] = 52
	keys['1'] = 10
	keys['2'] = 11
	keys['3'] = 12
	keys['4'] = 13
	keys['5'] = 14
	keys['6'] = 15
	keys['7'] = 16
	keys['8'] = 17
	keys['9'] = 18
	keys['0'] = 19
	keys['at'] = 11
	keys['numbersign'] = 12
	keys['exclam'] = 10
	keys['dollar'] = 13
	keys['percent'] = 14
	keys['asciicircum'] = 15
	keys['ampersand'] = 16
	keys['asterisk'] = 17
	keys['parenleft'] = 18
	keys['parenright'] = 19
	keys['underscore'] = 20
	keys['minus'] = 20
	keys['plus'] = 21
	keys['equal'] = 21
	keys['BackSpace'] = 22
	keys['Delete'] = 119
	out = {}
	for k in keys:
		out[k.lower()] = keys[k]
		out[k.title()] = keys[k]
	return out

class _FakeSocket(BytesIO):
    def makefile(self, *args, **kw):
        return self

class SSDPResponse(object):
    def __init__(self, response):
        self.location = response.getheader("location")
        self.usn = response.getheader("usn")
        self.st = response.getheader("st")
        self.cache = response.getheader("cache-control").split("=")[1]

    def __repr__(self):
        return f"<SSDPResponse({self.location}, {self.st}, {self.usn})"

class Discover():
	def __init__(self, timeout=2, retries=1, run=False):
		self.TIMEOUT = timeout
		self.RETRIES = retries
		self.DEVICES = []
		if run:
			self.discover()
	def discover(self):
		print(time.ctime(), "Scanning via ssdp for devices...")
		message = "\r\n".join(
			[
				"M-SEARCH * HTTP/1.1",
				'HOST: "239.255.255.250":1900',
				'MAN: "ssdp:discover"',
				"ST: roku:ecp",
				"MX: 2",
				"",
				"",
			]
		)
		socket.setdefaulttimeout(self.TIMEOUT)
		responses = {}
		for _ in range(self.RETRIES):
			sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
			sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
			sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
			m = message.format(st="roku:ecp")
			sock.sendto(m.encode(), ("239.255.255.250", 1900))
			l = []
			while 1:
				try:
					rhttp = HTTPResponse(_FakeSocket(sock.recv(1024)))
					rhttp.begin()
					if rhttp.status == 200:
						rssdp = SSDPResponse(rhttp)
						responses[rssdp.location] = rssdp
						if rssdp.location not in l:
							l.append(rssdp.location.split('http://')[1].split(':')[0])
				except socket.timeout:
					break
		print(time.ctime(), "Scan complete!")
		print(time.ctime(), f"{len(l)} devices found!")
		pos = 0
		for i in l:
			pos += 1
			print(time.ctime(), f"{pos}: {i}")
		self.DEVICES = l
		return l

class UI():
	"""Skeleton class for creating a ui for various whatevers."""
	def __init__(self):
		self.LAYOUT = []
		self.ROW = []
		self.FRAMES = []
		self.WINDOW = None
	def _add_elementToRow(self, e):
		#if type(e) != list:
		#	self.ROW.append([e])
		#else:
		self.ROW.append(e)
	def _add_rowToLayout(self, row=None):
		if row is None:
			#if class attribute used, blank after.
			row = self.ROW
			self.ROW = []
		self.LAYOUT.append(row)
	def addToFrame(self, title='Test frame', layout=None, width=None, height=None, tooltip='test tooltip', expand_x=False, expand_y=False):
		if layout is None:
			if len(self.ROW) > 0:
				self._add_rowToLayout()
			#since we're using an attribute, clear it and 
			#it's contributing ROWS attr.
			layout = self.LAYOUT
			self.LAYOUT = []
		key = f"-{title}-"
		frame = sg.Frame(title=title, layout=layout, title_location='n', size=(width, height), font=None, pad=1, border_width=1, key=key, tooltip=tooltip, expand_x=expand_x, expand_y=expand_y, element_justification="center", vertical_alignment='center') #t (top), c (center), r(bottom)
		self.FRAMES.append(frame)
		return frame
		print(time.ctime(), "Frame added!")
	def getWindow(self, title='Test Window', layout=None, grab_keyboard=True, width=900, height=600, expand_x=False, expand_y=False):
		self.GRAB_KEYBOARD = grab_keyboard
		#sets default for returning filtered keyboard events in the main remote menu
		key=f"-{title}-"
		if layout is None or len(layout) == 0:
			self.addToFrame(title=title, layout=layout, width=width, height=height, expand_x=expand_x, expand_y=expand_y)
			self.LAYOUT.append(self.FRAMES)
			self.FRAMES = []
			#since we're using an attribute, clear it and 
			#it's contributing ROWS attr.
			layout = self.LAYOUT
			self.LAYOUT = []
		elif len(layout) >= 1:
			if type(layout[0]) != list:
				layout = [layout]
		self.WINDOW = sg.Window(title=title, layout=layout, size=(width, height), return_keyboard_events=True, use_default_focus=False).finalize()
		return self.WINDOW
	def save(self, filepath=None, win=None):
		if win is None:
			win = self.WINDOW
		if filepath is None:
			filepath = os.path.join(os.path.expanduser("~"), f".{win.title}.dat")
		win.save_to_disk(filepath)

class Roku():
	def __init__(self, host=None, port=8060, scan=False, scan_type='ssdp', exec_setup=False, play_at_start=True, wait=1):
		self.ENSURE_PLAY_AT_START = play_at_start
		self.PLAYBACK_MONITOR_QUEUE = Queue()
		self.ACTIVE_APP = None
		self.SCAN_TYPE = 'ssdp'
		self.HOST = host
		self.PORT = port
		self.DEVICES = []
		#scan types are http and ssdp. http takes longer, but if full will
		#find all roku devices. ssdp is faster, but not always accurate if
		#some devices are not currently reporting.
		self.DISCOVER = Discover().discover
		#self.DISCOVER = RokuDiscoverer().discover
		self.DATA_DIR = os.path.join(os.path.expanduser("~"), '.rokuremote')
		self.ROKU_ICON= os.path.join(self.DATA_DIR, 'icon.png')
		self.ICONS_PATH = os.path.join(os.path.expanduser("~"), 'icons', 'media_playback')
		if not os.path.exists(self.DATA_DIR):
			exec_setup = True
		if exec_setup:
			#if data directory doesn't exist, create it.
			os.makedirs(self.DATA_DIR, exist_ok=True)
			self.setup()
		self.ICON_FILE = os.path.join(self.DATA_DIR, 'icon.png')
		if not os.path.exists(self.ICON_FILE):
			self._get_logo()
		self.SETTINGS_FILE = os.path.join(self.DATA_DIR, ".roku_hosts")
		self.SETTINGS = {}
		try:
			self.SETTINGS = self._load_settings()
			p = self.PORT
			try:
				self.PORT = self.SETTINGS['port']
			except:
				#if port set fails, set setting to temp var and then set class attribute.
				print(time.ctime(), "Couldn't set port from settings! ")
				self.SETTINGS['port'] = p
				self.PORT = self.SETTINGS['port']
		except Exception as e:
			print(time.ctime(), "Failed to load settings:", e)
		if self.HOST is not None:
			if self.HOST not in self.DEVICES:
				self.DEVICES.append(self.HOST)
			print(time.ctime(), "Host set:", self.HOST)
		elif self.HOST is None:
			print(time.ctime(), "Host is None!")
			try:
				self.HOST = self.SETTINGS['host']
				if self.HOST is None:
					print(time.ctime(), "Couldn't retreive host from settings! Re-initializing...")
					self.SETTINGS = self._init_settings(r=True)
					self._save_settings(self.SETTINGS)
					if self.HOST is None:
						scan = True
						print(time.ctime(), f"Failed get or replace host! Rescanning...")
					else:
						print(time.ctime(), "Host reset to", self.HOST)
						scan = False
				else:
					print(time.ctime(), "Host set fom settings:", self.HOST)
					scan = False
			except Exception as e:
				print(time.ctime(), f"Host not in settings. Re-initializing...")
				self.SETTINGS = self._init_settings()
				self.HOST = sorted(self.DISCOVER())[0]
				print(time.ctime(), "Host set:", self.HOST)
		if scan:
			try:
				self.DEVICES = self.DISCOVER()
			except:
				print(time.ctime(), "SSDP discover failed! Trying slow scan..")
				self.DEVICES = self._scan_network()
			print(time.ctime(), "devices:", self.DEVICES)
			if len(self.DEVICES) > 0:
				self.HOST = self.DEVICES[0]
				if 'http://' in self.HOST:
					self.HOST = self.HOST.split('http://')[1].split(':')
			else:
				print(time.ctime(), "No devices found via ssdp. Scanning with http..")
				self.HOST = self._scan_network()
				self.SCAN_TYPE = 'http'
				self.DEVICES = [self.HOST]
		#print(time.ctime(), "Host, Port:", self.HOST, self.PORT)
		self.BASE_URL = f"http://{self.HOST}:{self.PORT}"
		try:
			self.DEVICE_INFO = self._query_device()
		except Exception as e:
			print(time.ctime(), f"Couldn't get device info!")
			self.DEVICE_INFO = {}
		if self.DEVICE_INFO != {}:
			self.PLAYER = self._query_media_player()
			self.APPS = self.UpdateApps()
		self._save_settings()
		#initialize playback state
		self.STATE = self.getPlayerState()
		self.LAST_STATE = None
		#sets flag to ensure than when playback starts,
		#it does so at the beginning rather than the
		#last recorded chapter in history on device.
		self.LAST_PLAYBACK_PERCENTAGE = 0
		self.PLAYBACK_PERCENTAGE = self.getPlaybackPercentage()
		self.STATES = ['play', 'pause', 'close', 'startup', 'buffer']
		#init wait attribute. this is how long pauses take before proceeding.
		self.WAIT = wait


	def getlocalip(self):
		return subprocess.check_output("ifconfig | grep '192.168' | xargs | cut -d ' ' -f 2", shell=True).decode().strip()

	def compareStrings(self, str1, str2):
		matcher = SequenceMatcher(None, str1, str2)
		return matcher.ratio() * 100

	def _get_logo(self):
		url = "https://logos-world.net/wp-content/uploads/2021/02/Roku-Symbol.png"
		try:
			r = requests.get(url, stream=True)
			if r.status_code == 200:
				with open(os.path.join(self.DATA_DIR, 'icon.png'), 'wb') as f:
					r.raw.decode_content = True
					shutil.copyfileobj(r.raw, f)
					f.close()
				return True
			else:
				print(time.ctime(), f"Error downloading icon: Bad status code ({r.status_code}) - {r.text})")
				return False
		except Exception as e:
			print(time.ctime(), f"Error downloading icon: {e}")
			return False

	def search(self, query='Rick and Morty', media_type='series', country='us', match_percentage=72):
		url = "https://streaming-availability.p.rapidapi.com/shows/search/title"
		if media_type == 'series':
			querystring = {"country":country,"title":query,"show_type":'series',"series_granularity":"show","output_language":"en"}
		elif media_type == 'movie':
			querystring = {"country":country,"title":query,"show_type":'movie',"output_language":"en"}
		else:
			querystring = {"country":country,"title":query,"output_language":"en"}
		headers = {
			"x-rapidapi-key": "TiV3k10QNXmshRyyCcCXPKyq1gYJp1oKBNKjsn3ICR7bpX3yAB",
			"x-rapidapi-host": "streaming-availability.p.rapidapi.com"
		}
		response = requests.get(url, headers=headers, params=querystring)
		ret = response.json()
		out = {}
		for i in ret:
			title = i['title']
			item_type = i['itemType']
			t = i['showType']
			try:
				_ = out[t]
			except:
				out[t] = {}
			if t == 'series':
				p = self.compareStrings(title, query)
				print(time.ctime(), "%:", p)
				if p <= match_percentage:
					pass
				else:
					try:
						_ = out[t][title]
					except:
						out[t][title] = {}
					out[t][title]['series_id'] = i['id']
					out[t][title]['imdbid'] = i['imdbId']
					out[t][title]['tmdbid'] = i['tmdbId']
					out[t][title]['description'] = i['overview']
					try:
						out[t][title]['first_air_year'] = i['firstAirYear']
						out[t][title]['last_air_year'] = i['lastAirYear']
					except Exception as e:
						print(time.ctime(), "No air year found!", e)
						out[t][title]['first_air_year'] = None
						out[t][title][ 'last_air_year'] = None
					out[t][title]['seasons'] = i['seasonCount']
					out[t][title]['episodes'] = i['episodeCount']
					out[t][title]['streaming_options'] = i['streamingOptions']
			elif t == 'movie':
				p = compareStrings(title, query)
				print(time.ctime(), "%:", p)
				if p <= match_percentage:
					pass
				else:
					title = i['title']
					out[t][title] = {}
					out[t][title]['id'] = i['id']
					out[t][title]['imdbid'] = i['imdbId']
					out[t][title]['tmdbid'] = i['tmdbId']
					out[t][title]['description'] = i['overview']
					out[t][title]['release_date'] = i['releaseYear']
					out[t][title]['streaming_options'] = i['streamingOptions'][country]
		return out
	def _ckTemp(self):
		if not os.path.exists(self.SETTINGS_FILE):
			with open(self.SETTINGS_FILE, 'w') as f:
				f.write('')
				f.close()
				print(time.ctime(), "Settings file created!")
	def _send_local_ip(self):
		s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		s.connect(("8.8.8.8", 80))
		localip = s.getsockname()[0]
		s.close()
		return localip
	def _send_subnet(self, localip=None):
		if localip is None:
			localip = self._send_local_ip()
		return '.'.join(localip.split('.')[:3])
	def _scan_network(self, full=False):
		if full:
			print(time.ctime(), "Scanning network via HTTP for devices...")
		else:
			print(time.ctime(), "Scanning network via http for first available device...")
		self.DEVICES = []
		sn = self._send_subnet()
		for i in range(0, 30):
			ip = f"{sn}.{i}"
			url = f"http://{ip}:8060/"
			try:
				print(time.ctime(), "testing ip:", ip)
				r = requests.get(url)
				if '<serviceType>urn:roku-com:service:ecp:1</serviceType>' in r.text:
					print(time.ctime(), "device found!", ip)
					self.DEVICES.append(ip)
					self.SETTINGS['devices'] = self.DEVICES
					if full:
						pass
					else:
						self._save_settings(self.SETTINGS)
						return ip
			except:
				pass
		self._save_settings(self.SETTINGS)
		return self.DEVICES
	def _send(self, url, data=None, rtype='GET'):
		#handles get and post requests from remote to Roku device.
		if data is not None:#if data included, set type to post
			rtype = 'POST'
		if rtype == 'GET':
			r = requests.get(url)
		else:
			print(time.ctime(), "Action:", rtype)
			if data is not None:
				print(time.ctime(), "with data...")
				r = requests.post(url, data=data)
			else:
				print(time.ctime(), "No data for post!")
				r = requests.post(url)
		if r.status_code != 200:
			print(time.ctime(), f"Error in requests: Bad status code ({r.status_code}, {r.text}")
			return False
		else:
			try:
				return r.json()
			except Exception as e:
				#print(time.ctime(), "Couldn't get json. Returning text object...")
				return r.text
	def _parse_xml(self, xml_string):
		if type(xml_string) == str:
			#this is a bug workaround for xmldict.
			#may not need this, could be some confusion here.
			if '<?xml version=' in xml_string:
				xml_string = "\n".join(xml_string.splitlines()[1:])
			#if arg is string, convert to dict.
			try:
				return xmldict.xml_to_dict(xml_string)
			except Exception as e:
				print(time.ctime(), "Couldn't parse xml:", e)
				return xml_string
		elif type(xml_string) == dict:#if arg is already dict object, return.
			return xml_string
		else:
			print(time.ctime(), "xml type:", type(xml_string))
			input("Press enter to continue...")
	def _query_device(self):
		#get and parse device information
		return xmldict.xml_to_dict(self._send(f"{self.BASE_URL}/query/device-info"))['device-info']
	def _query_media_player(self):
		string = self._send(f"{self.BASE_URL}/query/media-player")
		try:
			return xmltojson.xmltodict.parse(string)['player']
		except Exception as e:
			print(time.ctime(), f"Error getting media player info from roku: {e}")
			return {}
	def _keyPress(self, key):
		#turn off play at start whilst we are sending skip event 'n such.
		self.ENSURE_PLAY_AT_START = False
		#send a key to the roku device.
		url = None
		chars = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '1', '2', '3', '4', '5', '6', '7', '8', '9', '0', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z']
		key_names = ['Home', 'Rev', 'Fwd', 'Play', 'Select', 'Left', 'Right', 'Down', 'Up', 'Back', 'InstantReplay', 'Info', 'Backspace', 'Search', 'Enter']
		k = quote(key.lower())
		print(time.ctime(), "key:", k)
		if key in chars:
			url = f"{self.BASE_URL}/keypress/Lit_{quote(k)}"
		elif key in key_names:
			url = f"{self.BASE_URL}/keypress/{k}"
		print(time.ctime(), "url:", url)
		print("TODO(???) - Roku._keyPress: set ack and conf flags.")
		print("Set ack flag on exit here (ENSURE_PLAY_AT_START)")
		print("Set confirmation flag on state change (event monitor)")
		if url is not None:
			ret = self._send(url, rtype='POST')
			if not ret:
				return False
			else:
				return f"{time.ctime()} Keypress function exiting..."
		else:
			print(time.ctime(), "Whoops!")
			return None
	def _get_apps(self):
		#get and parse xml data for all apps
		#currently installed on the Roku device.
		url = f"{self.BASE_URL}/query/apps"
		try:
			apps = self._send(url).splitlines()
			apps.pop(0)
			apps.pop(0)
			ct = len(apps) - 1
			apps.pop(ct)
			l = []
			for line in apps:
				d = {}
				d['appid'] = line.split('id="')[1].split('"')[0]
				d['type'] = line.split('type="')[1].split('"')[0]
				d['version'] = line.split('version="')[1].split('"')[0]
				d['name'] = line.split('">')[1].split('</app')[0]
				l.append(d)
			self.APPS = l
			return l
		except Exception as e:
			print(time.ctime(), f"Error in _get_apps(): {e}")
			return {}
	def UpdateApps(self):
		apps = self._get_apps()
		self.APPS_BY_ID = {}
		self.APPS_BY_NAME = {}
		for app in apps:
			#app['icon_data'] = self._get_app_icon(app['appid'])
			self.APPS_BY_ID[app['appid']] = app
			self.APPS_BY_NAME[app['name']] = app
		print(time.ctime(), "Applications dictionaries updated!")
	def _get_app_icon(self, appid):
		#TODO - this writes binary data to create icon file.
		#figure out how to do that to save output, then return a file path.
		url = f"{self.BASE_URL}/query/icon/{appid}"
		print(time.ctime(), "url:", url)
		print(time.ctime(), self._send(url))
	def _get_active_app(self):
		#get the current app now running on the roku device.
		url = f"{self.BASE_URL}/query/active-app"
		lines = self._send(url)
		d = {}
		d['appid'] = lines.split('id="')[1].split('"')[0]
		d['type'] = lines.split('type="')[1].split('"')[0]
		d['version'] = lines.split('version="')[1].split('"')[0]
		d['name'] = lines.split('">')[1].split('</app')[0]
		self.ACTIVE_APP = d
		return d
	def _get_registry(self, appid=None):
		if appid is None:
			if self.ACTIVE_APP is None:
				self.ACTIVE_APP= self._get_active_app()
			appid = self.ACTIVE_APP['appid']
		url = f"{self.BASE_URL}/query/registry/{appid}"
		return self._send(url)
	def _save_settings(self, settings=None):
		if settings is None:
			settings = self.SETTINGS
		else:
			settings = {}
			settings['host'] = self.HOST
			settings['port'] = self.PORT
			settings['url'] = self.BASE_URL
			settings['data_directory'] = self.DATA_DIR
			settings['devices'] = self.DEVICES
			settings['scan_type'] = self.SCAN_TYPE
		#dumps settings dictionary to file.
		try:
			with open(self.SETTINGS_FILE, 'wb') as f:
				pickle.dump(settings, f)
				f.close()
				return True
		except Exception as e:
			print(time.ctime(), f"Error saving settings file: {e}")
			return False
	def _load_settings(self, apply_settings=True):
		#load settings from pickled data file.
		#NOTE - use _init_settings to initialize!
		#this helper function doesn't handle errors.
		try:
			with open(self.SETTINGS_FILE, 'rb') as f:
				settings = pickle.load(f)
				f.close()
		except Exception as e:
			print(time.ctime(), f"Error loading settings file: {e}")
			settings = self._init_settings()
			self._save_settings(settings)
			apply_settings = True
			return False
		if apply_settings:
			self._apply_settings(settings)
		return settings
	def _apply_settings(self, settings=None):
		if settings is not None:
			self.SETTINGS = settings
		#updates class attributes from provided settings dictionary
		#TODO - possibly update with for loop through dictionary keys and set class __dict__ attributes.
		if self.HOST is None:
			try:
				self.HOST = self.SETTINGS['host']
			except:
				print(time.ctime(), "Host not in settings! Scanning for first available..")
				self.DEVICES = sorted(self.DISCOVER())
				self.HOST = self.DEVICES[0]
				self.SETTINGS['host'] = self.HOST
				print(time.ctime(), "Host auto set:", self.HOST)
		try:
			self.PORT = self.SETTINGS['port']
		except:
			self.SETTINGS['port'] = 8060
			self.PORT = 8060
		try:
			self.BASE_URL = self.SETTINGS['url']
		except:
			self.BASE_URL = f"http://{self.HOST}:{self.PORT}"
			self.SETTINGS['url'] = self.BASE_URL
		try:
			self.SETTINGS_FILE = self.SETTINGS['settings_file']
		except:
			self.SETTINGS_FILE = os.path.join(self.DATA_DIR, ".roku_hosts")
			self.SETTINGS['settings_file'] = self.SETTINGS_FILE
		try:
			self.DATA_DIR = self.SETTINGS['data_directory']
		except:
			self.DATA_DIR = os.path.join(os.path.expanduser("~"), '.rokuremote')
			self.SETTINGS['data_directory'] = self.DATA_DIR
		try:
			self.SCAN_TYPE = self.SETTINGS['scan_type']
		except:
			self.SCAN_TYPE = 'ssdp'
			self.SETTINGS['scan_type'] = self.SCAN_TYPE
		self._save_settings(self.SETTINGS)
		print(time.ctime(), "Settings applied!")

	def _init_settings(self, settings={}, r=False):
		"""
		initializes class attributes from SETTINGS variable.
		setting key is __attr__.lower()
		
		Exceptions: (don't follow that schema - TODO - FIX THAT!)
		self.SETTINGS['url'] = self.BASE_URL
		self.SETTINGS['data_directory'] = self.DATA_DIR

		Examples:
		self.SETTINGS['settings_file'] = self.SETTINGS_FILE
		self.SETTINGS['devices'] = self.DEVICES
		
		"""
		#if settings file exists, attempt to load from file.
		if not os.path.exists(self.SETTINGS_FILE):
			settings = None
		else:
			try:
				#if load succeeds, set re-init to False
				settings = self._load_settings()
			except Exception as e:
				#if load fails, create empty and complain.
				print(time.ctime(), f"Couldn't load settings file! Initializing again...")
				settings = None
		if r or settings is None:#full init: 'r' flag or 'settings is None' indicates a fail in settings dictionary, triggers re-init.
			#r flag in arguments will pre set this. Saves Dictionary to pickled dat file.
			if self.HOST is None:
				#if class attribute HOST is None, discover and auto-select first ip
				print(time.ctime(), "Discovering and auto-selecting first device...")
				settings['devices'] = sorted(self.DISCOVER())
				self.DEVICES = settings['devices']
				self.HOST = self.DEVICES[0]
				print(time.ctime(), "Host set:", self.HOST)
				#settings['host'] = input("Enter host ip:")
			else:
				#if it's set, use it as host key value in settings.
				settings['host'] = self.HOST
				print(time.ctime(), f"Host set: {self.HOST}")
			print(time.ctime(), "TODO: Create function to manage network scanning and select default device automatically.")
			print(time.ctime(), "TODO: in ui, allow option to manually input ip address of device.")
			settings['port'] = 9060
			settings['url'] = f"http://{self.HOST}:{self.PORT}"
			settings['settings_file'] = self.SETTINGS_FILE
			settings['data_directory'] = self.DATA_DIR
			self._save_settings(settings)
			print(time.ctime(), "Settings initialized!")
		self.SETTINGS = settings
		return settings

	def locateZip(self):
		return subprocess.check_output("find \"$HOME\" -name \"media_icons.zip\"", shell=True).decode().strip()

	def setup(self):		
		script_path = globals()['__file__']
		fname = os.path.basename(script_path).split('.')[0]
		dest = os.path.join(os.path.expanduser("~"), '.local', 'bin', fname)
		if not os.path.exists(self.ICONS_PATH):
			os.makedirs(self.ICONS_PATH, exist_ok=True)
		com = f"cp '{script_path}' '{dest}'"
		com2 = f"chmod a+x '{dest}'"
		print(time.ctime(), "Script location:", script_path)
		print(time.ctime(), "Destination:", dest)
		if not os.path.exists(dest):
			ret = subprocess.check_output(com, shell=True).decode().strip()
			ret2 = subprocess.check_output(com2, shell=True).decode().strip()
			print(time.ctime(), "ret1:", ret)
			print(time.ctime(), "ret2:", ret2)
		path = os.path.expanduser("~")
		zipfile = self.locateZip()
		com = f"cd '{self.ICONS_PATH}'; unzip -o '{zipfile}'"
		ret = subprocess.check_output(com, shell=True).decode().strip()
		print(time.ctime(), ret)
		ret = self.create_desktop_file()
		print(time.ctime(), ret)
	def download_image(self):
		try:
			response = requests.get('https://companieslogo.com/img/orig/ROKU-f0e3f010.png?t=1720244493', stream=True)
			response.raise_for_status()  # Raise an exception for bad status codes
			with open(self.ROKU_ICON, 'wb') as file:
				for chunk in response.iter_content(chunk_size=8192):
					if chunk:  # Filter out keep-alive new chunks
						file.write(chunk)
			file.close()
			print(time.ctime(), f"Image downloaded successfully: {self.ROKU_ICON}")
		except requests.exceptions.RequestException as e:
			print(time.ctime(), f"Error downloading image: {e}")

	def create_desktop_file(self):
		appdir = os.path.join(os.path.expanduser("~"), '.local', 'share', 'applications')
		execline = os.path.join(os.path.expanduser("~"), '.local', 'bin', 'rokuremote')
		execline = f"{execline} > ~/rokuremote.temp"
		data = f"""[Desktop Entry]
		Version=1.0
		Name=Roku Remote
		Comment=Remote for controlling Roku devices. Uses ECP (External control protocol) and python's PySimpleGUI.
		Exec={execline}
		Path={self.DATA_DIR}
		Icon={self.ROKU_ICON}
		Terminal=true
		Type=Application
		Categories=Utility;Development;"""
		dest = os.path.join(appdir, 'rokuremote.desktop')
		if not os.path.exists(self.ROKU_ICON):
			self.download_image()
		with open(dest, 'w') as f:
			f.write(data)
			f.close()
		return subprocess.check_output(f"chmod +x '{dest}'", shell=True).decode().strip()

	def togglePlayAtStart(self):
		if self.ENSURE_PLAY_AT_START:
			self.ENSURE_PLAY_AT_START = False
		else:
			self.ENSURE_PLAY_AT_START = True
		print(time.ctime(), f"Play at start toggled:", self.PLAY_AT_START)
		return self.ENSURE_PLAY_AT_START

	def getPlaybackPercentage(self):
		"""
		calculates playback percentage by querying media player on device,
		retreiving duration and position values, and converting to percentage.
		"""
		try:
			info = self._query_media_player()
			self.PLAYBACK_PERCENTAGE = round(int(info['position'].split(' ')[0]) / int(info['duration'].split(' ')[0]) * 100, 2)
		except:
			self.PLAYBACK_PERCENTAGE = 0
		return self.PLAYBACK_PERCENTAGE

	def getPlayerState(self):
		"""
		retreives player state ('playing', 'stopped', etc ...)
		"""
		return self._query_media_player()['@state']

	def hasError(self):
		"""
		Checks roku device for error state in media playback
		"""
		return json.loads(self._query_media_player()['@error'])

	def getCurrentApp(self):
		"""
		returns current app id and name
		returns a dictionary object
		"""
		d = {}
		d['name'] = info['plugin']['@name']
		d['id'] = info['plugin']['@id']
		return d

	def _get_percentage_diff(self):
		"""
		get percentage difference of current playback vs start.
		if jump greater than target, start playback at 0.
		TODO - ensure on 'close', 'load', 'buffer' states if ENSURE_PLAY_AT_START=True:
			set flag to trigger resume. This will stop it from doing so during rewinds/fwds and skips
		"""
		ret = self.PLAYBACK_PERCENTAGE - self.LAST_PLAYBACK_PERCENTAGE
		print(time.ctime(), "tested playback percentage:", self.PLAYBACK_PERCENTAGE)
		print(time.ctime(), "Play at start enabled:", self.ENSURE_PLAY_AT_START)
		if ret >= 1 and self.ENSURE_PLAY_AT_START:
			print(time.ctime(), "Playback position not at start. Fixing...")
			self._keyPress('Select')
			time.sleep(self.WAIT)
			self._keyPress('Left')
			time.sleep(self.WAIT)
			self._keyPress('Select')
		#print(time.ctime(), "diff:", ret)

	def OnStateChange(self, event=None, data=None, q=None):
		if q is not None:
			self.PLAYBACK_MONITOR_QUEUE = q
		d = {}
		if event is not None:
			d['event'] = event
		else:
			d['event'] = 'state_changed'
		if data is None:
			d['data'] = self.STATE
		else:
			d['data'] = data
		self.PLAYBACK_MONITOR_QUEUE.put_nowait(d)

	def PlaybackMonitorEventLoop(self, q=None, wait=None):
		"""
		Main monitor loop. Run this as a thread???
		"""
		if q is not None:
			self.PLAYBACK_MONITOR_QUEUE = q
		if wait is not None:
			self.WAIT = wait
		self.PLAYBACK_MONITOR_RUNNING = True
		while self.PLAYBACK_MONITOR_RUNNING:
			time.sleep(self.WAIT)
			self.STATE = self.getPlayerState()
			if self.STATE == self.LAST_STATE:
				pass
			else:
				self.LAST_PLAYBACK_PERCENTAGE = self.PLAYBACK_PERCENTAGE
				self.PLAYBACK_PERCENTAGE = self.getPlaybackPercentage()
				self._get_percentage_diff()
				if self.STATE not in self.STATES:
					print(time.ctime(), "State added:", self.STATE, self.STATES)
					self.STATES.append(self.STATE)
					event = 'state_added'
					event_value = self.STATE
				if self.STATE == 'play' or self.STATE == 'pause' or self.STATE == 'close':
					print(time.ctime(), "state:", self.STATE, self.PLAYBACK_PERCENTAGE)
					event = 'state_changed'
					event_value = self.STATE
				else:
					print(time.ctime(), "state:", self.STATE, self.PLAYBACK_PERCENTAGE)
					event = 'unhandled_state'
					event_value = self.STATE
					err = self.hasError()
					if err:
						print(time.ctime(), "has_error:", self.hasError())
						event = 'error_state'
						event_value = err
				self.OnStateChange(event=event, data=event_value)

			self.LAST_STATE = self.STATE
		self.PLAYBACK_MONITOR_RUNNING = False
		print(time.ctime(), "PlaybackMonitor exiting...")
		exit()

	def PlaybackMonitorStop(self):
		print(time.ctime(), f"Killing thread...")
		self.PLAYBACK_MONITOR_RUNNING = False
		self.PLAYBACK_MONITOR_THREAD.kill()

	def PlaybackMonitorGet(self):
		if self.PLAYBACK_MONITOR_QUEUE.unfinished_tasks > 0:
			event = self.PLAYBACK_MONITOR_QUEUE.get_nowait()
			self.PLAYBACK_MONITOR_QUEUE.task_done()
		else:
			event = None
		return event

	def PlaybackMonitorStart(self):
		self.PLAYBACK_MONITOR_THREAD = Thread(target=self.PlaybackMonitorEventLoop, args=(self.PLAYBACK_MONITOR_QUEUE,))
		self.PLAYBACK_MONITOR_THREAD.daemon = True
		self.PLAYBACK_MONITOR_THREAD.start()
		print(time.ctime(), f"Playback thread started!")

class rokuui(Roku):
	def __init__(self, exec_setup=False, grab_keyboard=True, wait=1):
		"""
		Main class for roku remote. Uses rokuremote.py.
		TODO: just added search to rokuremote.py. Need to test it.
		"""
		super().__init__(exec_setup=exec_setup, wait=wait)
		self.ui = UI()
		self.GRAB_KEYBOARD = grab_keyboard
		self.IS_TYPING = False
		#self.= Roku(exec_setup=exec_setup)
		#print(time.ctime(), "Remote Dict:", self.__dict__)
		self.run()

	def _update_play_at_start(self):
		self.WINDOW['-TOGGLE_ENSURE_PLAY_AT_START-'].update(self.ENSURE_PLAY_AT_START)

	def _toggle_play_at_start(self):
		"""
		No idea why, but this is backwards. Checking checkbox turns it off, unchecking is on, for some reason.
		Looking into it eventually....
		"""
		if self.ENSURE_PLAY_AT_START:
			self.ENSURE_PLAY_AT_START = True
		else:
			self.ENSURE_PLAY_AT_START = False
		print(time.ctime(), "Play at start toggled:", self.ENSURE_PLAY_AT_START)
		return self.ENSURE_PLAY_AT_START

	def frame_MediaControls(self):
		files = {}
		files["skip_next"] = os.path.join(self.ICONS_PATH, "next.png")
		files['skip_previous'] = os.path.join(self.ICONS_PATH, "skip_previous.png")
		files["back"] = os.path.join(self.ICONS_PATH, "back.png")
		files['right'] = os.path.join(self.ICONS_PATH, "right-arrow.png")
		files["down"] = os.path.join(self.ICONS_PATH, "down-arrow.png")
		files["left"] = os.path.join(self.ICONS_PATH, "left-arrow.png")
		files['up'] = os.path.join(self.ICONS_PATH, "up-arrow.png")
		files["select"] = os.path.join(self.ICONS_PATH, "check-mark.png")
		files['home'] = os.path.join(self.ICONS_PATH, "home.png")
		files['pause'] = os.path.join(self.ICONS_PATH, "pause.png")
		files['play'] = os.path.join(self.ICONS_PATH, "play.png")
		files['fwd'] = os.path.join(self.ICONS_PATH, "fast-forward.png")
		files['rev'] = os.path.join(self.ICONS_PATH, "rewind.png")
		files['stop'] = os.path.join(self.ICONS_PATH, "stop.png")
		files['instant_replay'] = os.path.join(self.ICONS_PATH, "replay.png")
		files['info'] = os.path.join(self.ICONS_PATH, "info.png")
		files['backspace'] = os.path.join(self.ICONS_PATH, "backspace.png")
		files['search'] = os.path.join(self.ICONS_PATH, "search.png")
		files['enter'] = os.path.join(self.ICONS_PATH, "enter.png")

		self.ui._add_elementToRow(sg.Text(f"Player state: {self.STATE}", key='-PLAYER_STATE-'))
		self.ui._add_elementToRow(sg.Text(f"Playback Percentage: %{self.PLAYBACK_PERCENTAGE}", key='-PLAYBACK_PERCENTAGE-'))
		self.ui._add_rowToLayout()
		txt = f"Play at start: {self.ENSURE_PLAY_AT_START}"
		self.ui._add_elementToRow(sg.Text(txt, key=f"-{txt}-"))
		self.ui._add_elementToRow(sg.Checkbox("Play next from beginning:", default=self.ENSURE_PLAY_AT_START, auto_size_text=True, change_submits=True, enable_events=True, key='-TOGGLE_ENSURE_PLAY_AT_START-', tooltip="Toggle play next from beginning, rather than last chapter in history (if previously viewed)."))
		self.ui._add_rowToLayout()
		self.ui._add_elementToRow(sg.Checkbox("Grab keyboard events:", default=self.GRAB_KEYBOARD, auto_size_text=True, change_submits=True, enable_events=True, key="-TOGGLE_GRAB_KEYBOARD-", tooltip=None))
		self.ui._add_rowToLayout()
		self.ui._add_elementToRow(sg.Image(size=(100, 100), filename=files['rev'], key="-REWIND-", background_color='white', tooltip="Rewind", enable_events=True))
		self.ui._add_elementToRow(sg.Image(size=(100, 100), filename=files['play'], key="-PLAY_PAUSE-", background_color='white', tooltip="Play/Pause", enable_events=True))
		self.ui._add_elementToRow(sg.Image(size=(100, 100), filename=files['fwd'], key="-FORWARD-", background_color='white', tooltip="Fast Forward", enable_events=True))
		self.ui._add_rowToLayout()
		self.ui._add_elementToRow(sg.Image(size=(100, 100), filename=files['back'], key="-BACK-", background_color='white', tooltip="Back", enable_events=True))
		self.ui._add_elementToRow(sg.Image(size=(100, 100), filename=files['up'], key="-UP-", background_color='white', tooltip="Up", enable_events=True))
		self.ui._add_elementToRow(sg.Image(size=(100, 100), filename=files['home'], key="-HOME-", background_color='white', tooltip="Home", enable_events=True))
		self.ui._add_rowToLayout()

		self.ui._add_elementToRow(sg.Image(size=(100, 100), filename=files['left'], key="-LEFT-", background_color='white', tooltip="Left", enable_events=True))
		self.ui._add_elementToRow(sg.Image(size=(100, 100), filename=files['select'], key="-SELECT-", background_color='white', tooltip="Select", enable_events=True))
		self.ui._add_elementToRow(sg.Image(size=(100, 100), filename=files['right'], key="-RIGHT-", background_color='white', tooltip="Right", enable_events=True))
		self.ui._add_rowToLayout()

		self.ui._add_elementToRow(sg.Image(size=(100, 100), filename=files['instant_replay'], key="-REPLAY-", background_color='white', tooltip="Instant Replay", enable_events=True))
		self.ui._add_elementToRow(sg.Image(size=(100, 100), filename=files['down'], key="-DOWN-", background_color='white', tooltip="Down", enable_events=True))
		self.ui._add_elementToRow(sg.Image(size=(100, 100), filename=files['enter'], key="-ENTER-", background_color='white', tooltip="Enter", enable_events=True))
		self.ui._add_rowToLayout()
		self.ui.addToFrame(title='Media-Controls', layout=self.ui.LAYOUT)
		self.ui.LAYOUT = []
		print(time.ctime(), "Media control frame created!")

	def frame_Output(self):
		#self.self.ui._add_elementToRow(sg.Combo(devices, default_value=default, size=(None, None), auto_size_text=True, change_submits=True, enable_events=True, disabled=False, right_click_menu=None, key='-DEVICES-', pad=None,  expand_x=False ,expand_y=False, tooltip="Select a device:", readonly=True), sg.Input(r.HOST, enable_events=True, key='-SET_DEVICE-', size=(None, 5), expand_x=False)
		self.ui._add_elementToRow(sg.Multiline(default_text="", autoscroll=True, autoscroll_only_at_bottom=True, size=(35, 10), auto_size_text=True, change_submits=True, enable_events=True, do_not_clear = True, key='-OUTPUT-', wrap_lines=True, expand_x=False, expand_y=True))
		self.ui._add_rowToLayout()
		self.ui.addToFrame(title='Output')
		print(time.ctime(), "Output frame created!")

	def frame_deviceDiscovery(self):
		self.ui._add_elementToRow(sg.Radio("SSDP", group_id="SCAN_TYPE", default=True, size=(None, None), auto_size_text=True, key="-SCAN_TYPE_SSDP-", tooltip="Set discovery type to 'ssdp' (Roku's DIAL implementation)", change_submits=True, enable_events=True, expand_x=False, expand_y=False))
		self.ui._add_elementToRow(sg.Radio("HTTP", group_id="SCAN_TYPE", default=False, size=(None, None), auto_size_text=True, key="-SCAN_TYPE_HTTP-", tooltip="Set discovery type to 'http', or basic test for services on port 80.", change_submits=True, enable_events=True, expand_x=False, expand_y=False))
		self.ui._add_elementToRow(sg.Button('Scan!', key='-START_SCAN-'))
		self.ui._add_rowToLayout()
		self.ui._add_elementToRow(sg.Text('Found devices:'))
		try:
			if self.SETTINGS['devices'] is None:
				devices = self.DISCOVER()
			else:
				devices = self.SETTINGS['devices']
		except Exception as e:
			print(time.ctime(), f"Error in settings dictionary: bad key - {e}")
			devices = self.DISCOVER()
		self.ui._add_elementToRow(sg.Combo(devices, default_value=self.HOST, size=(None, None), auto_size_text=True, change_submits=True, enable_events=True, disabled=False, right_click_menu=None, key='-DEVICES-', pad=None,  expand_x=False ,expand_y=False, tooltip="Select a device:", readonly=True))
		self.ui._add_elementToRow(sg.Button('Set!', key='-SET_DEVICE-'))
		self.ui._add_rowToLayout()
		self.ui._add_elementToRow(sg.Input(self.HOST, enable_events=True, key='-DEVICES-', size=(None, 5), expand_x=False))
		self.ui._add_elementToRow(sg.Text(self.HOST))
		self.ui._add_rowToLayout()
		self.ui._add_elementToRow(sg.Multiline(default_text="", autoscroll=True, autoscroll_only_at_bottom=True, size=(35, 10), auto_size_text=True, change_submits=True, enable_events=True, do_not_clear = True, key='-OUTPUT-', wrap_lines=True, expand_x=False, expand_y=True))
		self.ui._add_rowToLayout()
		self.ui.addToFrame(title='Device Discovery')
		print(time.ctime(), "Device discovery frame created!")

	def frame_getDeviceInfo(self):
		info = self._query_device()
		#print(time.ctime(), "info:", info)
		for k in info:
			v = info[k]
			self.ui._add_elementToRow(sg.Text(f"{k}='{v}'"))
			self.ui._add_rowToLayout()
		self.ui.addToFrame(title='Device Information')


	def run(self):
		self.frame_MediaControls()
		self.frame_deviceDiscovery()
		self.frame_getDeviceInfo()
		self.WINDOW = self.ui.getWindow(title='MediaControls', layout=self.ui.FRAMES)
		#e, v = win.read()
		return self.WINDOW

	def scan(self, scan_type=None):
		if scan_type is None:
			scan_type = self.SCAN_TYPE
		if scan_type == 'http':
			self.WINDOW['-OUTPUT-'].update("Starting http full scan..")
			devices = self._scan_network(full=True)
			print(time.ctime(), "Found devices:", devices)
			self.WINDOW['-DEVICES-'].update(values=devices, value=self.HOST)
			devs = "\n".join(devices)
			text = f"Found devices:\n{devs}"
			self.WINDOW['-OUTPUT-'].update(text)
		elif scan_type == 'ssdp':
			self.WINDOW['-OUTPUT-'].update("Starting ssdp discovery scan...")
			devices = self.DISCOVER()
			if len(devices) > 0:
				self.WINDOW['-DEVICES-'].update(values=devices, value=self.HOST)
				devs = "\n".join(devices)
				text = f"Found devices:\n{devs}"
				self.WINDOW['-OUTPUT-'].update(text)
			else:
				self.WINDOW['-OUTPUT-'].update("No devices found! Try again or choose a different scan type.")
		self._save_settings(self.SETTINGS)

	def testKeys(self, keystr, keep_keypad_separate=True):
		if keystr == '__TIMEOUT__':
			return None
		ascii_words = {'at': '@', 'numbersign': '#', 'exclam': '!', 'dollar': '$', 'percent': '%', 'asciicircum': '^', 'ampersand': '&', 'asterisk': '*', 'parenleft': '(', 'parenright': ')', 'underscore': '_', 'minus': '-', 'plus': '+', 'equal': '='}
		words = list(ascii_words.keys())
		if keystr.split(':')[0] in words:#if keystr needs ascii translated, assume keyboard input, set attrs, and return char.
			k, self.KEY_NUMBER = keystr.split(':')
			self.KEY_NAME = ascii_words[k]
			self.KEYPRESS = f"{self.KEY_NAME}:{self.KEY_NUM}"
			return f"TYPE_CHAR_{self.KEY_NAME}"
		print(time.ctime(), "keystr:", keystr)
		chars = getKeys()
		if keystr is None:
			return None
		#if return keyboard events:
		if self.GRAB_KEYBOARD:
			self.KEYPRESS = keystr
			#set keypress attribute on test, regardless of filter
			keys = ['Escape', 'Space', 'Select', 'Play', 'Up', 'Left', 'Right', 'Down', '111', '113', '114', '116', '85', '83', '80', '88', '65', '9']
			if ':' in keystr:
				self.KEY_NAME, self.KEY_NUM = keystr.split(':')
			else:
				self.KEY_NAME, self.KEY_NUM = keystr, None
			self.KEY_NAME = self.KEY_NAME.title()
			if self.KEY_NAME in list(chars.keys()) or self.KEY_NAME in words:
				if self.KEY_NAME in words:
					self.KEY_NAME = ascii_words[self.KEY_NAME]
				#if in list of single keyboard chars, assume typed letter and change to send key event tag.
				name = f"TYPE_CHAR_{self.KEY_NAME}"
				return name
			elif 'KP_' in self.KEY_NAME:
				name = self.KEY_NAME.split('KP_')[1]
				#if separating keypad directions from arrow keys...
				if not keep_keypad_separate:
					self.KEY_NAME = name
					#overwrite class attribute with direction name
			else:#else use as is
				name = self.KEY_NAME
			if name == 'Space':
				print(time.ctime(), "Space bar >> play/pause")
				name = 'Play_Pause'
				self.KEY_NAME = name
			if name == 'Enter' or name == 'Return':
				print(time.ctime(), "enter/return >> select")
				name = 'Select'
				self.KEY_NAME = name
			if name == 'Escape':
				print(time.ctime(), "Escape >> Back")
				name = "Back"
				self.KEY_NAME = name
			print(time.ctime(), "name:", name)
			if name in keys:
				return name
			elif self.KEY_NUM in keys:
				return self.KEY_NAME
			else:
				return None
		else:
			return None

def start_monitor(r):
	return r.PlaybackMonitorStart()

def main(exec_setup=False, wait=1, start_playback_monitor=True):
	"""
	main execute function for rokuremote.
	on start:
		if exec_setup:
			runs setup, regardless of local directory test results.
		wait is time to wait before continuing event monitor loop
		Creates roku object
		loads settings
		connects to device or scans for one
		initializes apps and device info
	on run:
		monitors player device states
		sends kepresses via menu
		
	TODO - integrate PlaybackMonitor event loop into this function
	"""
	r = rokuui(exec_setup=exec_setup, wait=wait)
	if start_playback_monitor:
		thread = start_monitor(r)
	win = r.ui.WINDOW
	r._update_play_at_start()
	k = None
	while True:
		e = r.PlaybackMonitorGet()
		if e is not None:
			print(time.ctime(), "Playback monitor:", e)
		#using window timeout instead of tine.sleep to pause.
		#here to stop a request flood for status updates.
		#TODO - work in threaded process and event queue.
		#time.sleep(r.WAIT)
		e, v = win.read(timeout=r.WAIT)
		if not win.was_closed():
			win['-PLAYBACK_PERCENTAGE-'].update(f"Playback Percentage: %{r.getPlaybackPercentage()}")
			win['-PLAYER_STATE-'].update(f"Player state: {r.getPlayerState()}")
		try:
			k = r.testKeys(e)
		except:
			#if test keys failed, exit occured, close window
			print(time.ctime(), "testKeys failed! Closing...")
			win.close()
		if k is not None:
			e = f"-{k.upper()}-"
			print(time.ctime(), "key pressed:", e)
		if e == sg.WINDOW_CLOSED:
			break
		elif e == '__TIMEOUT__':
			pass
		elif e == '-TOGGLE_GRAB_KEYBOARD-':
			r.GRAB_KEYBOARD = v[e]
			print(time.ctime(), "Keyboard event capture toggled:", r.GRAB_KEYBOARD)
		elif e == '-SCAN_TYPE_HTTP-':
			r.SCAN_TYPE = 'http'
			print(time.ctime(), "Scan type set: http")
		elif e == '-SCAN_TYPE_SSDP-':
			r.SCAN_TYPE = 'ssdp'
			print(time.ctime(), "Scan type set: ssdp")
		elif e == '-START_SCAN-':
			r.scan()
		elif e == '-SELECT-':
			r._keyPress('Select')
		elif e == '-REWIND-':
			r._keyPress('Rev')
		elif e == '-PLAY_PAUSE-':
			r._keyPress('Play')
		elif e == '-FORWARD-':
			r._keyPress('Fwd')
		elif e == '-BACK-':
			r._keyPress('Back')
		elif e == '-UP-':
			r._keyPress('Up')
		elif e == '-HOME-':
			r._keyPress('Home')
		elif e == '-LEFT-':
			r._keyPress('Left')
		elif e == '-RIGHT-':
			r._keyPress('Right')
		elif e == '-REPLAY-':
			r._keyPress('InstantReplay')
		elif e == '-DOWN-':
			r._keyPress('Down')
		elif e == '-ENTER-':
			r._keyPress('Enter')
		elif '-TYPE_CHAR_' in e:
			k = e.split('-TYPE_CHAR_')[1].split('-')[0]
			r._keyPress(k)
			print(time.ctime(), f"Sent keyboard input to roku: {k}")
		elif e == '-Toggle_Ensure_Play_At_Start-' or e == '-TOGGLE_ENSURE_PLAY_AT_START-':
			r.ENSURE_PLAY_AT_START = v[e]
			r.TOGGLE_ENSURE_PLAY_AT_START = r._toggle_play_at_start()
		else:
			print(time.ctime(), e, v)
	exit()
if __name__ == "__main__":
	main()
