import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
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
    <BrowserRouter>
      <ReactFlowProvider>
        <App />
      </ReactFlowProvider>
    </BrowserRouter>
  </React.StrictMode>,
);