import json
import boto3
import logging

# 로거 설정
logger = logging.getLogger()
logger.setLevel(logging.INFO)


# AWS Config 클라이언트 생성
config = boto3.client('config')

APPLICABLE_RESOURCES = ["AWS::Lambda::Function"]

def find_violation(current_tags, required_tags):
    logger.info(f"Checking tags: {current_tags} against required tags: {required_tags}")
    violation = ""
    for rtag, rvalues in required_tags.items():
        tag_present = False
        for tag in current_tags:
            if tag == rtag:
                tag_present = True
                value_match = False
                rvaluesplit = rvalues.split(",")
                for rvalue in rvaluesplit:
                    if current_tags[tag] == rvalue:
                        value_match = True
                    if current_tags[tag] != "":
                        if rvalue == "*":
                            value_match = True
                if not value_match:
                    violation += f"\n{current_tags[tag]} doesn't match any of {required_tags[rtag]}!"
        if not tag_present:
            violation += f"\nTag {rtag} is not present."
    if violation == "":
        return None
    return violation

def add_missing_tag(lambda_arn):
    client = boto3.client('lambda')
    tags_to_update = {'user': 'notag-user'}
    client.tag_resource(Resource=lambda_arn, Tags=tags_to_update)
    logger.info(f"Added/Updated tags: {tags_to_update} for {lambda_arn}")

def evaluate_compliance(configuration_item, rule_parameters):
    logger.info(f"Evaluating compliance for: {configuration_item}")
    
    if configuration_item["resourceType"] not in APPLICABLE_RESOURCES:
        return {
            "compliance_type": "NOT_APPLICABLE",
            "annotation": "The rule doesn't apply to resources of type " +
            configuration_item["resourceType"] + "."
        }

    if configuration_item["configurationItemStatus"] == "ResourceDeleted":
        return {
            "compliance_type": "NOT_APPLICABLE",
            "annotation": "The configurationItem was deleted and therefore cannot be validated."
        }

    if configuration_item["resourceType"] == "AWS::Lambda::Function":
        client = boto3.client('lambda')
        try:
            all_tags = client.list_tags(Resource=configuration_item["ARN"])
            current_tags = all_tags['Tags']
            logger.info(f"All tags: {all_tags}")
            logger.info(f"Current tags: {current_tags}")
        except Exception as e:
            logger.error(f"Error fetching tags: {e}")
            return {
                "compliance_type": "NON_COMPLIANT",
                "annotation": f"Failed to fetch tags: {e}"
            }

    violation = find_violation(current_tags, rule_parameters)        

    if violation:
        add_missing_tag(configuration_item["ARN"])
        return {
            "compliance_type": "NON_COMPLIANT",
            "annotation": violation
        }

    return {
        "compliance_type": "COMPLIANT",
        "annotation": "This resource is compliant with the rule."
    }

def lambda_handler(event, context):
    logger.info(f"Received event: {event}")
    logger.info(f"Context: {context}")
    
    invoking_event = json.loads(event["invokingEvent"])
    configuration_item = invoking_event["configurationItem"]
    rule_parameters = json.loads(event["ruleParameters"])
    
    logger.info(f"Configuration item: {configuration_item}")
    logger.info(f"Rule parameters: {rule_parameters}")
    
    result_token = "No token found."
    if "resultToken" in event:
        result_token = event["resultToken"]

    evaluation = evaluate_compliance(configuration_item, rule_parameters)
    config.put_evaluations(
    Evaluations=[
        {
            "ComplianceResourceType": configuration_item["resourceType"],
            "ComplianceResourceId": configuration_item["resourceId"],
            "ComplianceType": evaluation["compliance_type"],
            "Annotation": evaluation["annotation"],
            "OrderingTimestamp": configuration_item["configurationItemCaptureTime"]
        },
    ],
    ResultToken=result_token
)
