# -*- coding: utf-8 -*-
from __future__ import print_function # Python 2/3 compatibility
from botocore.exceptions import ClientError
import boto3
import pprint
import subprocess
import os

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html

# 
# Transforms 
#
class TransformFerkeeObjects(object):

    def __init__(self):
        self.dynamodb = None;
        self.pp = pprint.PrettyPrinter(indent=4)
        self.noDBMode = False

    def open_spider(self, spider):
        if (spider.noDBMode):
            self.noDBMode = spider.noDBMode
        else:
            self.dynamodb = boto3.resource('dynamodb', endpoint_url="http://localhost:8000")

    def run_command(self, command):
        print ("Running command: %s" % command)
        p = subprocess.Popen(command,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT, shell=True)
        return p.communicate('')[0]

    #
    # Pulls out the decision PDF from the specific URL, and parses the first section to act as a description
    #
    def getDecisionText(self, url):
        print ("================ getDecisionText")
        url = url.replace('http:', 'https:')
        print ("URL=%s" % url)
        urlParts = url.split('/')
        fileName = urlParts[len(urlParts)-1]
        curlOutput = self.run_command('cd /tmp; curl -O ' + url)

        print ("Curl output: %s" % ''.join(curlOutput))

        outputFile = "/tmp/" + fileName
        print ("Output file: %s" % outputFile)

        command = 'pdf2txt.py -m 1 -t text -L 1.0 ' + outputFile
        print ("Command=%s" % command)
        pdf2text = self.run_command(command)

        pdf2text = pdf2text.split("\n")

        pdf2text = [x for x in pdf2text if x.strip()]

        text =  '\n'.join(pdf2text)
        print ("PDF TEXT: %s" % text)
        os.remove(outputFile)
        return text

    def seenIssuanceBefore(self, issuance):
        if self.noDBMode:
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
        if self.noDBMode:
            return None;

        table = self.dynamodb.Table('FIDTest')

        try:
            table.put_item (Item=issuance)
        except ClientError as e:
            print("DynamoDB Error on put_item: %s" % e.response['Error']['Message'])
            self.pp.pprint(e.response)


    def process_item(self, item, spider):
        url = item['url']
        print ("URL=%s" % url)
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
                        'Type': issuanceType,
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
                    'Type': issuanceType,
                    'description': description,
                    'urls': [decision['decisionUrl']]
                }
                if (not self.seenIssuanceBefore(issuance)):
                    issuance['description'] = self.getDecisionText(issuanceURL)
                    self.saveIssuanceToDB(issuance);
                    newIssuances.append(issuance)
        
        return {"newIssuances": newIssuances}

class ProcessNewFerkeeItems(object):
    def __init__(self):
        self.pp = pprint.PrettyPrinter(indent=4)

    def process_item(self, item, spider):
        self.pp.pprint (item)
        return item




