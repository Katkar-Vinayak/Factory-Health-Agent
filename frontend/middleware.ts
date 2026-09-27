import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

function isTokenValid(token?: string): boolean {
  if (!token) return false;
  try {
    const parts = token.split(".");
    if (parts.length !== 3) return false;
    let base64 = parts[1].replace(/-/g, "+").replace(/_/g, "/");
    while (base64.length % 4 !== 0) {
      base64 += "=";
    }
    let jsonStr: string;
    if (typeof Buffer !== "undefined") {
      jsonStr = Buffer.from(base64, "base64").toString("utf-8");
    } else {
      jsonStr = atob(base64);
    }
    const payload = JSON.parse(jsonStr);
    if (payload.exp && payload.exp * 1000 <= Date.now()) {
      return false;
    }
    return true;
  } catch {
    return false;
  }
}

export function middleware(request: NextRequest) {
  const token = request.cookies.get("access_token")?.value;
  const { pathname } = request.nextUrl;
  const tokenValid = isTokenValid(token);

  // Protected paths requiring active session
  const isProtected = pathname === "/" || pathname.startsWith("/machines");

  if (isProtected && !tokenValid) {
    const loginUrl = new URL("/login", request.url);
    const response = NextResponse.redirect(loginUrl);
    if (token) {
      response.cookies.delete("access_token");
    }
    return response;
  }

  // Redirect already authenticated operators away from login
  if (pathname === "/login" && tokenValid) {
    const dashboardUrl = new URL("/", request.url);
    return NextResponse.redirect(dashboardUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/", "/machines/:path*", "/login"],
};
