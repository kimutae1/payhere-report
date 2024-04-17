import json
import boto3

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

    # AWS Config를 통해 제공되는 태그 정보 사용
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

def lambda_handler(event, context):
    print("Event:", json.dumps(event))  # 이벤트 로깅
    print("Context:", context)  # 컨텍스트 로깅
#    try:
#        # invokingEvent에서 JSON 문자열을 파싱하여 Python 객체로 변환
#        # 변환된 객체에서 configurationItem 추출
#        configuration_item = json.loads(event.get("invokingEvent", "{}")).get("configurationItem")
#        if not configuration_item:
#            raise ValueError("configurationItem not found in invokingEvent")
#    except KeyError as e:
#        print(f"Key error: {e} - event dictionary does not contain the expected key.")
#    except ValueError as e:
#        print(f"Value error: {e}")
#    except Exception as e:
#        print(f"Unexpected error: {e}")
#
# 이후 로직은 configuration_item이 성공적으로 추출되었을 때 실행됩니다.
# 예외가 발생한 경우, 이 부분은 실행되지 않을 수 있으므로 적절한 처리가 필요합니다.
 
# event를 불러오다
   # invoking_event = json.loads(event["invokingEvent"])
   # configuration_item = invoking_event["configurationItem"]
   # configuration_item = json.loads(event["configurationItem"])
    configuration_item = json.loads(event["invokingEvent"])["configurationItem"]
    rule_parameters = json.loads(event["ruleParameters"])
    result_token = event.get("resultToken", "No token found.")

    # 파라미터 로깅
    #print("Invoking Event:", invoking_event)
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
