"use client";

import { useRef, useEffect } from "react";
import { FacilityStatus, RoomStatus, AcademicRoom, Facility } from "@/types";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { Badge } from "@/components/ui/badge";
import { formatBuildingName, formatTime, formatDuration } from "@/utils/format";
import { useDateTimeContext } from "@/lib/DateTimeContext";
import RoomScheduleLoader from "./RoomScheduleLoader";

interface SidebarProps {
  facilityData: FacilityStatus | null;
  expandedItems: string[];
  setExpandedItems: React.Dispatch<React.SetStateAction<string[]>>;
  onBuildingClick: (id: string) => void;
  scrollToBuildingId?: string | null;
}

/**
 * Checks if a time is within the next N minutes from the reference time
 */
const isWithinMinutes = (
  timeStr: string | undefined,
  referenceTime: string,
  minutes: number
): boolean => {
  if (!timeStr) return false;

  const parseTime = (t: string): number => {
    const parts = t.split(":");
    return parseInt(parts[0], 10) * 60 + parseInt(parts[1], 10);
  };

  const targetMinutes = parseTime(timeStr);
  const refMinutes = parseTime(referenceTime);

  const diff = targetMinutes - refMinutes;
  return diff > 0 && diff <= minutes;
};

/**
 * Status dot component
 */
const StatusDot = ({
  status,
  isEndingSoon,
}: {
  status: "available" | "occupied";
  isEndingSoon: boolean;
}) => {
  let colorClass = "";

  if (status === "available") {
    colorClass = isEndingSoon
      ? "bg-yellow-400 shadow-[0_0_6px_rgba(250,204,21,0.6)]"
      : "bg-green-500 shadow-[0_0_6px_rgba(34,197,94,0.6)]";
  } else {
    colorClass = "bg-red-500 shadow-[0_0_6px_rgba(239,68,68,0.6)]";
  }

  return <div className={`w-2.5 h-2.5 rounded-full shrink-0 ${colorClass}`} />;
};

/**
 * Room accordion item component
 */
const RoomAccordionItem = ({
  roomNumber,
  room,
  facility,
  currentTime,
  isExpanded,
}: {
  roomNumber: string;
  room: AcademicRoom;
  facility: Facility;
  currentTime: string;
  isExpanded: boolean;
}) => {
  const isAvailable =
    room.status === RoomStatus.AVAILABLE ||
    room.status === RoomStatus.PASSING_PERIOD;

  const isEndingSoon =
    isAvailable && isWithinMinutes(room.availableUntil, currentTime, 30);

  const roomId = `${facility.id}-room-${roomNumber}`;

  return (
    <AccordionItem value={roomId} className="border-none">
      <AccordionTrigger className="py-2 px-3 hover:bg-zinc-800/50 rounded-md transition-colors cursor-pointer">
        <div className="flex items-center justify-between w-full mr-2">
          <div className="flex items-center gap-3">
            <StatusDot
              status={isAvailable ? "available" : "occupied"}
              isEndingSoon={isEndingSoon}
            />
            <span className="text-sm font-medium text-zinc-200">
              {roomNumber}
            </span>
          </div>
          <span className="text-xs text-zinc-500">
            {isAvailable
              ? room.availableUntil
                ? `until ${formatTime(room.availableUntil)}`
                : "open"
              : room.availableAt
              ? `at ${formatTime(room.availableAt)}`
              : "busy"}
          </span>
        </div>
      </AccordionTrigger>
      <AccordionContent className="px-3 pb-3">
        <div className="pl-5 space-y-2">
          {/* Room details */}
          <div className="space-y-1 text-xs text-zinc-400">
            {isAvailable ? (
              <>
                {room.availableFor && (
                  <p>
                    <span className="text-zinc-500">Available for:</span>{" "}
                    <span className="text-zinc-300">
                      {formatDuration(room.availableFor)}
                    </span>
                  </p>
                )}
                {room.nextClass && (
                  <p>
                    <span className="text-zinc-500">Next:</span>{" "}
                    <span className="text-zinc-300">
                      {room.nextClass.course} - {room.nextClass.title}
                    </span>
                  </p>
                )}
              </>
            ) : (
              <>
                {room.currentClass && (
                  <p>
                    <span className="text-zinc-500">Current:</span>{" "}
                    <span className="text-zinc-300">
                      {room.currentClass.course} - {room.currentClass.title}
                    </span>
                  </p>
                )}
                {room.availableAt && (
                  <p>
                    <span className="text-zinc-500">Available at:</span>{" "}
                    <span className="text-zinc-300">
                      {formatTime(room.availableAt)}
                    </span>
                    {room.availableFor && (
                      <>
                        {" "}
                        <span className="text-zinc-500">for</span>{" "}
                        <span className="text-zinc-300">
                          {formatDuration(room.availableFor)}
                        </span>
                      </>
                    )}
                  </p>
                )}
              </>
            )}
          </div>

          {/* Hourly time blocks - only load when expanded */}
          {isExpanded && (
            <div className="mt-3">
              <RoomScheduleLoader
                buildingId={facility.id}
                roomNumber={roomNumber}
                buildingHours={facility.hours}
              />
            </div>
          )}
        </div>
      </AccordionContent>
    </AccordionItem>
  );
};

