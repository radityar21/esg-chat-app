# ESG Chat App React Frontend

Modern, dark-themed React application for ESG Report Generation and Analytics, built with **Vite**, **Tailwind CSS**, and **Recharts**.

---

## 🎨 Features

- **Dark Theme Glassmorphism Design** — Modern UI with glass-effect cards and gradient accents
- **5 Core Pages**:
  - **Overview** — Dashboard landing page with quick actions
  - **Analytics** — 14 charts + 6 KPI cards for ESG metrics visualization
  - **Chat** — AI-powered ESG assistant (Amazon Bedrock Agent)
  - **Reports** — Report generation history and download links
  - **Reference** — ESG framework documentation
- **Real-time Data** — Live API integration with backend Lambda functions
- **Responsive Layout** — Sidebar navigation with Lucide React icons
- **Cost-Optimized Analytics** — S3-cached data with manual Athena refresh option

---

## 🏗️ Tech Stack

| Technology | Purpose |
|-----------|---------|
| **React 18** | UI framework |
| **Vite** | Build tool & dev server |
| **Tailwind CSS** | Utility-first styling |
| **Recharts** | Chart library (14 ESG visualizations) |
| **Lucide React** | Icon library |
| **JavaScript (ES6+)** | No TypeScript for simplicity |

---

## 📁 Project Structure

```
esg-chat-app-react/
├── src/
│   ├── components/
│   │   └── Sidebar.jsx           # Navigation sidebar with logo
│   ├── pages/
│   │   ├── Overview.jsx          # Landing page (default)
│   │   ├── Analytics.jsx         # 14 charts + 6 KPIs
│   │   ├── Chat.jsx              # Bedrock Agent chat interface
│   │   ├── Reports.jsx           # Report history & downloads
│   │   └── Reference.jsx         # ESG framework docs
│   ├── api.js                    # API endpoint configuration
│   ├── App.jsx                   # Main app with routing
│   ├── main.jsx                  # React entry point
│   └── index.css                 # Global styles + Tailwind
├── public/
│   └── _redirects                # SPA routing for Amplify
├── index.html                    # HTML template
├── vite.config.js                # Vite configuration
├── tailwind.config.js            # Tailwind theme (custom colors)
├── postcss.config.js             # PostCSS setup
└── package.json                  # Dependencies
```

---

## 🚀 Local Development

### Prerequisites
- Node.js 18+ and npm
- Backend API deployed (see `../esg-reporting-poc/README.md`)

### Setup

```bash
# Navigate to frontend directory
cd esg-chat-app-react

# Install dependencies
npm install

# Start development server (runs on http://localhost:5173)
npm run dev
```

### API Configuration

Edit `src/api.js` to point to your backend:

```javascript
export const API_BASE_URL = 'https://your-api-gateway-url.amazonaws.com/prod'
```

**Required endpoints:**
- `POST /chat` — Chat with Bedrock Agent
- `GET /status?execution_id=<id>` — Check report status
- `GET /history` — Get report history
- `GET /dashboard-data` — Get analytics data (S3 cache)
- `GET /dashboard-data?refresh=true` — Refresh from Athena

---

## 🏗️ Build & Deploy

### Local Build

```bash
# Build for production (output: dist/)
npm run build

# Preview production build locally
npm run preview
```

### Deploy to AWS Amplify (via GitHub)

1. **Push to GitHub** (see root `amplify.yml` for build config)
2. **Connect Amplify to GitHub repo**:
   - Go to AWS Amplify Console
   - Select repo: `https://github.com/radityar21/esg-chat-app`
   - Amplify will auto-detect `amplify.yml` in repo root
3. **Build triggers automatically** on push to `main` branch
4. **Environment variables** (set in Amplify Console if needed):
   - No env vars required (API URL is hardcoded in `api.js`)

**Current deployment:** `https://main.d337jqli3ubqmk.amplifyapp.com`

---

## 📊 Analytics Page Details

### 6 KPI Cards
- Total Scope 1 Emissions (tCO₂e)
- Total Scope 2 Emissions (tCO₂e)
- Total Scope 3 Emissions (tCO₂e)
- Portfolio Size (IDR Billion)
- Emission Intensity (tCO₂e/IDR B)
- PCAF Data Quality Score (1-5)

