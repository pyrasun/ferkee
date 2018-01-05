
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from scrapy.utils.log import configure_logging

configure_logging({'LOG_FORMAT': '%(levelname)s: %(message)s'})

process = CrawlerProcess(get_project_settings())

# 'followall' is the name of one of the spiders of the project.
process.crawl('ferkee', domain='ferc.gov', argNoDBMode=True)
process.start() # the script will block here until the crawling is finished


