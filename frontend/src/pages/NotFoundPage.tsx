import { Link } from "react-router-dom";

export function NotFoundPage() {
  return (
    <div style={{ padding: 60 }}>
      <h1
        style={{
          fontFamily: "var(--serif)",
          fontSize: 64,
          fontVariationSettings: '"opsz" 144, "wght" 420, "WONK" 1',
          margin: 0,
        }}
      >
        404 · <em>lost the plot</em>
      </h1>
      <p style={{ fontStyle: "italic", color: "var(--ink-soft)", fontSize: 18 }}>
        That route doesn&apos;t exist (or the manifest doesn&apos;t know about it).
      </p>
      <Link to="/">← Back to the front page</Link>
    </div>
  );
}