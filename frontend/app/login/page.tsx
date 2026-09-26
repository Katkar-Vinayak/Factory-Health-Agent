"use client";

export const dynamic = "force-dynamic";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import {
  Activity,
  Eye,
  EyeOff,
  AlertCircle,
  Info,
  Loader2
} from "lucide-react";
import { authService } from "../../lib/auth";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(false);

  // Validation & feedback state
  const [emailError, setEmailError] = useState("");
  const [passwordError, setPasswordError] = useState("");
  const [authError, setAuthError] = useState("");
  const [forgotPasswordNotice, setForgotPasswordNotice] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  // Email format validation
  const validateEmail = (value: string): boolean => {
    const trimmed = value.trim();
    if (!trimmed) {
      setEmailError("Please enter your plant operator email address.");
      return false;
    }
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(trimmed)) {
      setEmailError("Please enter a valid email format (e.g. operator@factory.com).");
      return false;
    }
    setEmailError("");
    return true;
  };

  const validatePassword = (value: string): boolean => {
    if (!value) {
      setPasswordError("Please enter your workspace password.");
      return false;
    }
    setPasswordError("");
    return true;
  };

  const handleEmailChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setEmail(e.target.value);
    if (emailError) validateEmail(e.target.value);
    if (authError) setAuthError("");
  };

  const handlePasswordChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setPassword(e.target.value);
    if (passwordError) validatePassword(e.target.value);
    if (authError) setAuthError("");
  };

  useEffect(() => {
    authService.getCurrentUser().then((user) => {
      if (user) {
        router.replace("/");
      }
    });
  }, [router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setAuthError("");
    setForgotPasswordNotice("");

    const isEmailValid = validateEmail(email);
    const isPasswordValid = validatePassword(password);

    if (!isEmailValid || !isPasswordValid) {
      return;
    }

    setIsLoading(true);
    try {
      const response = await authService.login({
        email,
        password,
        rememberMe,
      });

      if (response.success) {
        router.replace("/");
        router.refresh();
        return;
      }

      setAuthError(response.error || "Invalid email or password.");
    } catch {
      setAuthError("Unable to communicate with the authentication service.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleForgotPassword = async () => {
    setAuthError("");
    const res = await authService.requestPasswordReset(email);
    setForgotPasswordNotice(res.message);
  };

  return (
    <div className="min-h-screen bg-[#F5F5EE] flex flex-col items-center justify-center px-4 py-12 sm:px-6 lg:px-8 selection:bg-[#171717] selection:text-white">
      <div className="w-full max-w-[420px] flex flex-col items-center">
        {/* Brand Identity Header */}
        <div className="text-center mb-6">
          <div className="inline-flex items-center justify-center w-11 h-11 rounded-xl bg-[#171717] text-white mb-3 shadow-xs">
            <Activity className="w-5 h-5 text-white" />
          </div>
          <h1 className="text-xl font-bold tracking-tight text-[#171717]">
            Factory Health & Response Agent
          </h1>
          <p className="text-xs font-mono text-[#6B6B66] uppercase tracking-wider mt-1">
            Predictive Maintenance Intelligence
          </p>
        </div>

        {/* Authentication Card */}
        <div className="w-full bg-[#FAFAF5] rounded-2xl border border-[#DCDCD4] p-6 sm:p-8 shadow-xs">
          <div className="mb-6">
            <h2 className="text-xl sm:text-2xl font-extrabold text-[#171717] tracking-tight">
              Welcome back
            </h2>
            <p className="text-xs text-[#6B6B66] mt-1">
              Sign in to your factory workspace
            </p>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} noValidate className="space-y-4">
            {/* Email Field */}
            <div>
              <label
                htmlFor="operator-email"
                className="block text-xs font-semibold text-[#171717] mb-1.5"
              >
                Email
              </label>
              <input
                id="operator-email"
                name="email"
                type="email"
                autoComplete="email"
                value={email}
                onChange={handleEmailChange}
                placeholder="operator@factory.com"
                disabled={isLoading}
                aria-invalid={Boolean(emailError)}
                aria-describedby={emailError ? "email-error" : undefined}
                className={`w-full text-xs font-medium px-3.5 py-2.5 rounded-lg bg-[#FAFAF5] border text-[#171717] placeholder-[#8C8C85] transition focus:outline-none focus:ring-1 ${
                  emailError
                    ? "border-[#DE9E98] focus:border-[#9C382E] focus:ring-[#9C382E]"
                    : "border-[#DCDCD4] focus:border-[#171717] focus:ring-[#171717]"
                }`}
              />
              {emailError && (
                <p id="email-error" className="mt-1 text-[11px] text-[#9C382E] flex items-center">
                  <AlertCircle className="w-3 h-3 mr-1 shrink-0" />
                  {emailError}
                </p>
              )}
            </div>

            {/* Password Field */}
            <div>
              <label
                htmlFor="operator-password"
                className="block text-xs font-semibold text-[#171717] mb-1.5"
              >
                Password
              </label>
              <div className="relative">
                <input
                  id="operator-password"
                  name="password"
                  type={showPassword ? "text" : "password"}
                  autoComplete="current-password"
                  value={password}
                  onChange={handlePasswordChange}
                  placeholder="••••••••••••"
                  disabled={isLoading}
                  aria-invalid={Boolean(passwordError)}
                  aria-describedby={passwordError ? "password-error" : undefined}
                  className={`w-full text-xs font-medium px-3.5 py-2.5 pr-10 rounded-lg bg-[#FAFAF5] border text-[#171717] placeholder-[#8C8C85] transition focus:outline-none focus:ring-1 ${
                    passwordError
                      ? "border-[#DE9E98] focus:border-[#9C382E] focus:ring-[#9C382E]"
                      : "border-[#DCDCD4] focus:border-[#171717] focus:ring-[#171717]"
                  }`}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  aria-label={showPassword ? "Hide password" : "Show password"}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-[#8C8C85] hover:text-[#171717] transition cursor-pointer p-1"
                >
                  {showPassword ? (
                    <EyeOff className="w-4 h-4" />
                  ) : (
                    <Eye className="w-4 h-4" />
                  )}
                </button>
              </div>
              {passwordError && (
                <p id="password-error" className="mt-1 text-[11px] text-[#9C382E] flex items-center">
                  <AlertCircle className="w-3 h-3 mr-1 shrink-0" />
                  {passwordError}
                </p>
              )}
            </div>

            {/* Remember Me & Forgot Password Controls */}
            <div className="flex items-center justify-between pt-1">
              <label className="flex items-center space-x-2 text-xs text-[#6B6B66] cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={rememberMe}
                  onChange={(e) => setRememberMe(e.target.checked)}
                  disabled={isLoading}
                  className="rounded border-[#DCDCD4] text-[#171717] focus:ring-[#171717] w-3.5 h-3.5 accent-[#171717]"
                />
                <span>Remember me</span>
              </label>

              <button
                type="button"
                onClick={handleForgotPassword}
                className="text-xs font-medium text-[#6B6B66] hover:text-[#171717] underline underline-offset-2 transition cursor-pointer"
              >
                Forgot password?
              </button>
            </div>

            {/* Forgot Password Informational Banner */}
            {forgotPasswordNotice && (
              <div className="p-3 rounded-lg bg-[#F5F5EE] border border-[#DCDCD4] text-xs text-[#6B6B66] flex items-start space-x-2 animate-fadeIn">
                <Info className="w-4 h-4 text-[#8C8C85] mt-0.5 shrink-0" />
                <p className="leading-relaxed">{forgotPasswordNotice}</p>
              </div>
            )}

            {/* Authentication Error Callout */}
            {authError && (
              <div className="p-3.5 rounded-lg bg-[#FDF0EE] border border-[#DE9E98] text-xs text-[#9C382E] flex items-start space-x-2 animate-fadeIn">
                <AlertCircle className="w-4 h-4 text-[#9C382E] mt-0.5 shrink-0" />
                <div>
                  <p className="font-semibold">Sign in failed</p>
                  <p className="mt-0.5 text-[11px] text-[#9C382E] leading-relaxed">
                    {authError}
                  </p>
                </div>
              </div>
            )}

            {/* Submit Button */}
            <div className="pt-2">
              <button
                type="submit"
                disabled={isLoading}
                className="w-full py-2.5 px-4 rounded-lg bg-[#171717] hover:bg-[#2E2E2A] text-white text-xs font-semibold tracking-wider transition cursor-pointer flex items-center justify-center space-x-2 shadow-xs disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isLoading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin mr-1.5" />
                    <span>Signing in...</span>
                  </>
                ) : (
                  <span>Sign in</span>
                )}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
