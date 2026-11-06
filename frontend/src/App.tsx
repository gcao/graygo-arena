import {
  Activity,
  CheckCircle2,
  Clock,
  Download,
  Pause,
  Play,
  RefreshCw,
  Square,
  StepForward,
  StopCircle,
  UserRound
} from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import {
  createGame,
  exportGame,
  getGame,
  getProviderSettings,
  getTranscript,
  listProviders,
  listTurns,
  pauseGame,
  resumeGame,
  startGame,
  stepGame,
  stopGame,
  submitHumanMove,
  type CreateGameRequest,
  type GameResponse,
  type HumanMoveResponse,
  type ProviderInfo,
  type SeatColor,
  type TranscriptResponse,
  type TranscriptView,
  type TurnResponse
} from "./api/client";
import { connectGameEvents } from "./api/events";
import { BoardGrid } from "./components/BoardGrid";
import { CellInspector } from "./components/CellInspector";
import { TranscriptPanel } from "./components/TranscriptPanel";
import { TurnAudit } from "./components/TurnAudit";
import { cellAt, coordinateLabel, type Coordinate } from "./game/board";
import {
  isResumableGame,
  readPersistedWorkspace,
  writePersistedWorkspace,
  type GameConfigSnapshot,
  type SeatForm
} from "./storage/workspace";

type AutoRunMode = "idle" | "running" | "paused";
type AutoRunCommand = "idle" | "run" | "pause" | "stop";

function readAutoRunCommand(ref: { current: AutoRunCommand }): AutoRunCommand {
  return ref.current;
}

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => globalThis.setTimeout(resolve, ms));
}

