import boto3

def update_tags_for_resources(resource_arns, tags, region='ap-northeast-2'):
    """
    하나 이상의 AWS 리소스에 태그를 업데이트합니다.

    :param resource_arns: 태그를 업데이트할 리소스의 ARN 목록입니다.
    :param tags: 업데이트할 태그입니다. {'태그명': '태그값'} 형식의 딕셔너리입니다.
    :param region: 리소스가 위치한 리전입니다. 기본값은 'ap-northeast-2'입니다.
    """
    # Resource Groups Tagging API 클라이언트 생성
    tagging_client = boto3.client('resourcegroupstaggingapi', region_name=region)
    
    # 태그 업데이트
    tagging_client.tag_resources(
        ResourceARNs=resource_arns,
        Tags=tags
    )

# 사용 예
resource_arns = [
    'arn:aws:ec2:ap-northeast-2:123456789012:instance/i-1234567890abcdef0',
    'arn:aws:s3:::my-bucket'
]
tags = {
    'Project': 'MyProject',
    'Environment': 'Production'
}

update_tags_for_resources(resource_arns, tags)
