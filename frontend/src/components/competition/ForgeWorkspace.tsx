import type { ReactNode } from "react";
import { ArrowLeft, ShieldCheck, WarningCircle } from "@phosphor-icons/react";
import { Link } from "react-router-dom";

export type ForgeSection = "mission" | "playthrough" | "archive";

export function ForgeWorkspace({
  active,
  truthLabel,
  children,
  className = "",
}: {
  active: ForgeSection;
  truthLabel: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className={`forge-workspace ${className}`.trim()}>
      <ForgeTopNav active={active} truthLabel={truthLabel} />
      {children}
    </div>
  );
}

export function ForgeTopNav({
  active,
  truthLabel,
}: {
  active: ForgeSection;
  truthLabel: string;
}) {
  const links: { section: ForgeSection; code: string; label: string; to: string }[] = [
    { section: "mission", code: "01", label: "Judge Mission", to: "/" },
    { section: "playthrough", code: "02", label: "Playthrough Inspector", to: "/playthrough-inspector" },
    { section: "archive", code: "03", label: "Mission Archive", to: "/reports" },
  ];
  return (
    <header className="competition-top-nav">
      <Link className="competition-top-brand" to="/" aria-label="Playtest Forge home">
        <span className="competition-top-brand-mark" aria-hidden="true">PF</span>
        <span>Playtest / Forge</span>
      </Link>
      <nav aria-label="Competition pages">
        {links.map((item) => (
          <Link
            key={item.section}
            to={item.to}
            aria-current={active === item.section ? "page" : undefined}
          >
            <span aria-hidden="true">{item.code}</span>
            <b>{item.label}</b>
          </Link>
        ))}
      </nav>
      <span className="competition-top-status">
        <ShieldCheck size={14} weight="fill" aria-hidden="true" />
        <span>{truthLabel}</span>
      </span>
    </header>
  );
}

export function ForgePageHeader({
  eyebrow,
  title,
  description,
  back,
  aside,
}: {
  eyebrow: string;
  title: string;
  description: ReactNode;
  back?: { to: string; label: string };
  aside?: ReactNode;
}) {
  return (
    <section className="forge-page-header">
      <div className="forge-page-copy">
        {back && (
          <Link className="forge-back-link" to={back.to}>
            <ArrowLeft size={15} aria-hidden="true" /> {back.label}
          </Link>
        )}
        <span className="forge-eyebrow">{eyebrow}</span>
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      {aside && <div className="forge-page-aside">{aside}</div>}
    </section>
  );
}

export function ForgeMetricStrip({
  items,
}: {
  items: { value: ReactNode; label: string; tone?: "evidence" | "warning" | "risk" }[];
}) {
  return (
    <dl className="forge-metric-strip">
      {items.map((item) => (
        <div key={item.label} data-tone={item.tone}>
          <dt>{item.label}</dt>
          <dd>{item.value}</dd>
        </div>
      ))}
    </dl>
  );
}

export function ForgeStatePanel({
  eyebrow,
  title,
  description,
  actions,
  tone = "info",
}: {
  eyebrow: string;
  title: string;
  description: ReactNode;
  actions?: ReactNode;
  tone?: "info" | "error";
}) {
  return (
    <section className="forge-state-panel" data-tone={tone} role={tone === "error" ? "alert" : "status"}>
      <WarningCircle size={28} weight="duotone" aria-hidden="true" />
      <span className="forge-eyebrow">{eyebrow}</span>
      <h1>{title}</h1>
      <div className="forge-state-description">{description}</div>
      {actions && <div className="forge-state-actions">{actions}</div>}
    </section>
  );
}
