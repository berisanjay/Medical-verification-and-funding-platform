const nodemailer = require('nodemailer');
const { PrismaClient } = require('@prisma/client');
const prisma = new PrismaClient();

// Generate 6 digit OTP
const generateOTP = () => {
  return Math.floor(100000 + Math.random() * 900000).toString();
};

// Send OTP email directly via nodemailer
const sendOTPEmail = async (email, otp, purpose) => {
  const purposes = {
    REGISTRATION    : 'complete your registration',
    CAMPAIGN_CREATION: 'create your campaign',
    HOSPITAL_CHANGE : 'confirm hospital change',
    ADMIN_LOGIN     : 'complete admin login'
  };

  const action = purposes[purpose] || 'verify your action';

  const transporter = nodemailer.createTransport({
    service: 'gmail',
    auth: {
      user: process.env.EMAIL_USER,
      pass: process.env.EMAIL_APP_PASSWORD
    }
  });

  await transporter.sendMail({
    from    : `MediTrust Platform <${process.env.EMAIL_USER}>`,
    to      : email,
    subject : `MediTrust — Your OTP to ${action}`,
    text    : `
Dear User,

Your OTP to ${action} on MediTrust is:

    ${otp}

This OTP is valid for 10 minutes. Do not share this with anyone.

If you did not request this, please ignore this email.

With care,
Team MediTrust
    `
  });
};

// Create and save OTP to database
const createOTP = async (userId, email, purpose) => {
  const otp = generateOTP();

  // Expire any existing OTPs for this user and purpose
  await prisma.oTP.updateMany({
    where  : { user_id: userId, purpose, is_used: false },
    data   : { is_used: true }
  });

  // Create new OTP — expires in 10 minutes
  const expiresAt = new Date(Date.now() + 10 * 60 * 1000);

  await prisma.oTP.create({
    data: {
      user_id    : userId,
      email,
      otp_code   : otp,
      purpose,
      expires_at : expiresAt
    }
  });

  // Send email
  await sendOTPEmail(email, otp, purpose);

  return otp;
};

// Verify OTP from database
const verifyOTP = async (userId, otpCode, purpose) => {
  const otp = await prisma.oTP.findFirst({
    where: {
      user_id  : userId,
      otp_code : otpCode,
      purpose,
      is_used  : false,
      expires_at: { gt: new Date() }
    }
  });

  if (!otp) {
    return { valid: false, error: 'Invalid or expired OTP' };
  }

  // Mark OTP as used
  await prisma.oTP.update({
    where: { id: otp.id },
    data : { is_used: true }
  });

  return { valid: true };
};

module.exports = { createOTP, verifyOTP, generateOTP };