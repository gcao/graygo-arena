import type { TranscriptResponse, TranscriptView } from "../api/client";

type TranscriptPanelProps = {
  transcript: TranscriptResponse | null;
  view: TranscriptView;
  onViewChange: (view: TranscriptView) => void;
};

const views: TranscriptView[] = ["public", "black_private", "white_private", "debug"];

export function TranscriptPanel({ transcript, view, onViewChange }: TranscriptPanelProps) {
  return (
    <section className="panel transcript-panel">
      <div className="panel-heading">
        <h2>Transcripts</h2>
        <div className="segmented">
          {views.map((candidate) => (
            <button
              className={candidate === view ? "active" : ""}
              key={candidate}
              onClick={() => onViewChange(candidate)}
              type="button"
            >
              {candidate.replace("_", " ")}
            </button>
          ))}
        </div>
      </div>
      <div className="transcript-lines">
        {transcript?.entries.length ? (
          transcript.entries.map((entry, index) => <pre key={`${entry}-${index}`}>{entry}</pre>)
        ) : (
          <p className="muted">No transcript entries.</p>
        )}
      </div>
    </section>
  );
}
