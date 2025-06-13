from flask import Flask, render_template, request, redirect, url_for, flash, send_file, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
import requests
import json
from dotenv import load_dotenv
import base64
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
import tempfile
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_migrate import Migrate



load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
# app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///techelar.db'
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://techelar_user:Kevin254!@69.197.187.23:5432/techelar?sslmode=disable'
# app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:Kevin254!@localhost:5432/techelar'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Email Configuration
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER')

db = SQLAlchemy(app)
migrate = Migrate(app, db)

app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)

# M-Pesa Configuration
MPESA_CONSUMER_KEY = os.getenv('MPESA_CONSUMER_KEY')
MPESA_CONSUMER_SECRET = os.getenv('MPESA_CONSUMER_SECRET')
MPESA_PASSKEY = os.getenv('MPESA_PASSKEY')
MPESA_SHORTCODE = os.getenv('MPESA_SHORTCODE')
MPESA_ENV = os.getenv('MPESA_ENV', 'sandbox')
MPESA_CALLBACK_URL = os.getenv('MPESA_CALLBACK_URL', 'https://your-domain.com/mpesa/callback')

# Database Models
class Registration(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    admission_number = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    appointment_date = db.Column(db.Date, nullable=False)
    business_name = db.Column(db.String(100))
    course_type = db.Column(db.String(20), nullable=False)
    duration = db.Column(db.String(20), nullable=False)
    payment_status = db.Column(db.String(20), default='pending')
    phone = db.Column(db.String(15),nullable=False)
    payment_amount = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __init__(self, *args, **kwargs):
        super(Registration, self).__init__(*args, **kwargs)
        if not self.admission_number:
            self.generate_admission_number()

    def generate_admission_number(self):
        """Generate a unique admission number starting with TElar1000"""
        last_registration = Registration.query.order_by(Registration.id.desc()).first()
        if last_registration and last_registration.admission_number:
            last_number = int(last_registration.admission_number.replace('TElar', ''))
            self.admission_number = f'TElar{last_number + 1}'
        else:
            self.admission_number = 'TElar1000'

def get_mpesa_access_token():
    """Get M-Pesa access token"""
    try:
        url = f"https://{'sandbox' if MPESA_ENV == 'sandbox' else 'api'}.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
        auth = (MPESA_CONSUMER_KEY, MPESA_CONSUMER_SECRET)
        response = requests.get(url, auth=auth)
        
        # Log the response for debugging
        print(f"Access Token Response Status: {response.status_code}")
        print(f"Access Token Response Content: {response.text}")
        
        if response.status_code != 200:
            raise Exception(f"Failed to get access token. Status code: {response.status_code}")
            
        return response.json().get('access_token')
    except Exception as e:
        print(f"Error getting M-Pesa access token: {str(e)}")
        return None

def initiate_stk_push(phone_number, amount, account_reference):
    """Initiate M-Pesa STK Push"""
    try:
        access_token = get_mpesa_access_token()
        if not access_token:
            raise Exception("Failed to get access token")
            
        url = f"https://{'sandbox' if MPESA_ENV == 'sandbox' else 'api'}.safaricom.co.ke/mpesa/stkpush/v1/processrequest"
        
        # Format phone number to include country code
        if phone_number.startswith('0'):
            phone_number = '254' + phone_number[1:]
        elif phone_number.startswith('+'):
            phone_number = phone_number[1:]
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        password = base64.b64encode(f"{MPESA_SHORTCODE}{MPESA_PASSKEY}{timestamp}".encode()).decode()
        
        payload = {
            "BusinessShortCode": MPESA_SHORTCODE,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": amount,
            "PartyA": phone_number,
            "PartyB": MPESA_SHORTCODE,
            "PhoneNumber": phone_number,
            "CallBackURL": MPESA_CALLBACK_URL,
            "AccountReference": account_reference,
            "TransactionDesc": "WordPress Course Payment"
        }
        
        print(f"STK Push Request Payload: {json.dumps(payload, indent=2)}")
        
        response = requests.post(url, headers=headers, json=payload)
        print(f"STK Push Response Status: {response.status_code}")
        print(f"STK Push Response Content: {response.text}")
        
        if response.status_code != 200:
            raise Exception(f"Failed to initiate STK Push. Status code: {response.status_code}")
            
        return response.json()
    except Exception as e:
        print(f"Error initiating STK Push: {str(e)}")
        return None

def send_email(to_email, subject, message):
    """Send email using SMTP"""
    try:
        msg = MIMEMultipart()
        msg['From'] = app.config['MAIL_DEFAULT_SENDER']
        msg['To'] = to_email
        msg['Subject'] = subject

        # Create HTML message
        html = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #3498db;">New Contact Form Submission</h2>
                    <p><strong>Message:</strong></p>
                    <p style="background-color: #f8f9fa; padding: 15px; border-radius: 5px;">{message}</p>
                    <hr style="border: 1px solid #eee; margin: 20px 0;">
                    <p style="color: #666; font-size: 12px;">This is an automated message from the TechElar contact form.</p>
                </div>
            </body>
        </html>
        """
        
        msg.attach(MIMEText(html, 'html'))

        # Connect to SMTP server and send email
        with smtplib.SMTP(app.config['MAIL_SERVER'], app.config['MAIL_PORT']) as server:
            server.starttls()
            server.login(app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
            server.send_message(msg)
            
        return True
    except Exception as e:
        print(f"Error sending email: {str(e)}")
        return False

# Routes
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/courses')
def courses():
    return render_template('courses.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            # Get form data
            name = request.form['name']
            email = request.form['email']
            appointment_date = datetime.strptime(request.form['appointment_date'], '%Y-%m-%d').date() # business_name = request.form.get('business_name')
            course_type = request.form['course_type']
            duration = request.form['duration']
            phone = request.form['phone']
            print(course_type)
            print(duration)
            # Determine course cost based on course type and duration
            if course_type == 'wordpress':
                if duration == '1_month':
                    payment_amount = 15000
                elif duration == '3_months':
                    payment_amount = 45000
                else:
                    payment_amount = 0
            elif course_type == 'web_dev':
                if duration == '2_months':
                    payment_amount = 25000
                    
                else:
                    payment_amount = 50000
            elif course_type == 'digital_marketing':
                if duration == '2_months_digital':
                    payment_amount = 20000
                else:
                    payment_amount = 35000
            elif course_type == 'fullstack':
                print(duration)
                if duration == '4_months_fullstack':
                    payment_amount = 50000
            else:
                payment_amount = 0

            # Create registration
            registration = Registration(
                name=name,
                email=email,
                appointment_date=appointment_date,
                # business_name=business_name,
                phone=phone,
                course_type=course_type,
                duration=duration,
                payment_amount=payment_amount
            )

            db.session.add(registration)
            db.session.commit()

            flash(f'Registration successful! Your admission number is {registration.admission_number}', 'success')
            return redirect(url_for('admission_letter', admission_number=registration.admission_number))

        except Exception as e:
            print(f"Registration error: {str(e)}")
            flash('Error in registration. Please try again.', 'error')
            return redirect(url_for('register'))

    return render_template('register.html')

@app.route('/admission-letter/<admission_number>')
def admission_letter(admission_number):
    registration = Registration.query.filter_by(admission_number=admission_number).first_or_404()
    print(registration.course_type)
    return render_template('admission_letter.html', registration=registration)

@app.route('/download-admission-letter/<admission_number>')
def download_admission_letter(admission_number):
    """Generate and download admission letter as PDF"""
    try:
        registration = Registration.query.filter_by(admission_number=admission_number).first_or_404()

        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            doc = SimpleDocTemplate(
                tmp.name,
                pagesize=A4,
                rightMargin=72,
                leftMargin=72,
                topMargin=72,
                bottomMargin=72
            )

            styles = getSampleStyleSheet()
            title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'], fontSize=24, spaceAfter=30)
            heading_style = ParagraphStyle('CustomHeading', parent=styles['Heading2'], fontSize=16, spaceAfter=12)
            normal_style = styles['Normal']

            content = []

            # Header
            content.append(Paragraph("TECHELAR DIGITAL HUB", title_style))
            content.append(Paragraph("Nairobi, Kenya", normal_style))
            content.append(Spacer(1, 20))

            # Date and Personal Info
            content.append(Paragraph(f"Date: {registration.created_at.strftime('%B %d, %Y')}", normal_style))
            content.append(Paragraph(f"Admission Number: {registration.admission_number}", normal_style))
            content.append(Paragraph(f"Name: {registration.name}", normal_style))
            if registration.business_name:
                content.append(Paragraph(f"Business Name: {registration.business_name}", normal_style))
            content.append(Paragraph(f"Email: {registration.email}", normal_style))
            content.append(Spacer(1, 20))

            # Greeting
            content.append(Paragraph(f"Dear {registration.name},", normal_style))
            content.append(Paragraph(
                "We are pleased to inform you that your application for admission to TechElar Digital Hub has been accepted. This letter serves as your official admission confirmation.",
                normal_style))
            content.append(Spacer(1, 20))

            # Course Type Mapping
            course_type_map = {
                'wordpress': 'WordPress Development',
                'webdev': 'Web Development (HTML, CSS, Bootstrap)',
                'fullstack': 'Fullstack Web Development (Python Flask, SQL, HTML, CSS, JS)',
                'digital_marketing': 'Digital Marketing (SEO, Social Media, Email Marketing)',
                'data_science': 'Data Science (Python, Pandas, Machine Learning)',
                'mobile_dev': 'Mobile App Development (Flutter)',
                'backend': 'Backend Development with Node.js and Express',
                'uiux': 'UI/UX Design Fundamentals'
            }

            # Duration Mapping (could be expanded if needed)
            duration_map = {
                '1_month': '1 Month',
                '2_months': '2 Months',
                '3_months': '3 Months',
                '2_months_digital': '2 Months',
                '4_months_fullstack': '4 Months',
                '3_months_digital': '4 Months',
                
                '6_weeks': '6 Weeks'
            }

            course_data = [
                ["Course Type:", course_type_map.get(registration.course_type, "Unknown Course")],
                ["Duration:", duration_map.get(registration.duration, "Custom Duration")],
                ["Start Date:", registration.appointment_date.strftime('%B %d, %Y')],
                ["Course Fee:", f"KES {registration.payment_amount:.2f}"]
            ]

            course_table = Table(course_data, colWidths=[2*inch, 4*inch])
            course_table.setStyle(TableStyle([
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
                ('PADDING', (0, 0), (-1, -1), 6),
            ]))
            content.append(Paragraph("Course Details:", heading_style))
            content.append(course_table)
            content.append(Spacer(1, 20))

            # Payment Calculations
            if registration.duration == '1_month':
                weeks = 4
            elif registration.duration == '3_months':
                weeks = 12
            elif registration.duration == '2_months':
                weeks = 8
            elif registration.duration == '6_weeks':
                weeks = 6
            else:
                weeks = 8  # default fallback

            weekly_amount = registration.payment_amount / weeks

            payment_text = f"""
            Payment Options:
            <br/><br/>
            <b>Option 1: Full Payment</b>
            <br/>
            Pay the full amount of KES {registration.payment_amount:,.2f} using M-Pesa to:
            <br/>
            <b>Paybill Number:</b> 542542
            <br/>
            <b>Account Number:</b> 00105076123550
            <br/><br/>
            <b>Option 2: Weekly Installments</b>
            <br/>
            You can pay in weekly installments of KES {weekly_amount:,.2f} per week for {weeks} weeks.
            <br/><br/>
            <b>Installment Payment Schedule:</b>
            <br/>
            • First payment: Before course start date
            <br/>
            • Subsequent payments: Every week during the course duration
            <br/>
            • Total number of payments: {weeks} weeks
            <br/>
            • Amount per payment: KES {weekly_amount:,.2f}
            <br/><br/>
            <b>Option 3: Monthly Installments</b>
            <br/>
            You can also pay in monthly installments:
            <br/>
            • First Installment: 50% of the course fee (KES {registration.payment_amount * 0.5:,.2f})
            <br/>
            • Second Installment: 50% of the course fee (KES {registration.payment_amount * 0.5:,.2f})
            <br/><br/>
            <b>Note:</b> Please contact our office to set up your preferred payment plan and receive the detailed payment schedule.
            <br/><br/>
            After payment, please keep your M-Pesa confirmation message for reference.
            """
            content.append(Paragraph("PAYMENT INSTRUCTIONS", heading_style))
            content.append(Paragraph(payment_text, normal_style))
            content.append(Spacer(1, 20))

            # Next Steps
            content.append(Paragraph("Next Steps:", heading_style))
            next_steps = [
                "1. Complete your payment using the M-Pesa instructions above",
                "2. Save this admission letter for your records",
            ]
            for step in next_steps:
                content.append(Paragraph(step, normal_style))
            content.append(Spacer(1, 20))

            # Closing
            content.append(Paragraph("We look forward to welcoming you to TechElar and helping you achieve your web development goals!", normal_style))
            content.append(Spacer(1, 20))
            content.append(Paragraph("Best regards,", normal_style))
            content.append(Paragraph("The TechElar Team", normal_style))

            doc.build(content)

            return send_file(
                tmp.name,
                as_attachment=True,
                download_name=f'admission_letter_{admission_number}.pdf',
                mimetype='application/pdf'
            )

    except Exception as e:
        print(f"Error generating PDF: {str(e)}")
        flash('Error generating admission letter. Please try again.', 'error')
        return redirect(url_for('admission_letter', admission_number=admission_number))

@app.route('/checkout/<admission_number>')
def checkout(admission_number):
    registration = Registration.query.filter_by(admission_number=admission_number).first_or_404()
    return render_template('checkout.html', registration=registration)

@app.route('/process_payment/<int:registration_id>', methods=['POST'])
def process_payment(registration_id):
    """Process payment for a registration"""
    try:
        registration = Registration.query.get_or_404(registration_id)
        phone_number = request.form.get('phone_number')
        payment_amount = float(request.form.get('payment_amount', registration.payment_amount))
        
        if not phone_number:
            flash('Phone number is required', 'error')
            return redirect(url_for('checkout', admission_number=registration.admission_number))
            
        # Validate phone number format
        if not phone_number.startswith(('0', '+254', '254')):
            flash('Invalid phone number format. Please use format: 07XXXXXXXX or +254XXXXXXXXX', 'error')
            return redirect(url_for('checkout', admission_number=registration.admission_number))
        
        # Validate payment amount
        if payment_amount < 1000:
            flash('Minimum payment amount is KES 1,000', 'error')
            return redirect(url_for('checkout', admission_number=registration.admission_number))
            
        if payment_amount > registration.payment_amount:
            flash('Payment amount cannot exceed the full course cost', 'error')
            return redirect(url_for('checkout', admission_number=registration.admission_number))
        
        # Update registration with phone number
        registration.mpesa_phone = phone_number
        db.session.commit()
        
        # Initiate STK Push
        response = initiate_stk_push(phone_number, int(payment_amount), f"WP{registration.id}")
        
        if not response:
            flash('Failed to initiate payment. Please try again.', 'error')
            return redirect(url_for('checkout', admission_number=registration.admission_number))
            
        if response.get('ResponseCode') == '0':
            flash('Please check your phone for the M-Pesa prompt to complete the payment.', 'success')
            return redirect(url_for('confirmation', registration_id=registration.id))
        else:
            error_message = response.get('ResponseDescription', 'Payment initiation failed')
            flash(f'Payment initiation failed: {error_message}', 'error')
            return redirect(url_for('checkout', admission_number=registration.admission_number))
            
    except Exception as e:
        print(f"Error processing payment: {str(e)}")
        flash('An error occurred while processing your payment. Please try again.', 'error')
        return redirect(url_for('checkout', admission_number=registration.admission_number))

@app.route('/mpesa/callback', methods=['POST'])
def mpesa_callback():
    """Handle M-Pesa callback"""
    data = request.get_json()
    
    # Process the callback data
    if data.get('Body', {}).get('stkCallback', {}).get('ResultCode') == 0:
        # Payment successful
        merchant_request_id = data['Body']['stkCallback']['MerchantRequestID']
        checkout_request_id = data['Body']['stkCallback']['CheckoutRequestID']
        
        # Update registration status
        registration_id = int(merchant_request_id.split('_')[1])
        registration = Registration.query.get(registration_id)
        if registration:
            registration.payment_status = 'completed'
            db.session.commit()
    
    return {'status': 'success'}, 200

@app.route('/confirmation/<int:registration_id>')
def confirmation(registration_id):
    registration = Registration.query.get_or_404(registration_id)
    return render_template('confirmation.html', registration=registration)

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        try:
            name = request.form['name']
            email = request.form['email']
            subject = request.form['subject']
            message = request.form['message']

            # Send email to admin
            admin_email = app.config['MAIL_DEFAULT_SENDER']
            email_subject = f"Contact Form: {subject}"
            email_message = f"""
            Name: {name}
            Email: {email}
            Subject: {subject}
            
            Message:
            {message}
            """

            if send_email(admin_email, email_subject, email_message):
                flash('Your message has been sent successfully! We will get back to you soon.', 'success')
            else:
                flash('There was an error sending your message. Please try again later.', 'error')

            return redirect(url_for('contact'))

        except Exception as e:
            print(f"Contact form error: {str(e)}")
            flash('An error occurred. Please try again.', 'error')
            return redirect(url_for('contact'))

    return render_template('contact.html')
# admin dashboard to view all registrations
@app.route('/admin/registrations')
def admin_registrations():
    registrations = Registration.query.all()
    return render_template('admin_registrations.html', registrations=registrations)

# edit registration
@app.route('/admin/registrations/edit/<int:registration_id>', methods=['GET', 'POST'])
def edit_registration(registration_id):
    # get registration
    if not session.get('admin_logged_in'):
        flash('Please login to access the admin dashboard', 'error')
        return redirect(url_for('admin_login'))
    registration = Registration.query.get_or_404(registration_id)
    if request.method == 'POST':
        registration.name = request.form['name']
        registration.email = request.form['email']
        registration.appointment_date = datetime.strptime(request.form['appointment_date'], '%Y-%m-%d').date()
        registration.business_name = request.form['business_name']
        registration.course_type = request.form['course_type']
        registration.duration = request.form['duration']
        registration.payment_status = request.form['payment_status']
        db.session.commit()
        return redirect(url_for('admin_registrations'))
    
# login to admin dashboard hardcoded username and password
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == 'admin' and password == 'admin@TechElar':
            session['admin_logged_in'] = True
            flash('Login successful', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid username or password', 'error')
            return redirect(url_for('admin_login'))
    return render_template('admin_login.html')

# admin dashboard
@app.route('/admin')
def admin_dashboard():
    if not session.get('admin_logged_in'):
        flash('Please login to access the admin dashboard', 'error')
        return redirect(url_for('admin_login'))
    # get total courses
    total_courses = Registration.query.count()
    # get total students
    total_students = Registration.query.count()
    # get recent registrations
    recent_registrations = Registration.query.order_by(Registration.created_at.desc()).limit(5).all()
    return render_template('admin_dashboard.html', total_courses=total_courses, total_students=total_students, recent_registrations=recent_registrations)

# # recent registrations
# @app.route('/admin/recent_registrations')
# def recent_registrations():
#     registrations = Registration.query.order_by(Registration.created_at.desc()).limit(5).all()
#     return render_template('admin_recent_registrations.html', registrations=registrations)



if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Create tables if they don't exist
        # db.drop_all()  # Uncomment this line if you want to drop all tables

    # Don't use debug=True for production. Use Gunicorn in production.
    app.run(host='0.0.0.0', port=5010, debug=False)
