import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import current_app, render_template_string


def send_email(to_email, subject, template_str, context):
    """
    Send an email using SMTP.
    
    Args:
        to_email (str): Recipient email address
        subject (str): Email subject
        template_str (str): Email template as a string
        context (dict): Variables to render in the template
    
    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    try:
        current_app.logger.info(f"Attempting to send email to {to_email}")
        
        # Ensure context is a dictionary
        if not isinstance(context, dict):
            context = dict(context)
        
        # Render the template with the provided context
        html_content = render_template_string(template_str, **context)
        
        # Create message
        message = MIMEMultipart('alternative')
        message['Subject'] = subject
        
        # Handle MAIL_DEFAULT_SENDER properly (might be tuple or string)
        sender = current_app.config['MAIL_DEFAULT_SENDER']
        if isinstance(sender, tuple):
            sender_name, sender_email = sender
            message['From'] = f"{sender_name} <{sender_email}>"
            sender_address = sender_email  # Use just the email for SMTP sendmail
        else:
            message['From'] = sender
            sender_address = sender  # Use the full string for SMTP sendmail
            
        message['To'] = to_email
        
        # Add HTML content
        message.attach(MIMEText(html_content, 'html', 'utf-8'))
        
        # Log SMTP configuration
        current_app.logger.info(f"SMTP Configuration: Server={current_app.config['MAIL_SERVER']}, Port={current_app.config['MAIL_PORT']}, TLS={current_app.config['MAIL_USE_TLS']}")
        
        # Connect to SMTP server
        with smtplib.SMTP(current_app.config['MAIL_SERVER'], current_app.config['MAIL_PORT']) as server:
            # Use TLS if configured
            if current_app.config['MAIL_USE_TLS']:
                current_app.logger.info("Starting TLS connection")
                server.starttls()
            
            # Login if credentials are provided
            if current_app.config['MAIL_USERNAME'] and current_app.config['MAIL_PASSWORD']:
                current_app.logger.info(f"Logging in with username: {current_app.config['MAIL_USERNAME']}")
                server.login(current_app.config['MAIL_USERNAME'], current_app.config['MAIL_PASSWORD'])
            
            # Send email
            current_app.logger.info("Sending email...")
            server.sendmail(
                sender_address,  # Use the properly formatted sender address
                to_email,
                message.as_string()
            )
            current_app.logger.info("Email sent successfully")
        
        return True
    
    except Exception as e:
        current_app.logger.error(f"Failed to send email: {str(e)}")
        return False


def send_verification_email(user, token):
    """
    Send email verification email.
    
    Args:
        user (User): User object
        token (str): Verification token
    
    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    # Generate verification link
    verification_link = f"{current_app.config['FRONTEND_URL']}/verify-email/{token}"
    
    # Email template
    template = """
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
            .container { max-width: 600px; margin: 0 auto; padding: 20px; }
            .header { background-color: #f8f8f8; padding: 20px; text-align: center; }
            .content { padding: 20px; }
            .button { display: inline-block; background-color: #4CAF50; color: white; padding: 10px 20px; 
                      text-decoration: none; border-radius: 5px; }
            .footer { font-size: 12px; color: #777; text-align: center; margin-top: 20px; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2>Email Verification</h2>
            </div>
            <div class="content">
                <p>Hello {{ name }},</p>
                <p>Thank you for registering with us. Please click the button below to verify your email address:</p>
                <p style="text-align: center;">
                    <a href="{{ verification_link }}" class="button">Verify Email</a>
                </p>
                <p>Or copy and paste this link in your browser:</p>
                <p>{{ verification_link }}</p>
                <p>This link will expire in 24 hours.</p>
                <p>If you did not register for an account, please ignore this email.</p>
                <p>Best regards,<br>The Team</p>
            </div>
            <div class="footer">
                This is an automated message, please do not reply to this email.
            </div>
        </div>
    </body>
    </html>
    """
    
    # Context for template rendering
    context = {
        'name': f"{user.first_name} {user.last_name}",
        'verification_link': verification_link
    }
    
    return send_email(
        user.email,
        "Verify Your Email Address",
        template,
        context
    )


