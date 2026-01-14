"use client";

import { RoomScheduleBlock, HourlyScheduleBlock, BlockSection } from "@/types";
import { formatTime } from "@/utils/format";
import { useMemo, useState, useRef, useEffect, useCallback } from "react";
import { createPortal } from "react-dom";

interface HourlyTimeBlocksProps {
  schedule: RoomScheduleBlock[];
  buildingHours?: {
    open: string;
    close: string;
  };
}

/**
 * Converts raw schedule blocks into hourly blocks for display
 */
function convertToHourlyBlocks(
  schedule: RoomScheduleBlock[],
  buildingClose: string
): HourlyScheduleBlock[] {
  if (schedule.length === 0) return [];

  const hourlyBlocks: HourlyScheduleBlock[] = [];

  // Get the first schedule block's start hour (floored)
  const firstBlockHour = parseInt(schedule[0].start.split(":")[0], 10);
  const closeHour = parseInt(buildingClose.split(":")[0], 10);

  // Generate hourly blocks from first block's hour to building close
  for (let hour = firstBlockHour; hour < closeHour; hour++) {
    const hourStart = `${hour.toString().padStart(2, "0")}:00:00`;
    const hourEnd = `${(hour + 1).toString().padStart(2, "0")}:00:00`;

    const sections: BlockSection[] = [];

    // Find schedule blocks that overlap with this hour
    for (const block of schedule) {
      const blockStart = block.start;
      const blockEnd = block.end;

      // Check if block overlaps with this hour
      if (blockStart < hourEnd && blockEnd > hourStart) {
        // Calculate the intersection
        const sectionStart = blockStart > hourStart ? blockStart : hourStart;
        const sectionEnd = blockEnd < hourEnd ? blockEnd : hourEnd;

        sections.push({
          start: sectionStart,
          end: sectionEnd,
          status: block.status,
          details: block.details,
        });
      }
    }

    // If no sections found for this hour, it means no data (assume available based on building hours)
    if (sections.length === 0) {
      sections.push({
        start: hourStart,
        end: hourEnd,
        status: "available",
        details: null,
      });
    }

    hourlyBlocks.push({
      start: hourStart,
      end: hourEnd,
      sections,
    });
  }

  return hourlyBlocks;
}

/**
 * Parse time string (HH:mm:ss) to minutes since midnight
 */
function timeToMinutes(timeStr: string): number {
  const parts = timeStr.split(":");
  return parseInt(parts[0], 10) * 60 + parseInt(parts[1], 10);
}

/**
 * Tooltip content component
 */
function TooltipContent({ block }: { block: HourlyScheduleBlock }) {
  const startTime = formatTime(block.start);
  const endTime = formatTime(block.end);

  return (
    <div className="text-xs">
      <p className="font-medium text-zinc-200">
        {startTime} - {endTime}
      </p>
      {block.sections.length === 1 ? (
        <SingleSectionTooltip section={block.sections[0]} />
      ) : (
        <div className="mt-1 space-y-0.5">
          {block.sections.map((s, idx) => (
            <p key={idx} className="text-zinc-400">
              {formatTime(s.start)}-{formatTime(s.end)}:{" "}
              {s.status === "available" ? (
                <span className="text-green-400">Available</span>
              ) : (
                <span className="text-red-400">
                  {s.details?.course || s.details?.identifier || "Occupied"}
                </span>
              )}
            </p>
          ))}
        </div>
      )}
    </div>
  );
}

function SingleSectionTooltip({ section }: { section: BlockSection }) {
  if (section.status === "available") {
    return <p className="text-green-400 mt-0.5">Available</p>;
  }

  return (
    <div className="mt-0.5">
      <p className="text-red-400">
        {section.details?.type === "class" ? "Class" : "Event"}
      </p>
      {section.details && (
        <p className="text-zinc-400">
          {section.details.course || section.details.identifier}
          {section.details.title ? `: ${section.details.title}` : ""}
        </p>
      )}
    </div>
  );
}

/**
 * Portal tooltip that renders at the document body level
 */
