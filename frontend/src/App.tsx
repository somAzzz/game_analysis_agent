import { useEffect } from "react";
import { Link, Route, Routes, useLocation } from "react-router-dom";
import { FrontPage } from "@/pages/FrontPage";
import { IssuePage } from "@/pages/IssuePage";
import { DecisionGraphPage } from "@/pages/DecisionGraphPage";
import { NotFoundPage } from "@/pages/NotFoundPage";
import { JudgePage } from "@/pages/JudgePage";
import { PlaythroughInspectorPage } from "@/pages/PlaythroughInspectorPage";

/**
 * Top-level shell. Competition and archive routes:
 *
 *   /                              — JudgePage (Campaign → Repair → Proof)
 *   /playthrough-inspector         — verified representative replay
 *   /reports                       — FrontPage (issue shelf)
 *   /issue/:kind/:id              — IssuePage (per-issue typeset columns)
 *   /decision-graph/:runId         — DecisionGraphPage (React Flow graph)
 *
 * The Colophon is rendered on every page.
 */
export default function App() {
  return (
    <div>
      <ScrollToTop />
      <Routes>
        <Route path="/" element={<JudgePage />} />
        <Route path="/playthrough-inspector" element={<PlaythroughInspectorPage />} />
        <Route path="/reports" element={<FrontPage />} />
        <Route path="/issue/:kind/:id" element={<IssuePage />} />
        <Route
          path="/decision-graph/:runId"
          element={<DecisionGraphPage />}
        />
        <Route path="/decision-graph/:runId/:runIndex"
          element={<DecisionGraphPage />}
        />
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
      <Colophon />
    </div>
  );
}

function ScrollToTop() {
  const { pathname } = useLocation();
  useEffect(() => {
    window.scrollTo({ top: 0, left: 0, behavior: "instant" });
  }, [pathname]);
  return null;
}

function Colophon() {
  return (
    <footer className="colophon">
      <div className="row">
        <span>
          <Link to="/">Playtest Forge</Link>
        </span>
        <span><Link to="/playthrough-inspector">Playthrough Inspector</Link></span>
        <span><Link to="/reports">Mission Archive</Link></span>
        <span>Codex + Godot · v0.4</span>
      </div>
    </footer>
  );
}
