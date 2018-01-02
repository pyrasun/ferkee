# -*- coding: utf-8 -*-
from __future__ import print_function # Python 2/3 compatibility
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


    def print_issuance(self, issuanceType, issuanceURL, docket, description):
        print ("Issuance: %s %s %s %s" % (issuanceType, docket, issuanceURL, description))


    def process_item(self, item, spider):
        url = item['url']
        print ("URL=%s" % url)
        items = []
        issuanceType = ''
        savedSearch = False
        if ('notices' in item):
            items = item['notices']
            issuanceType = 'notice'
            savedSearch = True

        if ('delegated_orders' in item):
            items = item['delegated_orders']
            issuanceType = 'delegated_order'
            savedSearch = True

        if (savedSearch):
            for issuance in items:
                dockets = issuance['dockets'].split(' ')
                description = issuance['description']
                urls = issuance['urls']
                for docket in dockets:
                    self.print_issuance(issuanceType, urls, docket, description)


        if ('decisions' in item):
            issuanceType = 'decision'
            decisions = item['decisions']
            for decision in decisions:
                issuanceURL = decision['decisionUrl']
                docket = decision['docket']
                description = "TBD"
                self.print_issuance(issuanceType, issuanceURL, docket, description)
        

        return item


