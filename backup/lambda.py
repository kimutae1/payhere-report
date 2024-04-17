import boto3
import os
import requests

def lambda_handler(event, context):
    # 환경 변수에서 Slack Webhook URL을 가져옵니다.
    slack_url = os.environ['SLACK_URL']
    
    # 이벤트에서 리소스 정보를 추출합니다.
    resource_arn = event['detail']['responseElements']['arn']
    
    # 리소스 태그를 확인합니다.
    client = boto3.client('resourcegroupstaggingapi')
    tagging_info = client.get_resources(ResourceARNList=[resource_arn])
    
    # 태그가 없는 경우, 태그를 추가하고 Slack으로 알림을 보냅니다.
    if not tagging_info['ResourceTagMappingList'][0]['Tags']:
        # 태그 추가
        client.tag_resources(ResourceARNList=[resource_arn], Tags={'AutoTagged': 'true'})
        
        # Slack으로 알림 보내기
        message = f"태그가 없는 리소스가 생성되어 자동으로 태그를 추가했습니다: {resource_arn}"
        data = {'text': message}
        response = requests.post(slack_url, json=data)
        
        if response.status_code != 200:
            raise ValueError(f"Slack 알림 전송 실패: {response.text}")
    
    return {
        'statusCode': 200,
        'body': 'Success'
    }
