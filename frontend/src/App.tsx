import React, { useEffect, useState } from "react";
import {
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Tooltip,
  BarChart,
  Bar,
  LineChart,
  Line,
  AreaChart,
  Area,
  Legend,
  XAxis,
  YAxis,
  CartesianGrid,
  LabelList,
} from "recharts";
import {
  Routes,
  Route,
  Link,
  useNavigate,
  useLocation,
  Navigate,
} from "react-router-dom";

const API = `${import.meta.env.VITE_API_URL || ""}/api`;

// Demo-login prefill. Local development supplies VITE_DEMO_EMAIL /
// VITE_DEMO_PASSWORD via frontend/.env.development so the credential is
// never bundled into production builds. Deployments that want a prefill
// must provide their own values via VITE_* environment variables.
const DEMO_EMAIL = import.meta.env.VITE_DEMO_EMAIL || "admin@demo.com";
const DEMO_PASSWORD = import.meta.env.VITE_DEMO_PASSWORD || "";

/* =========================================================
   API HELPERS
========================================================= */

async function apiGet(path: string) {
  const token = localStorage.getItem("token");

  const response = await fetch(API + path, {
    method: "GET",
    headers: {
      Accept: "application/json",
      ...(token
        ? { Authorization: `Bearer ${token}` }
        : {}),
    },
  });

  const text = await response.text();

  let data: any = {};

  try {
    data = text ? JSON.parse(text) : {};
  } catch {
    data = {};
  }

  if (!response.ok) {
    throw new Error(
      data.detail ||
        `Request failed: ${response.status}`
    );
  }

  return data;
}

/* =========================================================
   PATCH API
========================================================= */

async function apiPatch(
  path: string,
  body: any
) {
  const token = localStorage.getItem("token");

  const response = await fetch(API + path, {
    method: "PATCH",

    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",

      ...(token
        ? {
            Authorization:
              `Bearer ${token}`,
          }
        : {}),
    },

    body: JSON.stringify(body),
  });

  const text =
    await response.text();

  let data: any = {};

  try {
    data = text
      ? JSON.parse(text)
      : {};
  } catch {
    data = {};
  }

  if (!response.ok) {
    throw new Error(
      data.detail ||
        `Request failed: ${response.status}`
    );
  }

  return data;
}

async function apiPost(
  path: string,
  body: any
) {
  const token = localStorage.getItem("token");

  const response = await fetch(API + path, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
      ...(token
        ? { Authorization: `Bearer ${token}` }
        : {}),
    },
    body: JSON.stringify(body),
  });

  const text = await response.text();
  let data: any = {};

  try {
    data = text ? JSON.parse(text) : {};
  } catch {
    data = {};
  }

  if (!response.ok) {
    throw new Error(
      data.detail ||
        `Request failed: ${response.status}`
    );
  }

  return data;
}

async function apiPostFormData(
  path: string,
  body: FormData
) {
  const token = localStorage.getItem("token");

  const response = await fetch(API + path, {
    method: "POST",
    headers: {
      Accept: "application/json",
      ...(token
        ? { Authorization: `Bearer ${token}` }
        : {}),
    },
    body,
  });

  const text = await response.text();
  let data: any = {};

  try {
    data = text ? JSON.parse(text) : {};
  } catch {
    data = {};
  }

  if (!response.ok) {
    const detail =
      typeof data.detail === "string"
        ? data.detail
        : data.detail?.error ||
          `Request failed: ${response.status}`;
    throw new Error(detail);
  }

  return data;
}

/* =========================================================
   ROUTE HELPER
========================================================= */

function makePath(name: string) {
  return (
    "/" +
    name
      .toLowerCase()
      .replace(/ /g, "-")
      .replace(/&/g, "and")
  );
}

/* =========================================================
   COMMON UI
========================================================= */

function currency(value: number) {
  return `₹${Number(
    value || 0
  ).toLocaleString("en-IN", {
    maximumFractionDigits: 2,
  })}`;
}

const tableHeader: React.CSSProperties = {
  textAlign: "left",
  padding: "12px",
  borderBottom:
    "1px solid #dfe7f1",
  fontSize: "12px",
  textTransform: "uppercase",
  letterSpacing: "0.04em",
  opacity: 0.65,
};

const tableCell: React.CSSProperties = {
  padding: "14px 12px",
  borderBottom:
    "1px solid #edf1f6",
  fontSize: "14px",
};

const primaryButton: React.CSSProperties = {
  padding: "10px 16px",
  borderRadius: "8px",
  border: "1px solid #1769d1",
  background: "#1769d1",
  color: "#ffffff",
  cursor: "pointer",
  fontWeight: 600,
};

const secondaryButton: React.CSSProperties = {
  padding: "10px 16px",
  borderRadius: "8px",
  border: "1px solid #d7e1ed",
  background: "#ffffff",
  color: "#17324d",
  cursor: "pointer",
  fontWeight: 600,
};

/* =========================================================
   STATUS BADGE
========================================================= */

function StatusBadge({
  status,
}: {
  status?: string | null;
}) {
  const value =
    String(status || "OPEN")
      .toUpperCase();

  let background = "#eef3f8";
  let color = "#475569";

  if (value === "OPEN") {
    background = "#fff3e6";
    color = "#b45309";
  }

  if (value === "UNDER_REVIEW") {
    background = "#eaf2ff";
    color = "#1769d1";
  }

  if (value === "APPROVED") {
    background = "#e8f7ee";
    color = "#18794e";
  }

  if (value === "REJECTED") {
    background = "#feecec";
    color = "#b42318";
  }

  if (value === "ESCALATED") {
    background = "#fff0f0";
    color = "#c2410c";
  }

  if (value === "RESOLVED") {
    background = "#e8f7ee";
    color = "#166534";
  }

  return (
    <span
      style={{
        display: "inline-block",
        padding: "5px 10px",
        borderRadius: "20px",
        fontSize: "12px",
        fontWeight: 700,
        background,
        color,
      }}
    >
      {value.replace("_", " ")}
    </span>
  );
}

/* =========================================================
   LAYOUT
========================================================= */

function Layout({
  children,
}: {
  children: React.ReactNode;
}) {
  const navigate =
    useNavigate();

  const groups = {
    FINANCE: [
      "Transactions",
      "Reconciliation",
      "Review Queue",
    ],

    INTELLIGENCE: [
      "Risk Assessment",
      "Anomaly Detection",
      "Forecasting",
      "Scenario Simulator",
      "Finance Copilot",
    ],

    REPORTING: [
      "CFO Reports",
      "Audit Logs",
    ],

    SYSTEM: ["Settings"],
  };

  function logout() {
    localStorage.removeItem(
      "token"
    );

    localStorage.removeItem(
      "user"
    );

    navigate("/login");
  }

  return (
    <div className="app">
      <aside>
        <h2>
          Finance Controller
        </h2>

        <Link to="/">
          Overview
        </Link>

        {Object.entries(groups).map(
          ([group, items]) => (
            <section key={group}>
              <small>
                {group}
              </small>

              {items.map((item) => (
                <Link
                  key={item}
                  to={makePath(item)}
                >
                  {item}
                </Link>
              ))}
            </section>
          )
        )}

        <button
          onClick={logout}
        >
          Logout
        </button>
      </aside>

      <main>
        {children}
      </main>
    </div>
  );
}

/* =========================================================
   LOGIN
========================================================= */

function Login() {
  const navigate =
    useNavigate();

  const [email, setEmail] =
    useState(
      DEMO_EMAIL
    );

  const [password, setPassword] =
    useState(
      DEMO_PASSWORD
    );

  const [error, setError] =
    useState("");

  const [loading, setLoading] =
    useState(false);

  async function handleLogin() {
    setError("");

    if (!email.trim()) {
      setError(
        "Please enter your email."
      );

      return;
    }

    if (!password) {
      setError(
        "Please enter your password."
      );

      return;
    }

    setLoading(true);

    try {
      const response =
        await fetch(
          `${API}/auth/login`,
          {
            method: "POST",

            headers: {
              "Content-Type":
                "application/json",

              Accept:
                "application/json",
            },

            body: JSON.stringify({
              email:
                email.trim(),
              password,
            }),
          }
        );

      const text =
        await response.text();

      let data: any;

      try {
        data = JSON.parse(text);
      } catch {
        data = {};
      }

      if (response.ok) {
        if (
          !data.access_token
        ) {
          setError(
            "Login succeeded, but the server did not return an access token."
          );

          return;
        }

        localStorage.setItem(
          "token",
          data.access_token
        );

        if (data.user) {
          localStorage.setItem(
            "user",
            JSON.stringify(
              data.user
            )
          );
        }

        navigate("/", {
          replace: true,
        });

        return;
      }

      if (
        response.status ===
        422
      ) {
        if (
          Array.isArray(
            data.detail
          )
        ) {
          const messages =
            data.detail
              .map(
                (
                  item: any
                ) => {
                  const location =
                    Array.isArray(
                      item.loc
                    )
                      ? item.loc.join(
                          " → "
                        )
                      : "";

                  return `${location}: ${
                    item.msg ||
                    "Invalid value"
                  }`;
                }
              )
              .join("\n");

          setError(
            `Login validation error:\n${messages}`
          );
        } else {
          setError(
            data.detail ||
              "FastAPI rejected the login data."
          );
        }

        return;
      }

      if (
        response.status ===
        401
      ) {
        setError(
          "Invalid email or password."
        );

        return;
      }

      setError(
        data.detail ||
          `Login failed. Server returned ${response.status}.`
      );
    } catch (err) {
      console.error(
        "LOGIN CONNECTION ERROR:",
        err
      );

      setError(
        "Cannot connect to the FastAPI backend. Make sure the backend is running."
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="login">
      <div className="panel">

        <h1>
          AI Finance Controller
        </h1>

        <p>
          Secure financial
          intelligence
          workspace
        </p>

        <input
          type="email"
          value={email}
          placeholder="Email"
          autoComplete="email"
          onChange={(event) =>
            setEmail(
              event.target.value
            )
          }
        />

        <input
          type="password"
          value={password}
          placeholder="Password"
          autoComplete="current-password"
          onChange={(event) =>
            setPassword(
              event.target.value
            )
          }
          onKeyDown={(event) => {
            if (
              event.key ===
              "Enter"
            ) {
              handleLogin();
            }
          }}
        />

        <button
          type="button"
          onClick={
            handleLogin
          }
          disabled={loading}
        >
          {loading
            ? "Signing in..."
            : "Sign in"}
        </button>

        {error && (
          <div
            className="error"
            style={{
              whiteSpace:
                "pre-line",
              marginTop:
                "12px",
            }}
          >
            {error}
          </div>
        )}

      </div>
    </div>
  );
}

/* =========================================================
   DASHBOARD
========================================================= */

function LegacyDashboardPage() {
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    const loadDashboard = () => apiGet("/dashboard")
      .then(setData)
      .catch((err) => {
        console.error(err);
        setError("Unable to load dashboard data.");
      });
    loadDashboard();
    window.addEventListener("reconciliation:completed", loadDashboard);
    return () => window.removeEventListener("reconciliation:completed", loadDashboard);
  }, []);

  if (error) {
    return <div className="state">{error}</div>;
  }

  if (!data) {
    return <div className="state">Loading dashboard…</div>;
  }

  const revenue = Number(data.revenue || 0);
  const expenses = Number(data.expenses || 0);
  const netProfit = Number(data.net_profit || 0);
  const cashBalance = Number(data.cash_balance || 0);
  const reconciliation = Number(data.reconciliation_rate || 0);
  const highRisk = Number(data.high_risk || 0);
  const refunds = Number(data.refunds || 0);
  const fees = Number(data.fees || 0);
  const latestReconciliation = data.reconciliation;

  const formatMoney = (value: number) =>
    `₹${value.toLocaleString("en-IN", {
      maximumFractionDigits: 2,
    })}`;

  const profitMargin =
    revenue > 0 ? (netProfit / revenue) * 100 : 0;

  return (
    <>
      {/* HEADER */}
      <header>
        <div>
          <h1>Executive Overview</h1>
          <p
            style={{
              margin: "6px 0 0",
              color: "#64748b",
              fontSize: "14px",
            }}
          >
            AI-powered financial control center
          </p>
          {latestReconciliation?.run_id ? (
            <p style={{ margin: "6px 0 0", color: "#64748b", fontSize: "12px" }}>
              Latest reconciliation: {latestReconciliation.matched}/{latestReconciliation.total} matched · {Number(latestReconciliation.match_rate).toFixed(1)}% · {latestReconciliation.exceptions} exceptions · variance {currency(latestReconciliation.variance)}
            </p>
          ) : null}
        </div>

        <span
          style={{
            padding: "8px 12px",
            borderRadius: "20px",
            background: "#eff6ff",
            color: "#2563eb",
            fontSize: "13px",
            fontWeight: 600,
          }}
        >
          ● Live database metrics
        </span>
      </header>

      {/* KPI CARDS */}
      <div className="grid">

        <div className="card">
          <small>Total Revenue</small>
          <strong>{formatMoney(revenue)}</strong>

          <span
            style={{
              color: "#16a34a",
              fontSize: "12px",
              marginTop: "6px",
              display: "block",
            }}
          >
            Income generated
          </span>
        </div>

        <div className="card">
          <small>Total Expenses</small>
          <strong>{formatMoney(expenses)}</strong>

          <span
            style={{
              color: "#64748b",
              fontSize: "12px",
              marginTop: "6px",
              display: "block",
            }}
          >
            Operating outflow
          </span>
        </div>

        <div className="card">
          <small>Net Profit</small>
          <strong>{formatMoney(netProfit)}</strong>

          <span
            style={{
              color:
                netProfit >= 0
                  ? "#16a34a"
                  : "#dc2626",
              fontSize: "12px",
              marginTop: "6px",
              display: "block",
            }}
          >
            {profitMargin.toFixed(1)}% profit margin
          </span>
        </div>

        <div className="card">
          <small>Cash Balance</small>
          <strong>{formatMoney(cashBalance)}</strong>

          <span
            style={{
              color: "#2563eb",
              fontSize: "12px",
              marginTop: "6px",
              display: "block",
            }}
          >
            Current liquidity
          </span>
        </div>

        <div className="card">
          <small>Reconciliation Rate</small>
          <strong>
            {reconciliation.toFixed(1)}%
          </strong>

          <span
            style={{
              color:
                reconciliation >= 95
                  ? "#16a34a"
                  : "#dc2626",
              fontSize: "12px",
              marginTop: "6px",
              display: "block",
            }}
          >
            {reconciliation >= 95
              ? "Healthy control"
              : "Requires attention"}
          </span>
        </div>

        <div className="card">
          <small>High Risk Items</small>
          <strong>{highRisk}</strong>

          <span
            style={{
              color:
                highRisk > 0
                  ? "#dc2626"
                  : "#16a34a",
              fontSize: "12px",
              marginTop: "6px",
              display: "block",
            }}
          >
            {highRisk > 0
              ? "Requires review"
              : "No critical items"}
          </span>
        </div>

      </div>

      {/* FINANCIAL CONTROL SUMMARY */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns:
            "repeat(auto-fit, minmax(280px, 1fr))",
          gap: "16px",
          marginTop: "20px",
        }}
      >

        {/* PROFITABILITY */}
        <div className="panel">
          <h2>Profitability</h2>

          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              padding: "12px 0",
              borderBottom: "1px solid #e5e7eb",
            }}
          >
            <span>Revenue</span>
            <strong>{formatMoney(revenue)}</strong>
          </div>

          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              padding: "12px 0",
              borderBottom: "1px solid #e5e7eb",
            }}
          >
            <span>Expenses</span>
            <strong>{formatMoney(expenses)}</strong>
          </div>

          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              padding: "12px 0",
            }}
          >
            <span>Net Profit</span>
            <strong>{formatMoney(netProfit)}</strong>
          </div>

          <div
            style={{
              marginTop: "8px",
              padding: "10px",
              background: "#f8fafc",
              borderRadius: "8px",
              fontSize: "13px",
            }}
          >
            Profit margin:{" "}
            <strong>{profitMargin.toFixed(1)}%</strong>
          </div>
        </div>

        {/* CASH & LIQUIDITY */}
        <div className="panel">
          <h2>Cash & Liquidity</h2>

          <div
            style={{
              fontSize: "28px",
              fontWeight: 700,
              margin: "18px 0",
            }}
          >
            {formatMoney(cashBalance)}
          </div>

          <p
            style={{
              color: "#64748b",
              fontSize: "13px",
              marginBottom: "16px",
            }}
          >
            Available cash balance based on current
            transaction data.
          </p>

          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              padding: "10px 0",
            }}
          >
            <span>Refunds</span>
            <strong>{formatMoney(refunds)}</strong>
          </div>

          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              padding: "10px 0",
            }}
          >
            <span>Fees</span>
            <strong>{formatMoney(fees)}</strong>
          </div>
        </div>

        {/* CONTROL HEALTH */}
        <div className="panel">
          <h2>Control Health</h2>

          <div style={{ marginTop: "18px" }}>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                marginBottom: "8px",
              }}
            >
              <span>Reconciliation</span>
              <strong>
                {reconciliation.toFixed(1)}%
              </strong>
            </div>

            <div
              style={{
                height: "8px",
                background: "#e5e7eb",
                borderRadius: "10px",
                overflow: "hidden",
              }}
            >
              <div
                style={{
                  width: `${Math.min(
                    reconciliation,
                    100
                  )}%`,
                  height: "100%",
                  background: "#2563eb",
                  borderRadius: "10px",
                }}
              />
            </div>
          </div>

          <div
            style={{
              marginTop: "22px",
              padding: "12px",
              borderRadius: "8px",
              background:
                reconciliation >= 95
                  ? "#f0fdf4"
                  : "#fef2f2",
              color:
                reconciliation >= 95
                  ? "#166534"
                  : "#991b1b",
              fontSize: "13px",
            }}
          >
            {reconciliation >= 95
              ? "✓ Reconciliation controls are operating within the target threshold."
              : "⚠ Reconciliation performance requires management attention."}
          </div>
        </div>

      </div>
            {/* REVENUE VS EXPENSES */}
<div
  className="panel"
  style={{
    marginTop: "20px",
  }}
>
  <div
    style={{
      display: "flex",
      justifyContent: "space-between",
      alignItems: "center",
      marginBottom: "20px",
    }}
  >
    <div>
      <h2>Revenue vs Expenses</h2>

      <p
        style={{
          color: "#64748b",
          fontSize: "13px",
          marginTop: "5px",
        }}
      >
        Current financial performance
      </p>
    </div>

    <span
      style={{
        padding: "6px 10px",
        borderRadius: "6px",
        background: "#f8fafc",
        color: "#475569",
        fontSize: "12px",
        fontWeight: 600,
      }}
    >
      Current Period
    </span>
  </div>

  {/* Revenue */}
  <div style={{ marginBottom: "22px" }}>
    <div
      style={{
        display: "flex",
        justifyContent: "space-between",
        marginBottom: "8px",
      }}
    >
      <span
        style={{
          fontSize: "14px",
          fontWeight: 600,
        }}
      >
        Revenue
      </span>

      <strong>
        {formatMoney(revenue)}
      </strong>
    </div>

    <div
      style={{
        height: "18px",
        background: "#e5e7eb",
        borderRadius: "6px",
        overflow: "hidden",
      }}
    >
      <div
        style={{
          width: "100%",
          height: "100%",
          background: "#2563eb",
          borderRadius: "6px",
        }}
      />
    </div>
  </div>

  {/* Expenses */}
  <div>
    <div
      style={{
        display: "flex",
        justifyContent: "space-between",
        marginBottom: "8px",
      }}
    >
      <span
        style={{
          fontSize: "14px",
          fontWeight: 600,
        }}
      >
        Expenses
      </span>

      <strong>
        {formatMoney(expenses)}
      </strong>
    </div>

    <div
      style={{
        height: "18px",
        background: "#e5e7eb",
        borderRadius: "6px",
        overflow: "hidden",
      }}
    >
      <div
        style={{
          width:
            revenue > 0
              ? `${Math.min(
                  (expenses / revenue) * 100,
                  100
                )}%`
              : "0%",
          height: "100%",
          background: "#64748b",
          borderRadius: "6px",
        }}
      />
    </div>
  </div>

  {/* Profit Summary */}
  <div
    style={{
      display: "flex",
      justifyContent: "space-between",
      marginTop: "24px",
      paddingTop: "16px",
      borderTop: "1px solid #e5e7eb",
    }}
  >
    <span>Net Profit</span>

    <strong>
      {formatMoney(netProfit)}
    </strong>
  </div>
