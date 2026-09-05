import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";

import App from "./App";

/* ------------------------------------------------------------------
   Fetch mocking helpers
------------------------------------------------------------------- */

function jsonResponse(data: unknown, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    text: async () => JSON.stringify(data),
    json: async () => data,
  } as any;
}

type RouteHandler = (init?: RequestInit) => unknown;

function mockFetch(routes: Record<string, unknown | RouteHandler>) {
  const calls: { url: string; method: string; body?: any }[] = [];
  const fn = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    const method = (init?.method || "GET").toUpperCase();
    const path = url.replace(/^https?:\/\/[^/]+/, "").split("?")[0];
    calls.push({
      url: path,
      method,
      body: init?.body ? JSON.parse(String(init.body)) : undefined,
    });
    const handler = routes[`${method} ${path}`];
    if (handler === undefined) {
      return jsonResponse({ detail: "Not found" }, 404);
    }
    const value =
      typeof handler === "function" ? (handler as RouteHandler)(init) : handler;
    return jsonResponse(value, 200);
  });
  vi.stubGlobal("fetch", fn);
  return { fn, calls };
}

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>
  );
}

function withToken() {
  localStorage.setItem("token", "test-token");
  localStorage.setItem(
    "user",
    JSON.stringify({ role: "Admin" })
  );
}

const DASHBOARD_PAYLOAD = {
  total_transactions: 200,
  reconciliation_rate: 80,
  high_risk: 0,
  current_run: {
    run_id: "REC-200",
    mode: "single_file",
    status: "COMPLETED",
    filename: "my_new_finance_data_200.csv",
    files: ["my_new_finance_data_200.csv"],
    created_at: "2026-09-05T00:00:00",
  },
  reconciliation: {
    run_id: "REC-200",
    total: 200,
    matched: 160,
    exceptions: 40,
    match_rate: 80,
    variance: 3575,
  },
  financial: {
    revenue: { available: true, value: 1250 },
    expenses: { available: true, value: 400 },
    refunds: { available: false, value: 0 },
    fees: { available: false, value: 0 },
    net_profit: { available: true, value: 850 },
    cash_balance: { available: true, value: 850 },
  },
};

/* ------------------------------------------------------------------
   LOGIN
------------------------------------------------------------------- */

describe("Login", () => {
  it("shows the login screen when there is no token", () => {
    renderAt("/");
    expect(screen.getByText("AI Finance Controller")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Sign in" })).toBeTruthy();
  });

  it("authenticates and navigates to the dashboard", async () => {
    const user = userEvent.setup();
    const { calls } = mockFetch({
      "POST /api/auth/login": {
        access_token: "token-123",
        user: { role: "Admin", email: "admin@demo.com" },
      },
      "GET /api/dashboard": DASHBOARD_PAYLOAD,
    });

    renderAt("/login");

    // The demo email is pre-filled; clear before typing to avoid appending.
    await user.clear(
      screen.getByPlaceholderText("Email")
    );
    await user.type(
      screen.getByPlaceholderText("Email"),
      "admin@demo.com"
    );
    await user.clear(
      screen.getByPlaceholderText("Password")
    );
    await user.type(
      screen.getByPlaceholderText("Password"),
      "DemoPassword123!"
    );
    await user.click(
      screen.getByRole("button", { name: "Sign in" })
    );

    await waitFor(() =>
      expect(screen.getByText("Finance Overview")).toBeTruthy()
    );

    const loginCall = calls.find(
      (call) => call.url === "/api/auth/login"
    );
    expect(loginCall).toBeTruthy();
    expect(loginCall!.body).toEqual({
      email: "admin@demo.com",
      password: "DemoPassword123!",
    });
    expect(localStorage.getItem("token")).toBe("token-123");
  });

  it("shows an error when credentials are rejected", async () => {
    const user = userEvent.setup();
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        jsonResponse({ detail: "Invalid email or password" }, 401)
      )
    );

    renderAt("/login");
    await user.type(
      screen.getByPlaceholderText("Email"),
      "admin@demo.com"
    );
    await user.type(
      screen.getByPlaceholderText("Password"),
      "wrong-password"
    );
    await user.click(
      screen.getByRole("button", { name: "Sign in" })
    );

    await waitFor(() =>
      expect(
        screen.getByText("Invalid email or password.")
      ).toBeTruthy()
    );
  });
});

/* ------------------------------------------------------------------
   DASHBOARD
------------------------------------------------------------------- */

