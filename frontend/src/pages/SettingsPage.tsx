import { useSearchParams } from "react-router";
import Layout from "../components/Layout";
import FireConfigPage from "./FireConfigPage";

const TABS = [
  { id: "plan", label: "Plan" },
  { id: "appearance", label: "Appearance" },
] as const;

export default function SettingsPage() {
  const [params, setParams] = useSearchParams();
  // Default to the Plan tab so the important "launch" settings are front and center.
  const tab = params.get("tab") === "appearance" ? "appearance" : "plan";

  return (
    <Layout>
      <div className="max-w-4xl space-y-6">
        <h2 className="text-xl font-semibold text-[var(--text-primary)] tracking-tight">Settings</h2>

        <div className="flex gap-6 border-b border-[var(--border)]">
          {TABS.map((t) => {
            const active = tab === t.id;
            return (
              <button
                key={t.id}
                onClick={() => setParams(t.id === "plan" ? {} : { tab: t.id })}
                className={`-mb-px border-b-2 px-1 py-2.5 text-sm transition-colors ${
                  active
                    ? "border-[var(--green)] text-[var(--green)] font-medium"
                    : "border-transparent text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
                }`}
              >
                {t.label}
              </button>
            );
          })}
        </div>

        {tab === "plan" ? <FireConfigPage /> : <AppearanceSettings />}
      </div>
    </Layout>
  );
}

function AppearanceSettings() {
  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-base font-semibold text-[var(--text-primary)] tracking-tight">Appearance</h3>
        <p className="mt-1 text-sm text-[var(--text-secondary)]">Theme and display preferences.</p>
      </div>
      <div className="rounded-lg border border-[var(--border)] bg-[var(--bg-card)] p-10 text-center">
        <p className="text-sm text-[var(--text-secondary)]">
          Coming soon — light/dark themes and display options.
        </p>
      </div>
    </div>
  );
}
