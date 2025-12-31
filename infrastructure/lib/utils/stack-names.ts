/**
 * Centralized stack name generator for consistent naming across all environments
 */
export class StackNames {
  /**
   * Generate consistent stack name: {Environment}-{StackName}
   * @param environment - The environment (dev, beta, prod)
   * @param stackName - The base stack name (DynamoDB, OddsCollector, etc.)
   * @returns Formatted stack name
   */
  static forEnvironment(environment: string, stackName: string): string {
    const envName = environment.charAt(0).toUpperCase() + environment.slice(1).toLowerCase();
    return `${envName}-${stackName}`;
  }
}
