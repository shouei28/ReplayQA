"use client";

import { useEffect, useRef } from "react";

interface Props {
  events: unknown[];
}

export function RecordingPlayer({ events }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current || events.length === 0) return;

    const container = containerRef.current;
    let cancelled = false;

    import("rrweb-player").then((mod) => {
      if (cancelled || !container) return;
      // rrweb-player attaches itself to the target element
      new mod.default({
        target: container,
        props: {
          events,
          width: 800,
          height: 450,
          autoPlay: false,
        },
      });
    });

    return () => {
      cancelled = true;
      container.innerHTML = "";
    };
  }, [events]);

  if (events.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-400 text-sm">
        No recording events found.
      </div>
    );
  }

  return <div ref={containerRef} className="w-full" />;
}
