# -*- coding: utf-8 -*-
from __future__ import print_function # Python 2/3 compatibility
import pprint
import re
import logging

from botocore.exceptions import ClientError
import boto3

import ferkee_props as fp
import news.news as news
import issuances.issuances as issuances

import utils

#
# Tests if a pipelien item is an issuance item or not
# 
def isIssuance(item):
  return any(key in item for key in ['notices', 'delegated_orders', 'decisions'])

pp = pprint.PrettyPrinter(indent=4)

# 
# Pipeline processor to transform the crawl data into our main DB format and saves them
#
class TransformFerkeeObjects(object):

    def __init__(self):
        self.dynamodb = None
        self.newsdao = None
        self.issuancedao = None
        self.log = logging.getLogger(__name__)

    #
    # Lifecycle start
    #
    def open_spider(self, spider):
        self.newsdao = news.NewsDAO()
        self.issuancedao = issuances.IssuanceDAO()
        if (not fp.props['noDBMode']):
            self.dynamodb = boto3.resource('dynamodb', region_name='us-east-1', endpoint_url=fp.props['dynamodb_endpoint_url'])

    def seenNewDocketBefore(self, newDocket):
        if (fp.props['noDBMode']):
            return False

        return False

        try:
          pass
        except ClientError as e:
            self.log.error("DynamoDB error on seenNewDocketBefore: %s" % e.response['Error']['Message'])
            self.log.error(pp.pformat(e.response))
            self.log.error("Offending input %s" % pp.pformat(newDocket))

        if response and 'Item' in response:
            return True
        else:
            return False

    def saveNewDocketToDB(self, newDocket):
        if (fp.props['noDBMode']):
            return None


        return None
        try:
          pass
        except ClientError as e:
            self.log.error("DynamoDB Error on saveNewDocketToDB put_item: %s" % e.response['Error']['Message'])
            self.log.error(pp.pformat(e.response))
            self.log.error("Offending input %s" % pp.pformat(newDocket))

    #
    # Scrapy Pipeline entry
    # 
    def process_item(self, item, spider):
        if isIssuance(item):
            return self.issuancedao.processIssuances(item, spider)
        elif ('newsItems' in item):
            return self.newsdao.processNews(item, spider)
        elif 'newDockets' in item:
            return self.processNewDockets(item, spider)
        else:
            self.log.warn ("Unknown pipeline item %s" % (item))

    #
    # Process new FERC dockets
    # 
    def processNewDockets(self, item, spider):
        unseenNewDockets = []
        for newDocket in item['newDockets']:
          if (not self.seenNewDocketBefore(newDocket)):
            self.saveNewDocketToDB(newDocket)
            unseenNewDockets.append(newDocket)
        return {"newDockets": unseenNewDockets}


#
# Filter out items that don't match the docket filter
# 
class FilterFerkeeItems(object):

    #
    # Scrapy pipeline entry
    #
    def process_item(self, item, spider):
        if isIssuance(item):
          issuancesArray = []
          for issuance in item['newIssuances']:
              docket = issuance['docket']
              if re.match(fp.props['decision_pattern'], docket, re.M|re.I):
                  issuancesArray.append(issuance)
          return {"newIssuances": issuancesArray}
        else:
          return item

#
# Processes all new issuances we haven't seen and sends alerts on them
#
class ProcessNewFerkeeItems(object):

    #
    # Scrapy pipeline entry
    #
    def process_item(self, item, spider):
        decisionAlertItems = []
        otherAlertItems = []

        if 'newIssuances' in item:
          print ("Alerting on %s issuances" % (len(item['newIssuances'])))
          for issuance in item['newIssuances']:
              if (issuance['type'] == 'Decision'):
                  if (len(decisionAlertItems) == 0):
                      decisionAlertItems.append("Daily Decision Issuance for %s, URL: %s" % (issuance['announceDate'], issuance['announceURL']))
                  urls = issuance['urls'][0]
                  url = urls['url']
                  alertHeader = "***************  New Certificate Pipeline Decision: %s: %s" % (issuance['docket'], url)
                  print (alertHeader)
                  alertText = "%s\n%s" % (alertHeader, issuance['description'])
                  decisionAlertItems.append(alertText)

              if (issuance['type'] in ['Notice', 'DelegatedOrder']):
                  if (len(otherAlertItems) == 0):
                      otherAlertItems.append("Daily %s Issuance for %s, URL: %s" % (issuance['announceDate'], issuance['type'], issuance['announceURL']))
                  urls = issuance['urls']
                  urlText = ""
                  for url in urls:
                      urlText = urlText + "\n\t%s: %s" % (url['type'], url['url'])
                  alertText = "*************** FERC %s alert on docket %s\n%s%s" % (issuance['type'], issuance['docket'], issuance['description'], urlText)
                  print (alertText)
                  otherAlertItems.append(alertText)
                  
          if (len(decisionAlertItems) > 0):
              utils.send_alert(fp.props['to'], "Ferkee Alert! Certificate Pipeline Decision(s) Published for %s" % (issuance['announceDate']), '\n\n'.join (decisionAlertItems))
          if (len(otherAlertItems) > 0):
              utils.send_alert(fp.props['noticeto'], "Ferkee Alert! FERC %s(s) Published for %s" % (issuance['type'], issuance['announceDate']), '\n\n'.join (otherAlertItems))
        elif 'newsItems' in item:
          newsAlertItems = []
          print ("Alerting on %s news items" % (len(item['newsItems'])))
          for news in item['newsItems']:
              alertHeader = "***************  %s %s" % (news['issuanceDate'], news['description'])
              urls = news['urls']
              urlText = ""
              for url in urls:
                  urlText = urlText + "\n\t%s: %s" % (url['text'], url['url'])
          
              alertText = "%s%s" % (alertHeader, urlText)
              print (alertText)
              newsAlertItems.append(alertText)
          if (len(newsAlertItems) > 0):
              utils.send_alert(fp.props['noticeto'], "Ferkee Alert! FERC News published to site", '\n\n'.join (newsAlertItems))
        else:
          print ("WARNING: No alerts found in %s" % item.keys())

        return item

