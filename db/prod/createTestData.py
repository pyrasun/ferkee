from __future__ import print_function # Python 2/3 compatibility
import boto3
import dbenv

notice = {
  'publishType':'Notice',
  'docket': 'CP15-558-000',
  'announceURL': 'http://elibrary.ferc.gov/idmws/search/eSaveAdv.asp?cat=issuance&fdt=on&fd=12/29/2017&td=12/29/2017&tdd=12/29/2017&typ=Notice,%20999,%20999,%20999&',
  'announceDate': '05/01/2017',
  'published': {
    'description':'Notice of Request under Blanket Authorization re Equitrans, L.P. under CP18-32.',
    'urls': [
      {
        'type':'Word',
        'url':'https://elibrary.ferc.gov/idmws/common/opennat.asp?fileID=14785945'
      },
      {
        'type':'FERC Generated PDF',
        'url':'https://elibrary.ferc.gov/idmws/common/opennat.asp?fileID=14786066'

      }
    ]
  }
}
dynamodb = boto3.resource('dynamodb', endpoint_url=dbenv.endpoint)

table = dynamodb.Table('FERCIssuance')

table.put_item (Item=notice)

