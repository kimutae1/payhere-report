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



def lambda_handler(event, context):
    print("Event:", json.dumps(event))  # 이벤트 로깅
    print("Context:", context)  # 컨텍스트 로깅

    try:
        invoking_event = json.loads(event["invokingEvent"])
        configuration_item = invoking_event["configurationItem"]
    except KeyError:
        send_message_to_slack("Error: 'invokingEvent' key not found in the event object.")
        return

    rule_parameters = json.loads(event.get("ruleParameters", "{}"))
    result_token = event.get("resultToken", "No token found.")

    evaluation = evaluate_compliance(configuration_item, rule_parameters)


    # 이벤트 로깅을 Slack 메시지로 전송
    event_text = json.dumps(event, indent=4)  # JSON 문자열로 변환
    send_message_to_slack(f"Logged Event: {event_text}")

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
