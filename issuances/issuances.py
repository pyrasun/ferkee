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

class IssuanceDAO:

    def __init__(self):
        self.dynamodb = None;
        self.log = logging.getLogger(__name__)
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

