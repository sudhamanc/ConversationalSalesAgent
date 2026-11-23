import React from "react";
import ReactDOM from "react-dom/client";
import "@copilotkit/react-core/v2/styles.css";
import App from "./App";
import GenerativeUIProvider from "./a2ui/GenerativeUIProvider";
import "./styles/index.css";
import { setupRemoteLogging } from "./utils/remoteLog";

setupRemoteLogging();

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <GenerativeUIProvider>
      <App />
    </GenerativeUIProvider>
  </React.StrictMode>
);
