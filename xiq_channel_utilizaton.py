#!/usr/bin/python3
import time
import sys
import getpass
import logging
import os
import pandas as pd
import argparse
import multiprocessing
from pprint import pprint as pp
from app.xiq_api import XIQ
from app.xiq_logger import logger
logger = logging.getLogger('channel_utilization.Main')
import plotly.express as px



PATH = os.path.dirname(os.path.abspath(__file__))

## TOKEN can be added to bypass login prompt
## TOKEN permission needs - device:r
XIQ_token = ''

## AP_NAME can be added to bypass device name prompt
ap_name = ''

def collectRadio(xiq, device_id, startTime, endTime, mp_queue):
    data = xiq.collectRadioInfo(device_id, startTime, endTime)
    if data:
        mp_queue.put(data)


def runDisplay(x,device_id,startTime):
    captured_data = []
    mp_queue = multiprocessing.Queue()
    processes = []
    endTime = startTime + 600000
    count = 24
    print(f"Collecting {str((endTime-startTime)/1000*count/60/60)} hours of radio data in 10 min increments... ",end='')
    while count > 0:
        p = multiprocessing.Process(target=collectRadio,args=(x, device_id, startTime, endTime, mp_queue))
        processes.append(p)
        p.start()
        startTime = startTime + 600000
        endTime = endTime + 600000
        count -= 1
    for p in processes:
        try:
            p.join()
            p.terminate()
        except:
            print("error occurred in thread")
    mp_queue.put('STOP')
    for data in iter(mp_queue.get, 'STOP'):
        captured_data = captured_data + data
    df = pd.DataFrame(captured_data) 
    df = df.sort_values(by='timestamp')
    print("Completed")
    return df
    




def main():
    global ap_name
    ## XIQ login info
    if XIQ_token:
        x = XIQ(token=XIQ_token)
    else:
        print("Enter your XIQ login credentials")
        username = input("Email: ")
        password = getpass.getpass("Password: ")
        x = XIQ(user_name=username,password = password)

    if ap_name == '':
        ap_name = input("Please enter the name of the AP you would like to check utilization for: ")
    
    try:
        device = x.collectDevices(pageSize=100, hostname=ap_name)
        validResponse = True
    except:
        logger.warning(f"Failed to get {ap_name}. Please try again.")
    # check for APs that were not found in XIQ
    if not device:
    # If missing APs were found send message to screen and log
        logger.warning(f"AP {ap_name} was not found!")
        print()
    else:
        # Get start Time from User
        valid_input = False
        while not valid_input:
            print("Please enter a Start time in the following format. '%m/%d/%y %H:%M' ")
            startTime = input("Entered Time must be greater than 4 hours ago: ")
            try:
                startTime = time.strptime(startTime,'%m/%d/%y %H:%M')
            except ValueError as e:
                print(e)
            else:
                startTime = int(time.mktime(startTime)*1000)
                ts = time.time()
                currentTime = int(ts*1000)
                validTime = currentTime-14400000 # 14400000 is 4 hours ago
                if currentTime > startTime > validTime:
                    print("The time entered is within the last 4 hours. Please enter an older time\n")
                elif startTime > currentTime:
                    print("You entered a time in the future! We can not time travel :)\n")
                else:
                    valid_input = True
        df = runDisplay(x=x,device_id=device[0]['id'],startTime=startTime)
        df['timestamp'] = df['timestamp'].map(lambda x : pd.Timestamp(x, unit='ms'))
        fig = px.line(
            df,
            x="timestamp",
            y="total_utilization",
            #y= df.columns[1:-1],
            color="interface_name",
            #markers=True,
            title=f"Total Utilization for {ap_name}",
        )
        fig.update(layout=dict(title=dict(x=0.5)))
        #fig = go.Figure(data=[go.Scatter(x=df.timestamp,y=df['total_utilization'], line=dict(color='blue'), name=)])
        fig.show()


if __name__ == '__main__':
    main()
