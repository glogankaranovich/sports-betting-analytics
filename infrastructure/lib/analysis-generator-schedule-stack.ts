import * as cdk from 'aws-cdk-lib';
import * as events from 'aws-cdk-lib/aws-events';
import * as targets from 'aws-cdk-lib/aws-events-targets';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import { Construct } from 'constructs';

export interface AnalysisGeneratorScheduleStackProps extends cdk.StackProps {
  environment: string;
  analysisGeneratorNBA: lambda.IFunction;
  analysisGeneratorNFL: lambda.IFunction;
  analysisGeneratorMLB: lambda.IFunction;
  analysisGeneratorNHL: lambda.IFunction;
  analysisGeneratorEPL: lambda.IFunction;
}

export class AnalysisGeneratorScheduleStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props: AnalysisGeneratorScheduleStackProps) {
    super(scope, id, props);

    const sports = [
      { name: 'NBA', lambda: props.analysisGeneratorNBA },
      { name: 'NFL', lambda: props.analysisGeneratorNFL },
      { name: 'MLB', lambda: props.analysisGeneratorMLB },
      { name: 'NHL', lambda: props.analysisGeneratorNHL },
      { name: 'EPL', lambda: props.analysisGeneratorEPL }
    ];

    const models = ['consensus', 'value', 'momentum', 'contrarian', 'hot_cold', 'rest_schedule', 'matchup', 'injury_aware'];
    const betTypes = ['games', 'props'];

    // Analysis generation - every 4 hours for each sport
    sports.forEach(sport => {
      models.forEach((model, modelIndex) => {
        betTypes.forEach((betType, betTypeIndex) => {
          // Stagger executions by 1 minute each to avoid overwhelming the system
          const minuteOffset = (modelIndex * betTypes.length + betTypeIndex) * 1;
          
          new events.Rule(this, `AnalysisRule${sport.name}${model}${betType}`, {
            schedule: events.Schedule.rate(cdk.Duration.hours(4)),
            description: `Generate ${sport.name} ${betType} analyses using ${model} model every 4 hours`,
            targets: [new targets.LambdaFunction(sport.lambda, {
              event: events.RuleTargetInput.fromObject({
                model: model,
                bet_type: betType
              })
            })]
          });
        });
      });
    });
  }
}