</div>

{/* RISK & EXCEPTION SUMMARY */}
<div
  style={{
    display: "grid",
    gridTemplateColumns:
      "repeat(auto-fit, minmax(240px, 1fr))",
    gap: "16px",
    marginTop: "20px",
  }}
>
  {/* HIGH RISK */}
  <div
    className="panel"
    style={{
      borderLeft: "4px solid #dc2626",
    }}
  >
    <small>HIGH RISK</small>

    <div
      style={{
        fontSize: "28px",
        fontWeight: 700,
        marginTop: "8px",
      }}
    >
      {highRisk}
    </div>

    <p
      style={{
        color: "#64748b",
        fontSize: "13px",
        marginTop: "6px",
      }}
    >
      Transactions requiring risk review
    </p>
  </div>

  {/* RECONCILIATION */}
  <div
    className="panel"
    style={{
      borderLeft: "4px solid #2563eb",
    }}
  >
    <small>RECONCILIATION</small>

    <div
      style={{
        fontSize: "28px",
        fontWeight: 700,
        marginTop: "8px",
      }}
    >
      {reconciliation.toFixed(1)}%
    </div>

    <p
      style={{
        color: "#64748b",
        fontSize: "13px",
        marginTop: "6px",
      }}
    >
      Transactions successfully reconciled
    </p>
  </div>

  {/* CONTROL STATUS */}
  <div
    className="panel"
    style={{
      borderLeft:
        reconciliation >= 95
          ? "4px solid #16a34a"
          : "4px solid #dc2626",
    }}
  >
    <small>CONTROL STATUS</small>

    <div
      style={{
        fontSize: "20px",
        fontWeight: 700,
        marginTop: "12px",
        color:
          reconciliation >= 95
            ? "#16a34a"
            : "#dc2626",
      }}
    >
      {reconciliation >= 95
        ? "Healthy"
        : "Attention Required"}
    </div>

    <p
      style={{
        color: "#64748b",
        fontSize: "13px",
        marginTop: "6px",
      }}
    >
      Based on reconciliation performance
    </p>
  </div>
</div>

{/* CONTROLLER ACTION */}
<div
  className="panel"
  style={{
    marginTop: "16px",
    background: "#f8fafc",
  }}
>
  <div
    style={{
      display: "flex",
      alignItems: "center",
      gap: "12px",
    }}
  >
    <strong>Controller Priority</strong>

    <span
      style={{
        padding: "5px 9px",
        borderRadius: "5px",
        background:
          highRisk > 0
            ? "#fef2f2"
            : "#f0fdf4",
        color:
          highRisk > 0
            ? "#b91c1c"
            : "#166534",
        fontSize: "11px",
        fontWeight: 700,
      }}
    >
      {highRisk > 0
        ? "ACTION REQUIRED"
        : "MONITOR"}
    </span>
  </div>

  <p
    style={{
      marginTop: "10px",
      color: "#475569",
      fontSize: "13px",
      lineHeight: 1.6,
    }}
  >
    {highRisk > 0
      ? `Review ${highRisk} high-risk transaction${
          highRisk === 1 ? "" : "s"
        } and investigate reconciliation exceptions before finalizing financial reports.`
      : "No high-risk transactions currently require immediate intervention. Continue monitoring financial controls."}
  </p>
</div>


{/* CASH & LIQUIDITY ANALYSIS */}
<div
  className="panel"
  style={{
    marginTop: "20px",
  }}
>
  <div
    style={{
      display: "flex",
      justifyContent: "space-between",
      alignItems: "center",
      marginBottom: "20px",
    }}
  >
    <div>
      <h2>Cash & Liquidity</h2>

      <p
        style={{
          color: "#64748b",
          fontSize: "13px",
          marginTop: "5px",
        }}
      >
        Current liquidity position derived from
        financial transaction data.
      </p>
    </div>

    <span
      style={{
        padding: "6px 10px",
        borderRadius: "6px",
        background: "#f8fafc",
        color: "#475569",
        fontSize: "12px",
        fontWeight: 600,
      }}
    >
      LIQUIDITY
    </span>
  </div>

  {/* CASH BALANCE */}
  <div
    style={{
      padding: "18px",
      borderRadius: "10px",
      background: "#f8fafc",
      marginBottom: "20px",
    }}
  >
    <small>Current Cash Balance</small>

    <div
      style={{
        fontSize: "30px",
        fontWeight: 700,
        marginTop: "7px",
      }}
    >
      {formatMoney(cashBalance)}
    </div>

    <p
      style={{
        color: "#64748b",
        fontSize: "12px",
        marginTop: "6px",
      }}
    >
      Based on available transaction-level
      financial data.
    </p>
  </div>

  {/* INFLOW / OUTFLOW */}
  <div
    style={{
      display: "grid",
      gridTemplateColumns:
        "repeat(auto-fit, minmax(220px, 1fr))",
      gap: "16px",
    }}
  >

    {/* INFLOW */}
    <div>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          marginBottom: "8px",
        }}
      >
        <span
          style={{
            fontSize: "13px",
            fontWeight: 600,
          }}
        >
          Revenue Inflow
        </span>

        <strong>
          {formatMoney(revenue)}
        </strong>
      </div>

      <div
        style={{
          height: "12px",
          background: "#e5e7eb",
          borderRadius: "6px",
          overflow: "hidden",
        }}
      >
        <div
          style={{
            width: "100%",
            height: "100%",
            background: "#2563eb",
            borderRadius: "6px",
          }}
        />
      </div>
    </div>

    {/* OUTFLOW */}
    <div>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          marginBottom: "8px",
        }}
      >
        <span
          style={{
            fontSize: "13px",
            fontWeight: 600,
          }}
        >
          Expense Outflow
        </span>

        <strong>
          {formatMoney(expenses)}
        </strong>
      </div>

      <div
        style={{
          height: "12px",
          background: "#e5e7eb",
          borderRadius: "6px",
          overflow: "hidden",
        }}
      >
        <div
          style={{
            width:
              revenue > 0
                ? `${Math.min(
                    (expenses / revenue) * 100,
                    100
                  )}%`
                : "0%",
            height: "100%",
            background: "#64748b",
            borderRadius: "6px",
          }}
        />
      </div>
    </div>

    {/* REFUNDS */}
    <div>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          marginBottom: "8px",
        }}
      >
        <span
          style={{
            fontSize: "13px",
            fontWeight: 600,
          }}
        >
          Refund Impact
        </span>

        <strong>
          {formatMoney(refunds)}
        </strong>
      </div>

      <div
        style={{
          height: "12px",
          background: "#e5e7eb",
          borderRadius: "6px",
          overflow: "hidden",
        }}
      >
        <div
          style={{
            width:
              revenue > 0
                ? `${Math.min(
                    (refunds / revenue) * 100,
                    100
                  )}%`
                : "0%",
            height: "100%",
            background: "#94a3b8",
            borderRadius: "6px",
          }}
        />
      </div>
    </div>
  </div>

  {/* LIQUIDITY SUMMARY */}
  <div
    style={{
      display: "grid",
      gridTemplateColumns:
        "repeat(auto-fit, minmax(200px, 1fr))",
      gap: "12px",
      marginTop: "22px",
      paddingTop: "18px",
      borderTop: "1px solid #e5e7eb",
    }}
  >
    <div>
      <small>Net Cash Flow</small>

      <div
        style={{
          fontSize: "18px",
          fontWeight: 700,
          marginTop: "6px",
        }}
      >
        {formatMoney(
          revenue -
            expenses -
            refunds -
            fees
        )}
      </div>
    </div>

    <div>
      <small>Fees</small>

      <div
        style={{
          fontSize: "18px",
          fontWeight: 700,
          marginTop: "6px",
        }}
      >
        {formatMoney(fees)}
      </div>
    </div>

    <div>
      <small>Liquidity Status</small>

      <div
        style={{
          fontSize: "18px",
          fontWeight: 700,
          marginTop: "6px",
          color:
            cashBalance >= 0
              ? "#16a34a"
              : "#dc2626",
        }}
      >
        {cashBalance >= 0
          ? "Positive"
          : "At Risk"}
      </div>
    </div>
  </div>

  {/* DATA LIMITATION */}
  <div
    style={{
      marginTop: "18px",
      padding: "10px 12px",
      background: "#f8fafc",
      borderRadius: "6px",
      fontSize: "11px",
      color: "#64748b",
    }}
  >
    Data note: liquidity indicators are calculated
    from currently available transaction data.
  </div>
</div>



{/* AI DECISION SUPPORT */}
<div
  className="panel"
  style={{
    marginTop: "20px",
    border: "1px solid #dbeafe",
  }}
>
  <div
    style={{
      display: "flex",
      justifyContent: "space-between",
      alignItems: "flex-start",
      gap: "16px",
    }}
  >
    <div>
      <h2>AI Decision Support</h2>

      <p
        style={{
          color: "#64748b",
          fontSize: "13px",
          marginTop: "5px",
        }}
      >
        AI-generated interpretation of current
        financial control signals.
      </p>
    </div>

    <span
      style={{
        padding: "6px 10px",
        borderRadius: "6px",
        background: "#eff6ff",
        color: "#2563eb",
        fontSize: "12px",
        fontWeight: 700,
      }}
    >
      AI CONTROL ENGINE
    </span>
  </div>

  <div
    style={{
      display: "grid",
      gridTemplateColumns:
        "repeat(auto-fit, minmax(220px, 1fr))",
      gap: "14px",
      marginTop: "20px",
    }}
  >

    {/* FINANCIAL HEALTH */}
    <div
      style={{
        padding: "16px",
        borderRadius: "8px",
        background: "#f8fafc",
      }}
    >
      <small>Financial Health</small>

      <div
        style={{
          fontSize: "20px",
          fontWeight: 700,
          marginTop: "8px",
        }}
      >
        {netProfit >= 0
          ? "Positive"
          : "At Risk"}
      </div>

      <p
        style={{
          color: "#64748b",
          fontSize: "12px",
          marginTop: "6px",
        }}
      >
        Based on revenue, expenses and
        current profitability.
      </p>
    </div>

    {/* CONTROL HEALTH */}
    <div
      style={{
        padding: "16px",
        borderRadius: "8px",
        background: "#f8fafc",
      }}
    >
      <small>Control Health</small>

      <div
        style={{
          fontSize: "20px",
          fontWeight: 700,
          marginTop: "8px",
        }}
      >
        {reconciliation >= 95
          ? "Strong"
          : "Needs Review"}
      </div>

      <p
        style={{
          color: "#64748b",
          fontSize: "12px",
          marginTop: "6px",
        }}
      >
        Reconciliation currently at{" "}
        {reconciliation.toFixed(1)}%.
      </p>
    </div>

    {/* RISK PRIORITY */}
    <div
      style={{
        padding: "16px",
        borderRadius: "8px",
        background: "#f8fafc",
      }}
    >
      <small>Risk Priority</small>

      <div
        style={{
          fontSize: "20px",
          fontWeight: 700,
          marginTop: "8px",
          color:
            highRisk > 0
              ? "#dc2626"
              : "#16a34a",
        }}
      >
        {highRisk > 0
          ? "High"
          : "Normal"}
      </div>

      <p
        style={{
          color: "#64748b",
          fontSize: "12px",
          marginTop: "6px",
        }}
      >
        {highRisk} high-risk transaction
        {highRisk === 1 ? "" : "s"} detected.
      </p>
    </div>

    {/* AI ACTION */}
    <div
      style={{
        padding: "16px",
        borderRadius: "8px",
        background: "#f8fafc",
      }}
    >
      <small>Recommended Action</small>

      <div
        style={{
          fontSize: "16px",
          fontWeight: 700,
          marginTop: "8px",
        }}
      >
        {highRisk > 0
          ? "Review Risk Queue"
          : reconciliation < 95
          ? "Investigate Exceptions"
          : "Continue Monitoring"}
      </div>

      <p
        style={{
          color: "#64748b",
          fontSize: "12px",
          marginTop: "6px",
        }}
      >
        Suggested next step based on
        current control signals.
      </p>
    </div>

  </div>

  {/* AI EXPLANATION */}
  <div
    style={{
      marginTop: "18px",
      padding: "14px",
      background: "#eff6ff",
      borderRadius: "8px",
      fontSize: "13px",
      lineHeight: 1.6,
      color: "#1e3a8a",
    }}
  >
    <strong>AI reasoning:</strong>{" "}

    {highRisk > 0
      ? `High-risk transactions are currently the primary control priority. The finance controller should review these items and validate supporting evidence before approval.`
      : reconciliation < 95
      ? `Reconciliation performance is below the preferred control threshold. Exception investigation should be prioritized.`
      : `Current financial and reconciliation indicators are within the preferred control range. Continue monitoring for emerging anomalies.`}
  </div>
</div>

{/* CONTROLLER ACTION CENTER */}
<div
  className="panel"
  style={{
    marginTop: "20px",
  }}
>
  <div
    style={{
      display: "flex",
      justifyContent: "space-between",
      alignItems: "center",
      marginBottom: "18px",
    }}
  >
    <div>
      <h2>Controller Action Center</h2>

      <p
        style={{
          color: "#64748b",
          fontSize: "13px",
          marginTop: "5px",
        }}
      >
        Prioritized actions based on current
        financial control signals.
      </p>
    </div>

    <span
      style={{
        padding: "6px 10px",
        borderRadius: "6px",
        background: "#f8fafc",
        color: "#475569",
        fontSize: "12px",
        fontWeight: 600,
      }}
    >
      PRIORITY QUEUE
    </span>
  </div>

  {/* ACTION 1 */}
  <div
    style={{
      display: "flex",
      justifyContent: "space-between",
      alignItems: "center",
      gap: "16px",
      padding: "15px",
      borderBottom: "1px solid #e5e7eb",
    }}
  >
    <div>
      <strong>Review high-risk transactions</strong>

      <p
        style={{
          margin: "5px 0 0",
          color: "#64748b",
          fontSize: "12px",
        }}
      >
        {highRisk} high-risk transaction
        {highRisk === 1 ? "" : "s"} currently
        require attention.
      </p>
    </div>

    <span
      style={{
        padding: "5px 9px",
        borderRadius: "5px",
        background:
          highRisk > 0 ? "#fef2f2" : "#f0fdf4",
        color:
          highRisk > 0 ? "#b91c1c" : "#166534",
        fontSize: "11px",
        fontWeight: 700,
        whiteSpace: "nowrap",
      }}
    >
      {highRisk > 0 ? "HIGH" : "CLEAR"}
    </span>
  </div>

  {/* ACTION 2 */}
  <div
    style={{
      display: "flex",
      justifyContent: "space-between",
      alignItems: "center",
      gap: "16px",
      padding: "15px",
      borderBottom: "1px solid #e5e7eb",
    }}
  >
    <div>
      <strong>Investigate reconciliation</strong>

      <p
        style={{
          margin: "5px 0 0",
          color: "#64748b",
          fontSize: "12px",
        }}
      >
        Current reconciliation rate is{" "}
        {reconciliation.toFixed(1)}%.
      </p>
    </div>

    <span
      style={{
        padding: "5px 9px",
        borderRadius: "5px",
        background:
          reconciliation >= 95
            ? "#f0fdf4"
            : "#fff7ed",
        color:
          reconciliation >= 95
            ? "#166534"
            : "#c2410c",
        fontSize: "11px",
        fontWeight: 700,
        whiteSpace: "nowrap",
      }}
    >
      {reconciliation >= 95
        ? "HEALTHY"
        : "REVIEW"}
    </span>
  </div>

  {/* ACTION 3 */}
  <div
    style={{
      display: "flex",
      justifyContent: "space-between",
      alignItems: "center",
      gap: "16px",
      padding: "15px",
      borderBottom: "1px solid #e5e7eb",
    }}
  >
    <div>
      <strong>Monitor liquidity</strong>

      <p
        style={{
          margin: "5px 0 0",
          color: "#64748b",
          fontSize: "12px",
        }}
      >
        Current cash balance:{" "}
        {formatMoney(cashBalance)}.
      </p>
    </div>

    <span
      style={{
        padding: "5px 9px",
        borderRadius: "5px",
        background:
          cashBalance >= 0
            ? "#f0fdf4"
            : "#fef2f2",
        color:
          cashBalance >= 0
            ? "#166534"
            : "#b91c1c",
        fontSize: "11px",
        fontWeight: 700,
        whiteSpace: "nowrap",
      }}
    >
      {cashBalance >= 0
        ? "STABLE"
        : "AT RISK"}
    </span>
  </div>

  {/* ACTION 4 */}
  <div
    style={{
      display: "flex",
      justifyContent: "space-between",
      alignItems: "center",
      gap: "16px",
      padding: "15px",
    }}
  >
    <div>
      <strong>Validate financial reports</strong>

      <p
        style={{
          margin: "5px 0 0",
          color: "#64748b",
          fontSize: "12px",
        }}
      >
        Ensure high-risk and reconciliation
        exceptions are reviewed before reporting.
      </p>
    </div>

    <span
      style={{
        padding: "5px 9px",
        borderRadius: "5px",
        background: "#eff6ff",
        color: "#1d4ed8",
        fontSize: "11px",
        fontWeight: 700,
        whiteSpace: "nowrap",
      }}
    >
      CONTROL
    </span>
  </div>
</div>

{/* DATA QUALITY & TRUST */}
<div
  className="panel"
  style={{
    marginTop: "20px",
    background: "#f8fafc",
  }}
>
  <div
    style={{
      display: "flex",
      justifyContent: "space-between",
      alignItems: "center",
      marginBottom: "14px",
    }}
  >
    <div>
      <h2>Data Quality & Trust</h2>

      <p
        style={{
          color: "#64748b",
          fontSize: "13px",
          marginTop: "5px",
        }}
      >
        Transparency indicators for finance-control decisions.
      </p>
    </div>

    <span
      style={{
        padding: "6px 10px",
        borderRadius: "6px",
        background: "#ffffff",
        color: "#475569",
        fontSize: "11px",
        fontWeight: 700,
        border: "1px solid #e2e8f0",
      }}
    >
      TRUST LAYER
    </span>
  </div>

  <div
    style={{
      display: "grid",
      gridTemplateColumns:
        "repeat(auto-fit, minmax(200px, 1fr))",
      gap: "12px",
    }}
  >
    <div
      style={{
        padding: "14px",
        background: "#ffffff",
        borderRadius: "8px",
        border: "1px solid #e2e8f0",
      }}
    >
      <small>Transaction Data</small>

      <div
        style={{
          fontWeight: 700,
          fontSize: "17px",
          marginTop: "7px",
        }}
      >
        Available
      </div>

      <span
        style={{
          fontSize: "11px",
          color: "#16a34a",
        }}
      >
        ✓ Source connected
      </span>
    </div>

    <div
      style={{
        padding: "14px",
        background: "#ffffff",
        borderRadius: "8px",
        border: "1px solid #e2e8f0",
      }}
    >
      <small>Reconciliation Data</small>

      <div
        style={{
          fontWeight: 700,
          fontSize: "17px",
          marginTop: "7px",
        }}
      >
        {reconciliation.toFixed(1)}%
      </div>

      <span
        style={{
          fontSize: "11px",
          color:
            reconciliation >= 95
              ? "#16a34a"
              : "#dc2626",
        }}
      >
        {reconciliation >= 95
          ? "✓ Within control threshold"
          : "⚠ Exceptions detected"}
      </span>
    </div>

    <div
      style={{
        padding: "14px",
        background: "#ffffff",
        borderRadius: "8px",
        border: "1px solid #e2e8f0",
      }}
    >
      <small>Risk Signals</small>

      <div
        style={{
          fontWeight: 700,
          fontSize: "17px",
          marginTop: "7px",
        }}
      >
        {highRisk} detected
      </div>

      <span
        style={{
          fontSize: "11px",
          color:
            highRisk > 0
              ? "#dc2626"
              : "#16a34a",
        }}
      >
        {highRisk > 0
          ? "⚠ Human review recommended"
          : "✓ No immediate escalation"}
      </span>
    </div>

    <div
      style={{
        padding: "14px",
        background: "#ffffff",
        borderRadius: "8px",
        border: "1px solid #e2e8f0",
      }}
    >
      <small>Decision Mode</small>

      <div
        style={{
          fontWeight: 700,
          fontSize: "17px",
          marginTop: "7px",
        }}
      >
        AI + Human
      </div>

      <span
        style={{
          fontSize: "11px",
          color: "#2563eb",
        }}
      >
        Controller approval retained
      </span>
    </div>
  </div>

  <div
    style={{
      marginTop: "14px",
      padding: "11px 13px",
      borderRadius: "7px",
      background: "#ffffff",
      border: "1px solid #e2e8f0",
      color: "#64748b",
      fontSize: "11px",
      lineHeight: 1.5,
    }}
  >
    <strong>Transparency:</strong>{" "}
    Dashboard insights are derived from available transaction,
    reconciliation, risk and financial metrics. AI suggestions
    support controller decisions and do not replace human approval.
  </div>
