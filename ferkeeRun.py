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
args = parser.parse_args()

pp = pprint.PrettyPrinter(indent=4)

config = configparser.RawConfigParser()
config.read(args.properties)
ferkee_props.props = dict(config.items("Ferkee"))

pp.pprint (ferkee_props.props)

configure_logging({'LOG_FORMAT': '%(levelname)s: %(message)s'})

process = CrawlerProcess(get_project_settings())

process.crawl('ferkee', domain='ferc.gov', argNoDBMode=args.nodb)
process.start() # the script will block here until the crawling is finished


