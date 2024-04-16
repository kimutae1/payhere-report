# 주어진 규칙에 따라 AWS Lambda 함수의 태그를 검사하여 규정에 맞지 않는 경우를 찾는 스크립트입니다.
# 필수 태그가 있는지, 태그 값이 유효한지 확인하고, 규정에 어긋나는 경우를 반환합니다.

import json
import boto3

APPLICABLE_RESOURCES = ["AWS::Lambda::Function"]

def find_violation(current_tags, required_tags):
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
                    violation = violation + "\n" + current_tags[tag] + " doesn't match any of " + required_tags[rtag] + "!"
        if not tag_present:
            violation = violation + "\n" + "Tag " + str(rtag) + " is not present."
    if violation == "":
        return None
    return violation

def evaluate_compliance(configuration_item, rule_parameters):
    
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
        all_tags = client.list_tags(Resource=configuration_item["ARN"])
        current_tags = all_tags['Tags']  # get only user tags.  

    violation = find_violation(current_tags, rule_parameters)        

    if violation:
        return {
            "compliance_type": "NON_COMPLIANT",
            "annotation": violation
        }

    return {
        "compliance_type": "COMPLIANT",
        "annotation": "This resource is compliant with the rule."
    }

def lambda_handler(event, context):
    invoking_event = json.loads(event["invokingEvent"])
    configuration_item = invoking_event["configurationItem"]
    rule_parameters = json.loads(event["ruleParameters"])
    result_token = "No token found."
    if "resultToken" in event:
        result_token = event["resultToken"]

    evaluation = evaluate_compliance(configuration_item, rule_parameters)

    config = boto3.client("config")
    config.put_evaluations(
        Evaluations=[
            {
                "ComplianceResourceType":
                    configuration_item["resourceType"],
                "ComplianceResourceId":
                    configuration_item["resourceId"],
                "ComplianceType":
                    evaluation["compliance_type"],
                "Annotation":
                    evaluation["annotation"],
                "OrderingTimestamp":
                    configuration_item["configurationItemCaptureTime"]
            },
        ],
        ResultToken=result_token
    )

    # Log current_tags, configuration_item, and rule_parameters for debugging
    #if configuration_item["resourceType"] == "AWS::Lambda::Function":
    client = boto3.client('lambda')
    #all_tags = client.list_tags(Resource=configuration_item["ARN"])
    current_tags = all_tags['Tags']  # get only user tags.  
    print("all_tags:", all_tags )
    print("Current Tags:", current_tags)
    print("Configuration Item:", configuration_item)
    print("Rule Parameters:", rule_parameters)
