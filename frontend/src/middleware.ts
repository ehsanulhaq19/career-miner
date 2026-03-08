import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const authRoutes = ["/login", "/register", "/forgot-password"];

export function middleware(request: NextRequest) {
  const token = request.cookies.get("token")?.value;
  const { pathname } = request.nextUrl;

  const isAuthRoute = authRoutes.some((route) => pathname.startsWith(route));

  if (!token && !isAuthRoute) {
    return NextResponse.redirect(new URL("/login", request.url));
  }

  if (token && isAuthRoute) {
    return NextResponse.redirect(new URL("/dashboard", request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico).*)"],
};
