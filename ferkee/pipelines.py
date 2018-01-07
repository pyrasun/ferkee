# -*- coding: utf-8 -*-
from __future__ import print_function # Python 2/3 compatibility
import pprint
import subprocess
import os
import re

from botocore.exceptions import ClientError
import boto3

import ferkee_props as fp

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
    # print ("Email alert=%s" % alert)
    if fp.props['noEmail']:
        return None
    sendEmailOutput = run_command ("sendEmail -f '%s' -t '%s' -u '%s' -s smtp.gmail.com:587 -xu '%s' -xp '%s' -m '%s'" % (fp.props['from'], to, subject, fp.props['from'], fp.props['from_p'], alert))
    print ("sendEmail Result: %s" % sendEmailOutput)

# 
# Transforms the crawl data into our main DB format and saves them
#
class TransformFerkeeObjects(object):

    def __init__(self):
        self.dynamodb = None;
        self.pp = pprint.PrettyPrinter(indent=4)

    def open_spider(self, spider):
        if (not fp.props['noDBMode']):
            self.dynamodb = boto3.resource('dynamodb', endpoint_url=fp.props['dynamodb_endpoint_url'])

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
            return False;

        table = self.dynamodb.Table('FIDTest')
        try:
            response = table.get_item(
                Key={
                    'docket': issuance['docket'],
                    'announceURL': issuance['announceURL']
                }
            )
        except ClientError as e:
            print("DynamoDB error on get_itemn: %s" % e.response['Error']['Message'])

        if response and 'Item' in response:
            return True
        else:
            return False


    def saveIssuanceToDB(self, issuance):
        if (fp.props['noDBMode']):
            return None;

        table = self.dynamodb.Table('FIDTest')

        try:
            table.put_item (Item=issuance)
        except ClientError as e:
            print("DynamoDB Error on put_item: %s" % e.response['Error']['Message'])
            self.pp.pprint(e.response)


    def process_item(self, item, spider):
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
                issuance = {
                    'docket': docket,
                    'announceURL': url,
                    'announceDate': issueDate,
                    'type': issuanceType,
                    'description': description,
                    'urls': [{'url':decision['decisionUrl'], 'type':'PDF'}]
                }
                if (not self.seenIssuanceBefore(issuance)):
                    issuance['description'] = self.getDecisionText(issuanceURL)
                    self.saveIssuanceToDB(issuance);
                    newIssuances.append(issuance)
        
        return {"newIssuances": newIssuances}

#
# Filter out items that don't match the docket filter
# 
class FilterFerkeeItems(object):

    def process_item(self, item, spider):
        issuances = []
        for issuance in item['newIssuances']:
            docket = issuance['docket']
            if re.match(fp.props['decision_pattern'], docket, re.M|re.I):
                print ("Docket %s matches pattern %s, accepting" % (docket, fp.props['decision_pattern']))
                issuances.append(issuance)
            else:
                print ("Docket %s does not match pattern %s, filtering" % (docket, fp.props['decision_pattern']))
        return {"newIssuances": issuances}


#
# Processes all new issuances we haven't seen and sends alerts on them
#
class ProcessNewFerkeeItems(object):
    def __init__(self):
        self.pp = pprint.PrettyPrinter(indent=4)

    def process_item(self, item, spider):
        decisionAlertItems = []
        otherAlertItems = []

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
        return item


