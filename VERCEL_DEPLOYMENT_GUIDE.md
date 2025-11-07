# Vercel Deployment Guide for Grocery Sales Dashboard

## ✅ Pre-Deployment Checklist

Your application is ready for deployment! Here's what has been verified:

- ✅ Backend URL updated to Render: `https://urc1oh1groceryanalysis.onrender.com`
- ✅ All missing Python packages added (`openpyxl`, `scikit-learn`)
- ✅ Frontend build tested successfully
- ✅ All API endpoints verified and match between frontend/backend
- ✅ Environment variables properly configured
- ✅ CORS configured correctly in backend

## 📋 Architecture Overview

- **Frontend**: React app with Tailwind CSS → Deploy to **Vercel**
- **Backend**: FastAPI with MongoDB → Already deployed on **Render**
- **Database**: MongoDB → Connected to Render backend

## 🚀 Vercel Deployment Steps

### Option 1: Deploy via Vercel Dashboard (Recommended)

1. **Login to Vercel**
   - Go to [vercel.com](https://vercel.com)
   - Sign in with your GitHub account

2. **Import Your Repository**
   - Click "Add New Project"
   - Select "Import Git Repository"
   - Choose your `GroceryAnalysis` repository
   - Select the `Grocery_Sales_URC` branch

3. **Configure Project Settings**
   
   **Root Directory**: `frontend`
   
   **Build Settings**:
   - Framework Preset: `Create React App`
   - Build Command: `yarn build`
   - Output Directory: `build`
   - Install Command: `yarn install`
   
   **Environment Variables** (Add these in Vercel):
   ```
   REACT_APP_BACKEND_URL=https://urc1oh1groceryanalysis.onrender.com
   ```

4. **Deploy**
   - Click "Deploy"
   - Wait for the build to complete (typically 2-3 minutes)
   - Your app will be live at `https://your-project-name.vercel.app`

### Option 2: Deploy via Vercel CLI

1. **Install Vercel CLI**
   ```bash
   npm install -g vercel
   ```

2. **Navigate to Frontend Directory**
   ```bash
   cd frontend
   ```

3. **Login to Vercel**
   ```bash
   vercel login
   ```

4. **Deploy**
   ```bash
   vercel --prod
   ```

5. **Set Environment Variables** (if not set in dashboard)
   ```bash
   vercel env add REACT_APP_BACKEND_URL production
   # Enter: https://urc1oh1groceryanalysis.onrender.com
   ```

## ⚙️ Vercel Project Settings

### Build & Development Settings

| Setting | Value |
|---------|-------|
| Framework Preset | Create React App |
| Build Command | `yarn build` |
| Output Directory | `build` |
| Install Command | `yarn install` |
| Development Command | `yarn start` |
| Root Directory | `frontend` |

### Environment Variables

Add these in Vercel Dashboard → Settings → Environment Variables:

| Key | Value | Environment |
|-----|-------|-------------|
| `REACT_APP_BACKEND_URL` | `https://urc1oh1groceryanalysis.onrender.com` | Production, Preview, Development |

### Custom Domain (Optional)

1. Go to Vercel Dashboard → Your Project → Settings → Domains
2. Add your custom domain
3. Configure DNS records as instructed by Vercel
4. Wait for DNS propagation (can take up to 48 hours)

## 🔧 Backend Configuration (Render)

Your backend is already deployed on Render. Ensure these settings:

### Environment Variables on Render

Make sure your Render backend has these environment variables:

```
MONGO_URL=<your-mongodb-connection-string>
DB_NAME=<your-database-name>
CORS_ORIGINS=https://your-vercel-app.vercel.app,https://your-custom-domain.com
```

⚠️ **Important**: Update `CORS_ORIGINS` to include your Vercel deployment URL(s) to prevent CORS errors.

### Update CORS After Deployment

1. Get your Vercel deployment URL (e.g., `https://grocery-dashboard.vercel.app`)
2. Go to Render Dashboard → Your Service → Environment
3. Update `CORS_ORIGINS` to include:
   ```
   https://grocery-dashboard.vercel.app,https://your-custom-domain.com
   ```
4. Save and redeploy your Render service

## 🧪 Testing Deployment

After deployment, test these features:

1. **Dashboard loads correctly**
   - Visit your Vercel URL
   - Check if dashboard shows data

2. **File Upload works**
   - Upload a sample Excel file
   - Verify data appears in dashboard

3. **Analytics display properly**
   - Navigate to Analytics tab
   - Check charts and tables

4. **Forecasting works**
   - Try generating a forecast
   - Verify predictions display

5. **Database View loads**
   - Check the Database View tab
   - Ensure data is visible

## 🐛 Troubleshooting

### Issue: CORS Error

**Symptom**: Console shows CORS error, API calls fail

**Solution**:
1. Check backend CORS_ORIGINS includes your Vercel URL
2. Ensure backend URL in `.env` is correct
3. Redeploy backend after updating CORS

### Issue: Environment Variable Not Found

**Symptom**: `undefined` for REACT_APP_BACKEND_URL

**Solution**:
1. Ensure variable is set in Vercel Dashboard
2. Redeploy the application
3. Environment variables require a redeploy to take effect

### Issue: Build Fails

**Symptom**: Vercel build fails with dependency errors

**Solution**:
1. Clear build cache in Vercel settings
2. Ensure `package.json` has all dependencies
3. Check for Node version compatibility
4. Try redeploying

### Issue: Blank Page After Deployment

**Symptom**: White screen, no content

**Solution**:
1. Check browser console for errors
2. Verify REACT_APP_BACKEND_URL is set correctly
3. Check if backend is accessible from browser
4. Review Vercel function logs

### Issue: API Calls Timing Out

**Symptom**: Long loading times, requests fail

**Solution**:
1. Check if Render backend is active (free tier sleeps after inactivity)
2. Consider upgrading Render plan for better performance
3. Check MongoDB connection status
4. Review backend logs on Render

## 📊 Performance Optimization

### Vercel Settings

1. **Enable Caching**
   - Static assets are automatically cached
   - `vercel.json` includes cache headers

2. **Enable Edge Network**
   - Your app is automatically distributed globally

3. **Monitor Performance**
   - Use Vercel Analytics (optional add-on)
   - Monitor Core Web Vitals

### Render Backend Optimization

1. **Keep Service Active**
   - Upgrade from free tier to prevent cold starts
   - Use external monitoring to ping service

2. **Database Indexing**
   - Ensure MongoDB has proper indexes
   - Monitor query performance

## 🔄 Continuous Deployment

### Automatic Deployments

Vercel automatically deploys when you push to your repository:

- **Production**: Pushes to `main` or `Grocery_Sales_URC` branch
- **Preview**: Pull requests create preview deployments
- **Development**: Other branches create development previews

### Manual Deployments

Trigger manual deployment:
1. Go to Vercel Dashboard → Your Project
2. Click "Deployments" tab
3. Click "Redeploy" on any previous deployment

## 📝 Post-Deployment Checklist

- [ ] Verify Vercel deployment is successful
- [ ] Test all major features (upload, dashboard, analytics)
- [ ] Update CORS settings on Render backend
- [ ] Configure custom domain (if applicable)
- [ ] Set up monitoring/analytics
- [ ] Update README with production URLs
- [ ] Test on mobile devices
- [ ] Share the URL with stakeholders

## 🆘 Support & Resources

- **Vercel Documentation**: https://vercel.com/docs
- **Render Documentation**: https://render.com/docs
- **React Documentation**: https://react.dev
- **FastAPI Documentation**: https://fastapi.tiangolo.com

## 📞 Need Help?

If you encounter issues not covered here:
1. Check Vercel deployment logs
2. Check Render backend logs
3. Review browser console for errors
4. Check network tab for failed requests
5. Verify environment variables are set correctly

---

**Deployment Summary**:
- Frontend: Vercel (Recommended for React apps)
- Backend: Render (Already deployed)
- Database: MongoDB (Connected to Render)
- Expected build time: 2-3 minutes
- Expected deployment URL: `https://<your-project>.vercel.app`
