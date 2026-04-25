export function connectGameEvents(gameId: string, onEvent: () => void): () => void {
  const source = new EventSource(`/api/games/${gameId}/events?live=true`);
  source.onmessage = onEvent;
  source.addEventListener("turn.resolved", onEvent);
  source.addEventListener("game.finished", onEvent);
  source.addEventListener("game.status_changed", onEvent);
  source.onerror = () => {
    source.close();
  };
  return () => source.close();
}
