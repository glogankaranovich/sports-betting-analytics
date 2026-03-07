"""
Benny Weekly Email Reporter
Sends weekly performance reports to subscribed users
"""
import json
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List
import boto3
from benny_trader import BennyTrader

ses = boto3.client('ses', region_name='us-east-1')
dynamodb = boto3.resource('dynamodb')

ENVIRONMENT = os.environ.get('ENVIRONMENT', 'dev')
FRONTEND_URL = os.environ.get('FRONTEND_URL', 'https://dev.carpoolbets.com')
FROM_EMAIL = os.environ.get('FROM_EMAIL', 'noreply@carpoolbets.com')


def load_template() -> str:
    """Load HTML email template"""
    template_path = os.path.join(os.path.dirname(__file__), 'templates', 'benny_weekly_report.html')
    with open(template_path, 'r') as f:
        return f.read()


def render_template(template: str, data: Dict[str, Any]) -> str:
    """Simple template rendering (Handlebars-style)"""
    html = template
    
    # Replace simple variables
    for key, value in data.items():
        if isinstance(value, (str, int, float)):
            html = html.replace(f'{{{{{key}}}}}', str(value))
    
    # Handle nested object properties (e.g., {{best_bet.game}})
    for key, value in data.items():
        if isinstance(value, dict):
            for nested_key, nested_value in value.items():
                html = html.replace(f'{{{{{key}.{nested_key}}}}}', str(nested_value))
    
    # Handle conditionals
    for key in ['has_pending_bets', 'has_completed_bets', 'has_notable_bets', 'has_ai_impact', 'best_bet', 'worst_bet']:
        if_block = f'{{{{#if {key}}}}}'
        endif_block = f'{{{{/if}}}}'
        
        if if_block in html:
            start = html.find(if_block)
            end = html.find(endif_block, start)
            
            if start != -1 and end != -1:
                content = html[start + len(if_block):end]
                
                if data.get(key):
                    html = html[:start] + content + html[end + len(endif_block):]
                else:
                    html = html[:start] + html[end + len(endif_block):]
    
    # Handle loops
    for list_key in ['pending_bets_list', 'completed_bets_list']:
        each_block = f'{{{{#each {list_key}}}}}'
        endeach_block = '{{/each}}'
        
        if each_block in html:
            start = html.find(each_block)
            end = html.find(endeach_block, start)
            
            if start != -1 and end != -1:
                template_item = html[start + len(each_block):end]
                items_html = ''
                
                for item in data.get(list_key, []):
                    item_html = template_item
                    for key, value in item.items():
                        item_html = item_html.replace(f'{{{{this.{key}}}}}', str(value))
                    items_html += item_html
                
                html = html[:start] + items_html + html[end + len(endeach_block):]
    
    return html


def prepare_email_data(dashboard_data: Dict[str, Any], report_type: str = 'weekly') -> Dict[str, Any]:
    """Prepare data for email template"""
    now = datetime.utcnow()
    start_date = now - timedelta(days=7 if report_type == 'weekly' else 1)
    
    # Format dates - only show year on end date
    week_start = start_date.strftime('%b %d')
    week_end = now.strftime('%b %d, %Y')
    
    # Calculate bankroll change
    bankroll = dashboard_data['current_bankroll']
    weekly_budget = dashboard_data['weekly_budget']
    bankroll_change = bankroll - weekly_budget
    bankroll_change_str = f"+${bankroll_change:.2f}" if bankroll_change >= 0 else f"-${abs(bankroll_change):.2f}"
    bankroll_change_color = "#10b981" if bankroll_change >= 0 else "#ef4444"
    
    # ROI color
    roi = dashboard_data['roi'] * 100
    roi_color = "#10b981" if roi >= 0 else "#ef4444"
    roi_str = f"+{roi:.1f}" if roi >= 0 else f"{roi:.1f}"
    
    # Pending bets
    pending_bets_list = []
    completed_bets_list = []
    
    for bet in dashboard_data['recent_bets']:
        bet_data = {
            'game': bet['game'],
            'prediction': bet['prediction'],
            'confidence': f"{bet['final_confidence'] * 100:.0f}",
            'stake': f"{bet['bet_amount']:.2f}"
        }
        
        if bet['status'] == 'pending':
            pending_bets_list.append(bet_data)
        else:
            result = f"+${bet['payout']:.2f}" if bet['status'] == 'won' else f"-${bet['bet_amount']:.2f}"
            result_color = "#10b981" if bet['status'] == 'won' else "#ef4444"
            border_color = "#10b981" if bet['status'] == 'won' else "#ef4444"
            
            completed_bets_list.append({
                **bet_data,
                'result': result,
                'result_color': result_color,
                'border_color': border_color
            })
    
    # Limit completed bets to 10 most recent
    completed_bets_list = completed_bets_list[:10]
    
    return {
        'report_type': report_type.capitalize(),
        'week_start': week_start,
        'week_end': week_end,
        'current_bankroll': f"{bankroll:.2f}",
        'bankroll_change': bankroll_change_str,
        'bankroll_change_color': bankroll_change_color,
        'win_rate': f"{dashboard_data['win_rate'] * 100:.1f}",
        'total_bets': dashboard_data['total_bets'] - dashboard_data['pending_bets'],
        'roi': roi_str,
        'roi_color': roi_color,
        'pending_bets': dashboard_data['pending_bets'],
        'has_pending_bets': len(pending_bets_list) > 0,
        'pending_bets_list': pending_bets_list,
        'has_completed_bets': len(completed_bets_list) > 0,
        'completed_bets_list': completed_bets_list,
        'has_notable_bets': dashboard_data['best_bet'] or dashboard_data['worst_bet'],
        'best_bet': {
            'game': dashboard_data['best_bet']['game'],
            'profit': f"{dashboard_data['best_bet']['profit']:.2f}"
        } if dashboard_data['best_bet'] else None,
        'worst_bet': {
            'game': dashboard_data['worst_bet']['game'],
            'loss': f"{dashboard_data['worst_bet']['loss']:.2f}"
        } if dashboard_data['worst_bet'] else None,
        'has_ai_impact': dashboard_data['ai_impact']['win_rate'] is not None,
        'ai_win_rate': f"{dashboard_data['ai_impact']['win_rate'] * 100:.1f}" if dashboard_data['ai_impact']['win_rate'] else "0.0",
        'ai_bets_count': dashboard_data['ai_impact']['bets_count'],
        'dashboard_url': f"{FRONTEND_URL}/benny",
        'unsubscribe_url': f"{FRONTEND_URL}/settings?unsubscribe=benny_weekly",
        'settings_url': f"{FRONTEND_URL}/settings"
    }


