import sys
import pprint
import ConfigParser as configparser



from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from scrapy.utils.log import configure_logging

pp = pprint.PrettyPrinter(indent=4)

config = configparser.RawConfigParser()
config.read(sys.argv[1])
properties = dict(config.items("Ferkee"))

pp.pprint (properties)

configure_logging({'LOG_FORMAT': '%(levelname)s: %(message)s'})

process = CrawlerProcess(get_project_settings())

# 'followall' is the name of one of the spiders of the project.
process.crawl('ferkee', domain='ferc.gov', argNoDBMode=True)
process.start() # the script will block here until the crawling is finished


