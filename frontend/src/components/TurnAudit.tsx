import type { TurnResponse } from "../api/client";

type TurnAuditProps = {
  turns: TurnResponse[];
};

export function TurnAudit({ turns }: TurnAuditProps) {
  const latest = turns.at(-1) ?? null;
  return (
    <section className="panel audit-panel">
      <h2>Turn Audit</h2>
      {latest ? (
        <>
          <div className="audit-summary">
            <span>Turn {latest.turn_index}</span>
            <span>B {latest.black_move}</span>
            <span>W {latest.white_move}</span>
            <span>{latest.status}</span>
          </div>
          <dl className="kv-list">
            <div>
              <dt>Pre BoardKey</dt>
              <dd className="mono">{latest.pre_board_key}</dd>
            </div>
            <div>
              <dt>Post BoardKey</dt>
              <dd className="mono">{latest.post_board_key}</dd>
            </div>
            <div>
              <dt>Captures</dt>
              <dd>{latest.captures.length ? latest.captures.join(", ") : "none"}</dd>
            </div>
            <div>
              <dt>Forbidden</dt>
              <dd>
                {latest.forbidden_updates.length ? latest.forbidden_updates.join(", ") : "none"}
              </dd>
            </div>
          </dl>
        </>
      ) : (
        <p className="muted">No resolved turns yet.</p>
      )}
      <div className="turn-list">
        {turns.map((turn) => (
          <span key={turn.turn_index}>
            #{turn.turn_index} B {turn.black_move} / W {turn.white_move}
          </span>
        ))}
      </div>
    </section>
  );
}