def get_subscribed_users() -> List[str]:
    """Get list of users subscribed to Benny weekly reports"""
    table = dynamodb.Table(f'carpool-bets-v2-{ENVIRONMENT}')
    
    try:
        response = table.query(
            IndexName='GenericQueryIndex',
            KeyConditionExpression='gsi_pk = :pk',
            ExpressionAttributeValues={
                ':pk': 'NOTIFICATION#BENNY_WEEKLY#EMAIL'
            },
            ProjectionExpression='email, gsi_sk'
        )
        
        # Get email from either 'email' attribute or 'gsi_sk' (which stores email)
        emails = []
        for item in response.get('Items', []):
            email = item.get('email') or item.get('gsi_sk')
            if email:
                emails.append(email)
        
        return emails if emails else [os.environ.get('ADMIN_EMAIL', 'glogankaranovich@gmail.com')]
    except Exception as e:
        print(f"Error fetching subscribed users: {e}")
        return [os.environ.get('ADMIN_EMAIL', 'glogankaranovich@gmail.com')]


def send_email(to_email: str, subject: str, html_body: str):
    """Send email via SES"""
    try:
        response = ses.send_email(
            Source=FROM_EMAIL,
            Destination={'ToAddresses': [to_email]},
            Message={
                'Subject': {'Data': subject, 'Charset': 'UTF-8'},
                'Body': {
                    'Html': {'Data': html_body, 'Charset': 'UTF-8'}
                }
            }
        )
        print(f"Email sent to {to_email}: {response['MessageId']}")
        return True
    except Exception as e:
        print(f"Failed to send email to {to_email}: {e}")
        return False


def lambda_handler(event, context):
    """Lambda handler for Benny reports (daily or weekly)"""
    try:
        report_type = event.get('report_type', 'weekly')
        print(f"Generating Benny {report_type} report...")
        
        # Get dashboard data
        dashboard_data = BennyTrader.get_dashboard_data()
        
        # Load and render template
        template = load_template()
        email_data = prepare_email_data(dashboard_data, report_type)
        html_body = render_template(template, email_data)
        
        # Get subscribed users
        subscribers = get_subscribed_users()
        print(f"Found {len(subscribers)} subscribers")
        
        # Send emails
        sent_count = 0
        failed_count = 0
        
        subject_prefix = "🤖 Benny's Daily Update" if report_type == 'daily' else "🤖 Benny's Weekly Report"
        
        for email in subscribers:
            if send_email(
                to_email=email,
                subject=f"{subject_prefix} - {email_data['week_start']} to {email_data['week_end']}",
                html_body=html_body
            ):
                sent_count += 1
            else:
                failed_count += 1
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': f'{report_type.capitalize()} report sent',
                'sent': sent_count,
                'failed': failed_count
            })
        }
        
    except Exception as e:
        print(f"Error generating report: {e}")
        import traceback
        traceback.print_exc()
        
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
