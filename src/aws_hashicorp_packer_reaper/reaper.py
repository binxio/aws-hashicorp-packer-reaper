import os
from datetime import timedelta
from typing import List

import boto3
import humanize
import durations

from .aws import EC2Instance
from .logger import log


def list_packer_instances(ec2: object) -> List[EC2Instance]:
    paginator = ec2.get_paginator("describe_instances")
    instances = []
    for response in paginator.paginate(
        Filters=[{"Name": "tag:Name", "Values": ["Packer Builder"]}]
    ):
        for reservation in response["Reservations"]:
            for instance in map(lambda i: EC2Instance(i), reservation["Instances"]):
                log.debug(
                    "found instance %s launched at %s, now in state %s",
                    instance,
                    instance.launch_time,
                    instance.state,
                )
                instances.append(instance)
    return instances


def expired_packer_instances(
    instances: List[EC2Instance], older_than: timedelta
) -> List[EC2Instance]:
    return list(
        filter(
            lambda i: i.state in ["running", "stopped"]
            and i.time_since_launch > older_than,
            instances,
        )
    )


def destroy_expired_instances(
    ec2: object, dry_run: bool, older_than: timedelta, mode: str
):
    count = 0
    instances = expired_packer_instances(list_packer_instances(ec2), older_than)
    for instance in instances:
        if mode == "terminate":
            log.info(
                "terminating %s created %s",
                instance,
                humanize.naturaltime(instance.time_since_launch),
            )
            count = count + 1
            if not dry_run:
                ec2.terminate_instances(InstanceIds=[instance.instance_id])
        else:
            if instance.state == "running":
                log.info(
                    "stopping %s created %s",
                    instance,
                    humanize.naturaltime(instance.time_since_launch),
                )
                count = count + 1
                if not dry_run:
                    ec2.stop_instances(InstanceIds=[instance.instance_id])
            elif instance.state == "stopped":
                log.debug("instance %s already stopped", instance)
            else:
                log.info(
                    "instance %s is in flux, current state is %s",
                    instance,
                    instance.state,
                )
    log.info(
        f"total of {len(instances)} instances, {count} {mode}{'ped' if mode == 'stop' else 'd'}, {len(instances)-count} skipped"
    )


def handler(request, _):
    log.setLevel(os.getenv("LOG_LEVEL", "INFO"))
    dry_run = request.get("dry_run", False)
    older_than = durations.Duration(request.get("older_than", "2h"))
    mode = request.get("mode", "stop")

    destroy_expired_instances(
        ec2=boto3.client("ec2"),
        dry_run=dry_run,
        older_than=timedelta(seconds=older_than.seconds),
        mode=mode,
    )
