# -*- coding: utf-8 -*-
from __future__ import print_function # Python 2/3 compatibility
from botocore.exceptions import ClientError
import boto3
import pprint
import subprocess
import os
import ferkee_props

#
# Run a generic command through the shell
#
def run_command(command, toSend=None):
    print ("Running command: %s" % command)
    p = subprocess.Popen(command,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, shell=True)
    return p.communicate(toSend)[0]

def send_alert(to, subject, alert):
    alert = alert.replace("'", "")
    print ("Email alert=%s" % alert)
    if ferkee_props.props['noEmail']:
        return None
    sendEmailOutput = run_command ("sendEmail -f '%s' -t '%s' -u '%s' -s smtp.gmail.com:587 -xu '%s' -xp '%s' -m '%s'" % (ferkee_props.props['from'], to, subject, ferkee_props.props['from'], ferkee_props.props['from_p'], alert))
    print ("sendEmail Result: %s" % sendEmailOutput)

# 
# Transforms the crawl data into our main DB format and saves them
#
class TransformFerkeeObjects(object):

    def __init__(self):
        self.dynamodb = None;
        self.pp = pprint.PrettyPrinter(indent=4)

    def open_spider(self, spider):
        if (not ferkee_props.props['noDBMode']):
            self.dynamodb = boto3.resource('dynamodb', endpoint_url="http://localhost:8000")

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
        if (ferkee_props.props['noDBMode']):
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
        if (ferkee_props.props['noDBMode']):
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
            for item in items:
                dockets = item['dockets'].split(' ')
                description = item['description']
                urls = item['urls']
                for docket in dockets:
                    issuance = {
                        'docket': docket,
                        'announceURL': url,
                        'type': issuanceType,
                        'description': description,
                        'urls': urls
                    }
                    if (not self.seenIssuanceBefore(issuance)):
                        self.saveIssuanceToDB(issuance)
                        newIssuances.append(issuance)
        elif ('decisions' in item):
            issuanceType = 'Decision'
            decisions = item['decisions']
            for decision in decisions:
                issuanceURL = decision['decisionUrl']
                docket = decision['docket']
                description = "TBD"
                issuance = {
                    'docket': docket,
                    'announceURL': url,
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
                    decisionAlertItems.append("Daily Decision Issuance URL: %s\n\n" % (issuance['announceURL']))
                urls = issuance['urls'][0]
                url = urls['url']
                alertText = "***************  New Certificate Pipeline Decision: %s: %s\n%s" % (issuance['docket'], url, issuance['description'])
                decisionAlertItems.append(alertText)

            if (issuance['type'] in ['Notice', 'DelegatedOrder']):
                if (len(otherAlertItems) == 0):
                    otherAlertItems.append("Daily %s Issuance URL: %s\n\n" % (issuance['type'], issuance['announceURL']))
                urls = issuance['urls']
                urlText = ""
                for url in urls:
                    urlText = urlText + "\n\t%s, Link: %s" % (url['type'], url['url'])
                alertText = "*************** FERC %s alert on docket %s\n%s%s" % (issuance['type'], issuance['docket'], issuance['description'], urlText)
                otherAlertItems.append(alertText)
                
        if (len(decisionAlertItems) > 0):
            send_alert(ferkee_props.props['to'], 'Ferkee Alert! Certificate Pipeline Decision(s) Published', '\n\n'.join (decisionAlertItems))
        if (len(otherAlertItems) > 0):
            send_alert(ferkee_props.props['noticeto'], 'Ferkee Alert! FERC Notices and/or Delegated Orders Published', '\n\n'.join (otherAlertItems))
        return item