export default function App() {
  const [persistedWorkspace] = useState(readPersistedWorkspace);
  const [providers, setProviders] = useState<ProviderInfo[]>([]);
  const [providerSettings, setProviderSettings] = useState<ProviderInfo[]>([]);
  const [black, setBlack] = useState<SeatForm>(() => persistedWorkspace.settings.black);
  const [white, setWhite] = useState<SeatForm>(() => persistedWorkspace.settings.white);
  const [boardSize, setBoardSize] = useState(() => persistedWorkspace.settings.boardSize);
  const [maxTurns, setMaxTurns] = useState(() => persistedWorkspace.settings.maxTurns);
  const [game, setGame] = useState<GameResponse | null>(() => persistedWorkspace.game);
  const [activeGameId, setActiveGameId] = useState<string | null>(
    () => persistedWorkspace.activeGameId ?? persistedWorkspace.game?.id ?? null
  );
  const [gameConfig, setGameConfig] = useState<GameConfigSnapshot | null>(
    () => persistedWorkspace.gameConfig
  );
  const [turns, setTurns] = useState<TurnResponse[]>([]);
  const [transcriptView, setTranscriptView] = useState<TranscriptView>(
    () => persistedWorkspace.settings.transcriptView
  );
  const [transcript, setTranscript] = useState<TranscriptResponse | null>(null);
  const [selected, setSelected] = useState<Coordinate | null>(null);
  const [humanMoveColor, setHumanMoveColor] = useState<SeatColor>("black");
  const [showNeighbors, setShowNeighbors] = useState(
    () => persistedWorkspace.settings.display.showNeighbors
  );
  const [showLastMoves, setShowLastMoves] = useState(
    () => persistedWorkspace.settings.display.showLastMoves
  );
  const [showCollisions, setShowCollisions] = useState(
    () => persistedWorkspace.settings.display.showCollisions
  );
  const [showCaptures, setShowCaptures] = useState(
    () => persistedWorkspace.settings.display.showCaptures
  );
  const [autoRunMode, setAutoRunMode] = useState<AutoRunMode>("idle");
  const autoRunCommandRef = useRef<AutoRunCommand>("idle");
  const autoRunLoopRef = useRef(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const applyGame = useCallback((nextGame: GameResponse) => {
    setGame(nextGame);
    setActiveGameId(isResumableGame(nextGame) ? nextGame.id : null);
  }, []);

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
      const [nextGame, nextTurns, nextTranscript] = await Promise.all([
        getGame(gameId),
        listTurns(gameId),
        getTranscript(gameId, view)
      ]);
      applyGame(nextGame);
      setTurns(nextTurns);
      setTranscript(nextTranscript);
    },
    [applyGame, transcriptView]
  );
  const gameId = game?.id ?? activeGameId;

  useEffect(() => {
    const shouldPersistGame = isResumableGame(game);
    const shouldKeepPendingGame = game === null && activeGameId !== null;
    writePersistedWorkspace({
      activeGameId: shouldPersistGame ? game.id : shouldKeepPendingGame ? activeGameId : null,
      game: shouldPersistGame ? game : null,
      gameConfig: shouldPersistGame || shouldKeepPendingGame ? gameConfig : null,
      settings: {
        black,
        white,
        boardSize,
        maxTurns,
        transcriptView,
        display: {
          showNeighbors,
          showLastMoves,
          showCollisions,
          showCaptures
        }
      }
    });
  }, [
    activeGameId,
    black,
    boardSize,
    game,
    gameConfig,
    maxTurns,
    showCaptures,
    showCollisions,
    showLastMoves,
    showNeighbors,
    transcriptView,
    white
  ]);

  useEffect(() => {
    if (!activeGameId) {
      return undefined;
    }
    let cancelled = false;
    refresh(activeGameId).catch((err: unknown) => {
      if (cancelled) {
        return;
      }
      setError(`Could not resume saved game ${activeGameId}: ${errorMessage(err)}`);
      setActiveGameId(null);
      setGame(null);
      setGameConfig(null);
      setTurns([]);
      setTranscript(null);
      setSelected(null);
    });
    return () => {
      cancelled = true;
    };
  }, [activeGameId, refresh]);

  useEffect(() => {
    if (!gameId) {
      return undefined;
    }
    return connectGameEvents(gameId, () => {
      void refresh(gameId);
    });
  }, [gameId, refresh]);

  const latestTurn = turns.at(-1) ?? null;
  const blackConfig = gameConfig?.black ?? black;
  const whiteConfig = gameConfig?.white ?? white;
  const humanColors = useMemo(
    () =>
      [
        blackConfig.provider === "human" ? "black" : null,
        whiteConfig.provider === "human" ? "white" : null
      ].filter((color): color is SeatColor => color !== null),
    [blackConfig.provider, whiteConfig.provider]
  );
  const pendingMoves = game?.pending_moves ?? {
    black: { status: "none" },
    white: { status: "none" }
  };
  const availableHumanColors = humanColors.filter(
    (color) => pendingMoves[color]?.status === "none"
  );
  const activeHumanColor =
    availableHumanColors.includes(humanMoveColor) ? humanMoveColor : availableHumanColors[0] ?? null;
  const isHumanGame = humanColors.length > 0;
  const canSealHumanMove = Boolean(game && game.status === "running" && activeHumanColor && !busy);
  const displayStatus =
    autoRunMode === "running"
      ? "auto-run"
      : autoRunMode === "paused"
        ? "paused"
        : game?.status ?? "no game";
  const sameSeatNotice =
    black.provider !== "human" &&
    black.provider === white.provider &&
    black.model === white.model
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

  useEffect(() => {
    if (activeHumanColor && activeHumanColor !== humanMoveColor) {
      setHumanMoveColor(activeHumanColor);
    }
  }, [activeHumanColor, humanMoveColor]);

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
    setActiveGameId(created.id);
    setGameConfig({ black: { ...black }, white: { ...white } });
    setTurns([]);
    setTranscript(null);
    setSelected(null);
    await refresh(created.id);
  }

  async function handleStart() {
    if (!game) return;
    const started = await startGame(game.id);
    applyGame(started);
    await refresh(started.id);
  }

  async function handleStep() {
    if (!game) return;
    const result = await stepGame(game.id);
    applyGame(result.game);
    await refresh(result.game.id);
  }

  async function submitHumanMoveAndRefresh(color: SeatColor, move: string): Promise<HumanMoveResponse> {
    if (!game) {
      throw new Error("No active game");
    }
    const result = await submitHumanMove(game.id, color, move);
    applyGame(result.game);
    await refresh(result.game.id);
    return result;
  }

  async function handleBoardPoint(coordinate: Coordinate) {
    setSelected(coordinate);
    if (!game || !canSealHumanMove || !activeHumanColor) {
      return;
    }
    if (cellAt(game.board, coordinate) !== "+") {
      setError("Select an empty point for the human move.");
      return;
    }
    const move = coordinateLabel(coordinate);
    await runAction(async () => {
      await submitHumanMoveAndRefresh(activeHumanColor, move);
    });
  }

  async function handleHumanPass(color: SeatColor) {
    await submitHumanMoveAndRefresh(color, "PASS");
  }

  async function handleAutorun() {
    if (!game || autoRunLoopRef.current) return;
    autoRunCommandRef.current = "run";
    autoRunLoopRef.current = true;
    setAutoRunMode("running");
    setError(null);
    let currentGame = game;
    try {
      currentGame = await ensureRunning(currentGame);
      while (readAutoRunCommand(autoRunCommandRef) === "run" && currentGame.status === "running") {
        const result = await stepGame(currentGame.id);
        currentGame = result.game;
        applyGame(currentGame);
        await refresh(currentGame.id);
        if (readAutoRunCommand(autoRunCommandRef) === "pause") {
          const paused = await pauseGame(currentGame.id);
          applyGame(paused);
          setAutoRunMode("paused");
          await refresh(paused.id);
          return;
        }
        if (readAutoRunCommand(autoRunCommandRef) === "stop") {
          const stopped = await stopGame(currentGame.id);
          applyGame(stopped);
          setAutoRunMode("idle");
          await refresh(stopped.id);
          return;
        }
        if (currentGame.status === "running") {
          await delay(250);
        }
      }
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      autoRunLoopRef.current = false;
      if (readAutoRunCommand(autoRunCommandRef) !== "pause") {
        setAutoRunMode("idle");
        autoRunCommandRef.current = "idle";
      }
    }
  }

  async function ensureRunning(currentGame: GameResponse): Promise<GameResponse> {
    if (currentGame.status === "created") {
      const started = await startGame(currentGame.id);
      applyGame(started);
      await refresh(started.id);
      return started;
    }
    if (currentGame.status === "paused") {
      const resumed = await resumeGame(currentGame.id);
      applyGame(resumed);
      await refresh(resumed.id);
      return resumed;
    }
    return currentGame;
  }

  async function handlePause() {
    if (!game) return;
    autoRunCommandRef.current = "pause";
    const paused = await pauseGame(game.id);
    applyGame(paused);
    setAutoRunMode("paused");
    await refresh(paused.id);
  }

  async function handleResume() {
    if (!game) return;
    if (autoRunMode === "paused") {
      void handleAutorun();
      return;
    }
    const resumed = await resumeGame(game.id);
    applyGame(resumed);
    await refresh(resumed.id);
  }

  async function handleStop() {
    if (!game) return;
    autoRunCommandRef.current = "stop";
    const stopped = await stopGame(game.id);
    applyGame(stopped);
    setAutoRunMode("idle");
    await refresh(stopped.id);
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
          <span className="status-chip">{displayStatus}</span>
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
          {game ? (
            <>
              <div className="control-grid">
                {game.status === "created" ? (
                  <IconButton disabled={busy} label="Start" onClick={() => runAction(handleStart)}>
                    <Play size={16} />
                  </IconButton>
                ) : null}
                {game.status === "running" && autoRunMode === "idle" && !isHumanGame ? (
                  <>
                    <IconButton disabled={busy} label="Step" onClick={() => runAction(handleStep)}>
                      <StepForward size={16} />
                    </IconButton>
                    <IconButton disabled={busy} label="Auto-run" onClick={() => void handleAutorun()}>
                      <Activity size={16} />
                    </IconButton>
                  </>
                ) : null}
                {autoRunMode === "running" ? (
                  <IconButton disabled={busy} label="Pause" onClick={() => runAction(handlePause)}>
                    <Pause size={16} />
                  </IconButton>
                ) : null}
                {game.status === "paused" || autoRunMode === "paused" ? (
                  <IconButton disabled={busy} label="Resume" onClick={() => runAction(handleResume)}>
                    <RefreshCw size={16} />
                  </IconButton>
                ) : null}
                {game.status === "running" || game.status === "paused" || autoRunMode !== "idle" ? (
                  <IconButton disabled={busy} label="Stop" onClick={() => runAction(handleStop)}>
                    <StopCircle size={16} />
                  </IconButton>
                ) : null}
                <IconButton disabled={busy} label="Export" onClick={() => runAction(exportBackendBundle)}>
                  <Download size={16} />
                </IconButton>
              </div>
              {isHumanGame ? (
                <HumanMovePanel
                  activeColor={activeHumanColor}
                  busy={busy}
                  humanColors={humanColors}
                  onPass={(color) => runAction(() => handleHumanPass(color))}
                  onSelectColor={setHumanMoveColor}
                  pendingMoves={pendingMoves}
                  status={game.status}
                />
              ) : null}
            </>
          ) : (
            <p className="muted control-empty">Create a game to show match controls.</p>
          )}
          {error ? <p className="error-text">{error}</p> : null}
        </section>
      </aside>

      <section className="workspace">
        <section className="panel board-panel">
          <div className="panel-heading">
            <div>
              <h2>Live Board</h2>
              <p className="muted">
                Turn {game?.current_turn ?? 0}
                {game ? ` / ${game.max_turns}` : ""} · {game?.board_key ?? "no BoardKey"}
              </p>
            </div>
            <div className="toggle-row">
              <Toggle label="Neighbors" value={showNeighbors} onChange={setShowNeighbors} />
              <Toggle label="Moves" value={showLastMoves} onChange={setShowLastMoves} />
              <Toggle label="Collisions" value={showCollisions} onChange={setShowCollisions} />
              <Toggle label="Captures" value={showCaptures} onChange={setShowCaptures} />
            </div>
          </div>
          {game?.result ? (
            <div aria-label="Final result" className="game-result" role="status">
              <strong>
                {game.result.winner === "draw"
                  ? "Draw"
                  : `${game.result.winner === "black" ? "Black" : "White"} wins by ${game.result.margin}`}
              </strong>
              <span>Black {game.result.black} · White {game.result.white}</span>
              <small>All remaining stones counted as alive.</small>
            </div>
          ) : null}
          {game ? (
            <BoardGrid
              board={game.board}
              latestTurn={latestTurn}
              onSelect={(coordinate) => void handleBoardPoint(coordinate)}
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
  const isHumanProvider = selectedProvider?.id === "human";
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
              model: nextProvider?.models[0] ?? "default",
              credential_ref: event.target.value === "human" ? "human" : value.credential_ref
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
      {value.provider === "graygo_nfsp_experimental" ? (
        <p className="muted">Experimental 32k-record NFSP policy. Playing strength is unvalidated.</p>
      ) : null}
      <label>
        Model
        <input
          disabled={isHumanProvider}
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

function HumanMovePanel({
  activeColor,
  busy,
  humanColors,
  onPass,
  onSelectColor,
  pendingMoves,
  status
}: {
  activeColor: SeatColor | null;
  busy: boolean;
  humanColors: SeatColor[];
  onPass: (color: SeatColor) => void | Promise<void>;
  onSelectColor: (color: SeatColor) => void;
  pendingMoves: GameResponse["pending_moves"];
  status: string;
}) {
  return (
    <div className="human-panel">
      <div className="human-seat-row">
        {humanColors.map((color) => {
          const moveStatus = pendingMoves[color]?.status ?? "none";
          const isActive = activeColor === color && moveStatus === "none";
          return (
            <button
              className={`human-seat-button ${isActive ? "active" : ""}`}
              disabled={busy || moveStatus !== "none" || status !== "running"}
              key={color}
              onClick={() => onSelectColor(color)}
              type="button"
            >
              {moveStatus === "sealed" ? (
                <CheckCircle2 size={15} />
              ) : moveStatus === "thinking" ? (
                <Clock size={15} />
              ) : (
                <UserRound size={15} />
              )}
              <span>{capitalize(color)}</span>
              <strong>{moveStatus}</strong>
            </button>
          );
        })}
      </div>
      {activeColor ? (
        <button
          className="secondary-action"
          disabled={busy || pendingMoves[activeColor]?.status !== "none" || status !== "running"}
          onClick={() => void onPass(activeColor)}
          type="button"
        >
          Pass {capitalize(activeColor)}
        </button>
      ) : null}
    </div>
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

function capitalize(value: string): string {
  return `${value.slice(0, 1).toUpperCase()}${value.slice(1)}`;
}

function errorMessage(err: unknown): string {
  return err instanceof Error ? err.message : String(err);
}
