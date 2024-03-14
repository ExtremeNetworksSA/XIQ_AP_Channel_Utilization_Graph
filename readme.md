# XIQ AP Channel Utilization
### XIQ_channel_utilization.py
## Purpose
This script will collect the last 30 minutes of Total Utilization for the AP entered when prompted. This information will be displayed on a graph for each wifi interface.

## Information
### Authentication
The script will prompt for you XIQ credentials. 
>You can also manually enter an API token on line 22.
### Collecting the device
The script will prompt for the name of the device after authentication with XIQ is preformed.
>You can also manually enter the name of the device on line 25.

## Needed Files
This script uses other files. If these files are missing the script will not function. 
In the same folder as the script, there should be an /app/ folder. Inside of this folder there should be a xiq_logger.py file and a xiq_api.py file.

## Running the script
open the terminal to the location of the script and run this command.
```
python XIQ_channel_utilization.py
```

## requirements
There are additional modules that need to be installed in order for this script to function. They are listed in the requirements.txt file and can be installed with the command 'pip install -r requirements.txt' if using pip.