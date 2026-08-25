import { Link } from "react-router-dom";

interface MastheadProps {
  kicker?: React.ReactNode;
  center?: React.ReactNode;
  date?: string;
}

export function Masthead({ kicker, center, date }: MastheadProps) {
  return (
    <header className="masthead">
      <span className="kicker">
        {kicker ?? (
          <Link to="/reports" style={{ borderBottom: 0 }}>
            ← Report archive
          </Link>
        )}
      </span>
      <span className="issue-line">{center}</span>
      <span className="date">{date ?? new Date().toUTCString()}</span>
    </header>
  );
}
