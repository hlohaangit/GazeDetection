#!/bin/bash

# Deploy Gaze Detection to ECS Fargate
# This script sets up the complete infrastructure for live streaming gaze detection

set -e

# Configuration
AWS_REGION=${AWS_REGION:-"us-east-1"}
CLUSTER_NAME=${CLUSTER_NAME:-"gaze-detection-cluster"}
SERVICE_NAME=${SERVICE_NAME:-"gaze-detection-service"}
TASK_FAMILY=${TASK_FAMILY:-"gaze-detection-task"}
ECR_REPOSITORY_NAME=${ECR_REPOSITORY_NAME:-"gaze-detection"}
IMAGE_TAG=${IMAGE_TAG:-"latest"}
VPC_CIDR=${VPC_CIDR:-"10.0.0.0/16"}
SUBNET_CIDR_1=${SUBNET_CIDR_1:-"10.0.1.0/24"}
SUBNET_CIDR_2=${SUBNET_CIDR_2:-"10.0.2.0/24"}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Starting ECS Fargate Deployment for Gaze Detection${NC}"

# Check prerequisites
echo -e "${YELLOW}🔍 Checking prerequisites...${NC}"

if ! command -v aws &> /dev/null; then
    echo -e "${RED}❌ AWS CLI is not installed. Please install it first.${NC}"
    exit 1
fi

if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is not installed. Please install it first.${NC}"
    exit 1
fi

# Check AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    echo -e "${RED}❌ AWS credentials not configured. Please run 'aws configure' first.${NC}"
    exit 1
fi

# Get AWS account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo -e "${GREEN}✅ AWS Account ID: ${AWS_ACCOUNT_ID}${NC}"

# Create ECR repository
echo -e "${YELLOW}📦 Setting up ECR repository...${NC}"
if ! aws ecr describe-repositories --repository-names $ECR_REPOSITORY_NAME --region $AWS_REGION &> /dev/null; then
    echo -e "${YELLOW}📦 Creating ECR repository: $ECR_REPOSITORY_NAME${NC}"
    aws ecr create-repository \
        --repository-name $ECR_REPOSITORY_NAME \
        --region $AWS_REGION \
        --image-scanning-configuration scanOnPush=true
fi

# Login to ECR
echo -e "${YELLOW}🔐 Logging into ECR...${NC}"
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

# Build and push Docker image
echo -e "${YELLOW}🔨 Building Docker image...${NC}"
docker build -f Dockerfile.ecs -t $ECR_REPOSITORY_NAME:$IMAGE_TAG .

ECR_IMAGE_URI=$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY_NAME:$IMAGE_TAG
echo -e "${YELLOW}🏷️  Tagging image: $ECR_IMAGE_URI${NC}"
docker tag $ECR_REPOSITORY_NAME:$IMAGE_TAG $ECR_IMAGE_URI

echo -e "${YELLOW}⬆️  Pushing image to ECR...${NC}"
docker push $ECR_IMAGE_URI

# Create IAM roles
echo -e "${YELLOW}👤 Setting up IAM roles...${NC}"

# ECS Task Execution Role
if ! aws iam get-role --role-name ecsTaskExecutionRole &> /dev/null; then
    echo -e "${YELLOW}👤 Creating ECS Task Execution Role...${NC}"
    
    # Create trust policy
    cat > ecs-task-execution-trust-policy.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Service": "ecs-tasks.amazonaws.com"
            },
            "Action": "sts:AssumeRole"
        }
    ]
}
EOF
    
    aws iam create-role \
        --role-name ecsTaskExecutionRole \
        --assume-role-policy-document file://ecs-task-execution-trust-policy.json
    
    aws iam attach-role-policy \
        --role-name ecsTaskExecutionRole \
        --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy
    
    aws iam attach-role-policy \
        --role-name ecsTaskExecutionRole \
        --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess
    
    rm -f ecs-task-execution-trust-policy.json
fi

# Gaze Detection Task Role
if ! aws iam get-role --role-name gaze-detection-task-role &> /dev/null; then
    echo -e "${YELLOW}👤 Creating Gaze Detection Task Role...${NC}"
    
    cat > gaze-detection-task-trust-policy.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Service": "ecs-tasks.amazonaws.com"
            },
            "Action": "sts:AssumeRole"
        }
    ]
}
EOF
    
    aws iam create-role \
        --role-name gaze-detection-task-role \
        --assume-role-policy-document file://gaze-detection-task-trust-policy.json
    
    # Create custom policy for gaze detection
    cat > gaze-detection-policy.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:PutObject",
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::gaze-detection-*",
                "arn:aws:s3:::gaze-detection-*/*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents"
            ],
            "Resource": "*"
        }
    ]
}
EOF
    
    aws iam put-role-policy \
        --role-name gaze-detection-task-role \
        --policy-name GazeDetectionPolicy \
        --policy-document file://gaze-detection-policy.json
    
    rm -f gaze-detection-task-trust-policy.json gaze-detection-policy.json
