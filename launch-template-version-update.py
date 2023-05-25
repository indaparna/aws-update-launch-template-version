import boto3
from botocore.exceptions import BotoCoreError, ClientError
from aws_tools_developemnt_framework import common_functions


# Provide the AWS region of interest
# region_name = 'ap-southeast-1'
ENABLE_DEBUG_MODE=True

def create_launch_template_version(template_id, ami_id):
    """
    Creates a new launch template version if the provided AMI ID is different from the current default version.

    Args:
        template_id (str): The ID of the launch template.
        ami_id (str): The ID of the AMI.

    Returns:
        None
    """

    try:
        ec2 = boto3.client('ec2')
        # Get the current default launch template version
        response = ec2.describe_launch_template_versions(LaunchTemplateId=template_id)

        # Extract the relevant information from the current default version
        current_version = response['LaunchTemplateVersions'][0]
        current_settings = current_version['LaunchTemplateData']
        current_ami_id = current_settings['ImageId']

        # Compare the AMI ID of the current default version with the new AMI ID
        if current_ami_id == ami_id:
            print("A default Launch Template already exists for the same AMI ID. No new launch template version created.")
            return

        print('Creating a new launch template version')
        # Update the AMI ID and any other desired changes
        current_settings['ImageId'] = ami_id

        # Create a new launch template version
        response = ec2.create_launch_template_version(
            LaunchTemplateId=template_id,
            LaunchTemplateData=current_settings,
            SourceVersion=str(current_version['VersionNumber']),
            VersionDescription='created by boto3'
        )

        new_version_id = response['LaunchTemplateVersion']['VersionNumber']

        print('Setting the new version as the default')
        # Set the new version as the default
        ec2.modify_launch_template(
            LaunchTemplateId=template_id,
            DefaultVersion=str(new_version_id)
        )

        print(f"New launch template version created: {new_version_id}")

    except (BotoCoreError, ClientError) as e:
        print("Error in creating launch template version:")
        print(e.response['Error']['Message'])

def get_launch_template_id(region, asg_name):
    """
    Retrieves the launch template ID for the specified Auto Scaling group name.

    Args:
        region (str): The AWS region where the Auto Scaling group is located.
        asg_name (str): The name of the Auto Scaling group.

    Returns:
        str: The ID of the launch template.
    """

    try:
        # Create a Boto3 Auto Scaling client
        autoscaling_client = boto3.client('autoscaling', region_name=region)
        # print(f"asg_name = {asg_name}")

        # Describe all Auto Scaling groups
        response = autoscaling_client.describe_auto_scaling_groups(AutoScalingGroupNames=[asg_name])

        for group in response['AutoScalingGroups']:
            launch_template_id = group['LaunchTemplate']['LaunchTemplateId']
            launch_template_name = group['LaunchTemplate']['LaunchTemplateName']
            # print(f"name = {launch_template_name}  id = {launch_template_id}")

            break
        return launch_template_id

    except (BotoCoreError, ClientError) as e:
        print("Error retrieving the launch template ID:")
        print(e.response['Error']['Message'])
        

def list_amis_with_tag_filter(tags):
    """
    Lists the latest AMI ID that matches the specified tag filters.

    Args:
        tags (dict): A dictionary containing the tags to filter the AMIs.

    Returns:
        str: The ID of the latest AMI that matches the tag filters.
    """
    try:

        # Create a Boto3 EC2 client
        ec2_client = boto3.client('ec2')

        # Convert the tags dictionary into a list of filters
        filters = [{'Name': f'tag:{tag_key}', 'Values': [f'*{tag_value_contains}*']} for tag_key, tag_value_contains in tags.items()]

        # List all the AMIs with the specified tag filters
        response = ec2_client.describe_images(Filters=filters)

        # Sort the AMIs based on the timestamp
        sorted_amis = sorted(response['Images'], key=lambda x: x['CreationDate'], reverse=True)

        if sorted_amis:
            latest_ami = sorted_amis[0]
            ami_id = latest_ami['ImageId']
            ami_name = ''
            for tag in latest_ami['Tags']:
                if tag['Key'] == 'Name':
                    ami_name = tag['Value']
                    break
            timestamp = common_functions.convert_utc_to_ist(latest_ami['CreationDate'])
            print(f"Latest AMI ID: {ami_id} | AMI Name: {ami_name} | AMI Timestamp: {timestamp}")
        else:
            print("No AMIs found with the specified tag filters.")
        return ami_id

    except (BotoCoreError, ClientError) as e:
        print("Error retrieving the latest AMI ID for ASG:")
        print(e.response['Error']['Message'])


if __name__ == "__main__":    
    """
    The main entry point of the program.
    """
    
    try:
        print('Starting Execution for main()')
        yaml_path = "config.yaml"
        yaml_data = common_functions.load_document_in_yaml_file("launch-template-version-update", yaml_path)
        region = yaml_data['AWS_REGION']
        amis = yaml_data['ASG_NAMES']
        
        print('------------')
        for ami in amis:

            if type(ami) is dict:
                for asg_name in ami:
                    result = {}
                    for dictionary in ami[asg_name]:
                        result.update(dictionary) 
                                           
                    launch_template_id = get_launch_template_id(region, asg_name)                
                    ami_id = list_amis_with_tag_filter(result)
                    print(f"launch_template_id = {launch_template_id}  ami_id = {ami_id}")
                
                    # Call the function to create the new launch template version if needed
                    # create_launch_template_version(launch_template_id, ami_id)
                print('------------')
        print('End of main()')
    except (BotoCoreError, ClientError) as e:
        print("Error in main:")
        print(e.response['Error']['Message'])
