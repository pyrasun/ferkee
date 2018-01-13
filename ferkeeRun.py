import sys
import pprint
import ConfigParser as configparser
import argparse

import ferkee_props

from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from scrapy.utils.log import configure_logging

parser = argparse.ArgumentParser()
parser.add_argument("-p", "--properties", help="Path to ferkee properties file", action="store")
parser.add_argument("--nodb", action="store_true")
parser.add_argument("--noemail", action="store_true")
args = parser.parse_args()

config = configparser.RawConfigParser()
config.read(args.properties)
ferkee_props.props = dict(config.items("Ferkee"))
ferkee_props.props['noDBMode'] = args.nodb
ferkee_props.props['noEmail'] = args.noemail

configure_logging({'LOG_FORMAT': '%(levelname)s: %(message)s'})

process = CrawlerProcess(get_project_settings())

ferkee_props.dump_props()

process.crawl('ferkee', domain='ferc.gov')
process.start() # the script will block here until the crawling is finished

