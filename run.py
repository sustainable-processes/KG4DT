import os
from sys import exit

from app.config import config_dict
from app import create_app

DEBUG = (os.getenv('FLASK_DEBUG', 'False') == 'True')
config_mode = 'Debug' if DEBUG else 'Production'

try:
    app_config = config_dict[config_mode]
except KeyError:
    exit("Error: Invalid \"FLASK_DEBUG\" in environment variables. Expected values [Debug, Production]")

app = create_app(app_config)
    
app.logger.info('DEBUG = ' + str(DEBUG))

if __name__ == "__main__":
    app.run()
