import os
from datetime import timedelta
from typing import List

import boto3
import humanize
import durations

from aws_hashicorp_packer_reaper.aws import EC2Instance
from aws_hashicorp_packer_reaper.logger import log


def list_packer_instances(ec2: object) -> List[EC2Instance]:
    paginator = ec2.get_paginator("describe_instances")
    instances = []
    for response in paginator.paginate(
        Filters=[{"Name": "tag:Name", "Values": ["Packer Builder"]}]
    ):
        for reservation in response["Reservations"]:
            for instance in map(lambda i: EC2Instance(i), reservation["Instances"]):
                log.debug(
                    "found instance %s launched %s, now in state %s",
                    instance,
                    humanize.naturaltime(instance.time_since_launch),
                    instance.state,
                )
                instances.append(instance)
    return instances


def expired_packer_instances(
    instances: List[EC2Instance], states: List[str], older_than: timedelta
) -> List[EC2Instance]:
    return list(
        filter(
            lambda i: i.state in states and i.time_since_launch > older_than, instances
        )
    )


def stop_expired_instances(ec2: object, dry_run: bool, older_than: timedelta):
    count = 0
    instances = expired_packer_instances(
        list_packer_instances(ec2), ["running"], older_than
    )
    for instance in instances:
        log.info(
            "stopping %s created %s",
            instance,
            humanize.naturaltime(instance.time_since_launch),
        )
        count = count + 1
        if not dry_run:
            ec2.stop_instances(InstanceIds=[instance.instance_id])
    log.info(f"total of {len(instances)} running instances stopped")


def terminate_expired_instances(ec2: object, dry_run: bool, older_than: timedelta):
    instances = expired_packer_instances(
        list_packer_instances(ec2), ["running", "stopped"], older_than
    )
    for instance in instances:
        log.info(
            "terminating %s created %s",
            instance,
            humanize.naturaltime(instance.time_since_launch),
        )
        if not dry_run:
            ec2.terminate_instances(InstanceIds=[instance.instance_id])
    log.info(f"total of {len(instances)} instances terminated")


operation = {"stop": stop_expired_instances, "terminate": terminate_expired_instances}


def handler(request, _):
    log.setLevel(os.getenv("LOG_LEVEL", "INFO"))
    dry_run = request.get("dry_run", False)
    older_than = durations.Duration(request.get("older_than", "2h"))
    mode = request.get("mode", "stop")

    operation[mode](
        ec2=boto3.client("ec2"),
        dry_run=dry_run,
        older_than=timedelta(seconds=older_than.seconds),
    )

if __name__ == '__main__':
    handler({"mode":"stop", "older_than": "1m", "dry_run": "true"}, {})
