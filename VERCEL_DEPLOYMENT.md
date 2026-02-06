# Deploying to Vercel

This guide explains how to deploy the AI Receptionist Appointment Booking System to Vercel.

## Frontend Deployment (Recommended)

The frontend is a React application built with Create React App, which works perfectly on Vercel.

### Option 1: Deploy Frontend Directory (Recommended)

1. **Connect your GitHub repository to Vercel**
   - Go to [vercel.com](https://vercel.com)
   - Click "New Project"
   - Import your GitHub repository

2. **Configure the project**
   - **Framework Preset**: Create React App
   - **Root Directory**: `frontend`
   - **Build Command**: `npm run build`
   - **Output Directory**: `build`
   - **Install Command**: `npm install`

3. **Set Environment Variables**
   ```
   REACT_APP_API_URL=https://your-backend-api-url.com
   ```
   
   If you haven't deployed your backend yet, you can:
   - Deploy backend to a cloud service (AWS, Railway, Render, etc.)
   - Use the backend URL from another hosting provider
   - For testing, temporarily use: `http://localhost:8000`

4. **Deploy**
   - Click "Deploy"
   - Vercel will automatically build and deploy your application

### Option 2: Deploy from Root Directory

If you want to deploy from the root directory:

1. Use the `vercel.json` in the root directory
2. Set the root directory to `frontend` in Vercel dashboard
3. Or use the Vercel CLI with: `vercel --cwd frontend`

## Environment Variables

Add these environment variables in your Vercel project settings:

### Frontend Environment Variables
- `REACT_APP_API_URL` - Your backend API URL (required)
  - Example: `https://your-backend.railway.app`
  - Example: `https://your-backend.render.com`
  - Example: `https://api.yourdomain.com`

## Backend Deployment

The backend (FastAPI) needs to be deployed separately as Vercel is optimized for frontend/serverless applications.

### Recommended Backend Hosting Options:

1. **Railway** (Recommended)
   - Supports Python/FastAPI natively
   - Easy deployment from GitHub
   - Free tier available
   - Guide: See `DEPLOYMENT.md` for Railway setup

2. **Render**
   - Good Python support
   - Free tier available
   - Auto-deploys from GitHub

3. **AWS/Azure/GCP**
   - Production-grade
   - See `DEPLOYMENT.md` for cloud deployment

4. **Docker on VPS**
   - Most control
   - See `DEPLOYMENT.md` for Docker deployment

## Troubleshooting

### 404 Error on Routes

If you're getting 404 errors when navigating to routes:

**Solution**: The `vercel.json` in the `frontend` directory is configured to handle this. It includes rewrites that route all requests to `index.html`, which is required for React Router to work.

Make sure:
1. You're deploying from the `frontend` directory
2. The `vercel.json` file is present in the frontend directory
3. The build command is `npm run build`
4. The output directory is `build`

### API Connection Issues

If the frontend can't connect to the backend:

1. **Check CORS settings** in your backend (`main.py`):
   ```python
   app.add_middleware(
       CORSMiddleware,
       allow_origins=["https://your-vercel-app.vercel.app"],
       allow_credentials=True,
       allow_methods=["*"],
       allow_headers=["*"],
   )
   ```

2. **Check environment variable**:
   - Make sure `REACT_APP_API_URL` is set in Vercel
   - It should point to your deployed backend
   - Don't include trailing slash

3. **Check backend is running**:
   - Visit your backend URL directly (e.g., `https://your-backend.com/docs`)
   - You should see the FastAPI docs

### Build Fails

If the build fails:

1. **Check Node version**: Vercel uses Node 18 by default. Ensure compatibility.
2. **Check dependencies**: Make sure all dependencies in `package.json` are correct
3. **Check build logs**: Vercel provides detailed build logs
4. **Test locally**: Run `npm run build` in the frontend directory

## Vercel CLI Deployment

You can also deploy using the Vercel CLI:

```bash
# Install Vercel CLI
npm i -g vercel

# Login
vercel login

# Deploy from frontend directory
cd frontend
vercel

# Or deploy from root with configuration
cd ..
vercel --cwd frontend
```

## Custom Domain

To add a custom domain:

1. Go to your project settings in Vercel
2. Navigate to "Domains"
3. Add your domain
4. Update your DNS records as instructed by Vercel

## Automatic Deployments

Vercel automatically deploys:
- **Production**: When you push to the `main` branch
- **Preview**: For every pull request

You can configure this in the project settings.

## Environment-Specific Builds

For different environments:

1. **Production**:
   - Deploys from `main` branch
   - Uses production environment variables

2. **Staging**:
   - Create a separate Vercel project
   - Connect to a `staging` branch
   - Use different environment variables

3. **Development**:
   - Vercel creates preview deployments for PRs
   - Great for testing before merging

## Complete Deployment Workflow

### 1. Deploy Backend
```bash
# Choose a backend hosting provider
# See DEPLOYMENT.md for detailed instructions
# Example: Railway, Render, AWS, etc.
```

### 2. Get Backend URL
```
https://your-backend.railway.app
```

### 3. Deploy Frontend to Vercel
```bash
# Via Vercel Dashboard:
1. Import repository
2. Set root directory: frontend
3. Add environment variable: REACT_APP_API_URL=https://your-backend.railway.app
4. Deploy

# Or via CLI:
cd frontend
vercel --prod
```

### 4. Update Backend CORS
Update your backend's CORS settings to allow your Vercel domain:
```python
allow_origins=["https://your-app.vercel.app"]
```

### 5. Test
Visit your Vercel URL and test the application.

## Production Checklist

Before going to production:

- [ ] Backend deployed and accessible
- [ ] Frontend deployed to Vercel
- [ ] Environment variables configured
- [ ] CORS properly configured on backend
- [ ] Custom domain configured (optional)
- [ ] SSL/HTTPS working (Vercel handles this automatically)
- [ ] Test all functionality
- [ ] Monitor logs for errors

## Support

If you encounter issues:

1. Check Vercel build logs
2. Check browser console for errors
3. Verify environment variables
4. Test backend separately
5. Review CORS configuration

For backend deployment issues, see `DEPLOYMENT.md`.

## Additional Resources

- [Vercel Documentation](https://vercel.com/docs)
- [Create React App Deployment](https://create-react-app.dev/docs/deployment/)
- [Vercel Environment Variables](https://vercel.com/docs/environment-variables)