export default function Sidebar({
  facilityData,
  expandedItems,
  setExpandedItems,
  onBuildingClick,
  scrollToBuildingId,
}: SidebarProps) {
  const { formattedTime } = useDateTimeContext();
  const containerRef = useRef<HTMLDivElement>(null);
  const buildingRefs = useRef<Record<string, HTMLDivElement | null>>({});

  // Scroll to building when scrollToBuildingId changes
  useEffect(() => {
    if (scrollToBuildingId && buildingRefs.current[scrollToBuildingId]) {
      const element = buildingRefs.current[scrollToBuildingId];
      const container = containerRef.current;

      if (element && container) {
        // Small delay to allow accordion to open first
        setTimeout(() => {
          const scrollTop = element.offsetTop - container.offsetTop - 16; // 16px padding from top

          container.scrollTo({
            top: scrollTop,
            behavior: "smooth",
          });
        }, 100);
      }
    }
  }, [scrollToBuildingId]);

  const getBadgeVariant = (
    available: number,
    total: number,
    isOpen: boolean
  ) => {
    if (!isOpen) return "outline";
    if (available === 0) return "error";
    if (available < total / 2) return "warning";
    return "success";
  };

  const handleToggle = (id: string) => {
    onBuildingClick(id);
  };

  // Check if a room accordion is expanded
  const isRoomExpanded = (facilityId: string, roomNumber: string) => {
    return expandedItems.includes(`${facilityId}-room-${roomNumber}`);
  };

  return (
    <div ref={containerRef} className="h-full overflow-y-auto p-4 sm:p-5">
      <h1 className="sm:text-3xl text-2xl font-bold mb-4">
        <span className="text-gold">ucf</span>Spots
      </h1>
      <p className="text-zinc-500 text-sm mb-4">
        Click a building on the map to see room availability.
      </p>

      {facilityData && (
        <Accordion
          type="multiple"
          value={expandedItems}
          onValueChange={setExpandedItems}
          className="space-y-2 border-none"
        >
          {Object.values(facilityData.facilities)
            .sort((a, b) => a.id.localeCompare(b.id))
            .map((facility) => {
              const availableRooms = Object.entries(facility.rooms).filter(
                ([, room]) =>
                  room.status === RoomStatus.AVAILABLE ||
                  room.status === RoomStatus.PASSING_PERIOD
              );
              const occupiedRooms = Object.entries(facility.rooms).filter(
                ([, room]) =>
                  room.status === RoomStatus.OCCUPIED ||
                  room.status === RoomStatus.OPENING_SOON
              );

              return (
                <AccordionItem
                  key={facility.id}
                  value={facility.id}
                  className="border-none"
                >
                  <div
                    ref={(el) => {
                      buildingRefs.current[facility.id] = el;
                    }}
                    className="bg-zinc-900 rounded-lg overflow-hidden border border-zinc-800/50"
                  >
                    <AccordionTrigger
                      className="p-3 hover:bg-zinc-800/50 transition-colors py-3 px-4 cursor-pointer"
                      onClick={() => handleToggle(facility.id)}
                    >
                      <div className="flex justify-between items-center w-full mr-2 text-left">
                        <span className="font-medium text-zinc-100">
                          {formatBuildingName(facility.name)}
                        </span>
                        <Badge
                          variant={getBadgeVariant(
                            facility.roomCounts.available,
                            facility.roomCounts.total,
                            facility.isOpen
                          )}
                          className="ml-2"
                        >
                          {facility.isOpen
                            ? `${facility.roomCounts.available}/${facility.roomCounts.total}`
                            : "Closed"}
                        </Badge>
                      </div>
                    </AccordionTrigger>
                    <AccordionContent className="px-2 pb-3">
                      <div className="space-y-3 pt-1">
                        {/* Available Rooms */}
                        <div>
                          <h4 className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest mb-1 px-3">
                            Available ({availableRooms.length})
                          </h4>
                          {availableRooms.length > 0 ? (
                            <Accordion
                              type="multiple"
                              value={expandedItems}
                              onValueChange={setExpandedItems}
                            >
                              {availableRooms
                                .sort(([a], [b]) =>
                                  a.localeCompare(b, undefined, {
                                    numeric: true,
                                  })
                                )
                                .map(([roomNumber, room]) => (
                                  <RoomAccordionItem
                                    key={roomNumber}
                                    roomNumber={roomNumber}
                                    room={room}
                                    facility={facility}
                                    currentTime={formattedTime}
                                    isExpanded={isRoomExpanded(
                                      facility.id,
                                      roomNumber
                                    )}
                                  />
                                ))}
                            </Accordion>
                          ) : (
                            <p className="text-xs text-zinc-500 italic px-3">
                              No available rooms.
                            </p>
                          )}
                        </div>

                        {/* Occupied Rooms */}
                        <div>
                          <h4 className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest mb-1 px-3">
                            Occupied ({occupiedRooms.length})
                          </h4>
                          {occupiedRooms.length > 0 ? (
                            <Accordion
                              type="multiple"
                              value={expandedItems}
                              onValueChange={setExpandedItems}
                            >
                              {occupiedRooms
                                .sort(([a], [b]) =>
                                  a.localeCompare(b, undefined, {
                                    numeric: true,
                                  })
                                )
                                .map(([roomNumber, room]) => (
                                  <RoomAccordionItem
                                    key={roomNumber}
                                    roomNumber={roomNumber}
                                    room={room}
                                    facility={facility}
                                    currentTime={formattedTime}
                                    isExpanded={isRoomExpanded(
                                      facility.id,
                                      roomNumber
                                    )}
                                  />
                                ))}
                            </Accordion>
                          ) : (
                            <p className="text-xs text-zinc-500 italic px-3">
                              No occupied rooms.
                            </p>
                          )}
                        </div>
                      </div>
                    </AccordionContent>
                  </div>
                </AccordionItem>
              );
            })}
        </Accordion>
      )}
    </div>
  );
}
