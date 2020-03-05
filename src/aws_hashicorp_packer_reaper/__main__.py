import os

import boto3
import click
import durations
from datetime import timedelta

from aws_hashicorp_packer_reaper.logger import log
from aws_hashicorp_packer_reaper.reaper import (
    destroy_expired_instances,
    list_packer_instances,
)


class Duration(click.ParamType):
    """
    A duration in human readable form as parsed by https://github.com/oleiade/durations
    """
    name = "duration"

    def convert(self, value, param, ctx) -> durations.Duration:
        if value is None:
            return value

        if isinstance(value, durations.Duration):
            return value

        try:
            return durations.Duration(value)
        except ValueError as e:
            self.fail(f'Could not parse "{value}" into duration ({e})', param, ctx)

@click.group(help="stop or terminate dangling packer instances")
@click.option("--dry-run", is_flag=True, default=False, help="do not change anything")
@click.option("--verbose", is_flag=True, default=False, help="output")
@click.pass_context
def main(ctx, dry_run, verbose):
    log.setLevel(os.getenv("LOG_LEVEL", "DEBUG" if verbose else "INFO"))
    ctx.obj = ctx.params


@main.command(help="packer builder instances")
@click.option("--older-than", type=Duration(), default="2h", required=False, help="period since launched")
@click.pass_context
def stop(ctx, older_than):
    destroy_expired_instances(
        boto3.client("ec2"), dry_run=ctx.obj["dry_run"], older_than=timedelta(seconds=older_than.seconds), mode="stop"
    )


@main.command(help="packer builder instances")
@click.option("--older-than", type=Duration(), default="2h", required=False, help="period since launched")
@click.pass_context
def terminate(ctx, older_than:Duration):
    destroy_expired_instances(
        boto3.client("ec2"), dry_run=ctx.obj["dry_run"], older_than=timedelta(seconds=older_than.seconds), mode="terminate"
    )


@main.command(help="packer builder instances")
@click.pass_context
def list(ctx):
    instances = list_packer_instances(boto3.client("ec2"))
    for i in instances:
        print(f"{i.state}\t{i}\t{i.time_since_launch}")


if __name__ == "__main__":
    main()
