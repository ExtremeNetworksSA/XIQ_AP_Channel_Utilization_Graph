import logging
import os
import inspect
from socketserver import BaseRequestHandler
import sys
import json
import time
from xmlrpc.client import APPLICATION_ERROR
import requests
from pprint import pprint as pp
current_dir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir) 
from requests.exceptions import HTTPError, ReadTimeout
from app.xiq_logger import logger

logger = logging.getLogger('AP_log_parser.xiq_collector')

PATH = current_dir

class XIQ:
    def __init__(self, user_name=None, password=None, token=None):
        self.URL = "https://api.extremecloudiq.com"
        self.headers = {"Accept": "application/json", "Content-Type": "application/json"}
        self.totalretries = 5
        if token:
            self.headers["Authorization"] = "Bearer " + token
        else:
            try:
                self.__getAccessToken(user_name, password)
            except ValueError as e:
                raise ValueError(e)
            except HTTPError as e:
               raise ValueError(e)
            except:
                log_msg = "Unknown Error: Failed to generate token for XIQ"
                logger.error(log_msg)
                raise ValueError(log_msg)
    #API CALLS
    def __setup_get_api_call(self, info, url):
        success = 0
        for count in range(1, self.totalretries):
            try:
                response = self.__get_api_call(url=url)
            except ValueError as e:
                print(f"API to {info} failed attempt {count} of {self.totalretries} with {e}")
            except Exception as e:
                print(f"API to {info} failed with {e}")
                print('script is exiting...')
                raise SystemExit
            except:
                print(f"API to {info} failed attempt {count} of {self.totalretries} with unknown API error")
            else:
                success = 1
                break
        if success != 1:
            print("failed to {}. Cannot continue to import".format(info))
            print("exiting script...")
            raise SystemExit
        if 'error' in response:
            if response['error_message']:
                log_msg = (f"Status Code {response['error_id']}: {response['error_message']}")
                logger.error(log_msg)
                print(f"API Failed {info} with reason: {log_msg}")
                print("Script is exiting...")
                raise SystemExit
        return response

    def __get_api_call(self, url):
        try:
            response = requests.get(url, headers= self.headers)
        except HTTPError as http_err:
            logger.error(f'HTTP error occurred: {http_err} - on API {url}')
            raise ValueError(f'HTTP error occurred: {http_err}') 
        if response is None:
            log_msg = "ERROR: No response received from XIQ!"
            logger.error(log_msg)
            raise ValueError(log_msg)
        if response.status_code != 200:
            log_msg = f"Error - HTTP Status Code: {str(response.status_code)}"
            logger.error(f"{log_msg}")
            try:
                data = response.json()
            except json.JSONDecodeError:
                logger.warning(f"\t\t{response.text}")
            else:
                if 'error_message' in data:
                    logger.warning(f"\t\t{data['error_message']}")
                    raise ValueError(log_msg)
            raise ValueError(log_msg) 
        try:
            data = response.json()
        except json.JSONDecodeError:
            logger.error(f"Unable to parse json data - {url} - HTTP Status Code: {str(response.status_code)}")
            raise ValueError("Unable to parse the data from json, script cannot proceed")
        return data

    def __post_api_call(self, url, payload):
        try:
            response = requests.post(url, headers= self.headers, data=payload)
        except HTTPError as http_err:
            logger.error(f'HTTP error occurred: {http_err} - on API {url}')
            raise ValueError(f'HTTP error occurred: {http_err}') 
        if response is None:
            log_msg = "ERROR: No response received from XIQ!"
            logger.error(log_msg)
            raise ValueError(log_msg)
        if response.status_code == 201:
            return "Success"
        elif response.status_code != 200:
            log_msg = f"Error - HTTP Status Code: {str(response.status_code)}"
            logger.error(f"{log_msg}")
            try:
                data = response.json()
            except json.JSONDecodeError:
                logger.warning(f"\t\t{response.text()}")
            else:
                if 'error_message' in data:
                    logger.warning(f"\t\t{data['error_message']}")
                    raise Exception(data['error_message'])
            raise ValueError(log_msg)
        try:
            data = response.json()
        except json.JSONDecodeError:
            logger.error(f"Unable to parse json data - {url} - HTTP Status Code: {str(response.status_code)}")
            raise ValueError("Unable to parse the data from json, script cannot proceed")
        return data
    

    def __getAccessToken(self, user_name, password):
        info = "get XIQ token"
        success = 0
        url = self.URL + "/login"
        payload = json.dumps({"username": user_name, "password": password})
        for count in range(1, self.totalretries):
            try:
                data = self.__post_api_call(url=url,payload=payload)
            except ValueError as e:
                print(f"API to {info} failed attempt {count} of {self.totalretries} with {e}")
            except Exception as e:
                raise ValueError(f"{e}")
            except:
                raise ValueError(f"API to {info} failed with unknown API error")
            else:
                success = 1
                break
        if success != 1:
            print("failed to get XIQ token. Cannot continue to import")
            print("exiting script...")
            raise SystemExit
        
        if "access_token" in data:
            #print("Logged in and Got access token: " + data["access_token"])
            self.headers["Authorization"] = "Bearer " + data["access_token"]
            return 0

        else:
            log_msg = "Unknown Error: Unable to gain access token for XIQ"
            logger.warning(log_msg)
            raise ValueError(log_msg)

    ## LRO Call
    def __post_lro_call(self, url, payload = {}, msg='', count = 1):
        try:
            response = requests.post(url, headers=self.headers, data=payload, timeout=60)
        except HTTPError as http_err:
            raise HTTPError(f'HTTP error occurred: {http_err} - on API {url}')
        except ReadTimeout as timout_err:
            raise HTTPError(f'HTTP error occurred: {timout_err} - on API {url}')
        except Exception as err:
            raise TypeError(f'Other error occurred: {err}: on API {url}')
        else:
            if response is None:
                error_msg = f"Error retrieving API {msg} from XIQ - no response!"
                raise TypeError(error_msg)
            elif response.status_code != 202:
                error_msg = f"Error retrieving API {msg} from XIQ - HTTP Status Code: {str(response.status_code)}"
                print(response.text)
                raise TypeError(error_msg) 
            data = response.headers
            # return the URL needed to check the status and collect data for the LRO
            return data['Location']
    
    def __getChildrenFromLocation(self, loc_id):
        info = "get floor id"
        url = self.URL + "/locations/tree?parentId=" + str(loc_id)
        children = self.__setup_get_api_call(info, url)
        child_ids = [child['id'] for child in children ]
        return child_ids

    # EXTERNAL ACCOUNTS
    def __getVIQInfo(self):
        info="get current VIQ name"
        success = 0
        url = "{}/account/home".format(self.URL)
        for count in range(1, self.totalretries):
            try:
                data = self.__get_api_call(url=url)
            except ValueError as e:
                print(f"API to {info} failed attempt {count} of {self.totalretries} with {e}")
            except:
                print(f"API to {info} failed attempt {count} of {self.totalretries} with unknown API error")
            else:
                success = 1
                break
        if success != 1:
            print(f"Failed to {info}")
            return 1
            
        else:
            self.viqName = data['name']
            self.viqID = data['id']        

    ## EXTERNAL FUNCTION

  
    #ACCOUNT SWITCH
    def selectManagedAccount(self):
        self.__getVIQInfo()
        info="gather accessible external XIQ acccounts"
        success = 0
        url = "{}/account/external".format(self.URL)
        for count in range(1, self.totalretries):
            try:
                data = self.__get_api_call(url=url)
            except ValueError as e:
                print(f"API to {info} failed attempt {count} of {self.totalretries} with {e}")
            except:
                print(f"API to {info} failed attempt {count} of {self.totalretries} with unknown API error")
            else:
                success = 1
                break
        if success != 1:
            print(f"Failed to {info}")
            return 1
            
        else:
            return(data, self.viqName)


    def switchAccount(self, viqID, viqName):
        info=f"switch to external account {viqName}"
        success = 0
        url = "{}/account/:switch?id={}".format(self.URL,viqID)
        payload = ''
        for count in range(1, self.totalretries):
            try:
                data = self.__post_api_call(url=url, payload=payload)
            except ValueError as e:
                print(f"API to {info} failed attempt {count} of {self.totalretries} with {e}")
            except Exception as e:
                print(f"API to {info} failed with {e}")
                print('script is exiting...')
                raise SystemExit
            except:
                print(f"API to {info} failed attempt {count} of {self.totalretries} with unknown API error")
            else:
                success = 1
                break
        if success != 1:
            print("failed to get XIQ token to {}. Cannot continue to import".format(info))
            print("exiting script...")
            raise SystemExit
        
        if "access_token" in data:
            #print("Logged in and Got access token: " + data["access_token"])
            self.headers["Authorization"] = "Bearer " + data["access_token"]
            self.__getVIQInfo()
            if viqName != self.viqName:
                logger.error(f"Failed to switch external accounts. Script attempted to switch to {viqName} but is still in {self.viqName}")
                print("Failed to switch to external account!!")
                print("Script is exiting...")
                raise SystemExit
            return 0

        else:
            log_msg = "Unknown Error: Unable to gain access token for XIQ"
            logger.warning(log_msg)
            raise ValueError(log_msg) 
    
    #SITES
    def DevicesFromSite(self,name):
        site_id = 0
        found = False
        info = f"check for site {name}"
        url = f"{self.URL}/locations/site?name={name}"
        response = self.__setup_get_api_call(info,url)
        if 'total_count' in response and response['total_count'] > 0:
            for site in response['data']:
                if name == site['name']:
                    site_id = site['id']
                    found = True
                    break
        if found:
            building_ids = self.__getChildrenFromLocation(site_id)
            floor_ids = []
            for building_id in building_ids:
                this_floor_ids = self.__getChildrenFromLocation(building_id)
                floor_ids = floor_ids + this_floor_ids
            if floor_ids:
                devices = self.collectDevices(pageSize=100, location_id=floor_ids)
            else:
                log_msg = f"No Floors were found in any buildings associated with Site {name}."
                raise ValueError(log_msg)
            return devices
        else:
            log_msg = f"No Site was found with the name {name}"
            raise ValueError(log_msg)
    
    ## Buildings
    def DevicesFromBuilding(self,name):
        building_id = 0
        found = False
        info = f"check for building {name}"
        url = f"{self.URL}/locations/building?name={name}"
        response = self.__setup_get_api_call(info,url)
        if 'total_count' in response and response['total_count'] > 0:
            for building in response['data']:
                if name == building['name']:
                    building_id = building['id']
                    found = True
                    break
        if found:
            floor_ids = self.__getChildrenFromLocation(building_id)
            if floor_ids:
                devices = self.collectDevices(pageSize=100, location_id=floor_ids)
            else:
                log_msg = f"No Floors were found in building {name}."
                raise ValueError(log_msg)
            return devices
        else:
            log_msg = f"No buildings was found with the name {name}"
            raise ValueError(log_msg)
        
    ## Floors
    def DevicesFromFloor(self,building_name,floor_name):
        building_id = 0 
        building_found = False
        floor_id = 0
        floor_found = False
        info =f"check for building {building_name}"
        url = f"{self.URL}/locations/building?name={building_name}"
        response = self.__setup_get_api_call(info,url)
        if 'total_count' in response and response['total_count'] > 0:
            for building in response['data']:
                if building_name == building['name']:
                    building_id = building['id']
                    building_found = True
                    break
        if building_found:
            info =f"check for floor {floor_name}"
            url = f"{self.URL}/locations/floor?name={floor_name}"
            response = self.__setup_get_api_call(info,url)
            if 'total_count' in response and response['total_count'] > 0:
                for floor in response['data']:
                    if floor_name == floor['name']:
                        if building_id == floor['parent_id']:
                            floor_id = floor['id']
                            floor_found = True
                            break
            if floor_found:
                devices = self.collectDevices(pageSize=100, location_id=floor_id)
            else:
                log_msg = f"No Floors with the name {floor_name} were found in building {building_name}."
                raise ValueError(log_msg)
            return devices
        else:
            log_msg = f"No buildings was found with the name {building_name}"
            raise ValueError(log_msg)


    ## Devices
    def collectDevices(self, pageSize, location_id=None, hostname=None, macaddr=None):
        info = "collecting devices" 
        page = 1
        pageCount = 1

        devices = []
        while page <= pageCount:
            url = self.URL + "/devices?page=" + str(page) + "&limit=" + str(pageSize) + "&connected=true"
            if location_id:
                if type(location_id) == list:
                    for l_id in location_id:
                        url = url + "&locationIds=" + str(l_id)
                else:
                    url = url  + "&locationId=" + str(location_id)
            elif hostname:
                if type(hostname) == list:
                    for name in hostname:
                        url = url + "&hostnames=" +str(name)
                else:
                    url = url + "&hostnames=" +str(hostname)
            elif macaddr:
                if type(macaddr) == list:
                    for mac in macaddr:
                        url = url + "&macAddresses=" +str(mac)
                else:
                    url = url + "&macAddresses=" +str(macaddr)
                
            rawList = self.__setup_get_api_call(info,url)
            devices = devices + [device for device in rawList['data'] if 'device_function' in device and device['device_function'] == "AP"]

            pageCount = rawList['total_pages']
            print(f"completed page {page} of {rawList['total_pages']} collecting Devices")
            page = rawList['page'] + 1 
        return devices


    ## Radio Info
    def collectRadioInfo(self, device_id, startTime,endTime):
        data_list = []
        info = 'Collect radio info'  
        url = self.URL + "/devices/" + str(device_id) + "/interfaces/wifi?startTime=" + str(startTime) + "&endTime=" + str(endTime)
        rawList = self.__setup_get_api_call(info,url)
        
        for interface in rawList:
            data = {}
            data['interface_name']= interface['interface_name']
            data["tx_utilization"]= interface['tx_utilization']
            data["rx_utilization"]= interface['rx_utilization']
            data["total_utilization"]= interface['total_utilization']
            data['timestamp'] = endTime
            data_list.append(data)
        return data_list
