import { DefaultSession, DefaultUser } from 'next-auth';
import { JWT, DefaultJWT } from 'next-auth/jwt';

declare module 'next-auth' {
  interface Session {
    user: {
      id: string;
      accessToken: string;
      role: string;
      tier: string;
    } & DefaultSession['user'];
  }

  interface User extends DefaultUser {
    id: string;
    accessToken: string;
    refreshToken: string;
    role: string;
    tier: string;
  }
}

declare module 'next-auth/jwt' {
  interface JWT extends DefaultJWT {
    id: string;
    accessToken: string;
    refreshToken: string;
    role: string;
    tier: string;
  }
}
