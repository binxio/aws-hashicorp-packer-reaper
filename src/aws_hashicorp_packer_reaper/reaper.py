from typing import List
import os
import boto3
from datetime import datetime, timedelta
from .logger import log
from pytz import UTC
from .aws import EC2Instance


def list_packer_instances(ec2: object) -> List[EC2Instance]:
    paginator = ec2.get_paginator("describe_instances")
    instances = []
    for response in paginator.paginate(
        Filters=[{"Name": "tag:Name", "Values": ["Packer Builder"]}]
    ):
        for reservation in response["Reservations"]:
            for instance in map(lambda i: EC2Instance(i), reservation["Instances"]):
                log.debug("adding instance %s %s %s", instance, instance.launch_time, instance.state)
                instances.append(instance)
    return instances


def expired_packer_instances(
    instances: List[EC2Instance], elapsed_time: timedelta
) -> List[EC2Instance]:
    return list(
        filter(
            lambda i: i.state in ["running", "stopped"]
            and i.running_for > elapsed_time,
            instances,
        )
    )


def destroy_expired_instances(ec2: object, dry_run: bool, hours: int, mode: str):
    instances = expired_packer_instances(
        list_packer_instances(ec2), timedelta(hours=hours)
    )
    for instance in instances:
        if mode == "terminate":
            log.info("terminating %s running for %s", instance, instance.running_for)
            if dry_run:
                continue
            ec2.terminate_instances(InstanceIds=[instance.instance_id])
        else:
            if instance.state == "running":
                log.info("stopping %s running for %s", instance, instance.running_for)
                if dry_run:
                    continue
                ec2.stop_instances(InstanceIds=[instance.instance_id])
            else:
                log.info("instance %s is not running", instance)


def handler(request, _):
    log.setLevel(os.getenv("LOG_LEVEL", "INFO"))
    dry_run = request.get("dry_run", False)
    hours = int(request.get("hours", 2))
    mode = request.get("mode", "stop")
    if hours < 0:
        raise ValueError("hours are less than 0")
    destroy_expired_instances(
        boto3.client("ec2"), dry_run, timedelta(hours=hours), mode
    )
