# AWS Hashicorp Packer Reaper
Hashicorp Packer is a great tool for building Amazon Machine Images. However, sometimes the virtual machine running packer
is not stopped. This utility:

1. stops or terminated all virtual machines with the name tag 'Packer Builder'

You can use it as a command line utility or install it as an AWS Lambda function and stop the spend , NoOps style!

## install the packer reaper
to install the packer reaper, type:

```sh
pip install aws-hashicorp-packer-reaper
```

## show running packer instances
To show running packer instances:
```sh
$ aws-hashicorp-packer-reaper list

i-06ac951992dbc11a1 (Packer Builder) launched 13 minutes ago - terminated
i-035ebe427a538c829 (Packer Builder) launched 4 minutes ago - running
INFO: 2 packer builder instances found
```

## stop running packer instances
To stop running packer instances older than 2 hours:
```sh
$ aws-hashicorp-packer-reaper stop --older-than 2h

INFO: stopping i-035ebe427a538c829 (Packer Builder) created 2 hours ago
INFO: total of 1 running instances stopped
```

## terminate running packer instances
To terminate stopped and running packer instances older than 24 hours:
```sh
aws-hashicorp-packer-reaper --verbose terminate --older-than 24h

INFO: terminating i-035ebe427a538c829 (Packer Builder) created 25 hours ago
INFO: total of 1 instances terminated
```

## deploy the packer reaper
To deploy the packer reaper as an AWS Lambda, type:

```sh
git clone https://github.com/binxio/aws-hashicorp-packer-reaper.git
cd aws-hashicorp-packer-reaper
aws cloudformation deploy \
	--capabilities CAPABILITY_IAM \
	--stack-name aws-hashicorp-packer-reaper \
	--template-file ./cloudformation/aws-hashicorp-packer-reaper.yaml
```
This will install the packer reaper in your AWS account and run every hour, stopping packer instances 
launched more than 2 hours ago and terminate instances older than 24 hours. You can change the schedule
and the action to meet your requirements.

