import React from "react";
import { createRoot } from "react-dom/client";

function App() {
  return (
    <div style={{fontFamily:"ui-sans-serif", padding:16}}>
      <h1>SessionScribe</h1>
      <p>Vite + React running. We can now wire the real UI.</p>
    </div>
  );
}
createRoot(document.getElementById("root")!).render(<App />);