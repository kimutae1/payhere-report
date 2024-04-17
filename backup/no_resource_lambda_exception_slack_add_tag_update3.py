import os
import json
import boto3
import requests

def find_violation(current_tags, required_tags):
    violation = ""
    for rtag, rvalues in required_tags.items():
        tag_present = False
        for tag, value in current_tags.items():
            if tag == rtag:
                tag_present = True
                value_match = False
                rvaluesplit = rvalues.split(",")
                for rvalue in rvaluesplit:
                    if value == rvalue:
                        value_match = True
                    if value != "":
                        if rvalue == "*":
                            value_match = True
                if not value_match:
                    violation += "\n" + value + " doesn't match any of " + required_tags[rtag] + "!"
        if not tag_present:
            violation += "\nTag " + str(rtag) + " is not present."
    return violation if violation else None

def evaluate_compliance(configuration_item, rule_parameters):
    if configuration_item["configurationItemStatus"] == "ResourceDeleted":
        return {
            "compliance_type": "NOT_APPLICABLE",
            "annotation": "The configurationItem was deleted and therefore cannot be validated."
        }

    current_tags = configuration_item.get("tags", {})

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

def send_message_to_slack(text):
    webhook_url = os.environ['SLACK_WEBHOOK_URL']
    slack_data = {'text': text}

    response = requests.post(
        webhook_url, data=json.dumps(slack_data),
        headers={'Content-Type': 'application/json'}
    )

    if response.status_code != 200:
        raise ValueError(
            'Request to slack returned an error %s, the response is:\n%s'
            % (response.status_code, response.text)
        )

def update_tags_for_resources(resource_arns, tags, aws_region):
    # boto3 클라이언트 생성
    client = boto3.client('resourcegroupstaggingapi', region_name=aws_region)
    
    # 리소스에 태그 업데이트
    response = client.tag_resources(
        ResourceARNList=resource_arns,
        Tags=tags
    )
    return response

def lambda_handler(event, context):
    event_all = json.dumps(event)
    print(event_all)
    if 'invokingEvent' not in event:
        #send_message_to_slack("Error: 'invokingEvent' key not found in the event object.")
        return

    invoking_event = json.loads(event['invokingEvent'])
    configuration_item = invoking_event.get("configurationItem")
    if not configuration_item:
        #send_message_to_slack("Error: 'configurationItem' key not found in the invokingEvent.")
        return

    rule_parameters = json.loads(event.get("ruleParameters", "{}"))
    result_token = event.get("resultToken", "No token found.")

    evaluation = evaluate_compliance(configuration_item, rule_parameters)

    if evaluation["compliance_type"] == "NON_COMPLIANT":
        resource_id = configuration_item["ARN"].split(":")[-1]
        aws_region = configuration_item["awsRegion"]
        compliance_message = f"NON_COMPLIANT: Resource {resource_id} does not comply with the rule. {evaluation['annotation']}"
        print("tag update 진행")
        update_response = update_tags_for_resources([configuration_item["ARN"]], rule_parameters, aws_region)
        compliance_message += f"\nTags updated for resource {resource_id}. Response: {update_response}"

        # 이벤트 로깅을 Slack 메시지로 전송
        event_text = json.dumps(event)  # JSON 문자열로 변환
        slack_message = f"""
        *Compliance Evaluation*
        - Compliance Status: {evaluation["compliance_type"]}
        - Resource Type: {configuration_item["resourceType"]}
        - ARN: {configuration_item["ARN"]}
        - AWS Region: {configuration_item["awsRegion"]}
        - AWS Account ID: {configuration_item["awsAccountId"]}
        - Message: {compliance_message}
        """
        #send_message_to_slack(slack_message)
