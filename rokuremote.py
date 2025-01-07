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
import socket
#from discovery2 import RokuDiscoverer

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
		print("Scanning via ssdp for devices...")
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
		print("Scan complete!")
		print(f"{len(l)} devices found!")
		pos = 0
		for i in l:
			pos += 1
			print(f"{pos}: {i}")
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
		print("Frame added!")

	def getWindow(self, title='Test Window', layout=None, width=640, height=480, expand_x=False, expand_y=False):
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
		self.WINDOW = sg.Window(title=title, layout=layout, size=(width, height)).finalize()
		return self.WINDOW

	def save(self, filepath=None, win=None):
		if win is None:
			win = self.WINDOW
		if filepath is None:
			filepath = os.path.join(os.path.expanduser("~"), f".{win.title}.dat")
		win.save_to_disk(filepath)

class Roku():
	def __init__(self, host=None, port=8060, scan=False, scan_type='ssdp', exec_setup=False):
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
			try:
				self.PORT = self.SETTINGS['port']
			except:
				self.SETTINGS['port'] = 8060
				self.PORT = self.SETTINGS['port']
		except Exception as e:
			pass
		if self.HOST is not None:
			if self.HOST not in self.DEVICES:
				self.DEVICES.append(self.HOST)
			print("loaded host:", self.HOST)
		elif self.HOST is None:
			try:
				self.HOST = self.SETTINGS['host']
				if self.HOST is None:
					print("Host saved in settings is None! Re-initializing...")
					self.SETTINGS = self._init_settings(r=True)
					self.HOST = self.SETTINGS['host']
					self.SETTINGS['url'] = self.BASE_URL
					self.SETTINGS['settings_file'] = self.SETTINGS_FILE
					self.SETTINGS['data_directory'] = self.DATA_DIR
					self.SETTINGS['devices'] = self.DEVICES
					self._save_settings(self.SETTINGS)
					if self.HOST is None:
						scan = True
						print(f"Failed get or replace host! Rescanning...")
					else:
						print("Host reset to", self.HOST)
						scan = False
				else:
					print("Host set fom settings:", self.HOST)
					scan = False
			except Exception as e:
				print(f"Host not in settings. Re-initializing...")
				self.SETTINGS = self._init_settings()
				self.HOST = sorted(self.DISCOVER())[0]
				print("Host set:", self.HOST)
		if scan:
			try:
				self.DEVICES = self.DISCOVER()
			except:
				print("SSDP discover failed! Trying slow scan..")
				self.DEVICES = self._scan_network()
			print("devices:", self.DEVICES)
			if len(self.DEVICES) > 0:
				self.HOST = self.DEVICES[0]
				if 'http://' in self.HOST:
					self.HOST = self.HOST.split('http://')[1].split(':')
			else:
				print("No devices found via ssdp. Scanning with http..")
				self.HOST = self._scan_network()
				self.SCAN_TYPE = 'http'
				self.DEVICES = [self.HOST]
		#print("Host, Port:", self.HOST, self.PORT)
		self.BASE_URL = f"http://{self.HOST}:{self.PORT}"
		try:
			self.DEVICE_INFO = self._query_device()
		except Exception as e:
			print(f"Couldn't get device info!")
			self.DEVICE_INFO = {}
		if self.DEVICE_INFO != {}:
			self.PLAYER = self._query_media_player()
			self.APPS = self.UpdateApps()
		self._save_settings()

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
				print(f"Error downloading icon: Bad status code ({r.status_code}) - {r.text})")
				return False
		except Exception as e:
			print(f"Error downloading icon: {e}")
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
				print("%:", p)
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
						print("No air year found!", e)
						out[t][title]['first_air_year'] = None
						out[t][title][ 'last_air_year'] = None
					out[t][title]['seasons'] = i['seasonCount']
					out[t][title]['episodes'] = i['episodeCount']
					out[t][title]['streaming_options'] = i['streamingOptions']
			elif t == 'movie':
				p = compareStrings(title, query)
				print("%:", p)
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
				print("Settings file created!")
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
			print("Scanning network via HTTP for devices...")
		else:
			print("Scanning network via http for first available device...")
		self.DEVICES = []
		sn = self._send_subnet()
		for i in range(0, 30):
			ip = f"{sn}.{i}"
			url = f"http://{ip}:8060/"
			try:
				print("testing ip:", ip)
				r = requests.get(url)
				if '<serviceType>urn:roku-com:service:ecp:1</serviceType>' in r.text:
					print("device found!", ip)
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
			print("Action:", rtype)
			if data is not None:
				print("with data...")
				r = requests.post(url, data=data)
			else:
				print("No data for post!")
				r = requests.post(url)
		if r.status_code != 200:
			print(f"Error in requests: Bad status code ({r.status_code}, {r.text}")
			return r.text
		else:
			try:
				return r.json()
			except Exception as e:
				print("Couldn't get json. Returning text object...")
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
				print("Couldn't parse xml:", e)
				return xml_string
		elif type(xml_string) == dict:#if arg is already dict object, return.
			return xml_string
		else:
			print("xml type:", type(xml_string))
			input("Press enter to continue...")
	def _query_device(self):
		#get and parse device information
		return xmldict.xml_to_dict(self._send(f"{self.BASE_URL}/query/device-info"))['device-info']
	def _query_media_player(self):
		string = self._send(f"{self.BASE_URL}/query/media-player")
		return xmltojson.xmltodict.parse(string)['player']
	def _keyPress(self, key):
		#send a key to the roku device.
		url = None
		chars = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '1', '2', '3', '4', '5', '6', '7', '8', '9', '0', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z']
		key_names = ['Home', 'Rev', 'Fwd', 'Play', 'Select', 'Left', 'Right', 'Down', 'Up', 'Back', 'InstantReplay', 'Info', 'Backspace', 'Search', 'Enter']
		k = quote(key.lower())
		print("key:", k)
		if key in chars:
			url = f"{self.BASE_URL}/keypress/Lit_{quote(k)}"
		elif key in key_names:
			url = f"{self.BASE_URL}/keypress/{k}"
		print("url:", url)
		if url is not None:
			return self._send(url, rtype='POST')
		else:
			print("Whoops!")
			return None
	def _get_apps(self):
		#get and parse xml data for all apps
		#currently installed on the Roku device.
		url = f"{self.BASE_URL}/query/apps"
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
	def UpdateApps(self):
		apps = self._get_apps()
		self.APPS_BY_ID = {}
		self.APPS_BY_NAME = {}
		for app in apps:
			#app['icon_data'] = self._get_app_icon(app['appid'])
			self.APPS_BY_ID[app['appid']] = app
			self.APPS_BY_NAME[app['name']] = app
		print("Applications dictionaries updated!")
	def _get_app_icon(self, appid):
		#TODO - this writes binary data to create icon file.
		#figure out how to do that to save output, then return a file path.
		url = f"{self.BASE_URL}/query/icon/{appid}"
		print("url:", url)
		print(self._send(url))
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
			print(f"Error saving settings file: {e}")
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
			print(f"Error loading settings file: {e}")
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
				print("Host not in settings! Scanning for first available..")
				self.DEVICES = sorted(self.DISCOVER())
				self.HOST = self.DEVICES[0]
				self.SETTINGS['host'] = self.HOST
				print("Host auto set:", self.HOST)
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
		print("Settings applied!")

	def _init_settings(self, settings={}, r=False):
		#if settings file exists, attempt to load from file.
		if not os.path.exists(self.SETTINGS_FILE):
			r = True#set reinit flag to True
		else:
			try:
				settings = self._load_settings()
				r = False
			except Exception as e:
				#if load fails, create empty and complain.
				print(f"Couldn't load settings file! Initializing again...")
				r = True
		if r:#create and save dictionary to pickled data file.
			if self.HOST is None:
				print("Discovering and auto-selecting first device...")
				settings['devices'] = sorted(self.DISCOVER())
				self.DEVICES = settings['devices']
				self.HOST = self.DEVICES[0]
				print("Host set:", self.HOST)
				#settings['host'] = input("Enter host ip:")
			else:
				settings['host'] = self.HOST
				print(f"Host set: {self.HOST}")
			print("TODO: Create function to manage network scanning and select default device automatically.")
			print("TODO: in ui, allow option to manually input ip address of device.")
			settings['port'] = 9060
			settings['url'] = f"http://{self.HOST}:{self.PORT}"
			settings['settings_file'] = self.SETTINGS_FILE
			settings['data_directory'] = self.DATA_DIR
			self._save_settings(settings)
			print("Settings initialized!")
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
		print("Script location:", script_path)
		print("Destination:", dest)
		if not os.path.exists(dest):
			ret = subprocess.check_output(com, shell=True).decode().strip()
			ret2 = subprocess.check_output(com2, shell=True).decode().strip()
			print("ret1:", ret)
			print("ret2:", ret2)
		path = os.path.expanduser("~")
		zipfile = self.locateZip()
		com = f"cd '{self.ICONS_PATH}'; unzip -o '{zipfile}'"
		ret = subprocess.check_output(com, shell=True).decode().strip()
		print(ret)
		ret = self.create_desktop_file()
		print(ret)
	def download_image(self):
		try:
			response = requests.get('https://companieslogo.com/img/orig/ROKU-f0e3f010.png?t=1720244493', stream=True)
			response.raise_for_status()  # Raise an exception for bad status codes
			with open(self.ROKU_ICON, 'wb') as file:
				for chunk in response.iter_content(chunk_size=8192):
					if chunk:  # Filter out keep-alive new chunks
						file.write(chunk)
			file.close()
			print(f"Image downloaded successfully: {self.ROKU_ICON}")
		except requests.exceptions.RequestException as e:
			print(f"Error downloading image: {e}")

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