describe("Dashboard", () => {
  it("shows a loading state while data is fetched", () => {
    withToken();
    let resolveDashboard:
      | ((value: unknown) => void)
      | undefined;
    vi.stubGlobal(
      "fetch",
      vi.fn(
        () =>
          new Promise((resolve) => {
            resolveDashboard = resolve;
          })
      )
    );

    renderAt("/");
    expect(screen.getByText("Loading dashboard…")).toBeTruthy();

    resolveDashboard?.(jsonResponse(DASHBOARD_PAYLOAD));
  });

  it("renders the current-run reconciliation summary", async () => {
    withToken();
    mockFetch({ "GET /api/dashboard": DASHBOARD_PAYLOAD });

    renderAt("/");

    await waitFor(() =>
      expect(screen.getByText("Finance Overview")).toBeTruthy()
    );
    expect(screen.getByText("● COMPLETED")).toBeTruthy();
    expect(
      screen.getByText("Current reconciliation run")
    ).toBeTruthy();
    expect(
      screen.getByText(/my_new_finance_data_200\.csv/)
    ).toBeTruthy();
    // Backend reconciliation numbers render as KPIs (variance never faked).
    expect(
      screen.getAllByText("₹3,575").length
    ).toBeGreaterThan(0);
    expect(
      screen.getAllByText("80.0%").length
    ).toBeGreaterThan(0);
  });

  it("shows the empty state when no reconciliation run exists", async () => {
    withToken();
    mockFetch({
      "GET /api/dashboard": {
        ...DASHBOARD_PAYLOAD,
        current_run: undefined,
        reconciliation: {},
      },
    });

    renderAt("/");

    await waitFor(() =>
      expect(
        screen.getByText("No reconciliation run available")
      ).toBeTruthy()
    );
  });

  it("shows the API error state", async () => {
    withToken();
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        jsonResponse({ detail: "boom" }, 500)
      )
    );

    renderAt("/");

    await waitFor(() =>
      expect(
        screen.getByText("Unable to load dashboard data.")
      ).toBeTruthy()
    );
  });
});

/* ------------------------------------------------------------------
   TRANSACTIONS (backend data in the table page)
------------------------------------------------------------------- */

describe("Transactions", () => {
  it("renders backend transaction data with run scoping", async () => {
    withToken();
    mockFetch({
      "GET /api/transactions": {
        run_id: "REC-200",
        total: 200,
        page: 1,
        items: [
          {
            transaction_id: "TXN-000000",
            amount: 1000,
            merchant: "Acme Traders",
            reconciliation_status: "MATCHED",
          },
        ],
      },
    });

    renderAt("/transactions");

    await waitFor(() =>
      expect(
        screen.getAllByText("Transactions").length
      ).toBeGreaterThan(0)
    );
    // The page renders the trusted backend payload.
    expect(screen.getByText(/REC-200/)).toBeTruthy();
    expect(screen.getByText(/TXN-000000/)).toBeTruthy();
    expect(screen.getByText(/Acme Traders/)).toBeTruthy();
  });

  it("shows the API error state", async () => {
    withToken();
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        jsonResponse({ detail: "boom" }, 500)
      )
    );

    renderAt("/transactions");

    await waitFor(() =>
      expect(
        screen.getByText(/Unable to load transactions/)
      ).toBeTruthy()
    );
  });
});

/* ------------------------------------------------------------------
   RISK / ANOMALY VIEW
------------------------------------------------------------------- */

describe("Risk / Anomaly", () => {
  it("renders risk items scoped to the current run", async () => {
    withToken();
    mockFetch({
      "GET /api/dashboard": DASHBOARD_PAYLOAD,
      "GET /api/risk": [
        {
          run_id: "REC-200",
          transaction_id: "TXN-000160",
          risk_level: "LOW",
          risk_score: 25,
          variance: 83,
        },
      ],
    });

    renderAt("/risk-assessment");

    await waitFor(() =>
      expect(
        screen.getAllByText("Risk Assessment").length
      ).toBeGreaterThan(0)
    );
    expect(
      screen.getAllByText(/run REC-200/).length
    ).toBeGreaterThan(0);
    expect(
      screen.getAllByText("TXN-000160").length
    ).toBeGreaterThan(0);
    expect(
      screen.getAllByText("LOW").length
    ).toBeGreaterThan(0);
  });

  it("shows the error state with a retry action", async () => {
    withToken();
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        jsonResponse({ detail: "boom" }, 500)
      )
    );

    renderAt("/risk-assessment");

    await waitFor(() =>
      expect(
        screen.getByText("Unable to load risk assessments.")
      ).toBeTruthy()
    );
    expect(
      screen.getByRole("button", { name: "Retry" })
    ).toBeTruthy();
  });
});

