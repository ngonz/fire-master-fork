import { useState, useMemo } from "react";
import { Link } from "react-router";
import { useAssetHub } from "../api/queries";
import Layout from "../components/Layout";
import { formatCurrency, fmtCompact as formatCompact } from "../utils/formatting";
import { accountTypeLabel, accountTypeColor } from "../utils/accountTypes";
import type { AccountTile } from "../types/assets";

type FilterTab = "all" | "retirement" | "banking" | "real_estate" | "credit_card" | "crypto" | "vehicle" | "private" | "other";

const FILTER_TABS: { key: FilterTab; label: string }[] = [
  { key: "all", label: "All" },
  { key: "retirement", label: "Retirement" },
  { key: "banking", label: "Banking" },
  { key: "real_estate", label: "Real Estate" },
  { key: "credit_card", label: "Credit Cards" },
  { key: "crypto", label: "Crypto" },
  { key: "vehicle", label: "Vehicles" },
  { key: "private", label: "Private" },
  { key: "other", label: "Other" },
];

const FILTER_GROUPS: Record<FilterTab, string[]> = {
  all: [],
  retirement: ["401k", "ira", "roth_ira"],
  banking: ["checking", "savings", "hsa"],
  real_estate: ["real_estate"],
  credit_card: ["CREDIT_CARD"],
  crypto: ["crypto"],
  vehicle: ["VEHICLE"],
  private: ["PRIVATE"],
  other: ["taxable", "other"],
};


function StatCard({
  label,
  value,
  color,
}: {
  label: string;
  value: string;
  color: string;
}) {
  return (
    <div className="bg-[var(--bg-card)] border border-[var(--border)] rounded-lg p-4 flex flex-col gap-1">
      <span className="text-xs uppercase tracking-wider text-[var(--text-secondary)]">
        {label}
      </span>
      <span
        className="text-2xl font-bold font-mono tracking-tight"
        style={{ color }}
      >
        {value}
      </span>
    </div>
  );
}

function AccountCard({ account }: { account: AccountTile }) {
  const typeLabel = accountTypeLabel(account.account_type);
  const typeColor = accountTypeColor(account.account_type);

  const change30d = account.value_change_30d;
  const changeColor = change30d != null
    ? change30d >= 0 ? "var(--green)" : "var(--red)"
    : undefined;
  const changeText = change30d != null
    ? `${change30d >= 0 ? "+" : ""}${formatCurrency(change30d)}`
    : null;

  return (
    <Link
      to={`/assets/account/${account.id}`}
      className="group block bg-[var(--bg-card)] border border-[var(--border)] rounded-lg p-4 hover:border-[color:var(--blue)]! transition-all duration-200 relative overflow-hidden"
      style={{ animationDelay: "0ms" }}
    >
      {/* Enrichment indicator — glowing dot in top-right */}
      {account.has_enrichment && (
        <span
          className="absolute top-3 right-3 w-2 h-2 rounded-full"
          style={{
            background: "var(--green)",
            boxShadow: "0 0 6px rgba(0,212,170,0.5)",
          }}
          title="Has notes & strategy"
        />
      )}

      {/* Type badge */}
      <div className="flex items-center gap-2 mb-3">
        <span
          className="text-[10px] font-semibold uppercase tracking-widest px-2 py-0.5 rounded"
          style={{
            color: typeColor,
            background: `${typeColor}15`,
            border: `1px solid ${typeColor}30`,
          }}
        >
          {typeLabel}
        </span>
        {account.fire_role && (
          <span
            className="text-[10px] tracking-wide px-1.5 py-0.5 rounded text-[var(--text-secondary)]"
            style={{
              background: "rgba(255,255,255,0.04)",
              border: "1px solid rgba(255,255,255,0.08)",
            }}
          >
            {account.fire_role}
          </span>
        )}
      </div>

      {/* Account name & institution */}
      <p className="text-sm font-medium text-[var(--text-primary)] leading-tight truncate mb-0.5">
        {account.name}
      </p>
      {account.institution && (
        <p className="text-xs text-[var(--text-secondary)] truncate mb-3">
          {account.institution}
        </p>
      )}
      {!account.institution && <div className="mb-3" />}

      {/* Balance */}
      <div className="flex items-end justify-between">
        <span
          className="text-xl font-bold font-mono tracking-tight"
          style={{
            color: account.is_asset ? "var(--text-primary)" : "var(--red)",
          }}
        >
          {account.is_asset ? "" : "-"}
          {formatCurrency(Math.abs(account.balance))}
        </span>
        {changeText && (
          <span
            className="text-xs font-mono"
            style={{ color: changeColor }}
          >
            {changeText}
          </span>
        )}
      </div>

      {/* Subtle bottom accent line */}
      <div
        className="absolute bottom-0 left-0 right-0 h-[2px] opacity-0 group-hover:opacity-100 transition-opacity duration-300"
        style={{ background: typeColor }}
      />
    </Link>
  );
}

