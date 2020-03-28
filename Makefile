include Makefile.mk

NAME=aws-hashicorp-packer-reaper
AWS_REGION=eu-central-1
S3_BUCKET_PREFIX=binxio-public
S3_BUCKET=$(S3_BUCKET_PREFIX)-$(AWS_REGION)

ALL_REGIONS=$(shell printf "import boto3\nprint('\\\n'.join(map(lambda r: r['RegionName'], boto3.client('ec2').describe_regions()['Regions'])))\n" | python | grep -v '^$(AWS_REGION)$$')

help:           ## Show this help.
	@fgrep -h "##" $(MAKEFILE_LIST) | grep -v fgrep | sed -e 's/\([^:]*\):[^#]*##\(.*\)/printf '"'%-20s - %s\\\\n' '\1' '\2'"'/' |bash

do-push: deploy

pre-build:
	pipenv run python setup.py check
	pipenv run python setup.py build

do-build: target/$(NAME)-$(VERSION).zip

upload-dist:		## to pypi
	rm -rf dist/*
	pipenv run python setup.py sdist
	pipenv run twine upload dist/*

target/$(NAME)-$(VERSION).zip: src/*/*.py requirements.txt Dockerfile.lambda
	mkdir -p target
	docker build --build-arg ZIPFILE=$(NAME)-$(VERSION).zip -t $(NAME)-lambda:$(VERSION) -f Dockerfile.lambda . && \
		ID=$$(docker create $(NAME)-lambda:$(VERSION) /bin/true) && \
		docker export $$ID | (cd target && tar -xvf - $(NAME)-$(VERSION).zip) && \
		docker rm -f $$ID && \
		chmod ugo+r target/$(NAME)-$(VERSION).zip

clean:		## all intermediate files
	rm -rf target
	find . -name \*.pyc | xargs rm 

test:			## run unit tests
	pipenv sync -d
	for i in $$PWD/cloudformation/*; do \
		aws cloudformation validate-template --template-body file://$$i > /dev/null || exit 1; \
	done
	PYTHONPATH=$(PWD)/src pipenv run pytest tests/test*.py

fmt:			## sources using black
	black $(find src -name *.py) tests/*.py

deploy: target/$(NAME)-$(VERSION).zip		## lambda zip to the region $(AWS_REGION)
	aws s3 --region $(AWS_REGION) \
		cp --acl \
		public-read target/$(NAME)-$(VERSION).zip \
		s3://$(S3_BUCKET)/lambdas/$(NAME)-$(VERSION).zip
	aws s3 --region $(AWS_REGION) \
		cp --acl public-read \
		s3://$(S3_BUCKET)/lambdas/$(NAME)-$(VERSION).zip \
		s3://$(S3_BUCKET)/lambdas/$(NAME)-latest.zip

deploy-all-regions: deploy ## lambda zip to all AWS regions
	@for REGION in $(ALL_REGIONS); do \
		echo "copying to region $$REGION.." ; \
		aws s3 --region $$REGION \
			cp --acl public-read \
			s3://$(S3_BUCKET_PREFIX)-$(AWS_REGION)/lambdas/$(NAME)-$(VERSION).zip \
			s3://$(S3_BUCKET_PREFIX)-$$REGION/lambdas/$(NAME)-$(VERSION).zip; \
		aws s3 --region $$REGION \
			cp  --acl public-read \
			s3://$(S3_BUCKET_PREFIX)-$$REGION/lambdas/$(NAME)-$(VERSION).zip \
			s3://$(S3_BUCKET_PREFIX)-$$REGION/lambdas/$(NAME)-latest.zip; \
	done


deploy-lambda:					## to your AWS account
	aws cloudformation deploy \
		--capabilities CAPABILITY_IAM \
		--stack-name $(NAME) \
		--template-file ./cloudformation/aws-hashicorp-packer-reaper.yaml \
		--parameter-override CFNCustomProviderZipFileName=lambdas/$(NAME)-$(VERSION).zip

delete-lambda:					## from your AWS account
	aws cloudformation delete-stack --stack-name $(NAME)
	aws cloudformation wait stack-delete-complete  --stack-name $(NAME)

deploy-pipeline:				## to your AWS account
		aws cloudformation deploy \
		--capabilities CAPABILITY_IAM \
                --stack-name $(NAME)-pipeline \
                --template-file ./cloudformation/cicd-pipeline.yaml \
                --parameter-overrides \
                        S3BucketPrefix=$(S3_BUCKET_PREFIX)

delete-pipeline:				## from your AWS account
	aws cloudformation delete-stack --stack-name $(NAME)-pipeline
	aws cloudformation wait stack-delete-complete  --stack-name $(NAME)-pipeline


demo: 						## to your AWS account
	export VPC_ID=$$(aws ec2  --output text --query 'Vpcs[?IsDefault].VpcId' describe-vpcs) ; \
        export SUBNET_IDS=$$(aws ec2 --output text --query 'Subnets[*].SubnetId' \
                                describe-subnets --filters Name=vpc-id,Values=$$VPC_ID | tr '\t' ','); \
	echo "deploy $(NAME)-demo in default VPC $$VPC_ID, subnets $$SUBNET_IDS" ; \
        ([[ -z $$VPC_ID ]] || [[ -z $$SUBNET_IDS ]] ) && \
                echo "Either there is no default VPC in your account or there are no subnets in the default VPC" && exit 1 ; \
	aws cloudformation deploy --stack-name $(NAME)-demo \
		--template-file ./cloudformation/demo-stack.yaml  \
		--parameter-overrides 	VPC=$$VPC_ID Subnets=$$SUBNET_IDS


delete-demo:					## from your AWS account
	aws cloudformation delete-stack --stack-name $(NAME)-demo
	aws cloudformation wait stack-delete-complete  --stack-name $(NAME)-demo