function PortalTooltip({
  block,
  anchorRect,
}: {
  block: HourlyScheduleBlock;
  anchorRect: DOMRect;
}) {
  const tooltipRef = useRef<HTMLDivElement>(null);
  const [position, setPosition] = useState({ top: 0, left: 0 });

  useEffect(() => {
    if (tooltipRef.current) {
      const tooltipRect = tooltipRef.current.getBoundingClientRect();
      const viewportWidth = window.innerWidth;

      // Position above the block, centered
      let left = anchorRect.left + anchorRect.width / 2 - tooltipRect.width / 2;
      let top = anchorRect.top - tooltipRect.height - 8;

      // Keep within viewport bounds
      if (left < 8) left = 8;
      if (left + tooltipRect.width > viewportWidth - 8) {
        left = viewportWidth - tooltipRect.width - 8;
      }

      // If tooltip would go above viewport, show below instead
      if (top < 8) {
        top = anchorRect.bottom + 8;
      }

      setPosition({ top, left });
    }
  }, [anchorRect]);

  return createPortal(
    <div
      ref={tooltipRef}
      className="fixed px-3 py-2 bg-zinc-900 border border-zinc-700 rounded-lg shadow-xl z-9999 pointer-events-none"
      style={{
        top: position.top,
        left: position.left,
        maxWidth: "min(300px, calc(100vw - 16px))",
      }}
    >
      <TooltipContent block={block} />
    </div>,
    document.body
  );
}

/**
 * Single hour block component with hover tooltip
 */
function HourBlock({
  block,
  index,
  hoveredIndex,
  onHover,
}: {
  block: HourlyScheduleBlock;
  index: number;
  hoveredIndex: number | null;
  onHover: (index: number | null, rect: DOMRect | null) => void;
}) {
  const blockRef = useRef<HTMLDivElement>(null);
  const blockStartMin = timeToMinutes(block.start);
  const blockEndMin = timeToMinutes(block.end);
  const blockDuration = blockEndMin - blockStartMin;

  const handleMouseEnter = useCallback(() => {
    if (blockRef.current) {
      const rect = blockRef.current.getBoundingClientRect();
      onHover(index, rect);
    }
  }, [index, onHover]);

  const handleMouseLeave = useCallback(() => {
    onHover(null, null);
  }, [onHover]);

  const isHovered = hoveredIndex === index;

  // Render sections within the block
  const renderSections = () => {
    return block.sections.map((section, idx) => {
      const sectionStartMin = timeToMinutes(section.start);
      const sectionEndMin = timeToMinutes(section.end);
      const sectionDuration = sectionEndMin - sectionStartMin;

      const widthPercent =
        blockDuration > 0 ? (sectionDuration / blockDuration) * 100 : 100;

      return (
        <div
          key={idx}
          className={`h-full transition-colors ${
            section.status === "available"
              ? isHovered
                ? "bg-green-500/50"
                : "bg-green-500/30"
              : isHovered
              ? "bg-red-400/60"
              : "bg-red-400/40"
          }`}
          style={{ width: `${Math.max(widthPercent, 2)}%` }}
        />
      );
    });
  };

  return (
    <div
      ref={blockRef}
      className="flex-1 min-w-0 h-8 sm:h-10 flex border border-zinc-700/50 hover:border-zinc-600 rounded-sm overflow-hidden cursor-pointer transition-all"
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
    >
      {renderSections()}
    </div>
  );
}

/**
 * Legend component
 */
function Legend() {
  return (
    <div className="flex items-center gap-4 mt-2 text-[10px] text-zinc-500">
      <div className="flex items-center gap-1.5">
        <div className="w-3 h-3 bg-green-500/30 border border-zinc-700/50 rounded-sm" />
        <span>Available</span>
      </div>
      <div className="flex items-center gap-1.5">
        <div className="w-3 h-3 bg-red-400/40 border border-zinc-700/50 rounded-sm" />
        <span>Unavailable</span>
      </div>
    </div>
  );
}

export default function HourlyTimeBlocks({
  schedule,
  buildingHours = { open: "07:00:00", close: "22:00:00" },
}: HourlyTimeBlocksProps) {
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);
  const [hoveredRect, setHoveredRect] = useState<DOMRect | null>(null);

  const hourlyBlocks = useMemo(
    () => convertToHourlyBlocks(schedule, buildingHours.close),
    [schedule, buildingHours.close]
  );

  const handleHover = useCallback(
    (index: number | null, rect: DOMRect | null) => {
      setHoveredIndex(index);
      setHoveredRect(rect);
    },
    []
  );

  if (hourlyBlocks.length === 0) {
    return (
      <p className="text-xs text-zinc-500 italic">No schedule data available</p>
    );
  }

  return (
    <div className="w-full">
      <div className="flex gap-0.5">
        {hourlyBlocks.map((block, idx) => (
          <HourBlock
            key={idx}
            block={block}
            index={idx}
            hoveredIndex={hoveredIndex}
            onHover={handleHover}
          />
        ))}
      </div>
      <Legend />

      {/* Portal tooltip - shows on hover */}
      {hoveredIndex !== null && hoveredRect && (
        <PortalTooltip
          block={hourlyBlocks[hoveredIndex]}
          anchorRect={hoveredRect}
        />
      )}
    </div>
  );
}
