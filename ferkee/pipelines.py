# -*- coding: utf-8 -*-

import pprint

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html


class FerkeePipeline(object):
    def process_item(self, item, spider):
        print "\n\n\n=============================\n"
        pp = pprint.PrettyPrinter(indent=4)
        pp.pprint(item)
        print "\n=============================\n\n\n"
        
        return item

