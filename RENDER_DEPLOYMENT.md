# Render.com Deployment Guide

## Prerequisites

1. **GitHub Repository** - Your code must be in a GitHub repository
2. **Render Account** - Sign up at [render.com](https://render.com)
3. **API Keys Ready** - Have your OpenAI and Twilio credentials ready

## Step-by-Step Deployment

### 1. Prepare Your Repository

Ensure your repository has these files:
- `requirements.txt` - Python dependencies
- `manage.py` - Django management script
- `ai_screener/` - Django project directory
- `interviews/` - Django app directory
- `.env.example` - Environment variables template

### 2. Connect to Render

1. **Sign in to Render**
   - Go to [render.com](https://render.com)
   - Sign in with your GitHub account

2. **Connect Repository**
   - Click "New +" → "Web Service"
   - Select "Connect a repository"
   - Choose your AI Interview Screener repository
   - Select the branch (usually `main` or `master`)

### 3. Configure Web Service

Fill in the service configuration:

**Basic Settings:**
- **Name**: `ai-interview-screener` (or your preferred name)
- **Environment**: `Python 3`
- **Region**: Choose closest to your users
- **Branch**: `main` (or your default branch)

**Build & Deploy Settings:**
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `gunicorn ai_screener.wsgi:application`
- **Auto-Deploy**: `Yes` (recommended)

### 4. Set Environment Variables

In the Render dashboard, add these environment variables:

```env
# Django Settings
SECRET_KEY=your-django-secret-key-here
DEBUG=False
ALLOWED_HOSTS=your-app-name.onrender.com

# OpenAI Configuration
OPENAI_API_KEY=your-openai-api-key-here
OPENAI_MODEL=gpt-3.5-turbo
TWILIO_ACCOUNT_SID=your-twilio-account-sid-here
TWILIO_AUTH_TOKEN=your-twilio-auth-token-here
TWILIO_PHONE_NUMBER=+1234567890

# Security
API_KEY=your-custom-api-key-here
WHITELISTED_NUMBERS=+1234567890,+1987654321

# Webhook URLs
WEBHOOK_BASE_URL=https://your-app-name.onrender.com

# File Storage
MEDIA_URL=/media/
MEDIA_ROOT=media/
```

**Important Notes:**
- Replace `your-app-name` with your actual service name
- Generate a strong Django secret key
- Use your actual API keys from OpenAI and Twilio
- Add your test phone numbers to `WHITELISTED_NUMBERS`

### 5. Deploy

1. **Click "Create Web Service"**
2. **Wait for Build** - First deployment takes 5-10 minutes
3. **Monitor Logs** - Check the build logs for any errors

### 6. Run Database Migrations

After successful deployment:

1. **Go to your service dashboard**
2. **Click on "Shell" tab**
3. **Run migrations:**
   ```bash
   python manage.py migrate
   ```
4. **Create superuser (optional):**
   ```bash
   python manage.py createsuperuser
   ```

### 7. Test Your Deployment

1. **Check your app URL**: `https://your-app-name.onrender.com`
2. **Test API endpoints** using your Postman collection
3. **Update Postman environment** with your new base URL

## Render.com Features

### Free Tier Benefits:
- **750 hours/month** of runtime
- **Automatic deployments** from GitHub
- **Custom domains** support
- **SSL certificates** included
- **Global CDN** for fast loading

### Scaling Options:
- **Upgrade to paid plans** for more resources
- **Custom domains** for professional URLs
- **Database services** for PostgreSQL
- **Background workers** for async tasks

## Troubleshooting

### Common Issues:

1. **Build Fails**
   - Check `requirements.txt` for correct dependencies
   - Verify Python version compatibility
   - Check build logs for specific errors

2. **Environment Variables Not Working**
   - Ensure all variables are set in Render dashboard
   - Check for typos in variable names
   - Restart the service after adding variables

3. **Database Issues**
   - Run migrations in the Render shell
   - Check database connection settings
   - Verify PostgreSQL service if using external DB

4. **Webhook Issues**
   - Update `WEBHOOK_BASE_URL` to your Render URL
   - Ensure Twilio webhooks point to correct endpoints
   - Check webhook logs in Twilio dashboard

### Getting Help:
- **Render Documentation**: [docs.render.com](https://docs.render.com)
- **Community Forum**: [community.render.com](https://community.render.com)
- **Support**: Available in Render dashboard

## Post-Deployment Checklist

- [ ] Environment variables configured
- [ ] Database migrations run
- [ ] API endpoints tested
- [ ] Postman collection updated
- [ ] Twilio webhooks configured
- [ ] Phone numbers whitelisted
- [ ] SSL certificate active
- [ ] Custom domain configured (optional)

## Cost Optimization

### Free Tier Tips:
- **Monitor usage** in Render dashboard
- **Optimize build times** by caching dependencies
- **Use efficient start commands** to reduce cold starts
- **Schedule deployments** during low-traffic periods

### Paid Features:
- **Custom domains** for professional URLs
- **Database services** for persistent data
- **Background workers** for heavy processing
- **Advanced monitoring** and analytics

Your AI Interview Screener is now deployed and ready for production use on Render.com!
