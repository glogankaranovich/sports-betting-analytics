#!/usr/bin/env node
import * as cdk from 'aws-cdk-lib';
import * as events from 'aws-cdk-lib/aws-events';
import * as targets from 'aws-cdk-lib/aws-events-targets';
import * as ecs from 'aws-cdk-lib/aws-ecs';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as iam from 'aws-cdk-lib/aws-iam';
import { Construct } from 'constructs';
import { PLATFORM_CONSTANTS } from './utils/constants';

export interface EcsScheduleStackProps extends cdk.StackProps {
  stage: string;
  cluster: ecs.ICluster;
  propsCollectorTask: ecs.FargateTaskDefinition;
  analysisGeneratorTask: ecs.FargateTaskDefinition;
  bennyTraderTask: ecs.FargateTaskDefinition;
}

export class EcsScheduleStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props: EcsScheduleStackProps) {
    super(scope, id, props);

    // EventBridge execution role
    const eventRole = new iam.Role(this, 'EventBridgeEcsRole', {
      assumedBy: new iam.ServicePrincipal('events.amazonaws.com'),
    });

    eventRole.addToPolicy(
      new iam.PolicyStatement({
        actions: ['ecs:RunTask'],
        resources: [
          props.propsCollectorTask.taskDefinitionArn,
          props.analysisGeneratorTask.taskDefinitionArn,
          props.bennyTraderTask.taskDefinitionArn,
        ],
      })
    );

    eventRole.addToPolicy(
      new iam.PolicyStatement({
        actions: ['iam:PassRole'],
        resources: ['*'],
        conditions: {
          StringLike: {
            'iam:PassedToService': 'ecs-tasks.amazonaws.com',
          },
        },
      })
    );

    const subnetSelection: ec2.SubnetSelection = { subnetType: ec2.SubnetType.PUBLIC };

    // Props Collector - every 6 hours
    new events.Rule(this, 'PropsCollectorSchedule', {
      schedule: events.Schedule.cron({ minute: '0', hour: '*/6' }),
      targets: [
        new targets.EcsTask({
          cluster: props.cluster,
          taskDefinition: props.propsCollectorTask,
          role: eventRole,
          subnetSelection,
          assignPublicIp: true,
        }),
      ],
    });

    // Analysis Generators - every 4 hours for each sport, staggered
    const sports = PLATFORM_CONSTANTS.SUPPORTED_SPORTS.split(',');
    const models = PLATFORM_CONSTANTS.SYSTEM_MODELS.split(',').filter(m => m !== 'benny');
    const betTypes = ['games', 'props'];

    let globalOffset = 0;
    sports.forEach((sport) => {
      models.forEach((model) => {
        betTypes.forEach((betType) => {
          const minute = globalOffset % 60;
          const hourOffset = Math.floor(globalOffset / 60);

          new events.Rule(this, `AnalysisGen-${sport}-${model}-${betType}`, {
            schedule: events.Schedule.cron({
              minute: minute.toString(),
              hour: `${hourOffset}/4`,
            }),
            targets: [
              new targets.EcsTask({
                cluster: props.cluster,
                taskDefinition: props.analysisGeneratorTask,
                role: eventRole,
                subnetSelection,
                assignPublicIp: true,
                containerOverrides: [
                  {
                    containerName: 'AnalysisGenerator',
                    environment: [
                      { name: 'SPORT', value: sport },
                      { name: 'MODEL', value: model },
                      { name: 'BET_TYPE', value: betType },
                    ],
                  },
                ],
              }),
            ],
          });

          globalOffset += 2;
        });
      });
    });

    // Benny Trader - multiple times daily for cash-out and double-down opportunities
    // 8 AM, 12 PM, 4 PM, 8 PM ET (13:00, 17:00, 21:00, 01:00 UTC)
    const bennySchedules = [
      { hour: '13', name: 'Morning' },   // 8 AM ET
      { hour: '17', name: 'Midday' },    // 12 PM ET
      { hour: '21', name: 'Afternoon' }, // 4 PM ET
      { hour: '1', name: 'Evening' },    // 8 PM ET
    ];

    bennySchedules.forEach((schedule) => {
      new events.Rule(this, `BennyTraderSchedule${schedule.name}`, {
        schedule: events.Schedule.cron({ minute: '0', hour: schedule.hour }),
        targets: [
          new targets.EcsTask({
            cluster: props.cluster,
            taskDefinition: props.bennyTraderTask,
            role: eventRole,
            subnetSelection,
            assignPublicIp: true,
          }),
        ],
      });
    });
  }
}
