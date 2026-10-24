import React from "react";
import { Badge } from "../ui/Badge";
import {
  Activity,
  BarChart2,
  CheckSquare,
  Compass,
  FileText,
  Play,
  Settings as SettingsIcon,
  ShieldCheck,
  Split
} from "lucide-react";
import { ProviderStatus } from "../../lib/types";

interface NavbarProps {
  activeTab: string;
  onSelectTab: (tab: string) => void;
  providerStatus?: ProviderStatus | null;
}

export const Navbar: React.FC<NavbarProps> = ({
  activeTab,
  onSelectTab,
  providerStatus,
}) => {
  const navItems = [
    { id: "dashboard", label: "Dashboard", icon: <Activity size={16} /> },
    { id: "documents", label: "Documents", icon: <FileText size={16} /> },
    { id: "playground", label: "Playground", icon: <Compass size={16} /> },
    { id: "testcases", label: "Test Cases", icon: <CheckSquare size={16} /> },
    { id: "runner", label: "Run Eval", icon: <Play size={16} /> },
    { id: "compare", label: "Compare", icon: <Split size={16} /> },
    { id: "settings", label: "Settings", icon: <SettingsIcon size={16} /> },
  ];

  const isDemo = providerStatus?.demo_mode ?? true;

  return (
    <header className="border-b-[2.5px] border-ink bg-surface sticky top-0 z-40">
      {/* Top Banner if in Demo Mode */}
      {isDemo && (
        <div className="bg-[#FFB020] text-ink border-b-2 border-ink px-4 py-1 text-xs font-mono font-bold flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="bg-ink text-white px-1.5 py-0.2 text-[10px] uppercase">DEMO MODE</span>
            <span>Running with zero external API costs & local embeddings. Add an Anthropic key in Settings to activate live LLM judge.</span>
          </div>
          <button
            onClick={() => onSelectTab("settings")}
            className="underline hover:text-white cursor-pointer"
          >
            Setup Guide &rarr;
          </button>
        </div>
      )}

      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-2.5 flex items-center justify-between">
        {/* Brand */}
        <div
          onClick={() => onSelectTab("dashboard")}
          className="flex items-center gap-3 cursor-pointer select-none group"
        >
          <div className="w-9 h-9 bg-lime border-2 border-ink shadow-[2px_2px_0_#171717] flex items-center justify-center font-display font-black text-xl text-ink group-hover:bg-lime-hover transition-all">
            <ShieldCheck size={22} className="stroke-[2.5]" />
          </div>
          <div>
            <div className="font-display font-extrabold text-lg leading-tight tracking-tight text-ink flex items-center gap-2">
              <span>AI TRUTH INSPECTOR</span>
              {isDemo ? (
                <Badge variant="demo" size="sm">DEMO</Badge>
              ) : (
                <Badge variant="pass" size="sm">LIVE</Badge>
              )}
            </div>
            <div className="font-mono text-[11px] text-ink/70 italic font-semibold">
              "Trust, but verify."
            </div>
          </div>
        </div>

        {/* Navigation Items */}
        <nav className="flex items-center gap-1">
          {navItems.map((item) => {
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => onSelectTab(item.id)}
                className={`flex items-center gap-1.5 px-3 py-1.5 font-display font-bold text-xs uppercase tracking-wider transition-all border-2 cursor-pointer ${
                  isActive
                    ? "bg-lime text-ink border-ink shadow-[2px_2px_0_#171717]"
                    : "bg-transparent text-ink border-transparent hover:border-ink hover:bg-surface-muted"
                }`}
              >
                {item.icon}
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>
      </div>
    </header>
  );
};
