# Automated AMI Backups
#
# This script will search for all instances having a tag with the name "backup"
# and value "Backup" on it. As soon as we have the instances list, we loop
# through each instance
# and create an AMI of it. Also, it will look for a "Retention" tag key which
# will be used as a retention policy number in days. If there is no tag with
# that name, it will use a 7 days default value for each AMI.
#
# After creating the AMI it creates a "DeleteOn" tag on the AMI indicating when
# it will be deleted using the Retention value and another Lambda function

import boto3
import collections
import datetime
import sys
import pprint

ec = boto3.client('ec2')
#image = ec.Image('id')

def format_tags(tags):
    list_tags = []
    for tag in tags:
        new_dict = {}
        new_dict[tag['Key']] = tag['Value']
        list_tags.append(new_dict)
    return list_tags

def lambda_handler(event, context):

    reservations = ec.describe_instances(Filters=[
        {
            'Name': 'tag:Backup',
            'Values': ['Daily']
        },
    ]).get('Reservations', [])

    instances = sum([[i for i in r['Instances']] for r in reservations], [])

    print("Found %d instances that need backing up" % len(instances))

    to_tag = collections.defaultdict(list)

    for instance in instances:
        retention_days = 7
        server_name = ''

        #create_image(instance_id, name, description=None, no_reboot=False, block_device_mapping=None, dry_run=False)
        # DryRun, InstanceId, Name, Description, NoReboot, BlockDeviceMappings
        create_time = datetime.datetime.now()
        create_fmt = create_time.strftime('%Y-%m-%d')
        
        for tags in format_tags(instance.tags):
            if 'Name' in tags:
                server_name = tags['Name']
        AMIid = ec.create_image(
            InstanceId=instance['InstanceId'],
            Name="Lambda - " + server_name + " from " +
            create_fmt,
            Description="Lambda created AMI of instance " +
            instance['InstanceId'] + " from " + create_fmt,
            NoReboot=True,
            DryRun=False)

        pprint.pprint(instance)

        to_tag[retention_days].append(AMIid['ImageId'])

        print("Retaining AMI %s of instance %s for %d days" % (
            AMIid['ImageId'],
            instance['InstanceId'],
            retention_days,
        ))

    print(to_tag.keys())

    for retention_days in to_tag.keys():
        delete_date = datetime.date.today() + datetime.timedelta(
            days=retention_days)
        delete_fmt = delete_date.strftime('%m-%d-%Y')
        print("Will delete %d AMIs on %s" %
              (len(to_tag[retention_days]), delete_fmt))

        #break

        ec.create_tags(Resources=to_tag[retention_days],
                       Tags=[
                           {
                               'Key': 'DeleteOn',
                               'Value': delete_fmt
                           },
                       ])