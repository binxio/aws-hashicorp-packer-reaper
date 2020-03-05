import os
import logging
import click
import boto3
from aws_hashicorp_packer_reaper.reaper import (
    destroy_expired_instances,
    list_packer_instances,
)
from aws_hashicorp_packer_reaper.logger import log


@click.group(help="stop or terminate dangling packer instances")
@click.option("--dry-run", is_flag=True, default=False, help="do not change anything")
@click.option("--verbose", is_flag=True, default=False, help="output")
@click.pass_context
def main(ctx, dry_run, verbose):
    log.setLevel(os.getenv("LOG_LEVEL", "DEBUG" if verbose else "INFO"))
    ctx.obj = ctx.params


@main.command()
@click.option("--hours", type=int, required=False, default=2, help="retention period")
@click.pass_context
def stop(ctx, hours):
    if hours < 0:
        click.echo("instances must be 1 hour or older")
        exit(1)

    destroy_expired_instances(
        boto3.client("ec2"), dry_run=ctx.obj["dry_run"], hours=hours, mode="stop"
    )


@main.command()
@click.option("--hours", type=int, required=False, default=2, help="retention period")
@click.pass_context
def terminate(ctx, hours):
    if hours < 0:
        click.echo("instances must be 1 hour or older")
        exit(1)

    destroy_expired_instances(
        boto3.client("ec2"), dry_run=ctx.obj["dry_run"], hours=hours, mode="terminate"
    )


@main.command()
@click.pass_context
def list(ctx):
    instances = list_packer_instances(boto3.client("ec2"))
    for i in instances:
        print(f"{i.state}\t{i}\t{i.running_for}")


if __name__ == "__main__":
    main()