class rokuui(Roku):
	def __init__(self, exec_setup=False):
		"""
		Main class for roku remote. Uses rokuremote.py.
		TODO: just added search to rokuremote.py. Need to test it.
		"""
		super().__init__(exec_setup=exec_setup)
		self.ui = UI()
		#self.= Roku(exec_setup=exec_setup)
		#print("Remote Dict:", self.__dict__)
		self.run()
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
		print("Media control frame created!")

	def frame_Output(self):
		#self.self.ui._add_elementToRow(sg.Combo(devices, default_value=default, size=(None, None), auto_size_text=True, change_submits=True, enable_events=True, disabled=False, right_click_menu=None, key='-DEVICES-', pad=None,  expand_x=False ,expand_y=False, tooltip="Select a device:", readonly=True), sg.Input(r.HOST, enable_events=True, key='-SET_DEVICE-', size=(None, 5), expand_x=False)
		self.ui._add_elementToRow(sg.Multiline(default_text="", autoscroll=True, autoscroll_only_at_bottom=True, size=(35, 10), auto_size_text=True, change_submits=True, enable_events=True, do_not_clear = True, key='-OUTPUT-', wrap_lines=True, expand_x=False, expand_y=True))
		self.ui._add_rowToLayout()
		self.ui.addToFrame(title='Output')
		print("Output frame created!")

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
			print(f"Error in settings dictionary: bad key - {e}")
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
		print("Device discovery frame created!")

	def frame_getDeviceInfo(self):
		info = self._query_device()
		#print("info:", info)
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
			print("Found devices:", devices)
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

def main(exec_setup=False):
	r = rokuui(exec_setup=exec_setup)
	win = r.ui.WINDOW
	while True:
		e, v = win.read()
		if e == sg.WINDOW_CLOSED:
			break
		elif e == '-SCAN_TYPE_HTTP-':
			r.SCAN_TYPE = 'http'
			print("Scan type set: http")
		elif e == '-SCAN_TYPE_SSDP-':
			r.SCAN_TYPE = 'ssdp'
			print("Scan type set: ssdp")
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
		else:
			print(e, v)
if __name__ == "__main__":
	main()