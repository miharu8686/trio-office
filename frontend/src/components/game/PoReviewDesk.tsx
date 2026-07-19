"use client";

import { Graphics } from "pixi.js";
import { useCallback, useEffect, useState, type ReactNode } from "react";
import { useGameStore, selectReviewQueue } from "@/stores/gameStore";
import type { ReviewItem } from "@/types";

/** How often the elapsed-time labels refresh (ms). */
const ELAPSED_REFRESH_MS = 10_000;

/** Max item rows rendered above the desk (rest folded into the count). */
const MAX_VISIBLE_ITEMS = 3;

/** Max papers drawn in the stack (visual cap only). */
const MAX_VISIBLE_PAPERS = 5;

const TYPE_BADGE: Record<ReviewItem["item_type"], { label: string; color: string }> = {
  completion: { label: "REPORT", color: "#4ade80" },
  permission: { label: "PERM", color: "#fb923c" },
  input: { label: "INPUT", color: "#60a5fa" },
};

function formatElapsed(createdAt: string, now: number): string {
  const started = new Date(createdAt).getTime();
  if (Number.isNaN(started)) return "";
  const minutes = Math.max(0, Math.floor((now - started) / 60_000));
  if (minutes < 60) return `${minutes}m`;
  return `${Math.floor(minutes / 60)}h${minutes % 60}m`;
}

/**
 * PoReviewDesk - the PO's review desk (trio view).
 *
 * Renders documents the agent is waiting on the human for (completed
 * reports, permission requests, input requests) as a paper stack with a
 * count, plus per-item rows showing type and wait time. The desk lights up
 * while anything is pending — a tall, aging stack means the human is the
 * bottleneck, not the agent.
 */
export function PoReviewDesk({ x, y }: { x: number; y: number }): ReactNode {
  const reviewQueue = useGameStore(selectReviewQueue);
  const [now, setNow] = useState(() => Date.now());
  const hasItems = reviewQueue.length > 0;

  useEffect(() => {
    if (!hasItems) return;
    setNow(Date.now());
    const timer = setInterval(() => setNow(Date.now()), ELAPSED_REFRESH_MS);
    return () => clearInterval(timer);
  }, [hasItems]);
  const visibleItems = reviewQueue.slice(-MAX_VISIBLE_ITEMS);
  const paperCount = Math.min(reviewQueue.length, MAX_VISIBLE_PAPERS);

  const drawDesk = useCallback(
    (g: Graphics) => {
      g.clear();

      // Pending highlight: warm glow behind the desk while items wait.
      if (hasItems) {
        g.roundRect(-12, -12, 194, 74, 10);
        g.fill({ color: 0xffaa33, alpha: 0.25 });
        g.roundRect(-6, -6, 182, 62, 8);
        g.stroke({ width: 3, color: 0xffaa33, alpha: 0.9 });
      }

      // Desk top
      g.roundRect(0, 0, 170, 18, 4);
      g.fill(0x8b5a2b);
      g.stroke({ width: 2, color: 0x5c3a17 });

      // Desk legs
      g.rect(8, 18, 10, 32);
      g.rect(152, 18, 10, 32);
      g.fill(0x6b4423);

      // Name plate
      g.roundRect(55, 22, 60, 14, 2);
      g.fill(0x333333);
      g.stroke({ width: 1, color: 0xffcc00 });

      // Paper stack on the desk
      for (let i = 0; i < paperCount; i++) {
        const offset = i * 4;
        g.roundRect(18 + (i % 2) * 2, -8 - offset, 34, 10, 1);
        g.fill(0xf5f5f0);
        g.stroke({ width: 1, color: 0xbbbbaa });
      }
    },
    [hasItems, paperCount],
  );

  return (
    <pixiContainer x={x} y={y}>
      <pixiGraphics draw={drawDesk} />
      {/* Name plate text (2x render scaled down for sharpness) */}
      <pixiContainer x={85} y={29} scale={0.5}>
        <pixiText
          text="PO REVIEW"
          anchor={0.5}
          style={{
            fontFamily: '"Courier New", monospace',
            fontSize: 18,
            fontWeight: "bold",
            fill: "#ffcc00",
          }}
          resolution={2}
        />
      </pixiContainer>
      {/* Stack count badge */}
      {hasItems && (
        <pixiContainer x={130} y={-14} scale={0.5}>
          <pixiText
            text={`x${reviewQueue.length}`}
            anchor={0.5}
            style={{
              fontFamily: '"Arial Black", Arial, sans-serif',
              fontSize: 30,
              fontWeight: "bold",
              fill: "#ffaa33",
            }}
            resolution={2}
          />
        </pixiContainer>
      )}
      {/* Item rows: newest at the bottom, stacked upward above the desk */}
      {visibleItems.map((item, i) => {
        const badge = TYPE_BADGE[item.item_type];
        const rowY = -30 - (visibleItems.length - 1 - i) * 14;
        const elapsed = formatElapsed(item.created_at, now);
        return (
          <pixiContainer key={item.id} x={0} y={rowY} scale={0.5}>
            <pixiText
              text={`${badge.label} ${elapsed}`}
              anchor={{ x: 0, y: 0.5 }}
              style={{
                fontFamily: '"Courier New", monospace',
                fontSize: 20,
                fontWeight: "bold",
                fill: badge.color,
              }}
              resolution={2}
            />
          </pixiContainer>
        );
      })}
    </pixiContainer>
  );
}