fi

# Create VPC and networking
echo -e "${YELLOW}🌐 Setting up VPC and networking...${NC}"

# Create VPC
VPC_ID=$(aws ec2 create-vpc --cidr-block $VPC_CIDR --query Vpc.VpcId --output text 2>/dev/null || \
         aws ec2 describe-vpcs --filters "Name=cidr-block,Values=$VPC_CIDR" --query Vpcs[0].VpcId --output text)

if [ "$VPC_ID" = "None" ] || [ -z "$VPC_ID" ]; then
    echo -e "${YELLOW}🌐 Creating VPC...${NC}"
    VPC_ID=$(aws ec2 create-vpc --cidr-block $VPC_CIDR --query Vpc.VpcId --output text)
    aws ec2 create-tags --resources $VPC_ID --tags Key=Name,Value=gaze-detection-vpc
fi

echo -e "${GREEN}✅ VPC ID: $VPC_ID${NC}"

# Create subnets
SUBNET_1_ID=$(aws ec2 create-subnet --vpc-id $VPC_ID --cidr-block $SUBNET_CIDR_1 --availability-zone ${AWS_REGION}a --query Subnet.SubnetId --output text 2>/dev/null || \
              aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC_ID" "Name=cidr-block,Values=$SUBNET_CIDR_1" --query Subnets[0].SubnetId --output text)

SUBNET_2_ID=$(aws ec2 create-subnet --vpc-id $VPC_ID --cidr-block $SUBNET_CIDR_2 --availability-zone ${AWS_REGION}b --query Subnet.SubnetId --output text 2>/dev/null || \
              aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC_ID" "Name=cidr-block,Values=$SUBNET_CIDR_2" --query Subnets[0].SubnetId --output text)

echo -e "${GREEN}✅ Subnet 1 ID: $SUBNET_1_ID${NC}"
echo -e "${GREEN}✅ Subnet 2 ID: $SUBNET_2_ID${NC}"

# Create security group
SECURITY_GROUP_ID=$(aws ec2 create-security-group --group-name gaze-detection-sg --description "Security group for gaze detection" --vpc-id $VPC_ID --query GroupId --output text 2>/dev/null || \
                    aws ec2 describe-security-groups --filters "Name=group-name,Values=gaze-detection-sg" --query SecurityGroups[0].GroupId --output text)

if [ "$SECURITY_GROUP_ID" = "None" ] || [ -z "$SECURITY_GROUP_ID" ]; then
    echo -e "${YELLOW}🔒 Creating security group...${NC}"
    SECURITY_GROUP_ID=$(aws ec2 create-security-group --group-name gaze-detection-sg --description "Security group for gaze detection" --vpc-id $VPC_ID --query GroupId --output text)
fi

# Add security group rules
aws ec2 authorize-security-group-ingress --group-id $SECURITY_GROUP_ID --protocol tcp --port 8080 --cidr 0.0.0.0/0 2>/dev/null || true
aws ec2 authorize-security-group-ingress --group-id $SECURITY_GROUP_ID --protocol tcp --port 22 --cidr 0.0.0.0/0 2>/dev/null || true

echo -e "${GREEN}✅ Security Group ID: $SECURITY_GROUP_ID${NC}"

# Create ECS cluster
echo -e "${YELLOW}🏗️  Creating ECS cluster...${NC}"
aws ecs create-cluster --cluster-name $CLUSTER_NAME --region $AWS_REGION 2>/dev/null || true

# Create CloudWatch log group
echo -e "${YELLOW}📊 Creating CloudWatch log group...${NC}"
aws logs create-log-group --log-group-name /ecs/gaze-detection --region $AWS_REGION 2>/dev/null || true

# Update task definition
echo -e "${YELLOW}📝 Updating task definition...${NC}"
sed -i.bak "s/ACCOUNT_ID/$AWS_ACCOUNT_ID/g; s/REGION/$AWS_REGION/g" task-definition.json
rm -f task-definition.json.bak

# Register task definition
aws ecs register-task-definition --cli-input-json file://task-definition.json --region $AWS_REGION

# Create Application Load Balancer (optional)
echo -e "${YELLOW}⚖️  Setting up Application Load Balancer...${NC}"

# Create ALB
ALB_ARN=$(aws elbv2 create-load-balancer \
    --name gaze-detection-alb \
    --subnets $SUBNET_1_ID $SUBNET_2_ID \
    --security-groups $SECURITY_GROUP_ID \
    --region $AWS_REGION \
    --query LoadBalancers[0].LoadBalancerArn \
    --output text 2>/dev/null || \
    aws elbv2 describe-load-balancers --names gaze-detection-alb --query LoadBalancers[0].LoadBalancerArn --output text)

if [ "$ALB_ARN" = "None" ] || [ -z "$ALB_ARN" ]; then
    echo -e "${YELLOW}⚖️  Creating Application Load Balancer...${NC}"
    ALB_ARN=$(aws elbv2 create-load-balancer \
        --name gaze-detection-alb \
        --subnets $SUBNET_1_ID $SUBNET_2_ID \
        --security-groups $SECURITY_GROUP_ID \
        --region $AWS_REGION \
        --query LoadBalancers[0].LoadBalancerArn \
        --output text)
fi

# Create target group
TARGET_GROUP_ARN=$(aws elbv2 create-target-group \
    --name gaze-detection-tg \
    --protocol HTTP \
    --port 8080 \
    --vpc-id $VPC_ID \
    --target-type ip \
    --health-check-path /health \
    --region $AWS_REGION \
    --query TargetGroups[0].TargetGroupArn \
    --output text 2>/dev/null || \
    aws elbv2 describe-target-groups --names gaze-detection-tg --query TargetGroups[0].TargetGroupArn --output text)

if [ "$TARGET_GROUP_ARN" = "None" ] || [ -z "$TARGET_GROUP_ARN" ]; then
    echo -e "${YELLOW}🎯 Creating target group...${NC}"
    TARGET_GROUP_ARN=$(aws elbv2 create-target-group \
        --name gaze-detection-tg \
        --protocol HTTP \
        --port 8080 \
        --vpc-id $VPC_ID \
        --target-type ip \
        --health-check-path /health \
        --region $AWS_REGION \
        --query TargetGroups[0].TargetGroupArn \
        --output text)
fi

# Create listener
aws elbv2 create-listener \
    --load-balancer-arn $ALB_ARN \
    --protocol HTTP \
    --port 80 \
    --default-actions Type=forward,TargetGroupArn=$TARGET_GROUP_ARN \
    --region $AWS_REGION 2>/dev/null || true

# Update service definition
echo -e "${YELLOW}📝 Updating service definition...${NC}"
sed -i.bak "s/SUBNET_ID_1/$SUBNET_1_ID/g; s/SUBNET_ID_2/$SUBNET_2_ID/g; s/SECURITY_GROUP_ID/$SECURITY_GROUP_ID/g; s|TARGET_GROUP_ARN|$TARGET_GROUP_ARN|g" service-definition.json
rm -f service-definition.json.bak

# Create ECS service
echo -e "${YELLOW}🚀 Creating ECS service...${NC}"
aws ecs create-service --cli-input-json file://service-definition.json --region $AWS_REGION 2>/dev/null || \
aws ecs update-service --cluster $CLUSTER_NAME --service $SERVICE_NAME --task-definition $TASK_FAMILY --region $AWS_REGION

# Get ALB DNS name
ALB_DNS=$(aws elbv2 describe-load-balancers --load-balancer-arns $ALB_ARN --query LoadBalancers[0].DNSName --output text)

echo -e "${GREEN}✅ ECS Fargate Deployment Completed Successfully!${NC}"
echo ""
echo -e "${GREEN}📋 Deployment Summary:${NC}"
echo -e "  Cluster: $CLUSTER_NAME"
echo -e "  Service: $SERVICE_NAME"
echo -e "  Load Balancer: $ALB_DNS"
echo -e "  Region: $AWS_REGION"
echo ""
echo -e "${YELLOW}🔗 API Endpoints:${NC}"
echo -e "  Health Check: http://$ALB_DNS/health"
echo -e "  Start Stream: POST http://$ALB_DNS/start"
echo -e "  Stop Stream: POST http://$ALB_DNS/stop"
echo -e "  Status: GET http://$ALB_DNS/status"
echo -e "  Analytics: GET http://$ALB_DNS/analytics"
echo ""
echo -e "${YELLOW}📝 Example Usage:${NC}"
echo -e "  # Start processing a stream"
echo -e "  curl -X POST http://$ALB_DNS/start \\"
echo -e "    -H 'Content-Type: application/json' \\"
echo -e "    -d '{\"stream_url\": \"rtsp://your-camera-stream-url\"}'"
echo ""
echo -e "  # Check status"
echo -e "  curl http://$ALB_DNS/status"
echo ""
echo -e "  # Get analytics"
echo -e "  curl http://$ALB_DNS/analytics?limit=10"
echo ""
echo -e "${YELLOW}⚠️  Important Notes:${NC}"
echo -e "- The service will take a few minutes to start up"
echo -e "- Monitor logs: aws logs tail /ecs/gaze-detection --follow"
echo -e "- Scale the service: aws ecs update-service --cluster $CLUSTER_NAME --service $SERVICE_NAME --desired-count 2"
echo -e "- Cost: You'll be charged for Fargate compute time and ALB usage" 