### 14 Charts
1. **Total Emissions by Scope** (bar chart) — Scope 1/2/3 comparison
2. **Emission Intensity Trends** (line chart) — tCO₂e per IDR Billion over time
3. **Scope 1 Emissions by Source** (pie chart) — Stationary combustion, mobile, fugitive
4. **Scope 2 Emissions Comparison** (bar chart) — Location-based vs market-based
5. **PCAF Data Quality Distribution** (bar chart) — Score 1-5 distribution
6. **Financed Emissions by Sector** (bar chart) — Top 8 sectors
7. **Financed Emissions Trends** (line chart) — 2023 vs 2024
8. **Portfolio Carbon Intensity** (bar chart) — tCO₂e per IDR Million by sector
9. **Training Hours by Department** (bar chart) — HR, Finance, Operations, etc.
10. **Employee Turnover Rate** (line chart) — Quarterly trends
11. **Gender Diversity by Level** (stacked bar) — Entry/Mid/Senior/Executive
12. **Geographic Emission Distribution** (pie chart) — By region
13. **Top 10 Borrowers** (bar chart) — Highest financed emissions
14. **Asset Class Distribution** (pie chart) — Corporate loans, mortgages, etc.

---

## 🎨 Theming

Custom Tailwind colors defined in `tailwind.config.js`:

```javascript
colors: {
  dark: {
    900: '#0a0e1a',  // Background
    800: '#0f1629',  // Card background
    700: '#1a2037',  // Hover states
  },
  accent: {
    blue: '#3b82f6',
    teal: '#06b6d4',
    purple: '#8b5cf6',
  },
}
```

**Glassmorphism effect:**
- `backdrop-blur-md`
- `bg-white/5` (5% white opacity)
- `border border-white/10`

---

## 🔧 Troubleshooting

### Build Fails in Amplify

**Issue:** `!! No index.html detected in deploy folder`

**Solution:** Ensure `amplify.yml` has correct `baseDirectory`:

```yaml
frontend:
  phases:
    build:
      commands:
        - cd esg-chat-app-react
        - npm ci
        - npm run build
  artifacts:
    baseDirectory: esg-chat-app-react/dist  # ← Must point to dist/
    files:
      - '**/*'
```

### API Endpoints Return 404

**Issue:** CORS or incorrect API URL

**Solution:**
1. Check `src/api.js` has correct `API_BASE_URL`
2. Verify API Gateway has CORS enabled (`Access-Control-Allow-Origin: *`)
3. Check API Gateway deployment stage is `prod`

### Analytics Page Shows No Data

**Issue:** Lambda `dashboard_data` not deployed or S3 cache empty

**Solution:**
1. Deploy `esg-reporting-poc/lambda/dashboard_data/` (see backend README)
2. Trigger Athena refresh: `GET /dashboard-data?refresh=true`
3. Check CloudWatch logs for errors

### Chart Rendering Issues

**Issue:** Recharts not displaying correctly

**Solution:**
1. Ensure `recharts` version 3.8.1+ installed
2. Check browser console for errors
3. Verify data structure matches chart component props

---

## 📝 Development Notes

### Adding a New Page

1. Create `src/pages/NewPage.jsx`
2. Import in `App.jsx`: `import NewPage from './pages/NewPage'`
3. Add to `pages` object: `newpage: <NewPage />`
4. Add navigation in `Sidebar.jsx`

### API Call Pattern

All API calls use native `fetch` (no Axios):

```javascript
const response = await fetch(`${API_BASE_URL}/endpoint`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ key: 'value' })
})
const data = await response.json()
```

### State Management

No Redux/Zustand — all state managed with React `useState`:
- `App.jsx` — active page routing
- `Chat.jsx` — chat messages + loading state
- `Reports.jsx` — report history + selected report
- `Analytics.jsx` — chart data + loading state

---

## 🔗 Related Documentation

- **Backend README:** `../esg-reporting-poc/README.md`
- **Root README:** `../README.md`
- **Implementation Changelog:** `../esg-reporting-poc/docs/IMPLEMENTATION_CHANGELOG.md`
- **Agent Instructions:** `../esg-reporting-poc/agent/README.md`

---

## 📦 Dependencies

```json
{
  "dependencies": {
    "lucide-react": "^1.18.0",    // Icons
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "recharts": "^3.8.1"          // Charts
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.3.1",
    "autoprefixer": "^10.4.19",
    "postcss": "^8.4.38",
    "tailwindcss": "^3.4.4",
    "vite": "^5.3.1"
  }
}
```

---

**Maintained by:** Tokaicom Mitra Indonesia (Tokai Group)  
**Last Updated:** June 15, 2026
