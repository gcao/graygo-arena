import {
  Activity,
  Download,
  Pause,
  Play,
  RefreshCw,
  ShieldCheck,
  Square,
  StepForward,
  StopCircle
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";

import {
  autorunGame,
  createGame,
  exportGame,
  getGame,
  getGuardrails,
  getProviderSettings,
  getTranscript,
  listProviders,
  listTurns,
  pauseGame,
  resumeGame,
  startGame,
  stepGame,
  stopGame,
  type CreateGameRequest,
  type GameResponse,
  type GuardrailCheckResponse,
  type ProviderInfo,
  type TranscriptResponse,
  type TranscriptView,
  type TurnResponse
} from "./api/client";
import { connectGameEvents } from "./api/events";
import { BoardGrid } from "./components/BoardGrid";
import { CellInspector } from "./components/CellInspector";
import { TranscriptPanel } from "./components/TranscriptPanel";
import { TurnAudit } from "./components/TurnAudit";
import type { Coordinate } from "./game/board";

type SeatForm = {
  provider: string;
  model: string;
  credential_ref: string;
};

type GameConfigSnapshot = {
  black: SeatForm;
  white: SeatForm;
};

const defaultSeat: SeatForm = {
  provider: "scripted_center",
  model: "default",
  credential_ref: "fake"
};

export default function App() {
  const [providers, setProviders] = useState<ProviderInfo[]>([]);
  const [providerSettings, setProviderSettings] = useState<ProviderInfo[]>([]);
  const [black, setBlack] = useState<SeatForm>(defaultSeat);
  const [white, setWhite] = useState<SeatForm>({
    provider: "scripted_pass",
    model: "default",
    credential_ref: "fake"
  });
  const [boardSize, setBoardSize] = useState(7);
  const [maxTurns, setMaxTurns] = useState(40);
  const [game, setGame] = useState<GameResponse | null>(null);
  const [gameConfig, setGameConfig] = useState<GameConfigSnapshot | null>(null);
  const [turns, setTurns] = useState<TurnResponse[]>([]);
  const [guardrails, setGuardrails] = useState<GuardrailCheckResponse[]>([]);
  const [transcriptView, setTranscriptView] = useState<TranscriptView>("public");
  const [transcript, setTranscript] = useState<TranscriptResponse | null>(null);
  const [selected, setSelected] = useState<Coordinate | null>(null);
  const [showNeighbors, setShowNeighbors] = useState(true);
  const [showLastMoves, setShowLastMoves] = useState(true);
  const [showCollisions, setShowCollisions] = useState(true);
  const [showCaptures, setShowCaptures] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listProviders()
      .then((items) => {
        setProviders(items);
        setProviderSettings(items);
        const first = items[0];
        if (first) {
          setBlack((current) => ({
            ...current,
            provider: current.provider || first.id,
            model: current.model || first.models[0] || "default"
          }));
        }
      })
      .catch((err: unknown) => setError(errorMessage(err)));
    getProviderSettings()
      .then(setProviderSettings)
      .catch(() => undefined);
  }, []);

  const refresh = useCallback(
    async (gameId: string, view = transcriptView) => {
      const [nextGame, nextTurns, nextTranscript, nextGuardrails] = await Promise.all([
        getGame(gameId),
        listTurns(gameId),
        getTranscript(gameId, view),
        getGuardrails(gameId)
      ]);
      setGame(nextGame);
      setTurns(nextTurns);
      setTranscript(nextTranscript);
      setGuardrails(nextGuardrails);
    },
    [transcriptView]
  );
  const gameId = game?.id ?? null;

  useEffect(() => {
    if (!gameId) {
      return undefined;
    }
    return connectGameEvents(gameId, () => {
      void refresh(gameId);
    });
  }, [gameId, refresh]);

  const latestTurn = turns.at(-1) ?? null;
  const sameSeatNotice =
    black.provider === white.provider && black.model === white.model
      ? "Same provider/model selected; backend will create isolated Black and White seat sessions."
      : null;

  const providerOptions = useMemo(
    () =>
      providers.length
        ? providers
        : [
            {
              id: "scripted_center",
              provider: "scripted_center",
              auth_type: "none",
              configured: true,
              models: ["default"]
            }
          ],
    [providers]
  );

  async function runAction(action: () => Promise<void>) {
    setBusy(true);
    setError(null);
    try {
      await action();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  async function handleCreateGame() {
    const payload: CreateGameRequest = {
      board_size: boardSize,
      ruleset: "graygo-v1",
      black: { ...black },
      white: { ...white },
      max_turns: maxTurns,
      show_private_summaries_in_ui: true,
      auto_run: false,
      invalid_move_policy: "pass"
    };
    const created = await createGame(payload);
    setGame(created);
    setGameConfig({ black, white });
    setTurns([]);
    setTranscript(null);
    setGuardrails([]);
    setSelected(null);
    await refresh(created.id);
  }

  async function handleLifecycle(action: (gameId: string) => Promise<GameResponse>) {
    if (!game) return;
    const updated = await action(game.id);
    setGame(updated);
    await refresh(updated.id);
  }

  async function handleStart() {
    if (!game) return;
    const started = await startGame(game.id);
    setGame(started);
    if (started.status === "running" && started.current_turn === 0) {
      const result = await stepGame(started.id);
      setGame(result.game);
    }
    await refresh(started.id);
  }

  async function handleStep() {
    if (!game) return;
    const result = await stepGame(game.id);
    setGame(result.game);
    await refresh(result.game.id);
  }

  async function handleAutorun() {
    if (!game) return;
    await autorunGame(game.id);
    await refresh(game.id);
  }

  async function changeTranscriptView(view: TranscriptView) {
    setTranscriptView(view);
    if (game) {
      setTranscript(await getTranscript(game.id, view));
    }
  }

  async function exportBackendBundle() {
    if (!game) return;
    const payload = await exportGame(game.id);
    const url = URL.createObjectURL(
      new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" })
    );
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `${game.id}.json`;
    anchor.click();
    URL.revokeObjectURL(url);
  }

  return (
    <main className="app-shell">
      <aside className="setup-panel">
        <div className="brand-row">
          <div>
            <h1>Gray Go Arena</h1>
            <p>Backend-authoritative AI match console</p>
          </div>
          <span className="status-chip">{game?.status ?? "no game"}</span>
        </div>

        <section className="panel">
          <h2>New Game</h2>
          <div className="form-grid">
            <label>
              Board
              <input
                max={13}
                min={3}
                onChange={(event) => setBoardSize(Number(event.target.value))}
                type="number"
                value={boardSize}
              />
            </label>
            <label>
              Max turns
              <input
                min={1}
                onChange={(event) => setMaxTurns(Number(event.target.value))}
                type="number"
                value={maxTurns}
              />
            </label>
          </div>
          <SeatEditor
            label="Black"
            onChange={setBlack}
            providers={providerOptions}
            value={black}
          />
          <SeatEditor
            label="White"
            onChange={setWhite}
            providers={providerOptions}
            value={white}
          />
          {sameSeatNotice ? <p className="notice">{sameSeatNotice}</p> : null}
          <button
            className="primary-action"
            disabled={busy}
            onClick={() => void runAction(handleCreateGame)}
            type="button"
          >
            <Play size={17} />
            Create Game
          </button>
        </section>

        <section className="panel">
          <h2>Controls</h2>
          <div className="control-grid">
            <IconButton disabled={!game || busy} label="Start" onClick={() => runAction(handleStart)}>
              <Play size={16} />
            </IconButton>
            <IconButton disabled={!game || busy} label="Step" onClick={() => runAction(handleStep)}>
              <StepForward size={16} />
            </IconButton>
            <IconButton disabled={!game || busy} label="Auto-run" onClick={() => runAction(handleAutorun)}>
              <Activity size={16} />
            </IconButton>
            <IconButton disabled={!game || busy} label="Pause" onClick={() => runAction(() => handleLifecycle(pauseGame))}>
              <Pause size={16} />
            </IconButton>
            <IconButton disabled={!game || busy} label="Resume" onClick={() => runAction(() => handleLifecycle(resumeGame))}>
              <RefreshCw size={16} />
            </IconButton>
            <IconButton disabled={!game || busy} label="Stop" onClick={() => runAction(() => handleLifecycle(stopGame))}>
              <StopCircle size={16} />
            </IconButton>
            <IconButton disabled={!game || busy} label="Export" onClick={() => runAction(exportBackendBundle)}>
              <Download size={16} />
            </IconButton>
          </div>
          {error ? <p className="error-text">{error}</p> : null}
        </section>
      </aside>

      <section className="workspace">
        <section className="panel board-panel">
          <div className="panel-heading">
            <div>
              <h2>Live Board</h2>
              <p className="muted">
                Turn {game?.current_turn ?? 0} · {game?.board_key ?? "no BoardKey"}
              </p>
            </div>
            <div className="toggle-row">
              <Toggle label="Neighbors" value={showNeighbors} onChange={setShowNeighbors} />
              <Toggle label="Moves" value={showLastMoves} onChange={setShowLastMoves} />
              <Toggle label="Collisions" value={showCollisions} onChange={setShowCollisions} />
              <Toggle label="Captures" value={showCaptures} onChange={setShowCaptures} />
            </div>
          </div>
          {game ? (
            <BoardGrid
              board={game.board}
              latestTurn={latestTurn}
              onSelect={setSelected}
              selected={selected}
              showCaptures={showCaptures}
              showCollisions={showCollisions}
              showLastMoves={showLastMoves}
              showNeighbors={showNeighbors}
            />
          ) : (
            <div className="empty-board">
              <Square size={22} />
              <span>Create a game to inspect the authoritative board.</span>
            </div>
          )}
        </section>

        <div className="side-grid">
          <CellInspector board={game?.board ?? []} selected={selected} />
          <section className="panel">
            <h2>Seats</h2>
            <div className="seat-summary">
              <SeatSummary color="Black" config={gameConfig?.black ?? black} move={latestTurn?.black_move} />
              <SeatSummary color="White" config={gameConfig?.white ?? white} move={latestTurn?.white_move} />
            </div>
          </section>
          <section className="panel">
            <h2>Settings</h2>
            <div className="settings-list">
              {providerSettings.map((provider) => (
                <div className="settings-row" key={provider.id}>
                  <span>{provider.id}</span>
                  <span>{provider.auth_type}</span>
                  <strong>{provider.configured ? "configured" : "not configured"}</strong>
                </div>
              ))}
            </div>
          </section>
        </div>

        <TurnAudit turns={turns} />
        <section className="panel guardrail-panel">
          <div className="panel-heading">
            <h2>Guardrails</h2>
            <ShieldCheck size={18} />
          </div>
          <div className="guardrail-list">
            {guardrails.length ? (
              guardrails.map((check) => (
                <div className={check.ok ? "guardrail-ok" : "guardrail-fail"} key={check.name}>
                  <strong>{check.name.replaceAll("_", " ")}</strong>
                  <span>{check.detail}</span>
                </div>
              ))
            ) : (
              <p className="muted">Create and step a game to run guardrails.</p>
            )}
          </div>
        </section>
        <TranscriptPanel
          onViewChange={(view) => void changeTranscriptView(view)}
          transcript={transcript}
          view={transcriptView}
        />
        <section className="panel raw-panel">
          <h2>Raw JSON</h2>
          <pre>{JSON.stringify({ game, latestTurn }, null, 2)}</pre>
        </section>
      </section>
    </main>
  );
}

function SeatEditor({
  label,
  providers,
  value,
  onChange
}: {
  label: string;
  providers: ProviderInfo[];
  value: SeatForm;
  onChange: (value: SeatForm) => void;
}) {
  const selectedProvider = providers.find((provider) => provider.id === value.provider) ?? providers[0];
  const models = selectedProvider?.models.length ? selectedProvider.models : ["default"];
  const modelListId = `${label.toLowerCase()}-model-options`;
  return (
    <fieldset className="seat-editor">
      <legend>{label}</legend>
      <label>
        Provider
        <select
          onChange={(event) => {
            const nextProvider = providers.find((provider) => provider.id === event.target.value);
            onChange({
              ...value,
              provider: event.target.value,
              model: nextProvider?.models[0] ?? "default"
            });
          }}
          value={value.provider}
        >
          {providers.map((provider) => (
            <option key={provider.id} value={provider.id}>
              {provider.id}
            </option>
          ))}
        </select>
      </label>
      <label>
        Model
        <input
          list={modelListId}
          onChange={(event) => onChange({ ...value, model: event.target.value })}
          value={value.model}
        />
        <datalist id={modelListId}>
          {models.map((model) => (
            <option key={model} value={model}>
              {model}
            </option>
          ))}
        </datalist>
      </label>
    </fieldset>
  );
}

function IconButton({
  children,
  disabled = false,
  label,
  onClick
}: {
  children: React.ReactNode;
  disabled?: boolean;
  label: string;
  onClick: () => void | Promise<void>;
}) {
  return (
    <button
      className="tool-button"
      disabled={disabled}
      onClick={() => void onClick()}
      title={label}
      type="button"
    >
      {children}
      <span>{label}</span>
    </button>
  );
}

function Toggle({
  label,
  value,
  onChange
}: {
  label: string;
  value: boolean;
  onChange: (value: boolean) => void;
}) {
  return (
    <label className="toggle">
      <input checked={value} onChange={(event) => onChange(event.target.checked)} type="checkbox" />
      {label}
    </label>
  );
}

function SeatSummary({
  color,
  config,
  move
}: {
  color: string;
  config: SeatForm;
  move: string | undefined;
}) {
  return (
    <div className="seat-card">
      <strong>{color}</strong>
      <span>{config.provider}</span>
      <span>{config.model}</span>
      <span>Last move: {move ?? "none"}</span>
    </div>
  );
}

function errorMessage(err: unknown): string {
  return err instanceof Error ? err.message : String(err);
}
