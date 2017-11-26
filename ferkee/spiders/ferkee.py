import scrapy
import re

class FercNotionalSpider(scrapy.Spider):
    name = "ferkee"

    # Normal operation - scrape the ferc.gov page and find the most recent notional decision URL, and scrape that
    def start_requests(self):
      urls = [
          'http://www.ferc.gov'
      ]
      for url in urls:
        yield scrapy.Request(url=url, callback=self.parseFrontPage)

    # For testing - hit one known multi decision page
    # def start_requests(self):
    #     urls = [
    #         'https://www.ferc.gov/EventCalendar/EventDetails.aspx?ID=9849&CalType=%20&CalendarID=101&Date=11/22/2017&View=Listview'
    #     ]
    #     for url in urls:
    #         yield scrapy.Request(url=url, callback=self.parseNotationals)

    # Search FERC front page looking for events like this below:
    # '/EventCalendar/EventDetails.aspx?ID=9840&CalType=%20&CalendarID=101&Date=11/20/2017&View=Listview'
    # When found, fire off a crawler to parse that
    def parseFrontPage(self, response):
      ordersPages = response.xpath('//a[contains(@href, "&CalendarID=101&")]') 
      notFound = True
      for index, link in enumerate(ordersPages):
        orderPageHref = link.xpath('@href').extract()[0];
        if (orderPageHref.startswith("/EventCalendar") and notFound): 
          notFound = False
          print response.urljoin(orderPageHref);
          yield scrapy.Request(response.urljoin(orderPageHref), callback=self.parseNotationals)

    # Parse a FERC notional order page, looking for Certificate Pipeline (CP) decisions
    def parseNotationals(self, response):
        myUrl = response.request.url
        result = {}
        result['url'] = myUrl;
        result['decisions'] = []
        dockets = response.css("#LabelSummary::text").extract_first()
        if (dockets):
          m = re.match(r'Docket Nos?.:? (.*)$', dockets, re.M|re.I)
          dockets = m.group(1)
          dockets = dockets.split(";")
          for docket in dockets: 
            docket = docket.strip()
            urlRE = 'http://www.ferc.gov/CalendarFiles/[0-9]*-' + docket + '[0-9]*.pdf'
            decisionURL = response.xpath('//a[contains(@href, "pdf")]').re(urlRE)
            decision = {'docket': docket, 'decisionUrl':decisionURL[0]}
            result['decisions'].append(decision)
            print ("%s;%s" % (docket, decisionURL[0]))
          return result

