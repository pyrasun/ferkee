import logging
from botocore.exceptions import ClientError
import boto3

import ferkee_props as fp


class NewsDAO:
    def __init__(self):
        self.dynamodb = None;
        self.log = logging.getLogger(__name__)
        if (not fp.props['noDBMode']):
            self.dynamodb = boto3.resource('dynamodb', region_name='us-east-1', endpoint_url=fp.props['dynamodb_endpoint_url'])

    #
    # Returns True if we've seen this news item already
    #
    def seenNewsBefore(self, news):
        if (fp.props['noDBMode']):
            return False;
        table = self.dynamodb.Table(fp.props['news_table'])
        response = None
        try:
            response = table.get_item(
                Key={
                    'description': news['description'],
                    'issuanceDate': news['issuanceDate'],
                }
            )
        except ClientError as e:
            self.log.error("DynamoDB error on seenNewsBefore: %s" % e.response['Error']['Message'])
            self.log.error(pp.pformat(e.response))
            self.log.error("Offending input %s" % pp.pformat(news))

        if response and 'Item' in response:
            return True
        else:
            return False

    #
    # Saves news item to the DB
    #
    def saveNewsToDB(self, news):
        if (fp.props['noDBMode']):
            return None;

        table = self.dynamodb.Table(fp.props['news_table'])

        try:
            table.put_item (Item=news)
        except ClientError as e:
            self.log.error("DynamoDB Error on saveNewsToDB put_item: %s" % e.response['Error']['Message'])
            self.log.error(pp.pformat(e.response))
            self.log.error("Offending input %s" % pp.pformat(news))


    #
    # Process News items
    # 
    def processNews(self, item, spider):
        newNews = []
        self.log.info("Processing %s news items" % len (item['newsItems']))
        for newsItem in item['newsItems']:
          self.log.info ("News Item: %s '%s'.  Links: %s" % (newsItem['issuanceDate'], newsItem['description'], newsItem['urls']))
          description = newsItem['description']
          if description is None or len(description) == 0:
            self.log.warn("News item has empty description, skipping")
          elif (not self.seenNewsBefore(newsItem)):
            self.saveNewsToDB(newsItem)
            newNews.append(newsItem)
        return {'newsItems':newNews}


