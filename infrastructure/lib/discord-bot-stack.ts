import * as cdk from 'aws-cdk-lib';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as apigateway from 'aws-cdk-lib/aws-apigateway';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import { Construct } from 'constructs';

export interface DiscordBotStackProps extends cdk.StackProps {
  environment: string;
  table: dynamodb.ITable;
}

export class DiscordBotStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props: DiscordBotStackProps) {
    super(scope, id, props);

    const { environment, table } = props;

    const botLambda = new lambda.Function(this, 'BennyDiscordBot', {
      functionName: `benny-discord-bot-${environment}`,
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'benny_discord_bot.handler',
      code: lambda.Code.fromAsset('../backend', {
        bundling: {
          image: lambda.Runtime.PYTHON_3_11.bundlingImage,
          command: [
            'bash', '-c',
            'pip install -r requirements.txt -t /asset-output && cp -au . /asset-output'
          ],
        },
      }),
      timeout: cdk.Duration.seconds(30),
      memorySize: 512,
      environment: {
        DYNAMODB_TABLE: table.tableName,
        DISCORD_PUBLIC_KEY: 'f664d65bb12412b314a6faefa30bc7d6e9e75b1393f8599f0aecec498a47e820',
      },
    });

    table.grantReadData(botLambda);

    botLambda.addToRolePolicy(new iam.PolicyStatement({
      actions: ['bedrock:InvokeModel'],
      resources: ['*'],
    }));

    botLambda.addToRolePolicy(new iam.PolicyStatement({
      actions: ['lambda:InvokeFunction'],
      resources: ['*'],
    }));

    const api = new apigateway.RestApi(this, 'BennyBotApi', {
      restApiName: `benny-discord-bot-${environment}`,
    });

    const interactions = api.root.addResource('interactions');
    interactions.addMethod('POST', new apigateway.LambdaIntegration(botLambda));

    new cdk.CfnOutput(this, 'BotEndpoint', {
      value: `${api.url}interactions`,
      description: 'Discord Interactions Endpoint URL',
    });
  }
}