</div>





      {/* AI INSIGHTS */}
      <div
        className="panel"
        style={{
          marginTop: "20px",
        }}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <div>
            <h2>AI Financial Insights</h2>

            <p
              style={{
                color: "#64748b",
                fontSize: "13px",
                marginTop: "5px",
              }}
            >
              Automated observations grounded in
              current financial data.
            </p>
          </div>

          <span
            style={{
              padding: "6px 10px",
              borderRadius: "6px",
              background: "#eff6ff",
              color: "#2563eb",
              fontSize: "12px",
              fontWeight: 600,
            }}
          >
            AI
          </span>
        </div>

        <div
          style={{
            display: "grid",
            gridTemplateColumns:
              "repeat(auto-fit, minmax(220px, 1fr))",
            gap: "12px",
            marginTop: "18px",
          }}
        >

          <div
            style={{
              padding: "14px",
              background: "#f8fafc",
              borderRadius: "8px",
            }}
          >
            <strong>Financial Performance</strong>
            <p
              style={{
                fontSize: "13px",
                color: "#64748b",
                marginTop: "7px",
              }}
            >
              Current net profit is{" "}
              {formatMoney(netProfit)} with a{" "}
              {profitMargin.toFixed(1)}% margin.
            </p>
          </div>

          <div
            style={{
              padding: "14px",
              background: "#f8fafc",
              borderRadius: "8px",
            }}
          >
            <strong>Control Monitoring</strong>
            <p
              style={{
                fontSize: "13px",
                color: "#64748b",
                marginTop: "7px",
              }}
            >
              {reconciliation.toFixed(1)}% of
              transactions are currently reconciled.
            </p>
          </div>

          <div
            style={{
              padding: "14px",
              background: "#f8fafc",
              borderRadius: "8px",
            }}
          >
            <strong>Risk Monitoring</strong>
            <p
              style={{
                fontSize: "13px",
                color: "#64748b",
                marginTop: "7px",
              }}
            >
              {highRisk} high-risk transaction
              {highRisk === 1 ? "" : "s"} currently
              require monitoring.
            </p>
          </div>

        </div>

        <div
          style={{
            marginTop: "16px",
            padding: "12px 14px",
            borderLeft: "3px solid #2563eb",
            background: "#f8fafc",
            fontSize: "13px",
          }}
        >
          <strong>Priority:</strong>{" "}
          Review high-risk transactions and
          investigate reconciliation exceptions
          before finalizing financial reports.
        </div>
      </div>
    </>
  );
}


/* =========================================================
   RECONCILIATION
========================================================= */

