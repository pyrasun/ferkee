# -*- coding: utf-8 -*-
from __future__ import print_function # Python 2/3 compatibility
from botocore.exceptions import ClientError
import boto3
import pprint


# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html


class FerkeePipeline(object):

    def __init__(self):
        self.dynamodb = None;
        self.pp = pprint.PrettyPrinter(indent=4)


    def open_spider(self, spider):
        self.dynamodb = boto3.resource('dynamodb', endpoint_url="http://localhost:8000")


    def saveIssuanceToDB(self, issuance):
        table = self.dynamodb.Table('FIDTest')
        self.pp.pprint(issuance)

        response = None

        doPut = False

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
            print("GetItem succeeded, skipping add")
        else:
            doPut = True

        if doPut:
            print ("Item does not exist, adding to DynamoDB")
            try:
                table.put_item (Item=issuance)
            except ClientError as e:
                print("DynamoDB Error on put_item: %s" % e.response['Error']['Message'])
                self.pp.pprint(e.response)

        print("Done")



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
                        'Description': description,
                        'urls': urls
                    }
                    self.saveIssuanceToDB(issuance)
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
                    'Description': description,
                    'urls': [decision['decisionUrl']]
                }
                self.saveIssuanceToDB(issuance)
        
        return item


