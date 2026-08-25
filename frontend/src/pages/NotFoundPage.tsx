import { Link } from "react-router-dom";
import { ForgeStatePanel, ForgeWorkspace } from "@/components/competition/ForgeWorkspace";

export function NotFoundPage() {
  return (
    <ForgeWorkspace active="mission" truthLabel="Route not found">
      <ForgeStatePanel
        eyebrow="404 / outside the evidence map"
        title="This route left the playable area."
        description="The address does not exist, or no generated manifest currently exposes it. Return to the judging story or browse the evidence archive."
        actions={<><Link to="/">Open Judge Mission</Link><Link to="/reports">Browse Mission Archive</Link></>}
      />
    </ForgeWorkspace>
  );
}
