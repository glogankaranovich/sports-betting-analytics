import * as cdk from 'aws-cdk-lib';
import * as events from 'aws-cdk-lib/aws-events';
import * as targets from 'aws-cdk-lib/aws-events-targets';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import { Construct } from 'constructs';

export interface AnalysisGeneratorScheduleStackProps extends cdk.StackProps {
  environment: string;
  sport: { key: string; name: string; months: string };
  analysisGeneratorFunction: lambda.IFunction;
}

export class AnalysisGeneratorScheduleStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props: AnalysisGeneratorScheduleStackProps) {
    super(scope, id, props);

    const { sport, analysisGeneratorFunction } = props;

    const models = ['consensus', 'value', 'momentum', 'contrarian', 'hot_cold', 'rest_schedule', 'matchup', 'injury_aware'];
    
    // Run analysis every 4 hours, 30 minutes after odds collection
    const analysisHours = ['0', '4', '8', '12', '16', '20'];
    
    analysisHours.forEach(hour => {
      models.forEach((model, index) => {
        // Game analysis
        new events.Rule(this, `${model}GameAnalysis${hour}`, {
          schedule: events.Schedule.cron({ minute: `${30 + index * 2}`, hour, month: sport.months }),
          description: `Generate ${model} ${sport.name} game analyses at ${hour}:${30 + index * 2} UTC`,
          targets: [new targets.LambdaFunction(analysisGeneratorFunction, {
            event: events.RuleTargetInput.fromObject({ model, bet_type: 'games', sport: sport.key })
          })]
        });

        // Prop analysis
        new events.Rule(this, `${model}PropAnalysis${hour}`, {
          schedule: events.Schedule.cron({ minute: `${46 + index * 2}`, hour, month: sport.months }),
          description: `Generate ${model} ${sport.name} prop analyses at ${hour}:${46 + index * 2} UTC`,
          targets: [new targets.LambdaFunction(analysisGeneratorFunction, {
            event: events.RuleTargetInput.fromObject({ model, bet_type: 'props', sport: sport.key })
          })]
        });
      });
    });
  }
}
