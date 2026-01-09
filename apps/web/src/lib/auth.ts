import type { NextAuthOptions, User } from 'next-auth';
import type { JWT } from 'next-auth/jwt';
import CredentialsProvider from 'next-auth/providers/credentials';

// Use BACKEND_API_URL for server-side auth calls (not exposed to client)
const API_URL = process.env.BACKEND_API_URL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Extended user type for authentication
interface AuthUser extends User {
  accessToken: string;
  refreshToken: string;
  role: string;
  tier: string;
}

// Extended JWT type
interface AuthToken extends JWT {
  id: string;
  accessToken: string;
  refreshToken: string;
  role: string;
  tier: string;
}

// Extended session user type
interface SessionUser {
  id: string;
  name?: string | null;
  email?: string | null;
  image?: string | null;
  accessToken: string;
  role: string;
  tier: string;
}

export const authOptions: NextAuthOptions = {
  providers: [
    CredentialsProvider({
      name: 'credentials',
      credentials: {
        email: { label: 'Email', type: 'email' },
        password: { label: 'Password', type: 'password' },
      },
      async authorize(credentials) {
        if (!credentials?.email || !credentials?.password) {
          return null;
        }

        try {
          // Call our FastAPI backend for authentication
          const response = await fetch(`${API_URL}/api/v1/auth/login`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              email: credentials.email,
              password: credentials.password,
            }),
          });

          if (!response.ok) {
            return null;
          }

          const tokens = await response.json();

          // Get user info with the access token
          const userResponse = await fetch(`${API_URL}/api/v1/auth/me`, {
            headers: {
              Authorization: `Bearer ${tokens.access_token}`,
            },
          });

          if (!userResponse.ok) {
            return null;
          }

          const user = await userResponse.json();

          return {
            id: user.id,
            email: user.email,
            name: user.full_name,
            accessToken: tokens.access_token,
            refreshToken: tokens.refresh_token,
            role: user.role,
            tier: user.tier,
          };
        } catch {
          // Authentication failed - return null to indicate failure
          return null;
        }
      },
    }),
  ],
  callbacks: {
    async jwt({ token, user }) {
      if (user) {
        const authUser = user as AuthUser;
        const authToken = token as AuthToken;
        authToken.id = authUser.id as string;
        authToken.accessToken = authUser.accessToken;
        authToken.refreshToken = authUser.refreshToken;
        authToken.role = authUser.role;
        authToken.tier = authUser.tier;
        return authToken;
      }
      return token;
    },
    async session({ session, token }) {
      if (session.user) {
        const authToken = token as AuthToken;
        const sessionUser = session.user as SessionUser;
        sessionUser.id = authToken.id;
        sessionUser.accessToken = authToken.accessToken;
        sessionUser.role = authToken.role;
        sessionUser.tier = authToken.tier;
      }
      return session;
    },
  },
  pages: {
    signIn: '/auth/login',
  },
  session: {
    strategy: 'jwt',
    maxAge: 24 * 60 * 60, // 24 hours
  },
  secret: process.env.NEXTAUTH_SECRET,
};
