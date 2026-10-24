import React, { useEffect, useState } from "react";
import { CaseResult, ProviderStatus } from "./lib/types";
import { api } from "./lib/api";
import { Navbar } from "./components/domain/Navbar";
import { DashboardPage } from "./pages/DashboardPage";
import { DocumentsPage } from "./pages/DocumentsPage";
import { PlaygroundPage } from "./pages/PlaygroundPage";
import { TestCasesPage } from "./pages/TestCasesPage";
import { EvaluationRunnerPage } from "./pages/EvaluationRunnerPage";
import { ResultsPage } from "./pages/ResultsPage";
import { FailureDetailPage } from "./pages/FailureDetailPage";
import { ComparePage } from "./pages/ComparePage";
import { SettingsPage } from "./pages/SettingsPage";

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<string>("dashboard");
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [selectedCaseResult, setSelectedCaseResult] = useState<CaseResult | null>(null);
  const [providerStatus, setProviderStatus] = useState<ProviderStatus | null>(null);

  const fetchStatus = async () => {
    try {
      const data = await api.getProviderStatus();
      setProviderStatus(data);
    } catch (err) {
      console.error("Provider status fetch error:", err);
    }
  };

  useEffect(() => {
    fetchStatus();
  }, []);

  const handleNavigate = (tab: string, runId?: string) => {
    setActiveTab(tab);
    if (runId) {
      setSelectedRunId(runId);
    }
  };

  const handleSelectCase = (caseResult: CaseResult) => {
    setSelectedCaseResult(caseResult);
    setActiveTab("failure_detail");
  };

  return (
    <div className="min-h-screen flex flex-col bg-paper text-ink font-body">
      <Navbar
        activeTab={activeTab}
        onSelectTab={(tab) => {
          setActiveTab(tab);
          if (tab !== "results") setSelectedRunId(null);
          if (tab !== "failure_detail") setSelectedCaseResult(null);
        }}
        providerStatus={providerStatus}
      />

      <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 lg:p-8">
        {activeTab === "dashboard" && (
          <DashboardPage
            onNavigate={handleNavigate}
            providerStatus={providerStatus}
          />
        )}

        {activeTab === "documents" && <DocumentsPage />}

        {activeTab === "playground" && <PlaygroundPage />}

        {activeTab === "testcases" && <TestCasesPage />}

        {activeTab === "runner" && (
          <EvaluationRunnerPage
            onEvaluationCompleted={(runId) => {
              setSelectedRunId(runId);
              setActiveTab("results");
            }}
          />
        )}

        {activeTab === "results" && selectedRunId && (
          <ResultsPage
            runId={selectedRunId}
            onBack={() => {
              setSelectedRunId(null);
              setActiveTab("dashboard");
            }}
            onSelectCase={handleSelectCase}
          />
        )}

        {activeTab === "results" && !selectedRunId && (
          <DashboardPage
            onNavigate={handleNavigate}
            providerStatus={providerStatus}
          />
        )}

        {activeTab === "failure_detail" && selectedCaseResult && (
          <FailureDetailPage
            caseResult={selectedCaseResult}
            onBack={() => setActiveTab("results")}
            onOverrideUpdated={() => {
              // Stay on page and let user inspect updated overrides
            }}
          />
        )}

        {activeTab === "compare" && <ComparePage />}

        {activeTab === "settings" && <SettingsPage />}
      </main>

      <footer className="border-t-2 border-ink py-4 px-6 text-center font-mono text-xs text-ink/70 bg-surface">
        <div className="flex flex-wrap items-center justify-between gap-2 max-w-7xl mx-auto">
          <span>AI Truth Inspector &bull; RAG Evaluation &amp; Failure Diagnosis Platform</span>
          <span className="font-bold">"Trust, but verify."</span>
        </div>
      </footer>
    </div>
  );
};

export default App;
