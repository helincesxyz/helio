import { BrowserRouter as Router, Navigate, Route, Routes } from "react-router-dom";
import { NavRail } from "./components/layout/NavRail";
import { HelioDataProvider } from "./context/HelioDataContext";
import { Agent } from "./pages/Agent";
import { Debug } from "./pages/Debug";
import { Home } from "./pages/Home";
import { Decisions } from "./pages/strategy/Decisions";
import { Memory } from "./pages/strategy/Memory";
import { Overview } from "./pages/strategy/Overview";
import { Performance } from "./pages/strategy/Performance";
import { StrategyLayout } from "./pages/strategy/StrategyLayout";
import { Trades } from "./pages/strategy/Trades";

function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex bg-bg text-ink">
      <NavRail />
      <div className="flex-1">{children}</div>
    </div>
  );
}

export default function App() {
  return (
    <HelioDataProvider>
      <Router>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route
            path="/agent"
            element={
              <AppShell>
                <Agent />
              </AppShell>
            }
          />
          <Route
            path="/strategy"
            element={
              <AppShell>
                <StrategyLayout />
              </AppShell>
            }
          >
            <Route index element={<Navigate to="overview" replace />} />
            <Route path="overview" element={<Overview />} />
            <Route path="performance" element={<Performance />} />
            <Route path="decisions" element={<Decisions />} />
            <Route path="trades" element={<Trades />} />
            <Route path="memory" element={<Memory />} />
          </Route>
          <Route path="/debug" element={<Debug />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Router>
    </HelioDataProvider>
  );
}