function Reconciliation() {
  const [data, setData] =
    useState<any>(null);

  const [loading, setLoading] =
    useState(true);

  const [error, setError] =
    useState("");

  const [filter, setFilter] =
    useState("ALL");

  const [selected, setSelected] =
    useState<any>(null);

  const [reviewNote, setReviewNote] =
    useState("");

  const [actionLoading, setActionLoading] =
    useState(false);

  const [actionError, setActionError] =
    useState("");

  const [successMessage, setSuccessMessage] =
    useState("");

  const [bankFile, setBankFile] =
    useState<File | null>(null);

  const [ledgerFile, setLedgerFile] =
    useState<File | null>(null);

  const [settlementFile, setSettlementFile] =
    useState<File | null>(null);

  const [multiRun, setMultiRun] =
    useState<any>(null);

  const [multiLoading, setMultiLoading] =
    useState(false);

  const [multiError, setMultiError] =
    useState("");

  const [singleFile, setSingleFile] =
    useState<File | null>(null);

  const [singleRun, setSingleRun] =
    useState<any>(null);

  const [singleLoading, setSingleLoading] =
    useState(false);

  const [singleError, setSingleError] =
    useState("");

  const [riskMap, setRiskMap] =
    useState<Record<string, any>>({});

  async function loadData() {
    setLoading(true);

    try {
      const result =
        await apiGet(
          "/reconciliation"
        );

      setData(result);

      const latestRunId = result?.run_id;
      if (latestRunId) {
        try {
          const riskRows = await apiGet(
            `/risk?run_id=${encodeURIComponent(String(latestRunId))}`
          );
          const nextMap: Record<string, any> = {};
          (Array.isArray(riskRows) ? riskRows : []).forEach(
            (row: any) => {
              if (row && row.transaction_id) {
                nextMap[row.transaction_id] = row;
              }
            }
          );
          setRiskMap(nextMap);
        } catch {
          // Risk lookup is optional for the priority callout.
        }
      }

      setError("");
    } catch (err) {
      console.error(
        "RECONCILIATION ERROR:",
        err
      );

      setError(
        "Unable to load reconciliation data."
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
  }, []);

  async function runMultiFileReconciliation() {
    if (!bankFile || !ledgerFile) {
      setMultiError("Bank CSV and Ledger CSV are required.");
      return;
    }

    setMultiLoading(true);
    setMultiError("");

    try {
      const formData = new FormData();
      formData.append("bank_file", bankFile);
      formData.append("ledger_file", ledgerFile);
      if (settlementFile) {
        formData.append("settlement_file", settlementFile);
      }

      const result = await apiPostFormData(
        "/reconciliation/multi-file",
        formData
      );
      setMultiRun(result);
      await loadData();
      window.dispatchEvent(new Event("reconciliation:completed"));
    } catch (err: any) {
      setMultiError(
        err.message ||
          "Unable to run multi-source reconciliation."
      );
    } finally {
      setMultiLoading(false);
    }
  }

  async function runSingleFileReconciliation() {
    if (!singleFile) {
      setSingleError("Choose a reconciliation CSV first.");
      return;
    }

    setSingleLoading(true);
    setSingleError("");
    try {
      const formData = new FormData();
      formData.append("file", singleFile);
      const result = await apiPostFormData(
        "/reconciliation/single-file",
        formData
      );
      setSingleRun(result);
      await loadData();
      window.dispatchEvent(new Event("reconciliation:completed"));
    } catch (err: any) {
      setSingleError(
        err.message ||
          "Unable to run single-file reconciliation."
      );
    } finally {
      setSingleLoading(false);
    }
  }

  /* =======================================================
     UPDATE REVIEW
  ======================================================= */

  async function updateReview(
    status: string
  ) {
    if (
      !selected?.review_item_id
    ) {
      setActionError(
        "This exception does not have a review item."
      );

      return;
    }

    setActionLoading(true);
    setActionError("");
    setSuccessMessage("");

    try {
      await apiPatch(
        `/review/${selected.review_item_id}`,
        {
          status,
          note:
            reviewNote.trim() ||
            null,
        }
      );

      const newStatus =
        status;

      const newNote =
        reviewNote.trim() ||
        null;

      setSelected(
        (previous: any) =>
          previous
            ? {
                ...previous,
                review_status:
                  newStatus,
                review_note:
                  newNote,
              }
            : previous
      );

      setSuccessMessage(
        `Review successfully updated to ${status.replace(
          "_",
          " "
        )}.`
      );

      await loadData();

    } catch (err: any) {
      console.error(err);

      setActionError(
        err.message ||
          "Unable to update review."
      );
    } finally {
      setActionLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="state">
        Loading reconciliation…
      </div>
    );
  }

  if (error) {
    return (
      <div className="state">
        {error}
      </div>
    );
  }

  let records: any[] = [];

  if (Array.isArray(data)) {
    records = data;
  } else if (
    Array.isArray(
      data?.records
    )
  ) {
    records =
      data.records;
  }

  const normalized =
    records.map(
      (
        item: any,
        index: number
      ) => {

        const transactionId =
          item.transaction_id ||
          item.transactionId ||
          item.id ||
          `TXN-${index + 1}`;

        const amount =
          Number(
            item.amount ?? 0
          );

        const settlementAmount =
          Number(
            item.settlement_amount ??
              item.settlementAmount ??
              0
          );

        const variance =
          item.variance !==
          undefined
            ? Math.abs(
                Number(
                  item.variance
                )
              )
            : Math.abs(
                amount -
                  settlementAmount
              );

        const rawStatus =
          item.status ||
          item.reconciliation_status ||
          "";

        const status =
          String(
            rawStatus
          ).toUpperCase();

        const isMatched =
          status ===
            "MATCHED" ||
          variance < 1;

        return {
          ...item,

          transactionId,

          amount,

          settlementAmount,

          variance,

          status,

          isMatched,

          reason:
            item.reason ||
            (isMatched
              ? "Exact settlement match"
              : "Settlement variance detected"),
        };
      }
    );

  const total =
    Number(
      data?.total ??
        normalized.length
    );

  const matched =
    Number(
      data?.matched ??
        normalized.filter(
          (item) =>
            item.isMatched
        ).length
    );

  const exceptions =
    Number(
      data?.exceptions ??
        Math.max(
          total - matched,
          0
        )
    );

  const matchRate =
    Number(
      data?.match_rate ??
        (total > 0
          ? (matched / total) *
            100
          : 0)
    );

  const totalVariance =
    Number(
      data?.variance || 0
    );

  const exceptionRows =
    normalized.filter(
      (item: any) =>
        !item.isMatched
    );

  const priorityRow =
    exceptionRows.length
      ? exceptionRows.reduce(
          (
            best: any,
            item: any
          ) =>
            (item.variance || 0) >
            (best.variance || 0)
              ? item
              : best
        )
      : null;

  const filtered =
    normalized.filter(
      (item) => {

        if (
          filter ===
          "MATCHED"
        ) {
          return item.isMatched;
        }

        if (
          filter ===
          "MISMATCH"
        ) {
          return !item.isMatched;
        }

        return true;
      }
    );

  return (
    <>
      <header>
        <div>
          <h1>
            Reconciliation
          </h1>

          <p
            style={{
              marginTop: "4px",
              opacity: 0.7,
            }}
          >
            Automated
            transaction-to-settlement
            matching
          </p>
        </div>

        <span>
          Finance Operations
        </span>
      </header>

      <div
        className="panel"
        style={{ marginTop: "20px" }}
      >
        <h2>Single Reconciliation File</h2>
        <p style={{ marginTop: "5px", opacity: 0.65 }}>
          Upload one combined reconciliation CSV containing Bank, Ledger, and Settlement amounts.
        </p>
        <div
          style={{
            display: "flex",
            alignItems: "end",
            gap: "14px",
            flexWrap: "wrap",
            marginTop: "18px",
          }}
        >
          <label
            style={{
              display: "flex",
              flexDirection: "column",
              gap: "8px",
              fontSize: "13px",
              fontWeight: 600,
              minWidth: "240px",
            }}
          >
            Reconciliation CSV
            <input
              type="file"
              accept=".csv,text/csv"
              onChange={(event) =>
                setSingleFile(event.target.files?.[0] || null)
              }
              style={{
                padding: "10px",
                border: "1px solid #d7e1ed",
                borderRadius: "8px",
                background: "#ffffff",
              }}
            />
          </label>
          <button
            type="button"
            style={primaryButton}
            disabled={singleLoading}
            onClick={runSingleFileReconciliation}
          >
            {singleLoading ? "Reconciling..." : "Run Reconciliation"}
          </button>
        </div>
        {singleError && (
          <div className="error" style={{ marginTop: "14px" }}>
            {singleError}
          </div>
        )}
        {singleRun && (
          <div style={{ marginTop: "22px" }}>
            <p style={{ margin: 0, fontSize: "13px", opacity: 0.7 }}>
              Run ID: <strong>{singleRun.run_id}</strong>
            </p>
            <p style={{ margin: "8px 0 0", fontSize: "13px", opacity: 0.7 }}>
              Detected columns: <strong>{Object.entries(singleRun.mapping || {}).filter(([, value]) => value).map(([key, value]) => `${key}=${value}`).join(", ") || "No semantic columns"}</strong>
              <br />Tolerance: <strong>₹0.01</strong> · Calculation: <strong>gross amount - fees - refunds + positive adjustments</strong>
            </p>
            <div
              className="grid"
              style={{ marginTop: "14px" }}
            >
              {[
                ["Match Rate", `${Number(singleRun.match_rate).toFixed(1)}%`],
                ["Total Transactions", singleRun.total],
                ["Matched", singleRun.matched],
                ["Partial", singleRun.partial],
                ["Mismatch", singleRun.mismatch],
                ["Unmatched", singleRun.unmatched],
                ["Duplicates", singleRun.duplicates],
                ["Exceptions", singleRun.exceptions],
                ["Total Variance", currency(singleRun.variance)],
              ].map(([label, value]) => (
                <div className="card" key={label as string}>
                  <small>{label as string}</small>
                  <strong>{value as React.ReactNode}</strong>
                </div>
              ))}
            </div>
            <div style={{ overflowX: "auto", marginTop: "18px" }}>
              <table style={{ width: "100%", minWidth: "850px" }}>
                <thead>
                  <tr>
                    {["Reference", "Status", "Confidence", "Variance", "Reason", "Sources"].map((heading) => (
                      <th key={heading} style={tableHeader}>{heading}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {singleRun.records.map((record: any) => (
                    <tr key={`${record.reference}-${record.id}`}>
                      <td style={tableCell}><strong>{record.reference}</strong></td>
                      <td style={tableCell}><StatusBadge status={record.status} /></td>
                      <td style={tableCell}>{record.confidence}/100</td>
                      <td style={tableCell}>{currency(record.variance)}</td>
                      <td style={tableCell}>{record.reason}</td>
                      <td style={tableCell}>{record.matched_sources.join(", ") || "None"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

      <div
        className="panel"
        style={{
          marginTop: "20px",
        }}
      >
        <h2>Multi-Source Reconciliation</h2>
        <p
          style={{
            marginTop: "5px",
            opacity: 0.65,
          }}
        >
          Compare independently normalized bank, ledger, and settlement records.
        </p>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(190px, 1fr))",
            gap: "14px",
            marginTop: "18px",
          }}
        >
          {[
            ["Bank CSV", bankFile, setBankFile, true],
            ["Ledger CSV", ledgerFile, setLedgerFile, true],
            ["Settlement CSV (Optional)", settlementFile, setSettlementFile, false],
          ].map(([label, file, setter, required]) => (
            <label
              key={label as string}
              style={{
                display: "flex",
                flexDirection: "column",
                gap: "8px",
                fontSize: "13px",
                fontWeight: 600,
              }}
            >
              {label as string}
              <input
                type="file"
                accept=".csv,text/csv"
                required={required as boolean}
                onChange={(event) =>
                  (setter as React.Dispatch<React.SetStateAction<File | null>>)(
                    event.target.files?.[0] || null
                  )
                }
                style={{
                  padding: "10px",
                  border: "1px solid #d7e1ed",
                  borderRadius: "8px",
                  background: "#ffffff",
                }}
              />
              {file instanceof File && (
                <span style={{ opacity: 0.65, fontWeight: 400 }}>
                  {file.name}
                </span>
              )}
            </label>
          ))}
        </div>

        <button
          type="button"
          style={{
            ...primaryButton,
            marginTop: "18px",
          }}
          disabled={multiLoading}
          onClick={runMultiFileReconciliation}
        >
          {multiLoading ? "Reconciling..." : "Run Reconciliation"}
        </button>

        {multiError && (
          <div
            className="error"
            style={{ marginTop: "14px" }}
          >
            {multiError}
          </div>
        )}

        {multiRun && (
          <div style={{ marginTop: "22px" }}>
            <div style={{ marginBottom: "14px", fontSize: "13px", opacity: 0.75 }}>
              {Object.entries(multiRun.roles || {}).map(([source, detail]: [string, any]) => (
                <span key={source} style={{ display: "inline-block", marginRight: "18px" }}>
                  <strong>{source.toUpperCase()}</strong>: {detail.confidence}% confidence
                  {detail.assumption ? ` · ${detail.assumption}` : ""}
                </span>
              ))}
              <span> · Tolerance: <strong>₹0.01</strong></span>
            </div>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(130px, 1fr))",
                gap: "12px",
              }}
            >
              <div className="card"><small>Run ID</small><strong>{multiRun.run_id}</strong></div>
              <div className="card"><small>Bank Records</small><strong>{multiRun.sources.bank.records}</strong></div>
              <div className="card"><small>Ledger Records</small><strong>{multiRun.sources.ledger.records}</strong></div>
              <div className="card"><small>Settlement Records</small><strong>{multiRun.sources.settlement.records}</strong></div>
              <div className="card"><small>Matched</small><strong>{multiRun.summary.matched}</strong></div>
              <div className="card"><small>Partial</small><strong>{multiRun.summary.partial}</strong></div>
              <div className="card"><small>Mismatch</small><strong>{multiRun.summary.mismatch}</strong></div>
              <div className="card"><small>Unmatched</small><strong>{multiRun.summary.unmatched}</strong></div>
              <div className="card"><small>Duplicates</small><strong>{multiRun.summary.duplicate}</strong></div>
              <div className="card"><small>Match Rate</small><strong>{Number(multiRun.summary.match_rate).toFixed(1)}%</strong></div>
              <div className="card"><small>Total Variance</small><strong>{currency(multiRun.summary.total_variance)}</strong></div>
            </div>

            <div style={{ overflowX: "auto", marginTop: "18px" }}>
              <table style={{ width: "100%", minWidth: "850px" }}>
                <thead>
                  <tr>
                    {[
                      "Reference",
                      "Status",
                      "Confidence",
                      "Variance",
                      "Reason",
                      "Sources",
                    ].map((heading) => (
                      <th key={heading} style={tableHeader}>{heading}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {multiRun.records.map((record: any) => (
                    <tr key={`${record.reference}-${record.status}`}>
                      <td style={tableCell}><strong>{record.reference}</strong></td>
                      <td style={tableCell}><StatusBadge status={record.status} /></td>
                      <td style={tableCell}>{record.confidence_score}/100</td>
                      <td style={tableCell}>{currency(record.variance)}</td>
                      <td style={tableCell}>{record.reason}</td>
                      <td style={tableCell}>{record.matched_sources.join(", ") || "None"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

      {/* ===================================================
          KPI
      =================================================== */}

      <div className="grid">

        <div className="card">
          <small>
            Match Rate
          </small>

          <strong>
            {matchRate.toFixed(
              1
            )}
            %
          </strong>

          <span
            style={{
              display:
                "block",
              marginTop:
                "8px",
              fontSize:
                "13px",
              opacity:
                0.65,
            }}
          >
            Settlement
            accuracy
          </span>
        </div>

        <div className="card">
          <small>
            Total Transactions
          </small>

          <strong>
            {total.toLocaleString(
              "en-IN"
            )}
          </strong>

          <span
            style={{
              display:
                "block",
              marginTop:
                "8px",
              fontSize:
                "13px",
              opacity:
                0.65,
            }}
          >
            Records evaluated
          </span>
        </div>

        <div className="card">
          <small>
            Matched
          </small>

          <strong>
            {matched.toLocaleString(
              "en-IN"
            )}
          </strong>

          <span
            style={{
              display:
                "block",
              marginTop:
                "8px",
              fontSize:
                "13px",
              opacity:
                0.65,
            }}
          >
            Automatically
            reconciled
          </span>
        </div>

        <div className="card">
          <small>
            Exceptions
          </small>

          <strong>
            {exceptions.toLocaleString(
              "en-IN"
            )}
          </strong>

          <span
            style={{
              display:
                "block",
              marginTop:
                "8px",
              fontSize:
                "13px",
              opacity:
                0.65,
            }}
          >
            Require
            investigation
          </span>
        </div>

      </div>

      {/* ===================================================
          VARIANCE
      =================================================== */}

      <div
        className="panel"
        style={{
          marginTop:
            "20px",
        }}
      >
        <div
          style={{
            display:
              "flex",
            justifyContent:
              "space-between",
            alignItems:
              "center",
            gap:
              "20px",
            flexWrap:
              "wrap",
          }}
        >
          <div>
            <h2>
              Settlement Variance
            </h2>

            <p
              style={{
                marginTop:
                  "5px",
                opacity:
                  0.65,
              }}
            >
              Total absolute
              variance detected
              across
              reconciliation
              records.
            </p>
          </div>

          <strong
            style={{
              fontSize:
                "24px",
            }}
          >
            {currency(
              totalVariance
            )}
          </strong>
        </div>
      </div>

      {/* ===================================================
          CURRENT RUN PRIORITY
      =================================================== */}

      {data?.run_id && priorityRow ? (
        <div
          className="panel"
          style={{
            marginTop: "20px",
            borderLeft: "4px solid #b42318",
          }}
        >
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              gap: "20px",
              flexWrap: "wrap",
            }}
          >
            <div>
              <small
                style={{
                  display: "block",
                  fontWeight: 700,
                  color: "#b42318",
                  letterSpacing: "0.4px",
                }}
              >
                CURRENT RUN PRIORITY
              </small>
              <h2
                style={{
                  margin: "8px 0 4px",
                  fontSize: "20px",
                }}
              >
                Investigate{" "}
                {priorityRow.transactionId}
              </h2>
              <p
                style={{
                  margin: 0,
                  opacity: 0.7,
                  fontSize: "14px",
                }}
              >
                Largest exception variance:{" "}
                {currency(
                  priorityRow.variance
                )}{" "}
                ·{" "}
                {priorityRow.reason ||
                  "Settlement variance detected"}
              </p>
            </div>

            <div
              style={{
                textAlign: "right",
              }}
            >
              <div
                style={{
                  fontSize: "13px",
                  opacity: 0.7,
                }}
              >
                Risk level
              </div>
              <strong
                style={{
                  fontSize: "18px",
                  color:
                    (riskMap[
                      priorityRow.transactionId
                    ]?.risk_level ||
                      "") ===
                    "HIGH"
                      ? "#b42318"
                      : (riskMap[
                          priorityRow.transactionId
                        ]?.risk_level ||
                          "") ===
                        "CRITICAL"
                      ? "#7a271a"
                      : "#17324d",
                }}
              >
                {riskMap[
                  priorityRow.transactionId
                ]?.risk_level ||
                  "Not assessed"}
              </strong>

              <div
                style={{
                  marginTop: "10px",
                  fontSize: "13px",
                  opacity: 0.7,
                }}
              >
                Recommended action
              </div>
              <strong
                style={{
                  color: "#1769d1",
                }}
              >
                Investigate
              </strong>
            </div>
          </div>
        </div>
      ) : null}

      {/* ===================================================
          FILTERS
      =================================================== */}

      <div
        className="panel"
        style={{
          marginTop:
            "20px",
        }}
      >
        <div
          style={{
            display:
              "flex",
            gap:
              "8px",
            flexWrap:
              "wrap",
            alignItems:
              "center",
            justifyContent:
              "space-between",
          }}
        >
          <div
            style={{
              display:
                "flex",
              gap:
                "8px",
              flexWrap:
                "wrap",
            }}
          >
            {[
              ["ALL", "All"],
              [
                "MATCHED",
                "Matched",
              ],
              [
                "MISMATCH",
                "Exceptions",
              ],
            ].map(
              ([
                value,
                label,
              ]) => (
                <button
                  key={
                    value
                  }
                  onClick={() =>
                    setFilter(
                      value
                    )
                  }
                  style={{
                    padding:
                      "9px 16px",
                    borderRadius:
                      "8px",
                    border:
                      filter ===
                      value
                        ? "1px solid #1769d1"
                        : "1px solid #d9e2ef",
                    background:
                      filter ===
                      value
                        ? "#1769d1"
                        : "#ffffff",
                    color:
                      filter ===
                      value
                        ? "#ffffff"
                        : "#17324d",
                    cursor:
                      "pointer",
                    fontWeight:
                      600,
                  }}
                >
                  {
                    label
                  }
                </button>
              )
            )}
          </div>

          <span
            style={{
              fontSize:
                "14px",
              opacity:
                0.65,
            }}
          >
            Showing{" "}
            {
              filtered.length
            }{" "}
            of{" "}
            {total.toLocaleString(
              "en-IN"
            )}
          </span>
        </div>
      </div>

      {/* ===================================================
          TABLE
      =================================================== */}

      <div
        className="panel"
        style={{
          marginTop:
            "20px",
          overflowX:
            "auto",
        }}
      >
        <h2>
          Reconciliation Results
        </h2>

        {filtered.length ===
        0 ? (
          <div
            style={{
              padding:
                "40px 10px",
              textAlign:
                "center",
              opacity:
                0.65,
            }}
          >
            No records
            available.
          </div>
        ) : (
          <table
            style={{
              width:
                "100%",
              borderCollapse:
                "collapse",
              marginTop:
                "18px",
              minWidth:
                "1100px",
            }}
          >
            <thead>
              <tr>
                <th
                  style={
                    tableHeader
                  }
                >
                  Transaction
                </th>

                <th
                  style={
                    tableHeader
                  }
                >
                  Amount
                </th>

                <th
                  style={
                    tableHeader
                  }
                >
                  Settlement
                </th>

                <th
                  style={
                    tableHeader
                  }
                >
                  Variance
                </th>

                <th
                  style={
                    tableHeader
                  }
                >
                  Reconciliation
                </th>

                <th
                  style={
                    tableHeader
                  }
                >
                  Review
                </th>

                <th
                  style={
                    tableHeader
                  }
                >
                  Action
                </th>
              </tr>
            </thead>

            <tbody>
              {filtered.map(
                (
                  item,
                  index
                ) => {
                  const isMatched =
                    item.isMatched;

                  return (
                    <tr
                      key={
                        item.transactionId ||
                        index
                      }
                    >
                      <td
                        style={
                          tableCell
                        }
                      >
                        <strong>
                          {
                            item.transactionId
                          }
                        </strong>

                        {item.merchant && (
                          <div
                            style={{
                              fontSize:
                                "12px",
                              opacity:
                                0.6,
                              marginTop:
                                "4px",
                            }}
                          >
                            {
                              item.merchant
                            }
                          </div>
                        )}
                      </td>

                      <td
                        style={
                          tableCell
                        }
                      >
                        {currency(
                          item.amount
                        )}
                      </td>

                      <td
                        style={
                          tableCell
                        }
                      >
                        {currency(
                          item.settlementAmount
                        )}
                      </td>

                      <td
                        style={
                          tableCell
                        }
                      >
                        <strong>
                          {currency(
                            item.variance
                          )}
                        </strong>
                      </td>

                      <td
                        style={
                          tableCell
                        }
                      >
                        <span
                          style={{
                            display:
                              "inline-block",
                            padding:
                              "5px 10px",
                            borderRadius:
                              "20px",
                            fontSize:
                              "12px",
                            fontWeight:
                              700,
                            background:
                              isMatched
                                ? "#e8f7ee"
                                : "#fff3e6",
                            color:
                              isMatched
                                ? "#18794e"
                                : "#b45309",
                          }}
                        >
                          {isMatched
                            ? "MATCHED"
                            : "EXCEPTION"}
                        </span>
                      </td>

                      <td
                        style={
                          tableCell
                        }
                      >
                        {isMatched ? (
                          <span
                            style={{
                              opacity:
                                0.5,
                              fontSize:
                                "13px",
                            }}
                          >
                            —
                          </span>
                        ) : (
                          <StatusBadge
                            status={
                              item.review_status ||
                              "OPEN"
                            }
                          />
                        )}
                      </td>

                      <td
                        style={
                          tableCell
                        }
                      >
                        <button
                          onClick={() => {
                            setSelected(
                              item
                            );

                            setReviewNote(
                              item.review_note ||
                                ""
                            );

                            setActionError(
                              ""
                            );

                            setSuccessMessage(
                              ""
                            );
                          }}
                          style={
                            secondaryButton
                          }
                        >
                          View
                        </button>
                      </td>
                    </tr>
                  );
                }
              )}
            </tbody>
          </table>
        )}
      </div>

      {/* ===================================================
          EXCEPTION ANALYSIS
      =================================================== */}

      {selected && (
        <div
          className="panel"
          style={{
            marginTop:
              "20px",
          }}
        >
          <div
            style={{
              display:
                "flex",
              justifyContent:
                "space-between",
              alignItems:
                "flex-start",
              gap:
                "20px",
            }}
          >
            <div>
              <h2>
                Exception Analysis
              </h2>

              <p
                style={{
                  marginTop:
                    "4px",
                  opacity:
                    0.65,
                }}
              >
                Transaction{" "}
                <strong>
                  {
                    selected.transactionId
                  }
                </strong>
              </p>
            </div>

            <button
              onClick={() =>
                setSelected(
                  null
                )
              }
              style={
                secondaryButton
              }
            >
              Close
            </button>
          </div>

          {/* =================================================
              REVIEW STATUS
          ================================================= */}

          {!selected.isMatched && (
            <div
              style={{
                marginTop:
                  "18px",
                padding:
                  "14px 16px",
                borderRadius:
                  "10px",
                background:
                  "#f6f9fd",
                border:
                  "1px solid #e1e8f1",
                display:
                  "flex",
                justifyContent:
                  "space-between",
                alignItems:
                  "center",
                flexWrap:
                  "wrap",
                gap:
                  "10px",
              }}
            >
              <div>
                <small
                  style={{
                    display:
                      "block",
                    opacity:
                      0.6,
                    marginBottom:
                      "5px",
                  }}
                >
                  Review Status
                </small>

                <StatusBadge
                  status={
                    selected.review_status ||
                    "OPEN"
                  }
                />
              </div>

              <div>
                <small
                  style={{
                    display:
                      "block",
                    opacity:
                      0.6,
                    marginBottom:
                      "5px",
                  }}
                >
                  Review Item
                </small>

                <strong>
                  #
                  {
                    selected.review_item_id
                  }
                </strong>
              </div>
            </div>
          )}

          {/* =================================================
              FINANCIAL DETAILS
          ================================================= */}

          <div
            className="grid"
            style={{
              marginTop:
                "20px",
            }}
          >
            <div className="card">
              <small>
                Transaction Amount
              </small>

              <strong>
                {currency(
                  selected.amount
                )}
              </strong>
            </div>

            <div className="card">
              <small>
                Settlement Amount
              </small>

              <strong>
                {currency(
                  selected.settlementAmount
                )}
              </strong>
            </div>

            <div className="card">
              <small>
                Variance
              </small>

              <strong>
                {currency(
                  selected.variance
                )}
              </strong>
            </div>
          </div>

          {/* =================================================
              EVIDENCE
          ================================================= */}

          <div
            style={{
              marginTop:
                "20px",
              padding:
                "18px",
              borderRadius:
                "10px",
              background:
                "#f6f9fd",
              border:
                "1px solid #e1e8f1",
            }}
          >
            <h3>
              Reconciliation Evidence
            </h3>

            <div
              style={{
                display:
                  "grid",
                gridTemplateColumns:
                  "repeat(auto-fit, minmax(180px, 1fr))",
                gap:
                  "15px",
                marginTop:
                  "15px",
              }}
            >
              <div>
                <small>
                  Transaction ID
                </small>

                <div
                  style={{
                    marginTop:
                      "5px",
                    fontWeight:
                      600,
                  }}
                >
                  {
                    selected.transactionId
                  }
                </div>
              </div>

              <div>
                <small>
                  Merchant
                </small>

                <div
                  style={{
                    marginTop:
                      "5px",
                    fontWeight:
                      600,
                  }}
                >
                  {
                    selected.merchant ||
                    "—"
                  }
                </div>
              </div>

              <div>
                <small>
                  Vendor
                </small>

                <div
                  style={{
                    marginTop:
                      "5px",
                    fontWeight:
                      600,
                  }}
                >
                  {
                    selected.vendor ||
                    "—"
                  }
                </div>
              </div>

              <div>
                <small>
                  Date
                </small>

                <div
                  style={{
                    marginTop:
                      "5px",
                    fontWeight:
                      600,
                  }}
                >
                  {
                    selected.date ||
                    "—"
                  }
                </div>
              </div>

              <div>
                <small>
                  Category
                </small>

                <div
                  style={{
                    marginTop:
                      "5px",
                    fontWeight:
                      600,
                  }}
                >
                  {
                    selected.category ||
                    "—"
                  }
                </div>
              </div>

              <div>
                <small>
                  Currency
                </small>

                <div
                  style={{
                    marginTop:
                      "5px",
                    fontWeight:
                      600,
                  }}
                >
                  {
                    selected.currency ||
                    "INR"
                  }
                </div>
              </div>
            </div>
          </div>

          {/* =================================================
              AI EXPLANATION
          ================================================= */}

          <div
            style={{
              marginTop:
                "20px",
              padding:
                "18px",
              borderRadius:
                "10px",
              background:
                "#f6f9fd",
              border:
                "1px solid #e1e8f1",
            }}
          >
            <h3>
              AI Explanation
            </h3>

            <p
              style={{
                marginTop:
                  "8px",
                lineHeight:
                  1.6,
              }}
            >
              {selected.variance <
              1
                ? "The transaction amount matches the settlement amount. No reconciliation exception was detected."
                : `The settlement amount differs from the transaction amount by ${currency(
                    selected.variance
                  )}. The exception should be investigated before final reconciliation.`}
            </p>

            <p
              style={{
                marginTop:
                  "12px",
                fontSize:
                  "13px",
                opacity:
                  0.7,
              }}
            >
              Reason:{" "}
              {
                selected.reason
              }
            </p>
          </div>

          {/* =================================================
              REVIEW NOTE
          ================================================= */}

          {!selected.isMatched && (
            <div
              style={{
                marginTop:
                  "20px",
              }}
            >
              <h3>
                Reviewer Note
              </h3>

              <textarea
                value={
                  reviewNote
                }
                onChange={(
                  event
                ) =>
                  setReviewNote(
                    event.target
                      .value
                  )
                }
                placeholder="Enter investigation findings, supporting evidence, or approval notes..."
                style={{
                  width:
                    "100%",
                  minHeight:
                    "110px",
                  marginTop:
                    "10px",
                  padding:
                    "12px",
                  borderRadius:
                    "8px",
                  border:
                    "1px solid #d7e1ed",
                  resize:
                    "vertical",
                  boxSizing:
                    "border-box",
                  fontFamily:
                    "inherit",
                }}
              />
            </div>
          )}

          {/* =================================================
              SUCCESS
          ================================================= */}

          {successMessage && (
            <div
              style={{
                marginTop:
                  "15px",
                padding:
                  "12px 14px",
                borderRadius:
                  "8px",
                background:
                  "#e8f7ee",
                color:
                  "#166534",
                border:
                  "1px solid #b7e4c7",
                fontSize:
                  "14px",
                fontWeight:
                  600,
              }}
            >
              ✓{" "}
              {
                successMessage
              }
            </div>
          )}

          {/* =================================================
              ERROR
          ================================================= */}

          {actionError && (
            <div
              className="error"
              style={{
                marginTop:
                  "12px",
              }}
            >
              {actionError}
            </div>
          )}

          {/* =================================================
              ACTIONS
          ================================================= */}

          {!selected.isMatched && (
            <div
              style={{
                marginTop:
                  "20px",
                paddingTop:
                  "20px",
                borderTop:
                  "1px solid #e5ebf2",
              }}
            >
              <h3>
                Review Actions
              </h3>

              <p
                style={{
                  marginTop:
                    "6px",
                  fontSize:
                    "13px",
                  opacity:
                    0.65,
                }}
              >
                Update the
                human-in-the-loop
                review status for
                this exception.
              </p>

              <div
                style={{
                  display:
                    "flex",
                  gap:
                    "10px",
                  flexWrap:
                    "wrap",
                  marginTop:
                    "14px",
                }}
              >
                <button
                  disabled={
                    actionLoading
                  }
                  onClick={() =>
                    updateReview(
                      "UNDER_REVIEW"
                    )
                  }
                  style={
                    primaryButton
                  }
                >
                  {actionLoading
                    ? "Updating..."
                    : "Investigate"}
                </button>

                <button
                  disabled={
                    actionLoading
                  }
                  onClick={() =>
                    updateReview(
                      "APPROVED"
                    )
                  }
                  style={{
                    ...primaryButton,
                    background:
                      "#18794e",
                    borderColor:
                      "#18794e",
                  }}
                >
                  Approve
                </button>

                <button
                  disabled={
                    actionLoading
                  }
                  onClick={() =>
                    updateReview(
                      "REJECTED"
                    )
                  }
                  style={{
                    ...primaryButton,
                    background:
                      "#b42318",
                    borderColor:
                      "#b42318",
                  }}
                >
                  Reject
                </button>

                <button
                  disabled={
                    actionLoading
                  }
                  onClick={() =>
                    updateReview(
                      "ESCALATED"
                    )
                  }
                  style={{
                    ...primaryButton,
                    background:
                      "#c2410c",
                    borderColor:
                      "#c2410c",
                  }}
                >
                  Escalate
                </button>

                <button
                  disabled={
                    actionLoading
                  }
                  onClick={() =>
                    updateReview(
                      "RESOLVED"
                    )
                  }
                  style={{
                    ...primaryButton,
                    background:
                      "#166534",
                    borderColor:
                      "#166534",
                  }}
                >
                  Resolve
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </>
  );
}

/* =========================================================
   REVIEW QUEUE
========================================================= */

function ReviewQueue() {
  const [items, setItems] =
    useState<any[]>([]);

  const [reconciliationMap, setReconciliationMap] =
    useState<Record<string, any>>(
      {}
    );

  const [loading, setLoading] =
    useState(true);

  const [error, setError] =
    useState("");

  const [selected, setSelected] =
    useState<any>(null);

  const [note, setNote] =
    useState("");

  const [actionLoading, setActionLoading] =
    useState(false);

  const [actionError, setActionError] =
    useState("");

  const [successMessage, setSuccessMessage] =
    useState("");

  async function loadReviewQueue() {
    setLoading(true);

    try {
      const [
        reviewData,
        reconciliationData,
      ] = await Promise.all([
        apiGet("/review"),
        apiGet(
          "/reconciliation"
        ),
      ]);

      const reviewItems =
        Array.isArray(
          reviewData
        )
          ? reviewData
          : [];

      const map: Record<
        string,
        any
      > = {};

      const records =
        Array.isArray(
          reconciliationData?.records
        )
          ? reconciliationData.records
          : [];

      records.forEach(
        (record: any) => {
          if (
            record.transaction_id
          ) {
            map[
              record.transaction_id
            ] = record;
          }
        }
      );

      setReconciliationMap(
        map
      );

      const exceptionItems = reviewItems.filter((item: any) => {
        const record = map[item.transaction_id];
        return record && record.status !== "MATCHED";
      });

      // Active exceptions sorted by financial impact (largest variance first).
      exceptionItems.sort((a: any, b: any) => {
        const va = Number(map[a.transaction_id]?.variance || 0);
        const vb = Number(map[b.transaction_id]?.variance || 0);
        return vb - va;
      });

      setItems(
        exceptionItems
      );

      setError("");
    } catch (err) {
      console.error(err);

      setError(
        "Unable to load review queue."
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadReviewQueue();
  }, []);

  async function updateReview(
    action: string
  ) {
    if (!selected?.id) {
      return;
    }

    setActionLoading(true);
    setActionError("");
    setSuccessMessage("");

    try {
      const result = await apiPost(
        `/review/${selected.id}/action`,
        {
          action,
          note:
            note.trim() ||
            null,
        }
      );

      setSelected(
        (previous: any) =>
          previous
            ? {
                ...previous,
                status: result.new_status,
                note:
                  note.trim() ||
                  null,
              }
            : previous
      );

      setSuccessMessage(
        `Review successfully updated to ${result.new_status.replace(
          "_",
          " "
        )}.`
      );

      await loadReviewQueue();

    } catch (err: any) {
      console.error(err);

      setActionError(
        err.message ||
          "Unable to update review."
      );
    } finally {
      setActionLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="state">
        Loading review queue…
      </div>
    );
  }

  if (error) {
    return (
      <div className="state">
        {error}
      </div>
    );
  }

  const open =
    items.filter(
      (x) =>
        x.status ===
        "OPEN"
    ).length;

  const underReview =
    items.filter(
      (x) =>
        x.status ===
        "UNDER_REVIEW"
    ).length;

  const escalated =
    items.filter(
      (x) =>
        x.status ===
        "ESCALATED"
    ).length;

  const resolved =
    items.filter(
      (x) =>
        x.status ===
        "RESOLVED"
    ).length;

  return (
    <>
      <header>
        <div>
          <h1>
            Review Center
          </h1>

          <p
            style={{
              marginTop:
                "4px",
              opacity:
                0.7,
            }}
          >
            Human-in-the-loop
            exception
            management
          </p>
        </div>

        <span>
          {
            items.length
          }{" "}
          review items
        </span>
      </header>

      {/* ===================================================
          KPI
      =================================================== */}

      <div className="grid">

        <div className="card">
          <small>
            Open
          </small>

          <strong>
            {open}
          </strong>

          <span
            style={{
              display:
                "block",
              marginTop:
                "8px",
              fontSize:
                "13px",
              opacity:
                0.65,
            }}
          >
            Awaiting
            investigation
          </span>
        </div>

        <div className="card">
          <small>
            Under Review
          </small>

          <strong>
            {underReview}
          </strong>

          <span
            style={{
              display:
                "block",
              marginTop:
                "8px",
              fontSize:
                "13px",
              opacity:
                0.65,
            }}
          >
            Currently
            investigated
          </span>
        </div>

        <div className="card">
          <small>
            Escalated
          </small>

          <strong>
            {escalated}
          </strong>

          <span
            style={{
              display:
                "block",
              marginTop:
                "8px",
              fontSize:
                "13px",
              opacity:
                0.65,
            }}
          >
            Requires
            higher-level
            review
          </span>
        </div>

        <div className="card">
          <small>
            Resolved
          </small>

          <strong>
            {resolved}
          </strong>

          <span
            style={{
              display:
                "block",
              marginTop:
                "8px",
              fontSize:
                "13px",
              opacity:
                0.65,
            }}
          >
            Closed
            exceptions
          </span>
        </div>

      </div>

      {/* ===================================================
          QUEUE
      =================================================== */}

      <div
        className="panel"
        style={{
          marginTop:
            "20px",
          overflowX:
            "auto",
        }}
      >
        <h2>
          Exception Review Queue
        </h2>

        {items.length ===
        0 ? (
          <div
            style={{
              padding:
                "40px",
              textAlign:
                "center",
              opacity:
                0.6,
            }}
          >
            No review items
            found.
          </div>
        ) : (
          <table
            style={{
              width:
                "100%",
              borderCollapse:
                "collapse",
              marginTop:
                "18px",
              minWidth:
                "1000px",
            }}
          >
            <thead>
              <tr>
                <th
                  style={
                    tableHeader
                  }
                >
                  Transaction
                </th>

                <th
                  style={
                    tableHeader
                  }
                >
                  Amount
                </th>

                <th
                  style={
                    tableHeader
                  }
                >
                  Settlement
                </th>

                <th
                  style={
                    tableHeader
                  }
                >
                  Variance
                </th>

                <th
                  style={
                    tableHeader
                  }
                >
                  Status
                </th>

                <th
                  style={
                    tableHeader
                  }
                >
                  Vendor
                </th>

                <th
                  style={
                    tableHeader
                  }
                >
                  Reason
                </th>

                <th
                  style={
                    tableHeader
                  }
                >
                  Risk
                </th>

                <th
                  style={
                    tableHeader
                  }
                >
                  Created
                </th>

                <th
                  style={
                    tableHeader
                  }
                >
                  Action
                </th>
              </tr>
            </thead>

            <tbody>
              {items.map(
                (item) => {
                  const transaction =
                    reconciliationMap[
                      item.transaction_id
                    ];

                  return (
                    <tr
                      key={
                        item.id
                      }
                    >
                      <td
                        style={
                          tableCell
                        }
                      >
                        <strong>
                          {
                            item.transaction_id
                          }
                        </strong>

                        <div
                          style={{
                            fontSize:
                              "12px",
                            opacity:
                              0.6,
                            marginTop:
                              "4px",
                          }}
                        >
                          {
                            transaction?.date ||
                            "—"
                          }
                        </div>
                      </td>

                      <td
                        style={
                          tableCell
                        }
                      >
                        {currency(
                          transaction?.amount ||
                            0
                        )}
                      </td>

                      <td
                        style={
                          tableCell
                        }
                      >
                        {currency(
                          transaction?.settlement_amount ||
                            0
                        )}
                      </td>

                      <td
                        style={
                          tableCell
                        }
                      >
                        <strong>
                          {currency(
                            transaction?.variance ||
                              0
                          )}
                        </strong>
                      </td>

                      <td
                        style={
                          tableCell
                        }
                      >
                        <StatusBadge
                          status={
                            item.status
                          }
                        />
                      </td>

                      <td
                        style={
                          tableCell
                        }
                      >
                        {
                          item.vendor ||
                          transaction?.vendor ||
                          "—"
                        }
                      </td>

                      <td
                        style={
                          tableCell
                        }
                      >
                        {item.reason || item.note || "—"}
                      </td>

                      <td
                        style={
                          tableCell
                        }
                      >
                        {item.risk_level ? (
                          <>
                            <StatusBadge status={item.risk_level} />
                            <div style={{ fontSize: "12px", marginTop: "4px", opacity: 0.65 }}>
                              {Number(item.risk_score || 0).toFixed(0)}/100
                            </div>
                            {Array.isArray(item.risk_factors) && item.risk_factors.length ? (
                              <div style={{ fontSize: "12px", marginTop: "4px", opacity: 0.65, fontStyle: "italic" }}>
                                {item.risk_factors.filter(Boolean).join(", ")}
                              </div>
                            ) : null}
                          </>
                        ) : "—"}
                      </td>

                      <td
                        style={
                          tableCell
                        }
                      >
                        {item.created_at ? new Date(item.created_at).toLocaleDateString("en-IN") : "—"}
                      </td>

                      <td
                        style={
                          tableCell
                        }
                      >
                        <button
                          style={
                            secondaryButton
                          }
                          onClick={() => {
                            setSelected(
                              {
                                ...item,
                                amount:
                                  transaction?.amount ||
                                  0,
                                settlement_amount:
                                  transaction?.settlement_amount ||
                                  0,
                                variance:
                                  transaction?.variance ||
                                  0,
                                merchant:
                                  transaction?.merchant ||
                                  null,
                                vendor:
                                  transaction?.vendor ||
                                  null,
                                date:
                                  transaction?.date ||
                                  null,
                                category:
                                  transaction?.category ||
                                  null,
                                reason:
                                  transaction?.reason ||
                                  "Settlement variance detected.",
                              }
                            );

                            setNote(
                              item.note ||
                                ""
                            );

                            setActionError(
                              ""
                            );

                            setSuccessMessage(
                              ""
                            );
                          }}
                        >
                          Review
                        </button>
                      </td>
                    </tr>
                  );
                }
              )}
            </tbody>
          </table>
        )}
      </div>

      {/* ===================================================
          REVIEW DETAIL
      =================================================== */}

      {selected && (
        <div
          className="panel"
          style={{
            marginTop:
              "20px",
          }}
        >
          <div
            style={{
              display:
                "flex",
              justifyContent:
                "space-between",
              alignItems:
                "flex-start",
              gap:
                "20px",
            }}
          >
            <div>
              <h2>
                Review Item
              </h2>

              <p
                style={{
                  marginTop:
                    "5px",
                  opacity:
                    0.65,
                }}
              >
                {
                  selected.transaction_id
                }
              </p>
            </div>

            <button
              style={
                secondaryButton
              }
              onClick={() =>
                setSelected(
                  null
                )
              }
            >
              Close
            </button>
          </div>

          <div
            style={{
              marginTop:
                "18px",
              padding:
                "14px 16px",
              borderRadius:
                "10px",
              background:
                "#f6f9fd",
              border:
                "1px solid #e1e8f1",
              display:
                "flex",
              justifyContent:
                "space-between",
              alignItems:
                "center",
              flexWrap:
                "wrap",
              gap:
                "12px",
            }}
          >
            <div>
              <small
                style={{
                  display:
                    "block",
                  opacity:
                    0.6,
                  marginBottom:
                    "5px",
                }}
              >
                Review Status
              </small>

              <StatusBadge
                status={
                  selected.status
                }
              />
            </div>

            <div>
              <small
                style={{
                  display:
                    "block",
                  opacity:
                    0.6,
                  marginBottom:
                    "5px",
                }}
              >
                Review Item ID
              </small>

              <strong>
                #
                {
                  selected.id
                }
              </strong>
            </div>
          </div>

          {/* =================================================
              FINANCIAL DETAILS
          ================================================= */}

          <div
            className="grid"
            style={{
              marginTop:
                "20px",
            }}
          >
            <div className="card">
              <small>
                Transaction Amount
              </small>

              <strong>
                {currency(
                  selected.amount
                )}
              </strong>
            </div>

            <div className="card">
              <small>
                Settlement Amount
              </small>

              <strong>
                {currency(
                  selected.settlement_amount
                )}
              </strong>
            </div>

            <div className="card">
              <small>
                Variance
              </small>

              <strong>
                {currency(
                  selected.variance
                )}
              </strong>
            </div>
          </div>

          {/* =================================================
              EXCEPTION REASON
          ================================================= */}

          <div
            style={{
              marginTop:
                "20px",
              padding:
                "18px",
              background:
                "#f6f9fd",
              border:
                "1px solid #e1e8f1",
              borderRadius:
                "10px",
            }}
          >
            <h3>
              Exception Reason
            </h3>

            <p
              style={{
                marginTop:
                  "8px",
                lineHeight:
                  1.6,
              }}
            >
              {
                selected.reason ||
                "Settlement variance detected."
              }
            </p>

            {selected.merchant && (
              <p
                style={{
                  marginTop:
                    "10px",
                  fontSize:
                    "13px",
                  opacity:
                    0.7,
                }}
              >
                Merchant:{" "}
                <strong>
                  {
                    selected.merchant
                  }
                </strong>
              </p>
            )}
          </div>

          {/* =================================================
              NOTE
          ================================================= */}

          <div
            style={{
              marginTop:
                "20px",
            }}
          >
            <h3>
              Reviewer Note
            </h3>

            <textarea
              value={note}
              onChange={(
                event
              ) =>
                setNote(
                  event.target
                    .value
                )
              }
              placeholder="Document investigation findings, evidence, or approval notes..."
              style={{
                width:
                  "100%",
                minHeight:
                  "110px",
                marginTop:
                  "10px",
                padding:
                  "12px",
                borderRadius:
                  "8px",
                border:
                  "1px solid #d7e1ed",
                boxSizing:
                  "border-box",
                resize:
                  "vertical",
                fontFamily:
                  "inherit",
              }}
            />
          </div>

          {/* =================================================
              SUCCESS
          ================================================= */}

          {successMessage && (
            <div
              style={{
                marginTop:
                  "15px",
                padding:
                  "12px 14px",
                borderRadius:
                  "8px",
                background:
                  "#e8f7ee",
                color:
                  "#166534",
                border:
                  "1px solid #b7e4c7",
                fontSize:
                  "14px",
                fontWeight:
                  600,
              }}
            >
              ✓{" "}
              {
                successMessage
              }
            </div>
          )}

          {/* =================================================
              ERROR
          ================================================= */}

          {actionError && (
            <div
              className="error"
              style={{
                marginTop:
                  "12px",
              }}
            >
              {actionError}
            </div>
          )}

          {/* =================================================
              ACTIONS
          ================================================= */}

          <div
            style={{
              display:
                "flex",
              gap:
                "10px",
              flexWrap:
                "wrap",
              marginTop:
                "18px",
              paddingTop:
                "18px",
              borderTop:
                "1px solid #e5ebf2",
            }}
          >
            <button
              disabled={
                actionLoading
              }
              style={
                primaryButton
              }
              onClick={() =>
                updateReview(
                  "INVESTIGATE"
                )
              }
            >
              {actionLoading
                ? "Updating..."
                : "Investigate"}
            </button>

            <button
              disabled={
                actionLoading
              }
              style={{
                ...primaryButton,
                background:
                  "#18794e",
                borderColor:
                  "#18794e",
              }}
              onClick={() =>
                updateReview(
                  "APPROVE"
                )
              }
            >
              Approve
            </button>

            <button
              disabled={
                actionLoading
              }
              style={{
                ...primaryButton,
                background:
                  "#b42318",
                borderColor:
                  "#b42318",
              }}
              onClick={() =>
                updateReview(
                  "REJECT"
                )
              }
            >
              Reject
            </button>

            <button
              disabled={
                actionLoading
              }
              style={{
                ...primaryButton,
                background:
                  "#c2410c",
                borderColor:
                  "#c2410c",
              }}
              onClick={() =>
                updateReview(
                  "ESCALATE"
                )
              }
            >
              Escalate
            </button>

            <button
              disabled={
                actionLoading
              }
              style={{
                ...primaryButton,
                background:
                  "#166534",
                borderColor:
                  "#166534",
              }}
              onClick={() =>
                updateReview(
                  "RESOLVE"
                )
              }
            >
              Resolve
            </button>

            <button
              disabled={
                actionLoading
              }
              style={secondaryButton}
              onClick={() =>
                updateReview(
                  "REOPEN"
                )
              }
            >
              Reopen
            </button>
          </div>
        </div>
      )}
    </>
  );
}

/* =========================================================
   GENERIC PAGE
========================================================= */

function ScenarioSimulator() {
  const [dashboard, setDashboard] = useState<any>(null);
  const [scenario, setScenario] = useState<any>(null);
  const [revenueChange, setRevenueChange] = useState("-10");
  const [expenseChange, setExpenseChange] = useState("0");
  const [refundChange, setRefundChange] = useState("0");
  const [feeChange, setFeeChange] = useState("0");
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState("");

  async function loadDashboard() {
    setLoading(true);
    setError("");
    try {
      setDashboard(await apiGet("/dashboard"));
    } catch (err) {
      console.error(err);
      setError("Unable to load current financial position.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadDashboard();
  }, []);

  async function runScenario() {
    setRunning(true);
    setError("");
    try {
      const result = await apiPost("/scenarios", {
        revenue_change: Number(revenueChange) || 0,
        expense_change: Number(expenseChange) || 0,
        refund_change: Number(refundChange) || 0,
        fee_change: Number(feeChange) || 0,
      });
      setScenario(result);
    } catch (err) {
      console.error(err);
      setError("Unable to calculate this scenario.");
    } finally {
      setRunning(false);
    }
  }

  if (loading) {
    return <div className="state">Loading scenario inputs…</div>;
  }

  if (error && !dashboard) {
    return (
      <div className="state">
        <p>{error}</p>
        <button type="button" onClick={loadDashboard}>Retry</button>
      </div>
    );
  }

  const currentRevenue = Number(dashboard?.revenue || 0);
  const currentExpenses = Number(dashboard?.expenses || 0);
  const currentNetProfit = Number(dashboard?.net_profit || 0);
  const projectedProfit = scenario?.projected_profit;
  const profitImpact = scenario
    ? Number(projectedProfit) - currentNetProfit
    : null;
  const money = (value: number) => currency(value);

  const inputs = [
    ["Revenue change (%)", revenueChange, setRevenueChange],
    ["Expense change (%)", expenseChange, setExpenseChange],
    ["Refund assumption (%)", refundChange, setRefundChange],
    ["Fee assumption (%)", feeChange, setFeeChange],
  ] as const;

  return (
    <>
      <header>
        <div>
          <h1>Scenario Analysis</h1>
          <p style={{ marginTop: "4px", opacity: 0.7 }}>
            Model controller assumptions against current backend metrics.
          </p>
        </div>
        <span>Deterministic finance engine</span>
      </header>

      <div className="panel">
        <h2>Scenario assumptions</h2>
        <div className="grid" style={{ marginTop: "16px" }}>
          {inputs.map(([label, value, setter]) => (
            <label key={label} style={{ display: "flex", flexDirection: "column", gap: "7px", fontSize: "13px", fontWeight: 600 }}>
              {label}
              <input
                type="number"
                value={value}
                onChange={(event) => setter(event.target.value)}
                style={{ padding: "11px", border: "1px solid #cdd9e8", borderRadius: "8px", font: "inherit" }}
              />
            </label>
          ))}
        </div>
        <button type="button" style={{ ...primaryButton, marginTop: "18px" }} disabled={running} onClick={runScenario}>
          {running ? "Calculating…" : "Run Scenario"}
        </button>
        {error && <div className="error">{error}</div>}
      </div>

      <div className="panel">
        <h2>Current position</h2>
        <div className="grid" style={{ marginTop: "16px" }}>
          <div className="card"><small>Current Revenue</small><strong>{money(currentRevenue)}</strong></div>
          <div className="card"><small>Current Expenses</small><strong>{money(currentExpenses)}</strong></div>
          <div className="card"><small>Current Net Profit</small><strong>{money(currentNetProfit)}</strong></div>
        </div>
      </div>

      {scenario ? (
        <div className="panel">
          <h2>Projected position</h2>
          <div className="grid" style={{ marginTop: "16px" }}>
            <div className="card"><small>Revenue Change</small><strong>{Number(revenueChange)}%</strong></div>
            <div className="card"><small>Projected Revenue</small><strong>{money(scenario.projected_revenue)}</strong></div>
            <div className="card"><small>Projected Expenses</small><strong>{money(scenario.projected_expenses)}</strong></div>
            <div className="card"><small>Projected Net Profit</small><strong>{money(projectedProfit)}</strong></div>
            <div className="card"><small>Profit Impact</small><strong style={{ color: Number(profitImpact) >= 0 ? "#18794e" : "#b42318" }}>{money(Number(profitImpact))}</strong></div>
            <div className="card"><small>Estimated Cash Impact</small><strong style={{ color: Number(scenario.cash_impact) >= 0 ? "#18794e" : "#b42318" }}>{money(scenario.cash_impact)}</strong></div>
          </div>
          <div style={{ marginTop: "18px", padding: "16px", background: "#f6f9fd", border: "1px solid #e1e8f1", borderRadius: "8px" }}>
            <strong>Controller Interpretation</strong>
            <p style={{ margin: "8px 0 0", lineHeight: 1.6 }}>
              {scenario.risk_impact === "HIGH" ? "The modeled position creates a high financial risk and requires controller attention." : "The modeled position remains within the current operating range."}
            </p>
            <strong style={{ display: "block", marginTop: "14px" }}>Recommended Action</strong>
            <p style={{ margin: "8px 0 0", lineHeight: 1.6 }}>
              {scenario.risk_impact === "HIGH" ? "Review revenue protection, expense controls, and liquidity coverage before approving the plan." : "Monitor the modeled change and validate the assumption against the latest operating evidence."}
            </p>
            <small style={{ display: "block", marginTop: "14px", opacity: 0.7 }}>
              Estimated Cash Impact is derived from projected profit and is not actual cash flow.
            </small>
          </div>
        </div>
      ) : (
        <div className="panel"><div className="state">Run a scenario to compare the projected position.</div></div>
      )}
    </>
  );
}

function AuditLogs() {
  const [logs, setLogs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function loadLogs() {
    setLoading(true);
    setError("");
    try {
      const result = await apiGet("/audit");
      setLogs(Array.isArray(result) ? result : []);
    } catch (err) {
      console.error(err);
      setError("Unable to load audit logs.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadLogs();
  }, []);

  if (loading) {
    return <div className="state">Loading audit logs…</div>;
  }

  if (error) {
    return (
      <div className="state">
        <p>{error}</p>
        <button type="button" onClick={loadLogs}>Retry</button>
      </div>
    );
  }

  return (
    <>
      <header>
        <div>
          <h1>Audit Logs</h1>
          <p style={{ marginTop: "4px", opacity: 0.7 }}>
            Immutable record of controller and system actions.
          </p>
        </div>
        <span>{logs.length} records</span>
      </header>
      <div className="panel" style={{ overflowX: "auto" }}>
        {logs.length === 0 ? (
          <div className="state">No audit activity recorded yet.</div>
        ) : (
          <table style={{ width: "100%", minWidth: "780px", borderCollapse: "collapse" }}>
            <thead>
              <tr>
                {["Timestamp", "User", "Action", "Entity", "Details"].map((heading) => (
                  <th key={heading} style={tableHeader}>{heading}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {logs.map((log, index) => (
                <tr key={`${log.created_at}-${index}`}>
                  <td style={tableCell}>{log.created_at ? new Date(log.created_at).toLocaleString("en-IN") : "—"}</td>
                  <td style={tableCell}>{log.user || "System"}</td>
                  <td style={tableCell}><strong>{log.action || "—"}</strong></td>
                  <td style={tableCell}>{log.entity || "—"}</td>
                  <td style={tableCell}>{log.detail || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </>
  );
}

function RiskAnomalyView({
  kind,
}: {
  kind: "risk" | "anomaly";
}) {
  const [items, setItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [activeRun, setActiveRun] = useState<string | null>(null);
  const isRisk = kind === "risk";
  const navigate = useNavigate();

  async function loadItems() {
    setLoading(true);
    setError("");
    let runId: string | null = null;
    try {
      try {
        const dashboard = await apiGet("/dashboard");
        runId = dashboard?.reconciliation?.run_id || null;
      } catch {
        runId = null;
      }
      const suffix = runId
        ? `?run_id=${encodeURIComponent(runId)}`
        : "";
      const result = await apiGet(
        (isRisk ? "/risk" : "/anomalies") + suffix
      );
      setItems(Array.isArray(result) ? result : []);
      setActiveRun(runId);
    } catch (err) {
      console.error(err);
      setError(`Unable to load ${isRisk ? "risk assessments" : "anomalies"}.`);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadItems();
  }, [kind]);

  const riskSummary = (() => {
    const counts: Record<string, number> = {};
    let totalVariance = 0;
    let largest: any = null;
    (items as any[]).forEach((item) => {
      const level = String(
        isRisk ? item.risk_level : item.severity || "UNKNOWN"
      ).toUpperCase();
      counts[level] = (counts[level] || 0) + 1;
      const v = Number(item.variance || 0);
      totalVariance += v;
      if (!largest || v > Number(largest.variance || 0)) {
        largest = item;
      }
    });
    return { counts, totalVariance, largest };
  })();

  if (loading) return <div className="state">Loading {isRisk ? "risk assessments" : "anomalies"}…</div>;
  if (error) {
    return <div className="state"><p>{error}</p><button type="button" onClick={loadItems}>Retry</button></div>;
  }

  return (
    <>
      <header>
        <div>
          <h1>{isRisk ? "Risk Assessment" : "Anomaly Detection"}</h1>
          <p style={{ marginTop: "4px", opacity: 0.7 }}>
            {isRisk ? "Prioritized transaction risk from deterministic controls." : "Detected transaction patterns requiring controller attention."}
          </p>
        </div>
        <span>{items.length} items{activeRun ? ` · run ${activeRun}` : ""}</span>
      </header>

      {/* CURRENT-RUN RISK OVERVIEW */}
      <div className="grid">
        <div className="card">
          <small>{isRisk ? "Exceptions Assessed" : "Anomalies Detected"}</small>
          <strong>{items.length}</strong>
          <span style={{ display: "block", marginTop: "8px", fontSize: "13px", opacity: 0.65 }}>
            {activeRun ? `Current run ${activeRun}` : "Current data"}
          </span>
        </div>
        <div className="card">
          <small>HIGH / CRITICAL</small>
          <strong>{(riskSummary.counts["HIGH"] || 0) + (riskSummary.counts["CRITICAL"] || 0)}</strong>
          <span style={{ display: "block", marginTop: "8px", fontSize: "13px", opacity: 0.65 }}>Require controller attention</span>
        </div>
        <div className="card">
          <small>MEDIUM</small>
          <strong>{riskSummary.counts["MEDIUM"] || 0}</strong>
          <span style={{ display: "block", marginTop: "8px", fontSize: "13px", opacity: 0.65 }}>Material review</span>
        </div>
        <div className="card">
          <small>LOW</small>
          <strong>{riskSummary.counts["LOW"] || 0}</strong>
          <span style={{ display: "block", marginTop: "8px", fontSize: "13px", opacity: 0.65 }}>Monitor</span>
        </div>
        <div className="card">
          <small>Total Variance</small>
          <strong>{currency(riskSummary.totalVariance)}</strong>
          <span style={{ display: "block", marginTop: "8px", fontSize: "13px", opacity: 0.65 }}>Financial impact of current run</span>
        </div>
      </div>

      {items.length > 0 && riskSummary.largest ? (
        <div className="panel" style={{ marginTop: "20px", borderLeft: "4px solid #b42318" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "20px", flexWrap: "wrap" }}>
            <div>
              <small style={{ display: "block", fontWeight: 700, color: "#b42318", letterSpacing: "0.4px" }}>
                TOP PRIORITY
              </small>
              <h2 style={{ margin: "8px 0 4px", fontSize: "20px" }}>{riskSummary.largest.transaction_id}</h2>
              <p style={{ margin: 0, opacity: 0.7, fontSize: "14px" }}>
                Variance: {currency(Number(riskSummary.largest.variance || 0))} ·{" "}
                {riskSummary.largest.reason || (isRisk ? "Risk requires investigation." : "Anomaly requires investigation.")}
              </p>
            </div>
            <div style={{ textAlign: "right" }}>
              <div style={{ fontSize: "13px", opacity: 0.7 }}>{isRisk ? "Risk level" : "Severity"}</div>
              <strong style={{ fontSize: "18px" }}>
                <StatusBadge status={riskSummary.largest.risk_level || riskSummary.largest.severity || "HIGH"} />
              </strong>
              <div style={{ marginTop: "10px", fontSize: "13px", opacity: 0.7 }}>Recommended action</div>
              <strong style={{ color: "#1769d1", display: "block", marginBottom: "10px" }}>Investigate</strong>
              <button style={secondaryButton} onClick={() => navigate("/review-queue")}>Open in Review Center</button>
            </div>
          </div>
        </div>
      ) : null}

      <div className="panel" style={{ overflowX: "auto" }}>
        {items.length === 0 ? (
          <div className="state">
            {isRisk
              ? "No risk assessments recorded for the current reconciliation run."
              : "No high-severity anomalies detected for this reconciliation run."}
          </div>
        ) : (
          <table style={{ width: "100%", minWidth: "760px", borderCollapse: "collapse" }}>
            <thead>
              <tr>
                {["Transaction", isRisk ? "Risk Score" : "Score", "Level", "Reason", "Risk Factors", "Recommended Action"].map((heading) => (
                  <th key={heading} style={tableHeader}>{heading}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {items.map((item, index) => {
                const factors = isRisk ? item.risk_factors : [item.evidence];
                return (
                  <tr key={`${item.transaction_id}-${index}`}>
                    <td style={tableCell}><strong>{item.transaction_id}</strong></td>
                    <td style={tableCell}>{Number(isRisk ? item.risk_score : item.score || 0).toFixed(0)}/100</td>
                    <td style={tableCell}><StatusBadge status={isRisk ? item.risk_level : item.severity} /></td>
                    <td style={tableCell}>{item.reason || "—"}</td>
                    <td style={tableCell}>{Array.isArray(factors) ? factors.filter(Boolean).join(", ") || "—" : factors || "—"}</td>
                    <td style={tableCell}>{isRisk ? "Review supporting evidence before approval." : "Investigate the transaction and confirm the control evidence."}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </>
  );
}

function CfoCommandCenter() {
  const [report, setReport] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const navigate = useNavigate();

  async function loadReport() {
    setLoading(true);
    setError("");
    try {
      setReport(await apiGet("/reports/cfo"));
    } catch (err) {
      console.error(err);
      setError("Unable to load the CFO command center.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadReport();
    window.addEventListener("reconciliation:completed", loadReport);
    return () => window.removeEventListener("reconciliation:completed", loadReport);
  }, []);

  if (loading) return <div className="state">Loading CFO command center...</div>;
  if (error) return <div className="state"><p>{error}</p><button type="button" onClick={loadReport}>Retry</button></div>;

  const metrics = report?.metrics || {};
  const reconciliation = metrics.reconciliation || {};
  const financial = metrics.financial || {};
  const trend = Array.isArray(report?.cash_flow_trend) ? report.cash_flow_trend : [];
  const expenses = Array.isArray(report?.expense_breakdown) ? report.expense_breakdown : [];
  const riskDistribution = metrics.risk_distribution || {};
  const riskExposure = Number(reconciliation.variance || 0);
  const unresolved = Number(reconciliation.exceptions || 0);
  const riskStatus = Number(metrics.high_risk || 0) > 0 ? "Attention required" : "Within current run";
  const health = Number(reconciliation.match_rate || 0);
  const moneyValue = (key: string, fallback: number) =>
    financial[key]?.available ? Number(financial[key].value || 0) : fallback;
  const revenue = moneyValue("revenue", Number(metrics.revenue || 0));
  const expense = moneyValue("expenses", Number(metrics.expenses || 0));
  const netPosition = Number(metrics.net_profit || 0);
  const netPositionAvailable = Boolean(financial?.net_profit?.available);
  const hasTrend = trend.length > 0;
  const severity = (danger: boolean, warning: boolean) => danger ? "danger" : warning ? "warning" : "positive";
  const kpis = [
    { label: "Revenue", value: financial.revenue?.available ? currency(revenue) : "Unavailable", detail: financial.revenue?.available ? "Current run data" : "Not in the current run's source schema", tone: severity(revenue < 0, !financial.revenue?.available) },
    { label: "Expenses", value: financial.expenses?.available ? currency(expense) : "Unavailable", detail: financial.expenses?.available ? "Current run data" : "Not in the current run's source schema", tone: severity(expense > revenue && revenue > 0, !financial.expenses?.available) },
    { label: "Net position", value: netPositionAvailable ? currency(netPosition) : "Unavailable", detail: netPositionAvailable ? (netPosition >= 0 ? "Positive position" : "Negative position") : "Not in the current run's source schema", tone: severity(netPosition < 0, !netPositionAvailable) },
    { label: "Risk exposure", value: currency(riskExposure), detail: `${Number(metrics.high_risk || 0)} high-risk items`, tone: severity(Number(metrics.high_risk || 0) > 0, riskExposure > 0) },
    { label: "Reconciliation health", value: `${health.toFixed(1)}%`, detail: `${unresolved} unresolved`, tone: severity(health < 90, health < 98) },
  ];
  const attention = [
    Number(metrics.high_risk || 0) > 0 ? { tone: "danger", title: `${metrics.high_risk} high-risk transaction${metrics.high_risk === 1 ? "" : "s"}`, detail: "Review deterministic risk assessments before approval.", amount: `${metrics.high_risk} item${metrics.high_risk === 1 ? "" : "s"}`, action: "Open risk", onClick: () => navigate("/risk-assessment") } : null,
    unresolved > 0 ? { tone: "warning", title: `${unresolved} unresolved reconciliation item${unresolved === 1 ? "" : "s"}`, detail: "Exceptions remain in the current reconciliation run.", amount: `${unresolved} item${unresolved === 1 ? "" : "s"}`, action: "Open review queue", onClick: () => navigate("/review-queue") } : null,
    Number(metrics.largest_variance || 0) > 0 ? { tone: "warning", title: "Largest variance requires review", detail: "The current run contains a material reconciliation variance.", amount: currency(Number(metrics.largest_variance || 0)), action: "Open reconciliation", onClick: () => navigate("/reconciliation") } : null,
  ].filter(Boolean) as any[];

  const num = (value: any) => {
    const number = Number(value);
    return Number.isFinite(number) ? number : 0;
  };
  const anomalies = report?.anomalies || {};
  const anomalyItems = Array.isArray(anomalies.recent) ? anomalies.recent : [];
  const reviewWorkload = report?.review_workload || {};
  const reviewByStatus = reviewWorkload.by_status || {};
  const alertsList = Array.isArray(report?.alerts) ? report.alerts : [];
  const forecastBlock = report?.forecast || {};
  const forecastSeries = forecastBlock.series || {};
  const scenarioBlock = report?.scenario_insights || {};
  const scenarioRows = Array.isArray(scenarioBlock.reference_scenarios) ? scenarioBlock.reference_scenarios : [];
  const auditItems = Array.isArray(report?.audit_trail) ? report.audit_trail : [];

  return (
    <div className="cfo-command-center">
      <header>
        <div><h1>CFO Command Center</h1><p className="cfo-subtitle">Current financial position, control health, and decisions requiring attention.</p></div>
        <button type="button" style={secondaryButton} onClick={loadReport}>Refresh</button>
      </header>

      <section className="cfo-kpis" aria-label="Executive KPIs">
        {kpis.map((kpi) => <div className={`cfo-kpi ${kpi.tone}`} key={kpi.label}><span>{kpi.label}</span><strong>{kpi.value}</strong><small>{kpi.detail}</small></div>)}
      </section>

      <section className="cfo-chart-grid">
        <div className="panel cfo-chart-panel"><div className="cfo-panel-heading"><div><h2>Revenue vs expenses</h2><p>Grouped by transaction date</p></div></div>{hasTrend ? <ResponsiveContainer width="100%" height={250}><LineChart data={trend}><CartesianGrid vertical={false} stroke="#e8edf3" /><XAxis dataKey="date" tickLine={false} axisLine={false} tick={{ fontSize: 11 }} /><YAxis tickLine={false} axisLine={false} tick={{ fontSize: 11 }} tickFormatter={(value: any) => formatChartMoney(value)} /><Tooltip formatter={(value: any) => [currency(Number(value)), "Amount"]} /><Legend /><Line type="monotone" dataKey="revenue" name="Revenue" stroke="#18805b" strokeWidth={3} dot={false} /><Line type="monotone" dataKey="expenses" name="Expenses" stroke="#c2413b" strokeWidth={3} dot={false} /></LineChart></ResponsiveContainer> : <div className="cfo-empty">No dated transaction data is available for this chart.</div>}</div>
        <div className="panel cfo-chart-panel"><div className="cfo-panel-heading"><div><h2>Cash flow trend</h2><p>Revenue, expenses, and net cash flow</p></div></div>{hasTrend ? <ResponsiveContainer width="100%" height={250}><AreaChart data={trend}><CartesianGrid vertical={false} stroke="#e8edf3" /><XAxis dataKey="date" tickLine={false} axisLine={false} tick={{ fontSize: 11 }} /><YAxis tickLine={false} axisLine={false} tick={{ fontSize: 11 }} tickFormatter={(value: any) => formatChartMoney(value)} /><Tooltip formatter={(value: any) => [currency(Number(value)), "Amount"]} /><Area type="monotone" dataKey="net_cash_flow" name="Net cash flow" stroke="#1769d1" fill="#dbeafe" strokeWidth={2} /><Line type="monotone" dataKey="revenue" name="Revenue" stroke="#18805b" dot={false} /><Line type="monotone" dataKey="expenses" name="Expenses" stroke="#c2413b" dot={false} /></AreaChart></ResponsiveContainer> : <div className="cfo-empty">No dated transaction data is available for this chart.</div>}</div>
      </section>

      <section className="cfo-chart-grid">
        <div className="panel cfo-chart-panel"><div className="cfo-panel-heading"><div><h2>Risk distribution</h2><p>Current reconciliation run</p></div></div><div className="cfo-distribution">{[["LOW", "Low risk", "#18805b"], ["MEDIUM", "Medium risk", "#c27a16"], ["HIGH", "High risk", "#c2413b"]].map(([key, label, color]) => <div className="cfo-distribution-row" key={key}><span><i style={{ background: color }} />{label}</span><strong>{Number(riskDistribution[key] || 0) + (key === "HIGH" ? Number(riskDistribution.CRITICAL || 0) : 0)}</strong></div>)}</div></div>
        <div className="panel cfo-chart-panel"><div className="cfo-panel-heading"><div><h2>Reconciliation health</h2><p>Current run outcome</p></div></div><div className="cfo-health"><div className="cfo-health-ring" style={{ background: `conic-gradient(#18805b ${health}%, #e8edf3 0)` }}><div><strong>{health.toFixed(1)}%</strong><small>matched</small></div></div><div className="cfo-health-legend"><span><i className="matched" />Matched <b>{Number(reconciliation.matched || 0)}</b></span><span><i className="partial" />Partial <b>{Number(reconciliation.partial || 0)}</b></span><span><i className="unmatched" />Unmatched <b>{Number(reconciliation.unmatched || 0)}</b></span></div></div></div>
        <div className="panel cfo-chart-panel"><div className="cfo-panel-heading"><div><h2>Expense breakdown</h2><p>Actual expense types</p></div></div>{expenses.length ? <div className="cfo-bars">{expenses.map((item: any) => <div className="cfo-bar-row" key={item.type}><div><span>{item.type}</span><strong>{currency(item.amount)}</strong></div><div className="cfo-bar-track"><i style={{ width: `${Math.min(100, Number(item.amount) / Math.max(...expenses.map((expenseItem: any) => Number(expenseItem.amount)), 1) * 100)}%` }} /></div></div>)}</div> : <div className="cfo-empty">No expense categories are available.</div>}</div>
      </section>

      <section className="cfo-attention"><div className="cfo-section-heading"><div><h2>CFO attention required</h2><p>Prioritized from current risk and reconciliation data.</p></div><button type="button" style={secondaryButton} onClick={() => navigate("/analytics")}>Open analytics</button></div>{attention.length ? <div className="cfo-issues">{attention.map((issue) => <div className={`cfo-issue ${issue.tone}`} key={issue.title}><div className="cfo-issue-marker" /><div className="cfo-issue-copy"><strong>{issue.title}</strong><span>{issue.detail}</span></div><b>{issue.amount}</b><button type="button" style={secondaryButton} onClick={issue.onClick}>{issue.action}</button></div>)}</div> : <div className="cfo-empty">No unresolved control issues are recorded for the current data.</div>}</section>

      <section className="cfo-chart-grid">
        <div className="panel cfo-chart-panel"><div className="cfo-panel-heading"><div><h2>Independent anomalies</h2><p>Statistical and control signals from the current run</p></div></div>{anomalyItems.length ? <div>{anomalyItems.slice(0, 6).map((item: any) => <div className="cfo-bar-row" key={`${item.transaction_id}-${item.score}`}><div><span>{item.transaction_id}</span><strong>{item.severity} · {num(item.score).toFixed(0)}/100</strong></div><div className="cfo-bar-track"><i style={{ width: `${Math.min(100, num(item.score))}%` }} /></div><small style={{ color: "#64748b", fontSize: 12 }}>{item.reason}</small></div>)}</div> : <div className="cfo-empty">No independent anomalies are recorded for the current run.</div>}</div>
        <div className="panel cfo-chart-panel"><div className="cfo-panel-heading"><div><h2>Review workload</h2><p>Items requiring a human decision</p></div></div><div className="cfo-health"><div className="cfo-health-ring" style={{ background: `conic-gradient(#c2413b ${Math.min(100, num(reviewWorkload.total) ? num(reviewWorkload.attention) / num(reviewWorkload.total) * 100 : 0)}%, #e8edf3 0)` }}><div><strong>{num(reviewWorkload.attention)}</strong><small>attention</small></div></div><div className="cfo-health-legend"><span><i className="matched" />Open <b>{num(reviewWorkload.open)}</b></span><span><i className="unmatched" />Total <b>{num(reviewWorkload.total)}</b></span></div></div>{Object.keys(reviewByStatus).length ? <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginTop: 10 }}>{Object.entries(reviewByStatus).map(([status, count]: any) => <span key={status} style={{ padding: "4px 10px", borderRadius: 12, background: "#f1f5f9", fontSize: 12 }}>{status}: {count}</span>)}</div> : null}</div>
        <div className="panel cfo-chart-panel"><div className="cfo-panel-heading"><div><h2>Alerts & control</h2><p>Deterministic control signals</p></div></div>{alertsList.length ? alertsList.map((alert: any, index: number) => <div key={index} style={{ display: "flex", gap: 10, alignItems: "center", padding: "10px 12px", marginBottom: 8, borderRadius: 10, background: alert.severity === "HIGH" ? "#fef2f2" : "#fffbeb", border: `1px solid ${alert.severity === "HIGH" ? "#fecaca" : "#fde68a"}` }}><b style={{ color: alert.severity === "HIGH" ? "#b91c1c" : "#b45309", fontSize: 12 }}>{alert.severity}</b><span style={{ fontSize: 13, color: "#334155" }}>{alert.message}</span></div>) : <div className="cfo-empty">No control alerts are currently active.</div>}</div>
      </section>

      <section className="cfo-chart-grid">
        <div className="panel cfo-chart-panel"><div className="cfo-panel-heading"><div><h2>Financial outlook</h2><p>30-day deterministic baseline (no fabricated confidence)</p></div></div>{forecastBlock.available === false ? <div className="cfo-empty">{forecastBlock.message || "Forecast unavailable for the current data."}</div> : <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))", gap: 10 }}>{["revenue", "expenses", "refunds", "fees"].map((key) => { const series = forecastSeries[key]; return <div key={key} style={{ padding: 12, borderRadius: 10, background: "#f8fafc", border: "1px solid #e7edf5" }}><small style={{ textTransform: "capitalize", fontSize: 12 }}>{key}</small><strong style={{ display: "block", fontSize: 16, marginTop: 4 }}>{series && series.available ? currency(num(series.forecast_total)) : "Unavailable"}</strong><small style={{ color: "#94a3b8", fontSize: 11 }}>{series && series.available ? `${series.historical_days_observed} days observed` : (series && series.reason) || "No dated data"}</small></div>; })}</div>}{forecastBlock.method ? <p style={{ fontSize: 12, opacity: 0.6, margin: "10px 0 0" }}>{forecastBlock.method}</p> : null}</div>
        <div className="panel cfo-chart-panel"><div className="cfo-panel-heading"><div><h2>Scenario insights</h2><p>Reference simulations on current data</p></div></div>{scenarioRows.length ? scenarioRows.map((row: any) => <div className="cfo-bar-row" key={row.label}><div><span>{row.label}</span><small style={{ display: "block", opacity: 0.6 }}>{row.description}</small></div><strong>{currency(num(row.projected_profit))}</strong></div>) : <div className="cfo-empty">No reference scenarios are available.</div>}{scenarioBlock.note ? <p style={{ fontSize: 12, opacity: 0.6, margin: "10px 0 0" }}>{scenarioBlock.note}</p> : null}</div>
      </section>

      <section className="panel"><div className="cfo-panel-heading"><div><h2>Audit / control trail</h2><p>Traceable to backend control and audit data</p></div></div>{auditItems.length ? <div style={{ maxHeight: 260, overflowY: "auto" }}>{auditItems.map((entry: any, index: number) => <div key={index} style={{ display: "flex", gap: 12, padding: "10px 0", borderBottom: "1px solid #eef2f7", fontSize: 13, alignItems: "center" }}><span style={{ minWidth: 180, fontWeight: 700, color: "#1e56a0" }}>{entry.action}</span><span style={{ color: "#475569", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{String(entry.detail || "")}</span><span style={{ color: "#94a3b8", marginLeft: "auto", whiteSpace: "nowrap" }}>{entry.created_at ? new Date(entry.created_at).toLocaleString() : ""}</span></div>)}</div> : <div className="cfo-empty">No audit events are recorded yet.</div>}</section>

      <section className="cfo-takeaway"><div><span className="cfo-eyebrow">CFO TAKEAWAY</span><h2>Decision-ready summary</h2><div className="cfo-takeaway-metrics"><span>Revenue <b>{financial.revenue?.available ? currency(revenue) : "Unavailable"}</b></span><span>Expenses <b>{financial.expenses?.available ? currency(expense) : "Unavailable"}</b></span><span>Risk exposure <b>{currency(riskExposure)}</b></span><span>Unresolved <b>{unresolved}</b></span></div><p><strong>DECISION:</strong> {unresolved || Number(metrics.high_risk || 0) ? "Prioritize unresolved reconciliation and risk items before approving the current financial position." : "The current data shows no unresolved control issues requiring immediate escalation."}</p></div><button type="button" style={primaryButton} onClick={() => navigate("/reconciliation")}>Review current controls</button></section>
    </div>
  );
}

function Page({
  title,
}: {
  title: string;
}) {
  const [data, setData] =
    useState<any>(null);

  useEffect(() => {
    let endpoint =
      "/analytics";

    if (
      title ===
      "Transactions"
    ) {
      endpoint =
        "/transactions";
    } else if (
      title ===
      "Risk Assessment"
    ) {
      endpoint =
        "/risk";
    } else if (
      title ===
      "Anomaly Detection"
    ) {
      endpoint =
        "/anomalies";
    } else if (
      title ===
      "Audit Logs"
    ) {
      endpoint =
        "/audit";
    }

    apiGet(endpoint)
      .then(setData)
      .catch(() =>
        setData({
          error:
            "Unable to load data",
        })
      );
  }, [title]);

  return (
    <>
      <header>
        <h1>
          {title}
        </h1>

        <span>
          Finance Controller
        </span>
      </header>

      <div className="panel">
        <pre>
          {JSON.stringify(
            data,
            null,
            2
          )}
        </pre>
      </div>
    </>
  );
}

/* =========================================================
   COPILOT
========================================================= */

function Copilot() {
  const [question, setQuestion] = useState(
    "Show high-risk transactions"
  );

  const [answer, setAnswer] = useState("");
  const [loading, setLoading] = useState(false);
  const [conversation, setConversation] =
    useState<{ role: string; content: string }[]>(
      []
    );

  let userRole = "";

  try {
    const stored = localStorage.getItem("user");

    if (stored) {
      userRole = JSON.parse(stored).role || "";
    }
  } catch {
    userRole = "";
  }

  const quickQuestions = [
    "What should I do first?",
    "Which exceptions should I review first?",
    "What is the largest reconciliation exception?",
    "What are today's most urgent finance issues?",
    "Why is the reconciliation rate below 100%?",
    "Show me the highest-risk transactions",
    "Summarize the current reconciliation run",
    "What changed in the latest upload?",
  ];

  async function askCopilot(customQuestion?: string) {
    const finalQuestion =
      customQuestion !== undefined
        ? customQuestion
        : question;

    if (!finalQuestion.trim()) return;

    setQuestion(finalQuestion);
    setLoading(true);
    setAnswer("");

    const nextConversation = [
      ...conversation,
      { role: "user", content: finalQuestion },
    ];
    setConversation(nextConversation);

    try {
      const token =
        localStorage.getItem("token");

      const response = await fetch(
        `${API}/copilot`,
        {
          method: "POST",

          headers: {
            "Content-Type":
              "application/json",

            Accept:
              "application/json",

            ...(token
              ? {
                  Authorization:
                    `Bearer ${token}`,
                }
              : {}),
          },

          body: JSON.stringify({
            question: finalQuestion,
            // Send only the most recent turns for follow-up context.
            history:
              nextConversation
                .slice(-8)
                .map((turn) => ({
                  role: turn.role,
                  content: turn.content,
                })),
          }),
        }
      );

      const data =
        await response.json();

      if (!response.ok) {
        const failure =
          data.detail ||
          "Copilot request failed.";
        setAnswer(failure);
        setConversation([
          ...nextConversation,
          { role: "assistant", content: failure },
        ]);

        return;
      }

      const result =
        data.answer ||
        "No answer returned.";
      setAnswer(result);
      setConversation([
        ...nextConversation,
        { role: "assistant", content: result },
      ]);
    } catch (error) {
      console.error(error);

      const failure =
        "Unable to connect to Copilot.";
      setAnswer(failure);
      setConversation([
        ...nextConversation,
        { role: "assistant", content: failure },
      ]);
    } finally {
      setLoading(false);
    }
  }

  function clearConversation() {
    setConversation([]);
    setAnswer("");
  }

  return (
    <>
      <header>
        <div>
          <h1>
            Finance Copilot
          </h1>

          <span>
            Ask about reconciliation, risk, anomalies,
            exceptions and finance operations.
          </span>

          {userRole && (
            <span
              style={{
                display: "inline-block",
                marginTop: "8px",
                padding: "4px 10px",
                borderRadius: "14px",
                background: "#eef6ff",
                border: "1px solid #cfe4fb",
                color: "#1e56a0",
                fontSize: "12px",
                fontWeight: 600,
              }}
            >
              Personalized to your role: {userRole}
            </span>
          )}
        </div>
      </header>

      <div className="panel">

        <div
          style={{
            marginBottom: "18px",
          }}
        >
          <h2
            style={{
              marginBottom: "6px",
            }}
          >
            Ask your finance controller
          </h2>

          <p
            style={{
              margin: 0,
              opacity: 0.7,
            }}
          >
            Every answer is grounded in the current
            reconciliation run's real data.
          </p>
        </div>

        <div
          style={{
            margin: "2px 0 6px",
          }}
        >
          <h3
            style={{
              margin: "0 0 12px",
              fontSize: "13px",
              fontWeight: 700,
              textTransform: "uppercase",
              letterSpacing: "0.05em",
              color: "#334e68",
            }}
          >
            Suggested questions
          </h3>

          <div
            style={{
              display: "flex",
              flexWrap: "wrap",
              gap: "10px",
              marginBottom: "20px",
            }}
          >
            {quickQuestions.map(
              (item) => (
                <button
                  key={item}
                  type="button"
                  onClick={() =>
                    askCopilot(item)
                  }
                  disabled={loading}
                  style={{
                    padding:
                      "10px 14px",
                    borderRadius:
                      "10px",
                    border:
                      "1px solid #c9dcf5",
                    background:
                      "#f2f7fe",
                    color:
                      "#14467e",
                    fontSize:
                      "14px",
                    fontWeight: 600,
                    lineHeight: 1.35,
                    textAlign: "left",
                    cursor:
                      loading
                        ? "not-allowed"
                        : "pointer",
                    boxShadow:
                      "0 1px 2px rgba(22,58,90,0.05)",
                    maxWidth:
                      "340px",
                  }}
                >
                  {item}
                </button>
              )
            )}
          </div>
        </div>

        <textarea
          value={question}
          onChange={(event) =>
            setQuestion(
              event.target.value
            )
          }
          onKeyDown={(event) => {
            if (
              event.key === "Enter" &&
              (event.ctrlKey ||
                event.metaKey)
            ) {
              event.preventDefault();
              askCopilot();
            }
          }}
          placeholder="Ask a finance question..."
          style={{
            width: "100%",
            minHeight: "120px",
            resize: "vertical",
            boxSizing: "border-box",
          }}
        />

        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "12px",
            marginTop: "12px",
          }}
        >
          <button
            onClick={() =>
              askCopilot()
            }
            disabled={
              loading ||
              !question.trim()
            }
          >
            {loading
              ? "Analyzing..."
              : "Ask Copilot"}
          </button>

          <span
            style={{
              fontSize: "12px",
              opacity: 0.6,
            }}
          >
            Ctrl + Enter to ask
          </span>

          {conversation.length > 0 && (
            <button
              type="button"
              onClick={clearConversation}
              disabled={loading}
              style={{
                marginLeft: "auto",
                background: "transparent",
                border: "1px solid #c9dcf5",
                color: "#14467e",
                cursor: loading
                  ? "not-allowed"
                  : "pointer",
              }}
            >
              Clear conversation
            </button>
          )}
        </div>

        {loading && (
          <div
            className="answer"
            style={{
              marginTop: "20px",
            }}
          >
            <strong>
              Copilot is analyzing your
              finance data...
            </strong>

            <p>
              Checking available metrics,
              risks, and exceptions.
            </p>
          </div>
        )}

        {!loading && conversation.length > 0 && (
          <div
            style={{
              marginTop: "20px",
            }}
          >
            <div
              style={{
                fontWeight: 700,
                marginBottom: "10px",
              }}
            >
              Conversation
            </div>

            {conversation.map(
              (turn, index) => (
                <div
                  key={index}
                  className="answer"
                  style={{
                    marginBottom: "12px",
                    whiteSpace: "pre-wrap",
                    lineHeight: 1.6,
                  }}
                >
                  <div
                    style={{
                      fontWeight: 700,
                      marginBottom: "6px",
                    }}
                  >
                    {turn.role === "user"
                      ? "You"
                      : "AI Controller"}
                  </div>

                  {turn.content}
                </div>
              )
            )}
          </div>
        )}

      </div>
    </>
  );
}

/* =========================================================
   OVERVIEW HELPERS
========================================================= */

function formatChartMoney(value: any) {
  const amount = Number(value || 0);
  const sign = amount < 0 ? "-" : "";
  const abs = Math.abs(amount);

  if (abs >= 10000000) {
    return `${sign}₹${(abs / 10000000).toFixed(2)} Cr`;
  }

  if (abs >= 100000) {
    return `${sign}₹${(abs / 100000).toFixed(2)} L`;
  }

  if (abs >= 1000) {
    return `${sign}₹${Math.round(abs).toLocaleString("en-IN")}`;
  }

  return `${sign}₹${abs.toFixed(2)}`;
}

function OverviewKpi({
  label,
  value,
  hint,
  accent,
}: {
  label: string;
  value: React.ReactNode;
  hint?: React.ReactNode;
  accent?: string;
}) {
  return (
    <div className="card">
      <small>{label}</small>

      <strong
        style={{
          ...(accent
            ? { color: accent }
            : {}),
        }}
      >
        {value}
      </strong>

      {hint ? (
        <span
          style={{
            display: "block",
            marginTop: "8px",
            color: "#64748b",
            fontSize: "12px",
          }}
        >
          {hint}
        </span>
      ) : null}
    </div>
  );
}

function OverviewChartPanel({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
}) {
  return (
    <div
      className="panel"
      style={{
        marginTop: 0,
        display: "flex",
        flexDirection: "column",
        height: "100%",
      }}
    >
      <h2
        style={{
          margin: "0 0 4px",
          fontSize: "17px",
        }}
      >
        {title}
      </h2>

      {subtitle ? (
        <p
          style={{
            margin: "0 0 16px",
            color: "#64748b",
            fontSize: "13px",
          }}
        >
          {subtitle}
        </p>
      ) : null}

      <div style={{ flex: 1 }}>
        {children}
      </div>
    </div>
  );
}

/* =========================================================
   RECONCILIATION STATUS CHART (DONUT)
========================================================= */

function ReconciliationStatusChart({
  matched,
  exceptions,
  total,
}: {
  matched: number;
  exceptions: number;
  total: number;
}) {
  const rate = total > 0 ? (matched / total) * 100 : 0;

  const data = [
    {
      name: "Matched",
      value: matched,
      color: "#2563eb",
    },
    {
      name: "Exceptions",
      value: exceptions,
      color: "#ef4444",
    },
  ].filter((entry) => entry.value > 0);

  if (total <= 0) {
    return (
      <div
        style={{
          color: "#64748b",
          fontSize: "13px",
          padding: "14px 4px",
        }}
      >
        The current reconciliation run contains no
        records to chart.
      </div>
    );
  }

  const share = (value: number) =>
    total > 0
      ? ((value / total) * 100).toFixed(1)
      : "0.0";

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: "8px",
        flexWrap: "wrap",
      }}
    >
      <div
        style={{
          width: 196,
          height: 196,
          position: "relative",
          flexShrink: 0,
        }}
      >
        <ResponsiveContainer
          width="100%"
          height="100%"
        >
          <PieChart>
            <Pie
              data={data}
              dataKey="value"
              nameKey="name"
              innerRadius={64}
              outerRadius={92}
              paddingAngle={
                data.length > 1 ? 2 : 0
              }
              strokeWidth={0}
            >
              {data.map((entry) => (
                <Cell
                  key={entry.name}
                  fill={entry.color}
                />
              ))}
            </Pie>
            <Tooltip
              formatter={(value: any) =>
                Number(value || 0).toLocaleString(
                  "en-IN"
                )
              }
            />
          </PieChart>
        </ResponsiveContainer>

        <div
          style={{
            position: "absolute",
            inset: 0,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            flexDirection: "column",
            pointerEvents: "none",
          }}
        >
          <strong
            style={{
              fontSize: "24px",
              color: "#17324d",
            }}
          >
            {rate.toFixed(1)}%
          </strong>

          <span
            style={{
              fontSize: "11px",
              color: "#64748b",
            }}
          >
            matched
          </span>
        </div>
      </div>

      <div
        style={{
          flex: 1,
          minWidth: 160,
        }}
      >
        {[
          {
            name: "Matched",
            value: matched,
            color: "#2563eb",
          },
          {
            name: "Exceptions",
            value: exceptions,
            color: "#ef4444",
          },
        ].map((entry) => (
          <div
            key={entry.name}
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              gap: "12px",
              padding: "8px 0",
              borderBottom:
                "1px solid #eef2f7",
            }}
          >
            <span
              style={{
                display: "flex",
                alignItems: "center",
                gap: "8px",
                fontSize: "13px",
                color: "#475569",
              }}
            >
              <span
                style={{
                  width: 10,
                  height: 10,
                  borderRadius: 3,
                  background:
                    entry.color,
                  display:
                    "inline-block",
                }}
              />
              {entry.name}
            </span>

            <span
              style={{
                fontWeight: 700,
                fontSize: "13px",
              }}
            >
              {entry.value.toLocaleString(
                "en-IN"
              )}
              <span
                style={{
                  fontWeight: 500,
                  color: "#94a3b8",
                  marginLeft: "6px",
                  fontSize: "12px",
                }}
              >
                {share(entry.value)}%
              </span>
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

/* =========================================================
   RISK DISTRIBUTION CHART
========================================================= */

function RiskDistributionChart({
  distribution,
}: {
  distribution?: any;
}) {
  const levels = [
    {
      key: "LOW",
      label: "Low",
      color: "#16a34a",
    },
    {
      key: "MEDIUM",
      label: "Medium",
      color: "#d97706",
    },
    {
      key: "HIGH",
      label: "High",
      color: "#ea580c",
    },
    {
      key: "CRITICAL",
      label: "Critical",
      color: "#dc2626",
    },
  ];

  const dist = distribution || {};

  const data = levels.map((level) => ({
    name: level.label,
    value: Number(
      dist[level.key] || 0
    ),
    color: level.color,
  }));

  const total = data.reduce(
    (sum, entry) => sum + entry.value,
    0
  );

  if (total === 0) {
    return (
      <div
        style={{
          color: "#64748b",
          fontSize: "13px",
          padding: "14px 4px",
        }}
      >
        No risk assessments were recorded
        for the current reconciliation run.
        Risk levels (Low / Medium / High /
        Critical) are all zero.
      </div>
    );
  }

  return (
    <ResponsiveContainer
      width="100%"
      height={240}
    >
      <BarChart
        data={data}
        margin={{
          top: 14,
          right: 12,
          left: -22,
          bottom: 0,
        }}
      >
        <CartesianGrid
          vertical={false}
          stroke="#eef2f7"
        />
        <XAxis
          dataKey="name"
          tickLine={false}
          axisLine={false}
          tick={{
            fontSize: 12,
            fill: "#475569",
          }}
        />
        <YAxis
          allowDecimals={false}
          tickLine={false}
          axisLine={false}
          tick={{
            fontSize: 11,
            fill: "#94a3b8",
          }}
        />
        <Tooltip
          cursor={{ fill: "#f1f5f9" }}
        />
        <Bar
          dataKey="value"
          radius={[6, 6, 0, 0]}
          barSize={44}
        >
          {data.map((entry) => (
            <Cell
              key={entry.name}
              fill={entry.color}
            />
          ))}
          <LabelList
            dataKey="value"
            position="top"
            style={{
              fontSize: 13,
              fontWeight: 700,
              fill: "#334155",
            }}
          />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

/* =========================================================
   EXCEPTION / VARIANCE CHART
========================================================= */

function ExceptionBars({
  items,
}: {
  items: any[];
}) {
  const data = items.map((item) => ({
    name:
      item.transaction_id ||
      item.reference ||
      item.id ||
      "Unknown",
    variance: Number(
      item.variance || 0
    ),
  }));

  const height = Math.max(
    200,
    Math.min(430, data.length * 40 + 40)
  );

  return (
    <ResponsiveContainer
      width="100%"
      height={height}
    >
      <BarChart
        data={data}
        layout="vertical"
        margin={{
          top: 4,
          right: 24,
          bottom: 4,
          left: 8,
        }}
      >
        <CartesianGrid
          horizontal={false}
          stroke="#eef2f7"
        />
        <XAxis type="number" hide />
        <YAxis
          type="category"
          dataKey="name"
          width={122}
          tickLine={false}
          axisLine={false}
          tick={{
            fontSize: 12,
            fill: "#475569",
          }}
          tickFormatter={(value: string) =>
            value.length > 18
              ? value.slice(0, 16) + "…"
              : value
          }
        />
        <Tooltip
          formatter={(value: any) => [
            currency(Number(value)),
            "Variance",
          ]}
        />
        <Bar
          dataKey="variance"
          fill="#2563eb"
          radius={[0, 4, 4, 0]}
          barSize={18}
        >
          <LabelList
            dataKey="variance"
            position="right"
            formatter={(value: any) =>
              formatChartMoney(value)
            }
            style={{
              fontSize: 12,
              fontWeight: 600,
              fill: "#334155",
            }}
          />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

/* =========================================================
   OVERVIEW (FINANCE CONTROLLER DASHBOARD)
========================================================= */

function Dashboard() {
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    const loadDashboard = () =>
      apiGet("/dashboard")
        .then(setData)
        .catch((err) => {
          console.error(err);
          setError(
            "Unable to load dashboard data."
          );
        });

    loadDashboard();

    window.addEventListener(
      "reconciliation:completed",
      loadDashboard
    );

    return () =>
      window.removeEventListener(
        "reconciliation:completed",
        loadDashboard
      );
  }, []);

  if (error) {
    return (
      <div className="state">
        {error}
      </div>
    );
  }

  if (!data) {
    return (
      <div className="state">
        Loading dashboard…
      </div>
    );
  }

  const rec = data.reconciliation || {};
  const run = data.current_run;
  const hasRun = Boolean(
    run && rec && rec.run_id
  );

  const total = Number(rec.total || 0);
  const matched = Number(rec.matched || 0);
  const exceptions = Number(
    rec.exceptions || 0
  );
  const matchRate = Number(
    rec.match_rate || 0
  );
  const variance = Number(
    rec.variance || 0
  );

  const highRisk = Number(
    data.high_risk || 0
  );

  const riskDistribution =
    data.risk_distribution || {};

  const topExceptions = Array.isArray(
    data.top_exceptions
  )
    ? data.top_exceptions
    : [];

  const financial = data.financial || {};

  const metricList = [
    {
      key: "revenue",
      label: "Revenue",
    },
    {
      key: "expenses",
      label: "Expenses",
    },
    {
      key: "refunds",
      label: "Refunds",
    },
    {
      key: "fees",
      label: "Fees",
    },
    {
      key: "net_profit",
      label: "Net Profit",
    },
    {
      key: "cash_balance",
      label: "Cash",
    },
  ];

  const financialChartData = metricList
    .filter(
      (metric) =>
        financial[metric.key] &&
        financial[metric.key].available
    )
    .map((metric) => ({
      name: metric.label,
      value: Number(
        financial[metric.key].value || 0
      ),
    }));

  const financialColors: Record<
    string,
    string
  > = {
    Revenue: "#16a34a",
    Expenses: "#dc2626",
    Refunds: "#d97706",
    Fees: "#6366f1",
    "Net Profit": "#2563eb",
    Cash: "#0d9488",
  };

  const showFinancialComparison =
    financialChartData.length >= 2;

  const files =
    (run && run.files && run.files.length
      ? run.files
      : []) || [];

  const modeLabel =
    run && run.mode === "single_file"
      ? "Single-file run"
      : run && run.mode === "multi_file"
      ? "Multi-file run"
      : "Reconciliation run";

  return (
    <>
      {/* HEADER */}
      <header>
        <div>
          <h1>Finance Overview</h1>

          <p
            style={{
              margin: "6px 0 0",
              color: "#64748b",
              fontSize: "14px",
            }}
          >
            Current-run reconciliation, risk, and
            exception intelligence
          </p>
        </div>

        <span
          style={{
            padding: "8px 12px",
            borderRadius: "20px",
            background: hasRun
              ? "#eff6ff"
              : "#f1f5f9",
            color: hasRun
              ? "#2563eb"
              : "#64748b",
            fontSize: "13px",
            fontWeight: 600,
            whiteSpace: "nowrap",
          }}
        >
          {hasRun
            ? `● ${run.status || "COMPLETED"}`
            : "● No current run"}
        </span>
      </header>

      {!hasRun ? (
        <div
          className="panel"
          style={{
            textAlign: "center",
            padding: "56px 28px",
          }}
        >
          <div
            style={{
              width: 52,
              height: 52,
              borderRadius: "50%",
              background: "#eff6ff",
              display: "grid",
              placeItems: "center",
              margin: "0 auto 16px",
              fontSize: "24px",
            }}
          >
            📊
          </div>

          <h2
            style={{
              margin: "0 0 8px",
            }}
          >
            No reconciliation run available
          </h2>

          <p
            style={{
              margin: "0 auto 22px",
              maxWidth: 460,
              color: "#64748b",
              fontSize: "14px",
              lineHeight: 1.6,
            }}
          >
            Upload finance data to start a
            reconciliation run. Overview KPIs,
            charts, and financial metrics are then
            derived from that current run.
          </p>

          <Link
            to="/reconciliation"
            style={primaryButton}
          >
            Upload finance data
          </Link>
        </div>
      ) : (
        <>
          {/* CURRENT RUN INDICATOR */}
          <div
            className="panel"
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              gap: "18px",
              flexWrap: "wrap",
              padding: "16px 20px",
            }}
          >
            <div style={{ minWidth: 220 }}>
              <small
                style={{
                  display: "block",
                  color: "#718096",
                  textTransform: "uppercase",
                  letterSpacing: "0.05em",
                  fontSize: "11px",
                  fontWeight: 700,
                  marginBottom: "4px",
                }}
              >
                Current reconciliation run
              </small>

              <div
                style={{
                  display: "flex",
                  flexWrap: "wrap",
                  gap: "8px",
                }}
              >
                {files.length ? (
                  files.map((file: string) => (
                    <span
                      key={file}
                      style={{
                        display:
                          "inline-flex",
                        alignItems:
                          "center",
                        gap: "6px",
                        padding:
                          "6px 10px",
                        borderRadius:
                          "8px",
                        background:
                          "#eff6ff",
                        border:
                          "1px solid #dbeafe",
                        color:
                          "#1d4ed8",
                        fontSize:
                          "12px",
                        fontWeight: 600,
                      }}
                    >
                      📄 {file}
                    </span>
                  ))
                ) : (
                  <span
                    style={{
                      fontSize: "14px",
                      fontWeight: 600,
                    }}
                  >
                    {modeLabel}
                  </span>
                )}
              </div>

              {run && run.created_at ? (
                <p
                  style={{
                    margin: "8px 0 0",
                    color: "#94a3b8",
                    fontSize: "12px",
                  }}
                >
                  {modeLabel} ·{" "}
                  {new Date(
                    run.created_at
                  ).toLocaleString()}
                </p>
              ) : null}
            </div>

            <div
              style={{
                display: "grid",
                gridTemplateColumns:
                  "repeat(auto-fit, minmax(110px, 1fr))",
                gap: "22px",
              }}
            >
              <div>
                <small
                  style={{
                    display: "block",
                    color: "#94a3b8",
                    fontSize: "11px",
                  }}
                >
                  Records
                </small>

                <strong
                  style={{
                    fontSize: "22px",
                  }}
                >
                  {total.toLocaleString(
                    "en-IN"
                  )}
                </strong>
              </div>

              <div>
                <small
                  style={{
                    display: "block",
                    color: "#94a3b8",
                    fontSize: "11px",
                  }}
                >
                  Matched
                </small>

                <strong
                  style={{
                    fontSize: "22px",
                    color: "#16a34a",
                  }}
                >
                  {matchRate.toFixed(1)}%
                </strong>
              </div>

              <div>
                <small
                  style={{
                    display: "block",
                    color: "#94a3b8",
                    fontSize: "11px",
                  }}
                >
                  Exceptions
                </small>

                <strong
                  style={{
                    fontSize: "22px",
                    color:
                      exceptions > 0
                        ? "#dc2626"
                        : "#16a34a",
                  }}
                >
                  {exceptions.toLocaleString(
                    "en-IN"
                  )}
                </strong>
              </div>
            </div>
          </div>

          {/* KPI CARDS */}
          <div
            className="grid"
            style={{ marginTop: "20px" }}
          >
            <OverviewKpi
              label="Total Transactions"
              value={total.toLocaleString(
                "en-IN"
              )}
              hint="Records in the current run"
            />

            <OverviewKpi
              label="Matched"
              value={matched.toLocaleString(
                "en-IN"
              )}
              hint="Transactions reconciled"
              accent="#16a34a"
            />

            <OverviewKpi
              label="Unresolved Exceptions"
              value={exceptions.toLocaleString(
                "en-IN"
              )}
              hint={
                exceptions > 0
                  ? "Require review"
                  : "All transactions matched"
              }
              accent={
                exceptions > 0
                  ? "#dc2626"
                  : "#16a34a"
              }
            />

            <OverviewKpi
              label="Match Rate"
              value={`${matchRate.toFixed(1)}%`}
              hint="Of current-run records"
              accent={
                matchRate >= 95
                  ? "#16a34a"
                  : matchRate >= 80
                  ? "#d97706"
                  : "#dc2626"
              }
            />

            <OverviewKpi
              label="Total Variance"
              value={currency(variance)}
              hint="Sum of absolute variances"
              accent={
                variance > 0
                  ? "#d97706"
                  : "#16a34a"
              }
            />

            <OverviewKpi
              label="High / Critical Risk"
              value={highRisk.toLocaleString(
                "en-IN"
              )}
              hint={
                highRisk > 0
                  ? "Transactions to review first"
                  : "No high-risk items detected"
              }
              accent={
                highRisk > 0
                  ? "#dc2626"
                  : "#16a34a"
              }
            />
          </div>

          {/* CHARTS */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns:
                "repeat(auto-fit, minmax(300px, 1fr))",
              gap: "16px",
              marginTop: "20px",
            }}
          >
            <OverviewChartPanel
              title="Reconciliation Status"
              subtitle="Current-run matched vs exceptions"
            >
              <ReconciliationStatusChart
                matched={matched}
                exceptions={exceptions}
                total={total}
              />
            </OverviewChartPanel>

            <OverviewChartPanel
              title="Risk Distribution"
              subtitle="Current-run risk assessments by level"
            >
              <RiskDistributionChart
                distribution={riskDistribution}
              />
            </OverviewChartPanel>
          </div>

          {/* LARGEST EXCEPTIONS */}
          {exceptions > 0 &&
          topExceptions.length > 0 ? (
            <div
              className="panel"
              style={{ marginTop: "20px" }}
            >
              <div
                style={{
                  display: "flex",
                  justifyContent:
                    "space-between",
                  alignItems: "flex-start",
                  gap: "16px",
                  flexWrap: "wrap",
                  marginBottom: "6px",
                }}
              >
                <div>
                  <h2
                    style={{
                      margin: "0 0 4px",
                      fontSize: "17px",
                    }}
                  >
                    Largest Exceptions
                  </h2>

                  <p
                    style={{
                      margin: 0,
                      color: "#64748b",
                      fontSize: "13px",
                    }}
                  >
                    Top {topExceptions.length} of{" "}
                    {exceptions} exceptions sorted
                    by absolute variance
                  </p>
                </div>

                <Link
                  to="/reconciliation"
                  style={secondaryButton}
                >
                  View full exception list
                </Link>
              </div>

              <ExceptionBars
                items={topExceptions}
              />
            </div>
          ) : null}

          {/* FINANCIAL SUMMARY */}
          <div
            className="panel"
            style={{ marginTop: "20px" }}
          >
            <h2
              style={{
                margin: "0 0 4px",
                fontSize: "17px",
              }}
            >
              Financial Summary
            </h2>

            <p
              style={{
                margin: "0 0 16px",
                color: "#64748b",
                fontSize: "13px",
              }}
            >
              Derived only from fields actually
              present in the uploaded data
            </p>

            {financialChartData.length === 0 ? (
              <div
                style={{
                  padding: "16px",
                  borderRadius: "10px",
                  background: "#f8fafc",
                  border:
                    "1px dashed #dbe5f2",
                  color: "#64748b",
                  fontSize: "14px",
                  lineHeight: 1.6,
                }}
              >
                Financial metrics are not available
                in the uploaded data. Revenue,
                expenses, refunds, fees, and profit
                figures are only shown when the
                current reconciliation dataset
                contains those fields.
              </div>
            ) : (
              <>
                {showFinancialComparison ? (
                  <div
                    style={{
                      marginBottom: "18px",
                    }}
                  >
                    <ResponsiveContainer
                      width="100%"
                      height={250}
                    >
                      <BarChart
                        data={financialChartData}
                        margin={{
                          top: 14,
                          right: 12,
                          left: 12,
                          bottom: 0,
                        }}
                      >
                        <CartesianGrid
                          vertical={false}
                          stroke="#eef2f7"
                        />
                        <XAxis
                          dataKey="name"
                          tickLine={false}
                          axisLine={false}
                          tick={{
                            fontSize: 12,
                            fill: "#475569",
                          }}
                        />
                        <YAxis
                          tickLine={false}
                          axisLine={false}
                          tick={{
                            fontSize: 11,
                            fill: "#94a3b8",
                          }}
                          tickFormatter={(
                            value: any
                          ) =>
                            formatChartMoney(
                              value
                            )
                          }
                        />
                        <Tooltip
                          formatter={(value: any) => [
                            currency(Number(value)),
                            "Amount",
                          ]}
                          cursor={{
                            fill: "#f1f5f9",
                          }}
                        />
                        <Bar
                          dataKey="value"
                          radius={[6, 6, 0, 0]}
                          barSize={46}
                        >
                          {financialChartData.map(
                            (entry) => (
                              <Cell
                                key={entry.name}
                                fill={
                                  financialColors[
                                    entry.name
                                  ] ||
                                  "#2563eb"
                                }
                              />
                            )
                          )}
                          <LabelList
                            dataKey="value"
                            position="top"
                            formatter={(
                              value: any
                            ) =>
                              formatChartMoney(
                                value
                              )
                            }
                            style={{
                              fontSize: 11,
                              fontWeight: 600,
                              fill: "#334155",
                            }}
                          />
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                ) : null}

                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns:
                      "repeat(auto-fit, minmax(170px, 1fr))",
                    gap: "12px",
                  }}
                >
                  {metricList.map((metric) => {
                    const item =
                      financial[metric.key];

                    if (!item || !item.available) {
                      return null;
                    }

                    const value = Number(
                      item.value || 0
                    );

                    const isNegative =
                      value < 0;

                    return (
                      <div
                        key={metric.key}
                        style={{
                          padding: "14px",
                          borderRadius: "10px",
                          background: "#f8fafc",
                          border:
                            "1px solid #e7edf5",
                        }}
                      >
                        <small
                          style={{
                            display: "block",
                            color: "#718096",
                            fontSize: "12px",
                          }}
                        >
                          {metric.label}
                        </small>

                        <strong
                          style={{
                            display: "block",
                            fontSize: "18px",
                            marginTop: "6px",
                            color: isNegative
                              ? "#dc2626"
                              : "#17324d",
                          }}
                        >
                          {currency(value)}
                        </strong>
                      </div>
                    );
                  })}

                  {metricList.some(
                    (metric) =>
                      !financial[metric.key] ||
                      !financial[metric.key]
                        .available
                  ) ? (
                    <div
                      style={{
                        padding: "14px",
                        borderRadius: "10px",
                        background: "#fffbf5",
                        border:
                          "1px dashed #f3e2c1",
                        color: "#a16207",
                        fontSize: "13px",
                        lineHeight: 1.5,
                      }}
                    >
                      Metrics not present in the
                      uploaded data are omitted —
                      no estimated or stale values
                      are shown.
                    </div>
                  ) : null}
                </div>
              </>
            )}
          </div>
        </>
      )}
    </>
  );
}

/* =========================================================
   PAGE LIST
========================================================= */

const pages = [
  "Transactions",
  "Settlements",
  "Refunds",
  "Fees",
  "Ledger",
  "Revenue",
  "Expenses",
  "Cash & Liquidity",
  "Financial Statements",
  "Ratio Analysis",
  "Budget vs Actual",
  "Forensic Analysis",
  "Alerts",
  "Policies & Controls",
  "Forecasting",
  "CFO Reports",
  "Security Center",
  "Settings",
];

/* =========================================================
   APP
========================================================= */

export default function App() {
  useLocation();

  const isLoggedIn =
    Boolean(
      localStorage.getItem(
        "token"
      )
    );

  return (
    <Routes>

      {/* =================================================
          LOGIN
      ================================================= */}

      <Route
        path="/login"
        element={
          isLoggedIn ? (
            <Navigate
              to="/"
              replace
            />
          ) : (
            <Login />
          )
        }
      />

      {/* =================================================
          DASHBOARD
      ================================================= */}

      <Route
        path="/"
        element={
          isLoggedIn ? (
            <Layout>
              <Dashboard />
            </Layout>
          ) : (
            <Navigate
              to="/login"
              replace
            />
          )
        }
      />

      {/* =================================================
          RECONCILIATION
      ================================================= */}

      <Route
        path="/reconciliation"
        element={
          isLoggedIn ? (
            <Layout>
              <Reconciliation />
            </Layout>
          ) : (
            <Navigate
              to="/login"
              replace
            />
          )
        }
      />

      {/* =================================================
          REVIEW CENTER
      ================================================= */}

      <Route
        path="/review-queue"
        element={
          isLoggedIn ? (
            <Layout>
              <ReviewQueue />
            </Layout>
          ) : (
            <Navigate
              to="/login"
              replace
            />
          )
        }
      />

      {/* =================================================
          COPILOT
      ================================================= */}

      <Route
        path="/finance-copilot"
        element={
          isLoggedIn ? (
            <Layout>
              <Copilot />
            </Layout>
          ) : (
            <Navigate
              to="/login"
              replace
            />
          )
        }
      />

      {/* =================================================
          OTHER PAGES
      ================================================= */}

      <Route
        path="/scenario-simulator"
        element={
          isLoggedIn ? (
            <Layout>
              <ScenarioSimulator />
            </Layout>
          ) : (
            <Navigate to="/login" replace />
          )
        }
      />

      <Route
        path="/audit-logs"
        element={
          isLoggedIn ? (
            <Layout>
              <AuditLogs />
            </Layout>
          ) : (
            <Navigate to="/login" replace />
          )
        }
      />

      <Route
        path="/risk-assessment"
        element={
          isLoggedIn ? <Layout><RiskAnomalyView kind="risk" /></Layout> : <Navigate to="/login" replace />
        }
      />

      <Route
        path="/anomaly-detection"
        element={
          isLoggedIn ? <Layout><RiskAnomalyView kind="anomaly" /></Layout> : <Navigate to="/login" replace />
        }
      />

      <Route
        path="/cfo-reports"
        element={
          isLoggedIn ? <Layout><CfoCommandCenter /></Layout> : <Navigate to="/login" replace />
        }
      />

      {pages.map(
        (page) => (
          <Route
            key={page}
            path={makePath(
              page
            )}
            element={
              isLoggedIn ? (
                <Layout>
                  <Page
                    title={
                      page
                    }
                  />
                </Layout>
              ) : (
                <Navigate
                  to="/login"
                  replace
                />
              )
            }
          />
        )
      )}

      {/* =================================================
          FALLBACK
      ================================================= */}

      <Route
        path="*"
        element={
          <Navigate
            to={
              isLoggedIn
                ? "/"
                : "/login"
            }
            replace
          />
        }
      />

    </Routes>
  );
}
