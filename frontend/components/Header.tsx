"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Cpu, User, LogOut } from "lucide-react";
import { NotificationCenter } from "./NotificationCenter";
import { authService, User as AuthUser } from "../lib/auth";

interface HeaderProps {
  onActionComplete?: () => void;
}

export function Header({ onActionComplete }: HeaderProps = {}) {
  const [currentUser, setCurrentUser] = useState<AuthUser | null>(null);

  useEffect(() => {
    authService.getCurrentUser().then((u) => setCurrentUser(u));
  }, []);

  return (
    <header className="border-b border-[#DCDCD4] bg-[#FAFAF5] sticky top-0 z-30 shadow-2xs">
      <div className="max-w-[1500px] w-full mx-auto px-4 sm:px-6 lg:px-8 py-3.5">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-[#171717] text-[#FAFAF5] rounded-lg shrink-0">
              <Cpu className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center space-x-2.5">
                <Link href="/" className="hover:opacity-80 transition">
                  <h1 className="text-base sm:text-lg font-bold tracking-tight text-[#171717]">
                    Factory Health &amp; Response Agent
                  </h1>
                </Link>
              </div>
              <p className="text-xs text-[#6B6B66]">
                Predictive Maintenance Intelligence &amp; Autonomous Diagnostics
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-2.5 self-end sm:self-center">

            {/* User Session / Sign Out or Sign In */}
            {currentUser ? (
              <button
                type="button"
                onClick={() => authService.logout()}
                className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-[#6B6B66] hover:text-[#9C382E] bg-[#FAFAF5] hover:bg-[#F0F0EA] border border-[#DCDCD4] transition cursor-pointer"
                title="Sign out of factory workspace"
              >
                <LogOut className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">Sign out</span>
              </button>
            ) : (
              <Link
                href="/login"
                className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-[#FAFAF5] hover:bg-[#F5F5EE] border border-[#DCDCD4] text-[#171717] transition"
                title="Sign In"
              >
                <User className="w-3.5 h-3.5 text-[#6B6B66]" />
                <span className="hidden sm:inline">Sign In</span>
              </Link>
            )}

            {/* Notification Bell & Dropdown */}
            <NotificationCenter onActionComplete={onActionComplete} />
          </div>
        </div>
      </div>
    </header>
  );
}
