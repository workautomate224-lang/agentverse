# AgentVerse Web Application

## Project Overview

AgentVerse is a Next.js 14 web application for AI-powered consumer simulation and persona management. The platform enables users to create virtual personas, run simulations, and analyze consumer behavior insights.

## Tech Stack

- **Framework**: Next.js 14 (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS with cyberpunk theme
- **State Management**: Zustand, TanStack React Query
- **Authentication**: NextAuth.js with credentials provider
- **UI Components**: Radix UI primitives
- **Charts**: Recharts
- **Animation**: Framer Motion
- **Form Handling**: React Hook Form + Zod
- **2D Graphics**: PixiJS (for VI World visualization)

## Project Structure

```
src/
├── app/                    # Next.js App Router pages
│   ├── auth/              # Authentication pages (login, register, forgot-password)
│   ├── dashboard/         # Protected dashboard routes
│   │   ├── accuracy/      # Accuracy benchmarking
│   │   ├── guide/         # User guide
│   │   ├── marketplace/   # Persona template marketplace
│   │   ├── personas/      # Persona creation and management
│   │   ├── products/      # Product testing simulations
│   │   ├── projects/      # Project management
│   │   ├── results/       # Simulation results
│   │   ├── settings/      # User settings
│   │   └── simulations/   # Simulation management
│   └── api/               # API routes (NextAuth)
├── components/            # React components
│   ├── charts/           # Recharts visualization components
│   ├── dashboard/        # Dashboard layout components
│   ├── focus-group/      # Focus group interview components
│   ├── marketplace/      # Marketplace components
│   ├── providers/        # Context providers
│   ├── simulation/       # Simulation progress components
│   ├── ui/               # Base UI components (Radix-based)
│   └── vi-world/         # PixiJS-based persona visualization
├── hooks/                 # Custom React hooks
│   ├── useApi.ts         # API hooks with React Query
│   ├── useFocusGroup.ts  # Focus group session hooks
│   ├── useWebSocket.ts   # WebSocket connection hooks
│   └── use-toast.ts      # Toast notification hooks
├── lib/                   # Utility libraries
│   ├── api.ts            # API client (Axios-based)
│   ├── auth.ts           # NextAuth configuration
│   ├── chartUtils.ts     # Chart utility functions
│   ├── exportService.ts  # Data export utilities
│   └── utils.ts          # General utilities (cn, etc.)
├── types/                 # TypeScript type definitions
└── middleware.ts          # NextAuth middleware
```

## Key Patterns

### Authentication

- Uses NextAuth.js with JWT strategy
- Custom credentials provider connecting to FastAPI backend
- Protected routes via middleware
- Extended session types for user metadata

```typescript
// Session includes: id, accessToken, role, tier
```

### API Integration

- Backend: FastAPI at `NEXT_PUBLIC_API_URL`
- API client with automatic token injection
- React Query for data fetching and caching
- WebSocket for real-time simulation updates

### State Management

- **Zustand**: Local UI state
- **React Query**: Server state and caching
- **Context**: Theme, API status, session

### Component Patterns

- Server Components for static content
- Client Components ('use client') for interactivity
- Radix primitives for accessible UI
- CVA (Class Variance Authority) for component variants

## Environment Variables

### Local Development (`.env.local`)
```env
NEXT_PUBLIC_API_URL=http://localhost:8000  # FastAPI backend URL (empty for production proxy)
NEXTAUTH_URL=http://localhost:3002         # NextAuth URL
NEXTAUTH_SECRET=your-dev-secret            # Development secret
BACKEND_API_URL=http://localhost:8000      # Backend URL for server-side calls
```

### Production (Vercel Dashboard)
Configure these in Vercel project settings (NOT in vercel.json):
- `BACKEND_API_URL` - Production backend API URL
- `NEXT_PUBLIC_WS_URL` - WebSocket URL for real-time updates
- `NEXTAUTH_SECRET` - Strong production secret (use `openssl rand -base64 32`)
- `NEXTAUTH_URL` - Production URL (e.g., https://your-domain.vercel.app)

## Development Commands

```bash
npm run dev          # Start development server (port 3002)
npm run build        # Production build
npm run start        # Start production server
npm run lint         # Run ESLint
npm run type-check   # TypeScript type checking
npm run test         # Run Vitest tests
```

## Deployment

### Docker

The application runs in Docker with the following configuration:
- Container name: `agentverse-web-prod`
- External port: 3003
- Internal port: 3000

### Build Process

1. `npm run build` - Creates optimized production build
2. Build outputs to `.next/` directory
3. Deploy via Docker or standalone Node.js

## Code Quality Standards

### TypeScript

- Strict mode enabled
- No `any` types - use proper interfaces
- Use `LucideIcon` type for icon props
- Proper error typing in catch blocks

### Error Handling

- No console.log/error/warn in production code
- Errors handled via React Query onError
- Toast notifications for user feedback
- Proper try/catch without empty catches

### Security

- No hardcoded secrets or IP addresses in code
- Environment variables for all sensitive data (via Vercel dashboard)
- NextAuth secret required in production
- API tokens stored securely in JWT (not localStorage)
- Security headers configured in vercel.json:
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: DENY`
  - `X-XSS-Protection: 1; mode=block`
  - `Strict-Transport-Security: max-age=31536000; includeSubDomains`
  - `Referrer-Policy: strict-origin-when-cross-origin`
  - `Permissions-Policy: camera=(), microphone=(), geolocation=()`

### React Best Practices

- useEffect dependencies properly declared
- Memoization for expensive computations
- Proper cleanup in useEffect
- Avoid inline function definitions in renders

## UI/UX Guidelines

### Theme

- Dark cyberpunk aesthetic
- Primary colors: Cyan (#00FFFF), Purple
- Background: Black with white/10 borders
- Font: Monospace for technical elements

### Components

- Square corners (no rounded)
- Glitch effects on hover
- Terminal-style loading states
- Matrix rain background effects

### Accessibility

- ARIA labels on interactive elements
- Keyboard navigation support
- Focus visible states
- Screen reader friendly

## Testing

- Unit tests with Vitest
- Component tests with React Testing Library
- E2E tests (if configured with Playwright)

## Common Tasks

### Adding a New Dashboard Page

1. Create page at `src/app/dashboard/[name]/page.tsx`
2. Add 'use client' if client-side interactivity needed
3. Use existing layout components
4. Add route to sidebar navigation

### Adding API Endpoints

1. Add types to `src/lib/api.ts`
2. Create React Query hook in `src/hooks/useApi.ts`
3. Handle loading/error states with existing patterns

### Creating New Components

1. Place in appropriate `src/components/` subdirectory
2. Use TypeScript interfaces for props
3. Use `cn()` for conditional classes
4. Follow existing component patterns

## Troubleshooting

### Build Errors

- Run `npm run type-check` to identify TypeScript issues
- Ensure all imports are valid
- Check for missing environment variables

### Authentication Issues

- Verify `NEXTAUTH_SECRET` is set
- Check API backend is running
- Verify callback URLs match

### WebSocket Disconnections

- Check API server WebSocket endpoint
- Verify CORS configuration
- Check network connectivity

## Recent QA Fixes (2026-01-08)

### Security & Configuration
- Removed hardcoded backend IP addresses from all config files
- Added HSTS, Referrer-Policy, and Permissions-Policy security headers
- Fixed localStorage token storage - now uses session-based token management
- Moved sensitive environment variables to Vercel dashboard (not in vercel.json)
- Added `.test-credentials.json` to `.gitignore`

### Code Quality & Type Safety
- Fixed type safety issues in auth.ts with proper interfaces
- Removed all `as any` type casts in useApi.ts (uses proper ExtendedSessionUser interface)
- Fixed double type casts (`as unknown as X`) in useWebSocket.ts with proper union types
- Removed remaining organization_id reference from marketplace hooks
- Added getAccessToken() method to API client for secure token access
- Removed all console.log/error/warn statements (21 files)
- Fixed `icon: any` type issues with LucideIcon type
- Build passes with 0 TypeScript errors

### Feature Removal
- Removed Organizations and Invitations feature (Team section)
- Deleted 7 page files, 6 component files
- Removed ~200 lines of API methods and types

## QA Testing Protocol

**Test Account Credentials** (use for every QA session):
- Email: `claude-test@agentverse.io`
- Password: `TestAgent2024!`
- See `.test-credentials.json` for full config

**Testing Workflow**:
1. Always test on localhost:3002 FIRST
2. Fix all issues locally before any deployment
3. Test ALL dashboard pages, buttons, features
4. Check browser console for errors
5. Verify database connectivity
6. Deploy to Vercel only after local tests pass
7. Final production test after deployment

**Dashboard Pages to Test**:
- /dashboard (main overview)
- /dashboard/personas
- /dashboard/simulations
- /dashboard/results
- /dashboard/products
- /dashboard/projects
- /dashboard/marketplace
- /dashboard/accuracy
- /dashboard/settings
- /dashboard/guide
