from __future__ import print_function # Python 2/3 compatibility
import boto3

import dbenv

dynamodb = boto3.resource('dynamodb', region_name='us-east-1', endpoint_url=dbenv.endpoint)

table = dynamodb.Table('FERCIssuance')
table.delete()

