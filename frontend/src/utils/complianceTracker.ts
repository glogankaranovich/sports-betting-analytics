// Compliance tracking utilities
export interface ComplianceData {
  ageVerified: boolean;
  termsAccepted: boolean;
  timestamp: string;
  userAgent: string;
  sessionId: string;
}

export interface UserAction {
  action: string;
  timestamp: string;
  data?: any;
}

class ComplianceTracker {
  private sessionId: string;
  private auditLog: UserAction[] = [];

  constructor() {
    this.sessionId = this.generateSessionId();
    this.loadAuditLog();
  }

  private generateSessionId(): string {
    return `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  private loadAuditLog(): void {
    const stored = localStorage.getItem('auditLog');
    if (stored) {
      this.auditLog = JSON.parse(stored);
    }
  }

  private saveAuditLog(): void {
    localStorage.setItem('auditLog', JSON.stringify(this.auditLog));
  }

  logAction(action: string, data?: any): void {
    const logEntry: UserAction = {
      action,
      timestamp: new Date().toISOString(),
      data
    };
    
    this.auditLog.push(logEntry);
    this.saveAuditLog();
    
    // Also send to backend for permanent storage
    this.sendToBackend(logEntry);
  }

  private async sendToBackend(logEntry: UserAction): Promise<void> {
    try {
      const complianceApiUrl = 'https://8676c11fr3.execute-api.us-east-1.amazonaws.com/prod';
      await fetch(`${complianceApiUrl}/compliance/log`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          sessionId: this.sessionId,
          ...logEntry
        })
      });
    } catch (error) {
      console.error('Failed to send compliance log:', error);
    }
  }

  checkAgeVerification(): boolean {
    const stored = localStorage.getItem('ageVerified');
    if (!stored) return false;
    
    const data = JSON.parse(stored);
    const verificationDate = new Date(data.timestamp);
    const now = new Date();
    const daysDiff = (now.getTime() - verificationDate.getTime()) / (1000 * 3600 * 24);
    
    // Age verification expires after 30 days
    return daysDiff < 30;
  }

  checkTermsAcceptance(): boolean {
    const stored = localStorage.getItem('termsAcceptance');
    if (!stored) return false;
    
    const data = JSON.parse(stored);
    return data.termsAccepted && data.privacyAccepted && data.risksAccepted;
  }

  getComplianceStatus(): ComplianceData {
    return {
      ageVerified: this.checkAgeVerification(),
      termsAccepted: this.checkTermsAcceptance(),
      timestamp: new Date().toISOString(),
      userAgent: navigator.userAgent,
      sessionId: this.sessionId
    };
  }

  clearUserData(): void {
    localStorage.removeItem('ageVerified');
    localStorage.removeItem('termsAcceptance');
    localStorage.removeItem('auditLog');
    this.auditLog = [];
    this.logAction('user_data_cleared');
  }

  exportUserData(): string {
    const ageData = localStorage.getItem('ageVerified');
    const termsData = localStorage.getItem('termsAcceptance');
    
    return JSON.stringify({
      ageVerification: ageData ? JSON.parse(ageData) : null,
      termsAcceptance: termsData ? JSON.parse(termsData) : null,
      auditLog: this.auditLog,
      sessionId: this.sessionId,
      exportTimestamp: new Date().toISOString()
    }, null, 2);
  }
}

export const complianceTracker = new ComplianceTracker();