def send_password_reset_email(user, token):
    """
    Send password reset email.
    
    Args:
        user (User): User object
        token (str): Password reset token
    
    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    # Generate reset link with token
    reset_link = f"{current_app.config['FRONTEND_URL']}/password/reset?token={token}"
    
    # Email template
    template = """
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body { 
                font-family: Arial, sans-serif; 
                line-height: 1.6; 
                color: #333;
                margin: 0;
                padding: 0;
                background-color: #f5f5f5;
            }
            .container { 
                max-width: 600px; 
                margin: 20px auto; 
                padding: 20px;
                background-color: #ffffff;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            .header { 
                background-color: #4CAF50;
                padding: 20px; 
                text-align: center;
                border-radius: 8px 8px 0 0;
                color: white;
            }
            .content { 
                padding: 20px;
                color: #333;
            }
            .button { 
                display: inline-block; 
                background-color: #4CAF50; 
                color: white; 
                padding: 12px 24px; 
                text-decoration: none; 
                border-radius: 5px;
                font-weight: bold;
                margin: 20px 0;
            }
            .button:hover {
                background-color: #45a049;
            }
            .footer { 
                font-size: 12px; 
                color: #777; 
                text-align: center; 
                margin-top: 20px;
                padding-top: 20px;
                border-top: 1px solid #eee;
            }
            .link {
                word-break: break-all;
                color: #4CAF50;
                text-decoration: none;
            }
            .link:hover {
                text-decoration: underline;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2>Password Reset Request</h2>
            </div>
            <div class="content">
                <p>Hello {{ name }},</p>
                <p>We received a request to reset your password. Click the button below to create a new password:</p>
                <p style="text-align: center;">
                    <a href="{{ reset_link }}" class="button">Reset Password</a>
                </p>
                <p>Or copy and paste this link in your browser:</p>
                <p><a href="{{ reset_link }}" class="link">{{ reset_link }}</a></p>
                <p><strong>Important:</strong> This link will expire in 1 hour.</p>
                <p>If you did not request a password reset, please ignore this email.</p>
                <p>Best regards,<br>The Team</p>
            </div>
            <div class="footer">
                This is an automated message, please do not reply to this email.
            </div>
        </div>
    </body>
    </html>
    """
    
    # Context for template rendering
    context = {
        'name': f"{user.first_name} {user.last_name}",
        'reset_link': reset_link
    }
    
    return send_email(
        user.email,
        "Reset Your Password",
        template,
        context
    )


def send_merchant_docs_submitted_to_admin(merchant_profile, admin_email_list=None): 
    """
    Notify super admins that a merchant has submitted documents.
    """
    from .utils import get_super_admin_emails 

    if admin_email_list is None: 
        admin_email_list = get_super_admin_emails()

    if not admin_email_list:
        current_app.logger.info("No super admin emails found to send merchant submission notice.")
        return False
    
    if not admin_email_list:
        current_app.logger.info("No super admin emails found to send merchant submission notice.")
        return False

    frontend_url = current_app.config['FRONTEND_URL']
   
    merchant_user = merchant_profile.user 
    merchant_name = f"{merchant_user.first_name} {merchant_user.last_name}" if merchant_user else "N/A"


    subject = f"Merchant Document Submission: {merchant_profile.business_name}"
    admin_link = f"{frontend_url}/superadmin/merchant-management" 

    template = """
    <!DOCTYPE html>
    <html>
    <head>
        <style> /* Basic styles, similar to other templates */ </style>
    </head>
    <body>
        <div class="container">
            <div class="header"><h2>Merchant Document Submission</h2></div>
            <div class="content">
                <p>Hello Admin,</p>
                <p>The merchant '<strong>{{ business_name }}</strong>' (User: {{ merchant_name }}) has submitted their documents for verification.</p>
                <p>Please review their submission in the admin panel:</p>
                <p style="text-align: center;">
                    <a href="{{ admin_link }}" class="button">Review Documents</a>
                </p>
                <p>Or copy and paste this link into your browser:</p>
                <p>{{ admin_link }}</p>
                <p>Thank you.</p>
            </div>
            <div class="footer">Automated Notification</div>
        </div>
    </body>
    </html>
    """
    context = {
        'business_name': merchant_profile.business_name,
        'merchant_name': merchant_name,
        'admin_link': admin_link
    }

    all_sent = True
    for admin_email in admin_email_list:
        if not send_email(admin_email, subject, template, context):
            all_sent = False
            current_app.logger.error(f"Failed to send submission notice to admin {admin_email} for merchant {merchant_profile.business_name}")
    return all_sent

def send_merchant_document_rejection_email(merchant_user, merchant_profile, document, admin_notes):
    """
    Notify merchant about a specific document rejection.
    """
    frontend_url = current_app.config['FRONTEND_URL']
    merchant_dashboard_link = f"{frontend_url}/business/verification" 
    
    subject = f"Action Required: Document Rejected for {merchant_profile.business_name}"
    template = """
    <!DOCTYPE html>
    <html>
    <head> <style> /* Basic styles */ </style> </head>
    <body>
        <div class="container">
            <div class="header"><h2>Document Rejection Notice</h2></div>
            <div class="content">
                <p>Dear {{ user_name }},</p>
                <p>We are writing to inform you that your submitted document, <strong>{{ document_type }}</strong>, for your merchant profile '<strong>{{ business_name }}</strong>' has been rejected.</p>
                <p><strong>Reason for rejection:</strong></p>
                <p>{{ admin_notes }}</p>
                <p>Please log in to your merchant dashboard to review the details and upload the corrected document(s).</p>
                <p style="text-align: center;">
                    <a href="{{ merchant_link }}" class="button">Go to Dashboard</a>
                </p>
                <p>If you have any questions, please contact our support team.</p>
                <p>Sincerely,<br>The Verification Team</p>
            </div>
            <div class="footer">Automated Notification</div>
        </div>
    </body>
    </html>
    """
    context = {
        'user_name': f"{merchant_user.first_name} {merchant_user.last_name}",
        'business_name': merchant_profile.business_name,
        'document_type': document.document_type.value.replace('_', ' ').title(),
        'admin_notes': admin_notes or "No specific reason provided. Please check your dashboard.",
        'merchant_link': merchant_dashboard_link
    }
    return send_email(merchant_user.email, subject, template, context)

def send_merchant_profile_rejection_email(merchant_user, merchant_profile, reason):
    """
    Notify merchant about overall profile rejection.
    """
    frontend_url = current_app.config['FRONTEND_URL']
    merchant_dashboard_link = f"{frontend_url}/business/verification" 

    subject = f"Important: Your Merchant Profile for {merchant_profile.business_name} was Rejected"
    template = """
    <!DOCTYPE html>
    <html>
    <head> <style> /* Basic styles */ </style> </head>
    <body>
        <div class="container">
            <div class="header"><h2>Merchant Profile Rejection</h2></div>
            <div class="content">
                <p>Dear {{ user_name }},</p>
                <p>We regret to inform you that your merchant profile '<strong>{{ business_name }}</strong>' has been rejected.</p>
                <p><strong>Reason for rejection:</strong></p>
                <p>{{ reason }}</p>
                <p>Please review the feedback and contact our support team if you have questions or wish to re-apply after addressing the issues.</p>
                 <p style="text-align: center;">
                    <a href="{{ merchant_link }}" class="button">Visit Dashboard</a>
                </p>
                <p>Sincerely,<br>The Verification Team</p>
            </div>
            <div class="footer">Automated Notification</div>
        </div>
    </body>
    </html>
    """
    context = {
        'user_name': f"{merchant_user.first_name} {merchant_user.last_name}",
        'business_name': merchant_profile.business_name,
        'reason': reason or "Please check your merchant dashboard for details or contact support.",
        'merchant_link': merchant_dashboard_link
    }
    return send_email(merchant_user.email, subject, template, context)

def send_merchant_profile_approval_email(merchant_user, merchant_profile):
    """
    Notify merchant about profile approval.
    """
    frontend_url = current_app.config['FRONTEND_URL']
    merchant_dashboard_link = f"{frontend_url}/business/verification" 

    subject = f"Congratulations! Your Merchant Profile for {merchant_profile.business_name} is Approved"
    template = """
    <!DOCTYPE html>
    <html>
    <head> <style> /* Basic styles */ </style> </head>
    <body>
        <div class="container">
            <div class="header"><h2>Merchant Profile Approved!</h2></div>
            <div class="content">
                <p>Dear {{ user_name }},</p>
                <p>Congratulations! We are pleased to inform you that your merchant profile '<strong>{{ business_name }}</strong>' has been successfully verified and approved.</p>
                <p>You can now access all merchant features and start managing your store.</p>
                <p style="text-align: center;">
                    <a href="{{ merchant_link }}" class="button">Go to Your Dashboard</a>
                </p>
                <p>Welcome aboard!</p>
                <p>Sincerely,<br>The Team</p>
            </div>
            <div class="footer">Automated Notification</div>
        </div>
    </body>
    </html>
    """
    context = {
        'user_name': f"{merchant_user.first_name} {merchant_user.last_name}",
        'business_name': merchant_profile.business_name,
        'merchant_link': merchant_dashboard_link
    }
    return send_email(merchant_user.email, subject, template, context)