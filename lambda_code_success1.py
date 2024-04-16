import json
import boto3

# event, context를 모두 print하고, 모든 파라미터를 출력하는 코드 추가
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
                    violation += "\n" + current_tags[tag] + " doesn't match any of " + required_tags[rtag] + "!"
        if not tag_present:
            violation += "\nTag " + str(rtag) + " is not present."
    return violation if violation else None

def evaluate_compliance(configuration_item, rule_parameters):
    if configuration_item["resourceType"] not in APPLICABLE_RESOURCES:
        return {
            "compliance_type": "NOT_APPLICABLE",
            "annotation": "The rule doesn't apply to resources of type " + configuration_item["resourceType"] + "."
        }

    if configuration_item["configurationItemStatus"] == "ResourceDeleted":
        return {
            "compliance_type": "NOT_APPLICABLE",
            "annotation": "The configurationItem was deleted and therefore cannot be validated."
        }

    current_tags = {}
    if configuration_item["resourceType"] == "AWS::Lambda::Function":
        client = boto3.client('lambda')
        all_tags = client.list_tags(Resource=configuration_item["ARN"])
        current_tags = all_tags['Tags']  # 사용자 태그만 가져옵니다.

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
    print("Event:", json.dumps(event))  # 이벤트 로깅
    print("Context:", context)  # 컨텍스트 로깅

    invoking_event = json.loads(event["invokingEvent"])
    configuration_item = invoking_event["configurationItem"]
    rule_parameters = json.loads(event["ruleParameters"])
    result_token = event.get("resultToken", "No token found.")

    # 파라미터 로깅
    print("Invoking Event:", invoking_event)
    print("Configuration Item:", configuration_item)
    print("Rule Parameters:", rule_parameters)
    print("Result Token:", result_token)

    evaluation = evaluate_compliance(configuration_item, rule_parameters)

    config = boto3.client("config")
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
