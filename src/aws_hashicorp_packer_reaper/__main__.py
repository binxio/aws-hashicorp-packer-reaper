import os
from typing import Tuple
from aws_hashicorp_packer_reaper.aws import Tag

import boto3
import click
import humanize
from aws_hashicorp_packer_reaper.click_argument_types import Duration, TagParam
from datetime import timedelta

from aws_hashicorp_packer_reaper.logger import log
from aws_hashicorp_packer_reaper.reaper import (
    stop_expired_instances,
    terminate_expired_instances,
    list_packer_instances,
)


@click.group(help="stop or terminate dangling packer instances")
@click.option("--dry-run", is_flag=True, default=False, help="do not change anything")
@click.option("--verbose", is_flag=True, default=False, help="output")
@click.pass_context
def main(ctx, dry_run, verbose):
    log.setLevel(os.getenv("LOG_LEVEL", "DEBUG" if verbose else "INFO"))
    ctx.obj = ctx.params


@main.command(help="packer builder instances")
@click.option("--older-than", type=Duration(), required=True, help="period since launched")
@click.option("--tag", 'tags', type=TagParam(), required=False, multiple=True, help="Tags to filter instances by. Specify with Name=Value format. Can specify --tag multiple times.")
@click.pass_context
def stop(ctx, older_than, tags):
    stop_expired_instances(
        boto3.client("ec2"), dry_run=ctx.obj["dry_run"], older_than=timedelta(seconds=older_than.seconds), tags=tags
    )


@main.command(help="packer builder instances")
@click.option("--older-than", type=Duration(), required=True, help="period since launched")
@click.option("--tag", 'tags', type=TagParam(), required=False, multiple=True, help="Tags to filter instances by. Specify with Name=Value format. Can specify --tag multiple times.")
@click.pass_context
def terminate(ctx, older_than:Duration, tags:Tuple[Tag]):
    terminate_expired_instances(
        boto3.client("ec2"), dry_run=ctx.obj["dry_run"], older_than=timedelta(seconds=older_than.seconds), tags=tags
    )


@main.command(help="packer builder instances")
@click.option("--tag", 'tags', type=TagParam(), required=False, multiple=True, default=[], help="Tags to filter instances by. Specify with Name=Value format. Can specify --tag multiple times.")
@click.pass_context
def list(ctx, tags: Tuple[Tag]):
    instances = list_packer_instances(boto3.client("ec2"), [tag for tag in tags])
    for i in instances:
        print(f"{i} launched {humanize.naturaltime(i.time_since_launch)} - {i.state}")
    log.info(f"{len(instances)} packer builder instances found")


if __name__ == "__main__":
    main()
