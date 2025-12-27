# Document Intelligence Platform - React Frontend

Modern, minimal React + TypeScript frontend inspired by Stripe, Vercel, and Linear.

## Design Philosophy

- **Minimal & Clean**: Inspired by Stripe's simplicity
- **Modern**: Vercel-style dark mode and smooth animations  
- **Professional**: Linear's beautiful UI and great UX
- **Responsive**: Mobile-first approach
- **Accessible**: WCAG 2.1 AA compliance

## Color Palette

```
Primary:   #2563eb (Blue)
Success:   #10b981 (Green)
Warning:   #f59e0b (Amber)
Error:     #ef4444 (Red)  
Neutral:   Slate/Gray shades
Background: White/Dark mode support
```

## Tech Stack

- **Framework**: React 18 + TypeScript
- **Build Tool**: Vite
- **Routing**: React Router v6
- **State Management**: Zustand + React Query
- **Styling**: Tailwind CSS
- **UI Components**: Headless UI + Custom
- **Charts**: Chart.js + Recharts
- **Icons**: Heroicons
- **Animations**: Framer Motion
- **HTTP Client**: Axios
- **Notifications**: React Hot Toast

## Project Structure

```
frontend/
├── public/
│   ├── favicon.ico
│   └── logo.svg
├── src/
│   ├── components/
│   │   ├── auth/
│   │   │   ├── LoginForm.tsx
│   │   │   ├── RegisterForm.tsx
│   │   │   └── ProtectedRoute.tsx
│   │   ├── dashboard/
│   │   │   ├── MetricsCard.tsx
│   │   │   ├── AutomationChart.tsx
│   │   │   ├── RecentDocuments.tsx
│   │   │   └── QuickActions.tsx
│   │   ├── documents/
│   │   │   ├── DocumentUpload.tsx
│   │   │   ├── DocumentList.tsx
│   │   │   ├── DocumentCard.tsx
│   │   │   ├── DocumentViewer.tsx
│   │   │   └── BatchUpload.tsx
│   │   ├── analytics/
│   │   │   ├── AutomationMetrics.tsx
│   │   │   ├── TrendChart.tsx
│   │   │   ├── PerformanceTable.tsx
│   │   │   └── InsightsPanel.tsx
│   │   ├── chat/
│   │   │   ├── ChatInterface.tsx
│   │   │   ├── MessageList.tsx
│   │   │   ├── MessageInput.tsx
│   │   │   └── ChatHistory.tsx
│   │   ├── common/
│   │   │   ├── Button.tsx
│   │   │   ├── Input.tsx
│   │   │   ├── Card.tsx
│   │   │   ├── Badge.tsx
│   │   │   ├── Spinner.tsx
│   │   │   ├── Modal.tsx
│   │   │   ├── Dropdown.tsx
│   │   │   └── Toast.tsx
│   │   └── layout/
│   │       ├── Layout.tsx
│   │       ├── Sidebar.tsx
│   │       ├── Header.tsx
│   │       └── Footer.tsx
│   ├── pages/
│   │   ├── Dashboard.tsx
│   │   ├── Documents.tsx
│   │   ├── Analytics.tsx
│   │   ├── Chat.tsx
│   │   ├── Settings.tsx
│   │   ├── Login.tsx
│   │   └── NotFound.tsx
│   ├── services/
│   │   ├── api.ts
│   │   ├── auth.service.ts
│   │   ├── documents.service.ts
│   │   ├── analytics.service.ts
│   │   └── chat.service.ts
│   ├── hooks/
│   │   ├── useAuth.ts
│   │   ├── useDocuments.ts
│   │   ├── useAnalytics.ts
│   │   ├── useTheme.ts
│   │   └── useWebSocket.ts
│   ├── types/
│   │   ├── index.ts
│   │   ├── document.types.ts
│   │   ├── analytics.types.ts
│   │   └── user.types.ts
│   ├── utils/
│   │   ├── format.ts
│   │   ├── validation.ts
│   │   └── constants.ts
│   ├── styles/
│   │   └── index.css
│   ├── App.tsx
│   └── main.tsx
├── .env.example
├── .eslintrc.cjs
├── .gitignore
├── index.html
├── package.json
├── postcss.config.js
├── tailwind.config.js
├── tsconfig.json
├── tsconfig.node.json
└── vite.config.ts
```