/* ------------------------------------------------------------------
   CFO COMMAND CENTER — truthful unavailable states
------------------------------------------------------------------- */

describe("CFO Command Center", () => {
  it("shows Unavailable (never fake zero) for missing financial dimensions", async () => {
    withToken();
    mockFetch({
      "GET /api/reports/cfo": {
        metrics: {
          total_transactions: 200,
          high_risk: 0,
        },
        financial: {
          revenue: { available: false, value: 0 },
          expenses: { available: false, value: 0 },
          refunds: { available: false, value: 0 },
          fees: { available: false, value: 0 },
          net_profit: { available: false, value: 0 },
          cash_balance: { available: false, value: 0 },
        },
      },
    });

    renderAt("/cfo-reports");

    await waitFor(() =>
      expect(screen.getAllByText("Unavailable").length).toBeGreaterThan(0)
    );
  });
});

/* ------------------------------------------------------------------
   COPILOT
------------------------------------------------------------------- */

describe("Copilot", () => {
  it("shows suggested questions and asks a quick question", async () => {
    withToken();
    const user = userEvent.setup();
    const { calls } = mockFetch({
      "POST /api/copilot": {
        answer: "Priority exception review: start with TXN-000160.",
      },
    });

    renderAt("/finance-copilot");

    await waitFor(() =>
      expect(screen.getByText("Suggested questions")).toBeTruthy()
    );
    expect(
      screen.getByRole("button", {
        name: "What should I do first?",
      })
    ).toBeTruthy();

    await user.click(
      screen.getByRole("button", {
        name: "What should I do first?",
      })
    );

    await waitFor(() =>
      expect(
        screen.getByText(/Priority exception review/)
      ).toBeTruthy()
    );
    // The question was sent to the backend and the turn is shown.
    expect(
      calls.some(
        (call) =>
          call.url === "/api/copilot" &&
          call.body?.question === "What should I do first?"
      )
    ).toBe(true);
    expect(screen.getByText("You")).toBeTruthy();
    expect(screen.getAllByText("AI Controller").length).toBeGreaterThan(0);
  });

  it("threads conversation history on follow-up questions", async () => {
    withToken();
    const user = userEvent.setup();
    const { calls } = mockFetch({
      "POST /api/copilot": { answer: "Grounding answer." },
    });

    renderAt("/finance-copilot");

    const input = screen.getByPlaceholderText(
      "Ask a finance question..."
    );
    await user.clear(input);
    await user.type(input, "What are the biggest risks?");
    await user.click(
      screen.getByRole("button", { name: "Ask Copilot" })
    );

    await waitFor(() =>
      expect(screen.getByText("Grounding answer.")).toBeTruthy()
    );

    await user.clear(input);
    await user.type(
      input,
      "Which merchant is responsible?"
    );
    await user.click(
      screen.getByRole("button", { name: "Ask Copilot" })
    );

    await waitFor(() =>
      expect(calls.length).toBe(2)
    );

    const followUp = calls[1];
    expect(followUp.body.question).toBe(
      "Which merchant is responsible?"
    );
    expect(followUp.body.history).toBeTruthy();
    expect(followUp.body.history[0].role).toBe("user");
    expect(followUp.body.history[0].content).toBe(
      "What are the biggest risks?"
    );
  });

  it("clears the conversation", async () => {
    withToken();
    const user = userEvent.setup();
    mockFetch({
      "POST /api/copilot": { answer: "Answer one." },
    });

    renderAt("/finance-copilot");

    const input = screen.getByPlaceholderText(
      "Ask a finance question..."
    );
    await user.clear(input);
    await user.type(input, "Summarize the run");
    await user.click(
      screen.getByRole("button", { name: "Ask Copilot" })
    );
    await waitFor(() =>
      expect(screen.getByText("Answer one.")).toBeTruthy()
    );

    await user.click(
      screen.getByRole("button", {
        name: "Clear conversation",
      })
    );

    await waitFor(() =>
      expect(screen.queryByText("Answer one.")).toBeNull()
    );
    expect(
      screen.queryByText("Conversation")
    ).toBeNull();
  });

  it("shows the error state when the copilot request fails", async () => {
    withToken();
    const user = userEvent.setup();
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        jsonResponse({ detail: "Copilot request failed." }, 500)
      )
    );

    renderAt("/finance-copilot");

    const input = screen.getByPlaceholderText(
      "Ask a finance question..."
    );
    await user.clear(input);
    await user.type(input, "Hello");
    await user.click(
      screen.getByRole("button", { name: "Ask Copilot" })
    );

    await waitFor(() =>
      expect(
        screen.getByText("Copilot request failed.")
      ).toBeTruthy()
    );
  });
});