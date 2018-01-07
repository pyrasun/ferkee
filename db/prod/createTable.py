from __future__ import print_function # Python 2/3 compatibility
import boto3
import dbenv

dynamodb = boto3.resource('dynamodb', region_name='us-east-1', endpoint_url=dbenv.endpoint)

table = dynamodb.create_table(
    TableName='FERCIssuance',
    KeySchema=[
        {
            'AttributeName': 'docket',
            'KeyType': 'HASH'  #Partition key
        },
        {
            'AttributeName': 'announceURL',
            'KeyType': 'RANGE'  #Sort key
        }
    ],
    AttributeDefinitions=[
        {
            'AttributeName': 'docket',
            'AttributeType': 'S'
        },
        {
            'AttributeName': 'announceURL',
            'AttributeType': 'S'
        },

    ],
    ProvisionedThroughput={
        'ReadCapacityUnits': 10,
        'WriteCapacityUnits': 10
    }
)
print("Table status:", table.table_status)