## Features

### 1. Authentication
- JWT-based authentication
- Login/Register forms
- Protected routes
- Token refresh
- Remember me functionality

### 2. Dashboard
- Real-time metrics display
- Automation rate tracking (90%+ goal)
- Recent documents list
- Quick actions panel
- Performance charts

### 3. Document Management
- Single file upload (drag & drop)
- Batch upload (10-15 files)
- Document list with search/filter
- Real-time processing status
- Document viewer
- Download/delete actions

### 4. Analytics
- Automation metrics dashboard
- Trend analysis charts
- Performance tables
- AI insights panel
- Custom date ranges
- Export to CSV

### 5. AI Chat
- Conversational interface
- Document Q&A
- RAG-powered responses
- Chat history
- Streaming responses
- Context-aware

### 6. Settings
- Profile management
- API keys
- Theme toggle (light/dark)
- Notification preferences
- Rate limit info

## Installation

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Copy environment variables
cp .env.example .env

# Edit .env with your API endpoint
# API_URL=http://localhost:8003

# Start development server
npm run dev

# Open browser at http://localhost:3000
```

## Environment Variables

Create `.env` file:

```env
VITE_API_URL=http://localhost:8003
VITE_WS_URL=ws://localhost:8003
VITE_APP_NAME=Document Intelligence Platform
VITE_APP_VERSION=2.0.0
```

## API Integration

All API calls go through `/api` proxy to `http://localhost:8003` (API Gateway).

**Endpoints Used:**
- `POST /auth/login` - User authentication
- `GET /documents` - List documents  
- `POST /documents/upload` - Upload document
- `POST /documents/batch-upload` - Batch upload
- `GET /analytics/automation-metrics` - Get metrics
- `POST /chat/message` - Send chat message
- `GET /mcp/tools` - List MCP tools

## Development

```bash
# Run dev server (hot reload)
npm run dev

# Type checking  
npm run type-check

# Linting
npm run lint

# Build for production
npm run build

# Preview production build
npm run preview
```

## Production Build

```bash
# Build optimized bundle
npm run build

# Output: dist/ directory

# Serve with your web server
# nginx, Apache, or Node.js server
```

## Docker Deployment

```dockerfile
FROM node:18-alpine as build

WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

## Browser Support

- Chrome (last 2 versions)
- Firefox (last 2 versions)
- Safari (last 2 versions)
- Edge (last 2 versions)

## Performance

- Lighthouse score: 95+
- First Contentful Paint: < 1.5s
- Time to Interactive: < 3.0s
- Bundle size: < 300KB gzipped
- Code splitting for routes
- Lazy loading for charts

## Accessibility

- WCAG 2.1 AA compliant
- Keyboard navigation
- Screen reader support
- Proper ARIA labels
- Focus indicators
- Color contrast ratios

## Key Features Implementation

### Real-Time Updates
- WebSocket connection for live status
- React Query for automatic refetch
- Optimistic UI updates

### File Upload
- Drag & drop interface
- Multiple file selection
- Progress indicators
- File validation
- Chunked uploads for large files

### Dark Mode
- System preference detection
- Manual toggle
- Persistent preference
- Smooth transitions

### Charts & Visualizations
- Automation rate over time
- Document processing trends
- Performance metrics
- Interactive tooltips

## Contributing

1. Follow the existing code structure
2. Use TypeScript for type safety
3. Write meaningful commit messages
4. Test responsive design
5. Check accessibility
6. Run linter before commit

## Troubleshooting

**Port already in use:**
```bash
# Change port in vite.config.ts
server: { port: 3001 }
```

**API connection errors:**
```bash
# Check API Gateway is running
curl http://localhost:8003/health

# Verify proxy configuration in vite.config.ts
```

**Build errors:**
```bash
# Clear cache
rm -rf node_modules dist
npm install
npm run build
```

## License

MIT License - Document Intelligence Platform Team

## Version

2.0.0 - Modern React Frontend with Security & MCP Integration

