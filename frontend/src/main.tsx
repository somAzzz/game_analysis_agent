import React from "react";
import ReactDOM from "react-dom/client";
import { HashRouter } from "react-router-dom";
import { ReactFlowProvider } from "@xyflow/react";
import App from "./App";
import "./styles/global.css";
import "@xyflow/react/dist/style.css";

const rootElement = document.getElementById("root");
if (!rootElement) {
  throw new Error("#root not found — did you update index.html?");
}

ReactDOM.createRoot(rootElement).render(
  <React.StrictMode>
    <HashRouter>
      <ReactFlowProvider>
        <App />
      </ReactFlowProvider>
    </HashRouter>
  </React.StrictMode>,
);
