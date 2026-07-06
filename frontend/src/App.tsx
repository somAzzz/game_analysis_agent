import { Link, Route, Routes } from "react-router-dom";
import { FrontPage } from "@/pages/FrontPage";
import { IssuePage } from "@/pages/IssuePage";
import { DecisionGraphPage } from "@/pages/DecisionGraphPage";
import { NotFoundPage } from "@/pages/NotFoundPage";

/**
 * Top-level shell. Three routes:
 *
 *   /                              — FrontPage (issue shelf)
 *   /issue/:kind/:id              — IssuePage (per-issue typeset columns)
 *   /decision-graph/:runId         — DecisionGraphPage (React Flow graph)
 *
 * The Colophon is rendered on every page.
 */
export default function App() {
  return (
    <div>
      <Routes>
        <Route path="/" element={<FrontPage />} />
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

function Colophon() {
  return (
    <footer className="colophon">
      <div className="row">
        <span>
          <Link to="/">The Analytical Review</Link>
        </span>
        <span>Set in Fraunces &amp; Newsreader</span>
        <span>React + React Flow · v0.3</span>
      </div>
    </footer>
  );
}