"""
This config file extends the test environment configuration
so that we can run the lettuce acceptance tests on SauceLabs.
"""

# We intentionally define lots of variables that aren't used, and
# want to import all variables from base settings files
# pylint: disable=W0401, W0614

from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
import os

PORTS = [2000, 2001, 2020, 2109, 2222, 2310, 3000, 3001,
        3030, 3210, 3333, 4000, 4001, 4040, 4321, 4502, 4503,
        5050, 5555, 5432, 6060, 6666, 6543, 7000, 7070, 7774,
        7777, 8003, 8031, 8080, 8081, 8765, 8888,
        9080, 9090, 9876, 9999, 49221, 55001]

DESIRED_CAPABILITIES = {
    'chrome': DesiredCapabilities.CHROME,
    'internet explorer': DesiredCapabilities.INTERNETEXPLORER,
    'firefox': DesiredCapabilities.FIREFOX,
    'opera': DesiredCapabilities.OPERA,
    'iphone': DesiredCapabilities.IPHONE,
    'ipad': DesiredCapabilities.IPAD,
    'safari': DesiredCapabilities.SAFARI,
    'android': DesiredCapabilities.ANDROID
}

PLATFORMS = ['Linux', 'OS X 10.8', 'OS X 10.6', 'Windows 8', 'Windows 7', 'Windows XP']

#HACK
#This needs to be done because Jenkins needs to satisfy URLs, JSON, BASH, SAUCE, and PYTHON
#This is the simplest way to adhere to all of these requirements and still be readable
DEFAULT_CONFIG = 'Linux-chrome--'

SAUCE_INFO = os.environ.get('SAUCE_INFO', DEFAULT_CONFIG).split('-')
if len(SAUCE_INFO) != 4:
    SAUCE_INFO = DEFAULT_CONFIG.split('-')

# Information needed to utilize Sauce Labs.
SAUCE = {
    'SAUCE_ENABLED': os.environ.get('SAUCE_ENABLED'),
    'USERNAME': os.environ.get('SAUCE_USER_NAME'),
    'ACCESS_ID': os.environ.get('SAUCE_API_KEY'),
    'PLATFORM': SAUCE_INFO[0] if SAUCE_INFO[0] in PLATFORMS else 'Linux',
    'BROWSER': DESIRED_CAPABILITIES.get(SAUCE_INFO[1].lower(), DesiredCapabilities.CHROME),
    'VERSION': SAUCE_INFO[2],
    'DEVICE': SAUCE_INFO[3],
    'SESSION': 'Jenkins Acceptance Tests',
    'BUILD': os.environ.get('BUILD_DISPLAY_NAME', 'LETTUCE TESTS'),
}
