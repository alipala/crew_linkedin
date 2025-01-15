# Social Media Content Generation with CrewAI 🤖

An intelligent agentic system that leverages CrewAI to manage social media content(LinkedIn) creation and posting. The system uses AI agents to scrape trending topics, analyze engagement, generate content, and manage post scheduling.

## Features 🌟

- 🔍 **Find Most Attractive Linkedin Post**: Automatically finds topic related content from LinkedIn via Google Search API
- 📊 **Engagement Analysis**: Analyzes post engagement metrics to identify trending topics
- ✍️ **Content Generation**: Creates engaging LinkedIn posts based on analysis
- 🤝 **Slack Integration**: Review and approve posts via Slack
- 📅 **Scheduled Posting**: Automated daily posting at optimal times
- 🔄 **Content Regeneration**: Request new content generation if needed

## Architecture 🏗️

The system uses multiple specialized AI agents:
- `LinkedInPostSearchAgent`: Scrapes LinkedIn for trending AI content
- `LinkedInInteractionAnalyzeAgent`: Analyzes engagement metrics
- `BrainstormAgent`: Generates content ideas
- `WebSearchAgent`: Researches supporting content
- `PostCreateAgent`: Creates engaging posts
- `NotificationAgent`: Manages Slack notifications
- `ShareAgent`: Publishes approved content

## Prerequisites 📋

- Python 3.11+
- Chrome/Chromium browser
- LinkedIn account
- Slack workspace with app configuration
- Railway.app account (for deployment)

## Installation 🛠️

1. Clone the repository:
```bash
git clone https://github.com/yourusername/crew_linkedin.git
cd crew_linkedin
```

2. Create and activate virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables in `.env`:
```env
# LinkedIn Credentials
LINKEDIN_EMAIL=your_email
LINKEDIN_PASSWORD=your_password
LINKEDIN_ACCESS_TOKEN=your_access_token
LINKEDIN_PERSON_ID=your_person_id

# Slack Configuration
SLACK_WEBHOOK_URL=your_webhook_url
SLACK_SIGNING_SECRET=your_signing_secret

# API Keys
OPENAI_API_KEY=your_openai_key
SERPER_API_KEY=your_serper_key
API_KEY=your_custom_api_key

# Environment
ENVIRONMENT=development
CHROME_BINARY_PATH=/usr/bin/chromium  # For Linux/Railway
```

## Local Development 💻

1. Start the application:
```bash
python run.py
```

2. Use ngrok for Slack callbacks:
```bash
ngrok http 8000
```

3. Update Slack app's Interactive Components URL to your ngrok URL:
```
https://your-ngrok-url/slack/interactive
```

4. Test the endpoints:
```bash
# Health check
curl http://localhost:8000/health

# Trigger execution
curl -X POST http://localhost:8000/api/execute \
  -H "Authorization: Bearer your_api_key"
```

## Railway Deployment 🚂

1. Install Railway CLI:
```bash
npm i -g @railway/cli
```

2. Login and initialize:
```bash
railway login
railway init
```

3. Set environment variables:
```bash
railway variables set \
  SLACK_SIGNING_SECRET=xxx \
  SLACK_WEBHOOK_URL=xxx \
  LINKEDIN_ACCESS_TOKEN=xxx \
  LINKEDIN_PERSON_ID=xxx \
  API_KEY=xxx \
  OPENAI_API_KEY=xxx \
  SERPER_API_KEY=xxx \
  ENVIRONMENT=production \
  CHROME_BINARY_PATH=/usr/bin/chromium
```

4. Deploy:
```bash
railway up
```

5. Update Slack app's Interactive Components URL to your Railway URL:
```
https://your-app-name.up.railway.app/slack/interactive
```

## Usage 📱

1. **Scheduled Execution**:
   - The app runs daily at 8 AM CET
   - Does Google search on LinkedIn for given topic content
   - Generates and sends post to Slack for approval

2. **On-Demand Execution**:
```bash
curl -X POST https://your-app-name.up.railway.app/api/execute \
  -H "Authorization: Bearer your_api_key"
```

3. **Content Approval**:
   - Review post in Slack
   - Click "Approve" to publish
   - Click "Regenerate" for new content

## Contributing 🤝

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request


## License 📄

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments 🙏

- [CrewAI](https://github.com/joaomdmoura/crewAI)
- [undetected-chromedriver](https://github.com/ultrafunkamsterdam/undetected-chromedriver)
- Railway.app for hosting