export default function AssetsPage() {
  const [filter, setFilter] = useState<FilterTab>("all");
  const { data: hub, isLoading } = useAssetHub();

  const filteredAccounts = useMemo(() => {
    if (!hub) return [];
    const accounts = [...hub.accounts].sort(
      (a, b) => Math.abs(b.balance_cents) - Math.abs(a.balance_cents)
    );
    if (filter === "all") return accounts;
    const types = FILTER_GROUPS[filter];
    return accounts.filter((a) => types.includes(a.account_type));
  }, [hub, filter]);

  const tabCounts = useMemo(() => {
    if (!hub) return {} as Record<FilterTab, number>;
    const counts: Record<FilterTab, number> = {
      all: hub.accounts.length,
      retirement: 0,
      banking: 0,
      real_estate: 0,
      credit_card: 0,
      crypto: 0,
      vehicle: 0,
      private: 0,
      other: 0,
    };
    for (const acct of hub.accounts) {
      for (const [key, types] of Object.entries(FILTER_GROUPS)) {
        if (key !== "all" && types.includes(acct.account_type)) {
          counts[key as FilterTab]++;
        }
      }
    }
    return counts;
  }, [hub]);

  if (isLoading || !hub) {
    return (
      <Layout>
        <div className="flex items-center justify-center h-96 text-[var(--text-secondary)]">
          Loading...
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="space-y-6">
        {/* Header */}
        <div>
          <h2 className="text-xl font-semibold text-[var(--text-primary)] tracking-tight">
            Asset Hub
          </h2>
          <p className="text-sm text-[var(--text-secondary)] mt-1">
            {hub.accounts.length} accounts
            {hub.accounts.filter((a) => a.has_enrichment).length > 0 && (
              <span>
                {" \u00B7 "}
                <span style={{ color: "var(--green)" }}>
                  {hub.accounts.filter((a) => a.has_enrichment).length} enriched
                </span>
              </span>
            )}
          </p>
        </div>

        {/* Stat cards */}
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          <StatCard
            label="Net Worth"
            value={formatCompact(hub.total_net_worth)}
            color="var(--text-primary)"
          />
          <StatCard
            label="Total Assets"
            value={formatCompact(hub.total_assets)}
            color="var(--green)"
          />
          <StatCard
            label="Total Liabilities"
            value={formatCompact(hub.total_liabilities)}
            color="var(--red)"
          />
        </div>

        {/* Filter tabs */}
        <div className="flex gap-1 border-b border-[var(--border)] pb-px overflow-x-auto">
          {FILTER_TABS.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setFilter(tab.key)}
              className={`px-3 py-2 text-sm transition-colors relative whitespace-nowrap shrink-0 ${
                filter === tab.key
                  ? "text-[var(--text-primary)]"
                  : "text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
              }`}
            >
              {tab.label}
              <span className="ml-1.5 text-xs text-[var(--text-secondary)]">
                {tabCounts[tab.key] ?? 0}
              </span>
              {filter === tab.key && (
                <span className="absolute bottom-0 left-0 right-0 h-[2px] bg-[var(--blue)]" />
              )}
            </button>
          ))}
        </div>

        {/* Category balance summary */}
        {filter !== "all" && filteredAccounts.length > 0 && (
          <div className="bg-[var(--bg-card)] border border-[var(--border)] rounded-lg px-4 py-3 flex items-center justify-between">
            <span className="text-sm text-[var(--text-secondary)]">
              {FILTER_TABS.find((t) => t.key === filter)?.label} — {filteredAccounts.length} account{filteredAccounts.length !== 1 ? "s" : ""}
            </span>
            <span
              className="text-lg font-bold font-mono"
              style={{
                color:
                  filteredAccounts.reduce((sum, a) => sum + (a.is_asset ? a.balance_cents : -a.balance_cents), 0) >= 0
                    ? "var(--green)"
                    : "var(--red)",
              }}
            >
              {formatCurrency(filteredAccounts.reduce((sum, a) => sum + (a.is_asset ? a.balance_cents : -a.balance_cents), 0) / 100)}
            </span>
          </div>
        )}

        {/* Account grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {filteredAccounts.map((account) => (
            <AccountCard key={account.id} account={account} />
          ))}
        </div>

        {filteredAccounts.length === 0 && (
          <div className="text-center py-12 text-[var(--text-secondary)] text-sm">
            No accounts in this category.
          </div>
        )}
      </div>
    </Layout>
  );
}
