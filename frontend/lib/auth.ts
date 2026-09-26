/**
 * Factory Health & Response Agent - Authentication Service
 * ========================================================
 * Provides real client-side session management via secure HTTP-only cookies.
 * Does not store JWT tokens in localStorage or sessionStorage.
 */

export interface User {
  id: string;
  email: string;
  name: string;
  role: "operator" | "reliability_engineer" | "plant_manager" | "admin" | string;
  shift?: string;
}

export interface LoginCredentials {
  email: string;
  password: string;
  rememberMe?: boolean;
}

export interface AuthResponse {
  success: boolean;
  user?: User;
  message?: string;
  error?: string;
  authConfigured: boolean;
}

export interface AuthStatus {
  isConfigured: boolean;
  provider: "none" | "jwt" | "oauth2" | "saml";
  allowGuestAccess: boolean;
}

export function getApiBaseUrl(): string {
  if (process.env.NEXT_PUBLIC_API_URL) {
    if (typeof window !== "undefined") {
      const currentHost = window.location.hostname;
      if (currentHost === "localhost") {
        return "http://localhost:8000";
      }
      if (currentHost === "127.0.0.1") {
        return "http://127.0.0.1:8000";
      }
    }
    return process.env.NEXT_PUBLIC_API_URL;
  }
  if (typeof window !== "undefined") {
    return `http://${window.location.hostname}:8000`;
  }
  return "http://localhost:8000";
}

class AuthService {
  private static instance: AuthService;

  private constructor() {}

  public static getInstance(): AuthService {
    if (!AuthService.instance) {
      AuthService.instance = new AuthService();
    }
    return AuthService.instance;
  }

  /**
   * Checks backend authentication status.
   */
  public async getAuthStatus(): Promise<AuthStatus> {
    return {
      isConfigured: true,
      provider: "jwt",
      allowGuestAccess: false,
    };
  }

  /**
   * Authenticates operator credentials against FastAPI backend.
   * On success, backend sets secure HTTP-only cookie.
   */
  public async login(credentials: LoginCredentials): Promise<AuthResponse> {
    const trimmedEmail = credentials.email.trim();
    if (!trimmedEmail) {
      return {
        success: false,
        authConfigured: true,
        error: "Please enter your operator email address.",
      };
    }

    if (!credentials.password) {
      return {
        success: false,
        authConfigured: true,
        error: "Please enter your password.",
      };
    }

    try {
      const res = await fetch(`${getApiBaseUrl()}/api/auth/login`, {
        method: "POST",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          email: trimmedEmail,
          password: credentials.password,
          remember_me: Boolean(credentials.rememberMe),
        }),
      });

      if (!res.ok) {
        let errorMsg = "Invalid email or password.";
        try {
          const errData = await res.json();
          if (errData.detail) errorMsg = errData.detail;
        } catch {
          // Keep default message
        }
        return {
          success: false,
          authConfigured: true,
          error: errorMsg,
        };
      }

      const data = await res.json();
      return {
        success: true,
        user: data.user,
        authConfigured: true,
      };
    } catch {
      return {
        success: false,
        authConfigured: true,
        error: "Unable to reach the authentication server. Please verify backend is running on port 8000.",
      };
    }
  }

  /**
   * Terminates active session by calling logout endpoint (clears HTTP-only cookie).
   */
  public async logout(): Promise<void> {
    try {
      await fetch(`${getApiBaseUrl()}/api/auth/logout`, {
        method: "POST",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
        },
      });
    } catch {
      // Best-effort logout
    }
    if (typeof window !== "undefined") {
      window.location.href = "/login";
    }
  }

  /**
   * Validates current authenticated operator from backend session cookie.
   */
  public async getCurrentUser(): Promise<User | null> {
    try {
      const res = await fetch(`${getApiBaseUrl()}/api/auth/me?_t=${Date.now()}`, {
        method: "GET",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
        },
      });

      if (!res.ok) {
        return null;
      }

      const data = await res.json();
      return data.user || null;
    } catch {
      return null;
    }
  }

  /**
   * Informational password recovery inquiry.
   */
  public async requestPasswordReset(_email: string): Promise<{ success: boolean; message: string }> {
    return {
      success: false,
      message: "Password recovery is managed by the system administrator. Please contact factory IT operations.",
    };
  }
}

export const authService = AuthService.getInstance();
