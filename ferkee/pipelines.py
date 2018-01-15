# -*- coding: utf-8 -*-
from __future__ import print_function # Python 2/3 compatibility
import pprint
import subprocess
import os
import re
import logging

from botocore.exceptions import ClientError
import boto3

import ferkee_props as fp
import news.news as news

#
# Run a generic command through the shell
#
def run_command(command, toSend=None):
    # print ("Running command: %s" % command)
    p = subprocess.Popen(command,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, shell=True)
    return p.communicate(toSend)[0]

#
# Send an email alert
# 
def send_alert(to, subject, alert):
    alert = alert.replace("'", "")
    if fp.props['noEmail']:
        return None
    sendEmailOutput = run_command ("sendEmail -f '%s' -t %s -u '%s' -s smtp.gmail.com:587 -xu '%s' -xp '%s' -m '%s'" % (fp.props['from'], to, subject, fp.props['from'], fp.props['from_p'], alert))
    print ("sendEmail Result: %s" % sendEmailOutput)

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
        self.log = logging.getLogger(__name__)

    #
    # Lifecycle start
    #
    def open_spider(self, spider):
        self.newsdao = news.NewsDAO()
        if (not fp.props['noDBMode']):
            self.dynamodb = boto3.resource('dynamodb', region_name='us-east-1', endpoint_url=fp.props['dynamodb_endpoint_url'])

    #
    # Pulls out the decision PDF from the specific URL, and parses the first section to act as a description
    #
    def getDecisionText(self, url):
        url = url.replace('http:', 'https:')
        urlParts = url.split('/')
        fileName = urlParts[len(urlParts)-1]
        curlOutput = run_command('cd /tmp; curl -O ' + url)

        outputFile = "/tmp/" + fileName

        command = 'pdf2txt.py -m 1 -t text -L 1.0 ' + outputFile
        pdf2text = run_command(command)
        pdf2text = pdf2text.decode("utf8")

        pdf2text = pdf2text.split("\n")

        pdf2text = [x for x in pdf2text if x.strip()]

        text =  '\n'.join(pdf2text)
        os.remove(outputFile)
        return text

    def seenIssuanceBefore(self, issuance):
        if (fp.props['noDBMode']):
            return False

        table = self.dynamodb.Table(fp.props['issuance_table'])
        try:
            response = table.get_item(
                Key={
                    'docket': issuance['docket'],
                    'announceURL': issuance['announceURL']
                }
            )
        except ClientError as e:
            self.log.error("DynamoDB error on seenIssuanceBefore: %s" % e.response['Error']['Message'])
            self.log.error(pp.pformat(e.response))
            self.log.error("Offending input %s" % pp.pformat(issuance))

        if response and 'Item' in response:
            return True
        else:
            return False


    def saveIssuanceToDB(self, issuance):
        if (fp.props['noDBMode']):
            return None

        table = self.dynamodb.Table(fp.props['issuance_table'])

        try:
            table.put_item (Item=issuance)
        except ClientError as e:
            self.log.error("DynamoDB Error on saveIssuanceToDB put_item: %s" % e.response['Error']['Message'])
            self.log.error(pp.pformat(e.response))
            self.log.error("Offending input %s" % pp.pformat(issuance))


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
            return self.processIssuances(item, spider)
        elif ('newsItems' in item):
            return self.processNews(item, spider)
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
    # Process News items
    # 
    def processNews(self, item, spider):
        newNews = []
        self.log.info("Processing %s news items" % len (item['newsItems']))
        for newsItem in item['newsItems']:
          self.log.info ("News Item: %s '%s'.  Links: %s" % (newsItem['issuanceDate'], newsItem['description'], newsItem['urls']))
          if (not self.newsdao.seenNewsBefore(newsItem)):
            self.newsdao.saveNewsToDB(newsItem)
            newNews.append(newsItem)
        return {'newsItems':newNews}

    #
    # Process all issuances
    # 
    def processIssuances(self, item, spider):
        url = ''
        if 'url' in item:
          url = item['url']
        items = []
        issuanceType = ''
        savedSearch = False
        if ('notices' in item):
            items = item['notices']
            issuanceType = 'Notice'
            savedSearch = True

        if ('delegated_orders' in item):
            items = item['delegated_orders']
            issuanceType = 'DelegatedOrder'
            savedSearch = True

        newIssuances = []

        if (savedSearch):
            matchObj = re.search( r'tdd=(\d\d/\d\d/\d\d\d\d)', url, re.M|re.I)
            issueDate = "Unknown"
            if (matchObj):
                issueDate = matchObj.group(1)
            for item in items:
                dockets = item['dockets'].split(' ')
                description = item['description']
                urls = item['urls']
                for docket in dockets:
                    issuance = {
                        'docket': docket,
                        'announceURL': url,
                        'announceDate': issueDate,
                        'type': issuanceType,
                        'description': description,
                        'urls': urls
                    }
                    if (not self.seenIssuanceBefore(issuance)):
                        self.saveIssuanceToDB(issuance)
                        newIssuances.append(issuance)
                        # pp.pprint(issuance)
        elif ('decisions' in item):
            matchObj = re.search( r'Date=(\d\d/\d\d/\d\d\d\d)', url, re.M|re.I)
            issueDate = "Unknown"
            if (matchObj):
                issueDate = matchObj.group(1)
            issuanceType = 'Decision'
            decisions = item['decisions']
            for decision in decisions:
                issuanceURL = decision['decisionUrl']
                docket = decision['docket']
                description = "TBD"
                if (not issuanceURL or len(issuanceURL.strip()) == 0):
                  issuanceURL = None
                  decision['decisionUrl'] = 'None'

                issuance = {
                    'docket': docket,
                    'announceURL': url,
                    'announceDate': issueDate,
                    'type': issuanceType,
                    'description': description,
                    'urls': [{'url':decision['decisionUrl'], 'type':'PDF'}]
                }
                if (not self.seenIssuanceBefore(issuance)):
                    if (issuanceURL):
                      issuance['description'] = self.getDecisionText(issuanceURL)
                    else:
                      issuance['description'] = "[Description not available]"
                    self.saveIssuanceToDB(issuance)
                    # pp.pprint(issuance)
                    newIssuances.append(issuance)
        return {"newIssuances": newIssuances}
#
# Filter out items that don't match the docket filter
# 
class FilterFerkeeItems(object):

    #
    # Scrapy pipeline entry
    #
    def process_item(self, item, spider):
        if isIssuance(item):
          issuances = []
          for issuance in item['newIssuances']:
              docket = issuance['docket']
              if re.match(fp.props['decision_pattern'], docket, re.M|re.I):
                  issuances.append(issuance)
          return {"newIssuances": issuances}
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
              send_alert(fp.props['to'], "Ferkee Alert! Certificate Pipeline Decision(s) Published for %s" % (issuance['announceDate']), '\n\n'.join (decisionAlertItems))
          if (len(otherAlertItems) > 0):
              send_alert(fp.props['noticeto'], "Ferkee Alert! FERC %s(s) Published for %s" % (issuance['type'], issuance['announceDate']), '\n\n'.join (otherAlertItems))
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
              send_alert(fp.props['noticeto'], "Ferkee Alert! FERC News published to site", '\n\n'.join (newsAlertItems))
        else:
          print ("WARNING: No alerts found in %s" % item.keys())

        return item

