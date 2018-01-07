import scrapy
import re

class FercNotionalSpider(scrapy.Spider):
    name = "ferkee"

    def __init__(self, *args, **kwargs):
        super(FercNotionalSpider, self).__init__(*args, **kwargs)

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
      for index, link in enumerate(ordersPages):
        orderPageHref = link.xpath('@href').extract()[0];
        if (orderPageHref.startswith("/EventCalendar")): 
          # print response.urljoin(orderPageHref);
          yield scrapy.Request(response.urljoin(orderPageHref), callback=self.parseNotationals)

      noticePages = response.xpath('//a[contains(@href, "&typ=Notice")]') 
      for index, link in enumerate(noticePages):
        noticePageHref = link.xpath('@href').extract()[0];
        # print response.urljoin(noticePageHref);
        noticeRequest= scrapy.Request(response.urljoin(noticePageHref), callback=self.parseSavedSearch)
        noticeRequest.meta['issuanceType'] = 'notices'
        yield noticeRequest

      delegatedOrderPages = response.xpath('//a[contains(@href, "&typ=Delegated")]') 
      for index, link in enumerate(delegatedOrderPages):
        delegatedOrderPageHref = link.xpath('@href').extract()[0];
        # print response.urljoin(delegatedOrderPageHref);
        delegatedOrderRequest = scrapy.Request(response.urljoin(delegatedOrderPageHref), callback=self.parseSavedSearch)
        delegatedOrderRequest.meta['issuanceType'] = 'delegated_orders'
        yield delegatedOrderRequest

    # Parse a FERC notional order page, looking for all notional decisions
    def parseNotationals(self, response):
        myUrl = response.request.url
        # print ("Crawling %s" % (myUrl))
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
            if (len(decisionURL) > 0):
              decision = {'docket': docket, 'decisionUrl':decisionURL[0]}
              result['decisions'].append(decision)
              # print ("%s;%s" % (docket, decisionURL[0]))
            else:
              decision = {'docket': docket, 'decisionUrl':''}
              result['decisions'].append(decision)
              # print ("No URL found for %s" % docket);
          return result

    # Parse a saved search result, this is basically a pre-filled form that we have to manually submit
    # (on the browser the submit is done via JavaScript onload())
    def parseSavedSearch(self, response):
        request = scrapy.http.FormRequest.from_response(response, callback=self.parseSavedSearchResult)
        request.meta['originalURL'] = response.request.url;
        request.meta['issuanceType'] = response.request.meta['issuanceType']
        return [request]
    
    # Parse a FERC saved search
    def parseSavedSearchResult(self, response):
        issuanceType = response.meta['issuanceType']
        # print ("\n\n*****************************************");
        # print ("parseSavedSearchResults %s: Response %s" % (issuanceType, response));
        result = {}
        result['url'] = response.meta['originalURL']
        result[issuanceType] = []
        row = 0
        for tr in response.xpath('//tr'):
            dockets = ' '.join (tr.xpath('td[3]/text()').extract())
            dockets = dockets.lstrip().rstrip()
            description = ' '.join (tr.xpath('td[4]/text()').extract())
            description = description.lstrip().rstrip()
            URLs = tr.xpath('td[6]/table/tr/td/a')
            urlArray = []
            for url in URLs:
                urlData = {}
                href = url.xpath("@href").extract_first()
                href = response.urljoin(href)
                urlText = url.xpath("text()").extract_first()
                urlData['url'] = href;
                urlData['type'] = urlText;
                urlArray.append(urlData)

            if (dockets and description and dockets.startswith("CP")):
              # print ("Row %s: dockets: %s, description: %s, URLs: %s" % (row, dockets, description, URLs))
              issuance = {'dockets': dockets, 'urls':urlArray, 'description':description}
              result[issuanceType].append(issuance)
            row = row + 1

        return result

