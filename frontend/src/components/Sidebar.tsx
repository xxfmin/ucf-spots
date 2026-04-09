"use client";

import { useRef, useEffect, useState, useMemo } from "react";
import { FacilityStatus, RoomStatus, AcademicRoom, Facility } from "@/types";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { Badge } from "@/components/ui/badge";
import { ResponsivePopover } from "@/components/ui/responsive-popover";
import { LoadingSpinner } from "@/components/ui/loading-spinner";
import { Input } from "@/components/ui/input";

const HIDE_TIME_PICKER_INDICATOR =
  "[&::-webkit-calendar-picker-indicator]:hidden [&::-webkit-calendar-picker-indicator]:appearance-none";
import {
  CircleQuestionMark,
  Search,
  ListFilter,
  CalendarClock,
  MessageSquare,
  Clock,
} from "lucide-react";
import {
  formatBuildingName,
  formatTime,
  formatDuration,
  BUILDING_NAMES,
} from "@/utils/format";
import { useDateTimeContext } from "@/lib/DateTimeContext";
import { FilterCriteria, filterFacilities } from "@/utils/filterUtils";
import { DateTimePicker } from "@/components/ui/date-time-picker";
import RoomScheduleLoader from "./RoomScheduleLoader";
import FeedbackDialog from "./FeedbackDialog";
import moment from "moment-timezone";

interface SidebarProps {
  facilityData: FacilityStatus | null;
  expandedItems: string[];
  setExpandedItems: React.Dispatch<React.SetStateAction<string[]>>;
  onBuildingClick: (id: string) => void;
  scrollToBuildingId?: string | null;
  isFetching?: boolean;
}

/**
 * Checks if a time is within the next N minutes from the reference time
 */
const isWithinMinutes = (
  timeStr: string | undefined,
  referenceTime: string,
  minutes: number,
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
      <AccordionTrigger className="py-2 px-3 hover:bg-surface-row-hover rounded-md transition-colors cursor-pointer">
        <div className="flex items-center justify-between w-full mr-2">
          <div className="flex items-center gap-3">
            <StatusDot
              status={isAvailable ? "available" : "occupied"}
              isEndingSoon={isEndingSoon}
            />
            <span className="text-sm font-medium font-mono text-foreground">
              {roomNumber}
            </span>
          </div>
          <span className="text-xs text-secondary">
            {isAvailable
              ? room.availableUntil
                ? `until ${formatTime(room.availableUntil)}`
                : "open"
              : room.availableAt
                ? `free at ${formatTime(room.availableAt)}`
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
  isFetching = false,
}: SidebarProps) {
  const {
    formattedTime,
    selectedDateTime,
    setSelectedDateTime,
    isCurrentDateTime,
  } = useDateTimeContext();
  const [dateTimePickerOpen, setDateTimePickerOpen] = useState(false);
  const [feedbackDialogOpen, setFeedbackDialogOpen] = useState(false);
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const buildingRefs = useRef<Record<string, HTMLDivElement | null>>({});
  const [searchQuery, setSearchQuery] = useState("");

  // Filter states
  const [startTime, setStartTime] = useState<string>("");
  const [freeUntil, setFreeUntil] = useState<string>("");
  const [minDuration, setMinDuration] = useState<number | "">("");

  const hasActiveFilter = Boolean(startTime || freeUntil || minDuration);
  const isCustomDateTime = !isCurrentDateTime;

  // Scroll to building when scrollToBuildingId changes
  useEffect(() => {
    if (scrollToBuildingId && buildingRefs.current[scrollToBuildingId]) {
      const element = buildingRefs.current[scrollToBuildingId];
      const container = scrollContainerRef.current;

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
    isOpen: boolean,
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

  // Build filter criteria
  const filterCriteria: FilterCriteria = useMemo(() => {
    const criteria: FilterCriteria = {
      now: moment().tz("America/New_York"),
    };

    if (startTime) {
      criteria.startTime = startTime;
    }
    if (freeUntil) {
      criteria.freeUntil = freeUntil;
    }
    if (minDuration && typeof minDuration === "number") {
      criteria.minDuration = minDuration;
    }

    return criteria;
  }, [startTime, freeUntil, minDuration]);

  // Filter facilities based on search query and filter criteria
  const filteredFacilities = useMemo(() => {
    if (!facilityData) {
      return {};
    }

    let facilities = facilityData.facilities;

    // Apply filter criteria (time-based filters)
    if (hasActiveFilter) {
      facilities = filterFacilities(facilities, filterCriteria);
    }

    // Apply search query
    if (!searchQuery.trim()) {
      return facilities;
    }

    const query = searchQuery.trim().toLowerCase();
    const filtered: Record<string, Facility> = {};

    Object.entries(facilities).forEach(([id, facility]) => {
      // Search by building code (id) or building name
      const matchesId = id.toLowerCase().includes(query);
      const matchesName = facility.name.toLowerCase().includes(query);
      const matchesFormatted = formatBuildingName(id)
        .toLowerCase()
        .includes(query);

      if (matchesId || matchesName || matchesFormatted) {
        filtered[id] = facility;
      }
    });

    return filtered;
  }, [facilityData, searchQuery, filterCriteria, hasActiveFilter]);

  return (
    <div className="h-full flex flex-col p-4 sm:px-6 sm:py-4 overflow-hidden">
      <div className="flex items-center justify-between mb-6">
        {/* ml-0.5 nudges the "u" to optically align with elements below */}
        <h1 className="text-2xl font-bold ml-0.5">
          <span className="text-gold">ucf</span>Spots
        </h1>
        <ResponsivePopover
          title="Important Notes"
          desktopContentClassName="w-80 p-4 sm:p-3 rounded-lg bg-surface-raised border"
          mobileContentClassName="w-[min(20rem,calc(100vw-2rem))] max-w-[calc(100vw-2rem)] p-4 sm:p-3 rounded-lg bg-surface-raised border-border-muted text-zinc-200 [&>button]:top-3 [&>button]:right-3 !duration-200 data-[state=open]:!slide-in-from-top-0 data-[state=closed]:!slide-out-to-top-0 data-[state=open]:!slide-in-from-left-0 data-[state=closed]:!slide-out-to-left-0 data-[state=open]:!zoom-in-100 data-[state=closed]:!zoom-out-100"
          trigger={
            <button
              className="group cursor-pointer"
              aria-label="Important notes"
            >
              <CircleQuestionMark className="h-5 w-5 mr-1 text-secondary group-hover:text-primary transition-colors duration-300" />
            </button>
          }
        >
          <div className="space-y-4">
            <h3 className="font-semibold text-base">Important Notes:</h3>
            <ul className="space-y-2.5 text-sm text-primary pl-4 list-disc">
              <li className="leading-relaxed">
                Building/room access may be restricted to specific colleges or
                departments
              </li>
              <li className="leading-relaxed">
                Displayed availability only reflects official class schedules
              </li>
              <li className="leading-relaxed">
                Rooms may be occupied by unofficial meetings or study groups
              </li>
              <li className="leading-relaxed">
                Different schedules may apply during exam periods
              </li>
              <li className="leading-relaxed">
                Please leave rooms the way you found them for the next students
              </li>
            </ul>
            <div className="pt-2 -my-1 border-t space-y-1.5">
              <button
                onClick={() => setFeedbackDialogOpen(true)}
                className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-primary hover:bg-surface-hover rounded-md transition-colors cursor-pointer w-full"
              >
                <MessageSquare className="h-4 w-4 text-secondary" />
                <span>Leave Feedback</span>
              </button>
            </div>
          </div>
        </ResponsivePopover>
      </div>

      {/* Search Bar, Date/Time Picker, and Filter */}
      <div className="flex gap-2 mb-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-zinc-400" />
          <Input
            type="text"
            placeholder="Search..."
            value={searchQuery}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
              setSearchQuery(e.target.value)
            }
            className="pl-9 bg-surface-input border-border-subtle text-primary hover:border-border-strong placeholder:text-zinc-500 focus-visible:ring-zinc-700 transition-colors duration-300"
          />
        </div>

        {/* Date/Time Picker — Popover on desktop, Dialog on mobile */}
        <ResponsivePopover
          title="Select date and time"
          open={dateTimePickerOpen}
          onOpenChange={setDateTimePickerOpen}
          desktopAlign="end"
          desktopSideOffset={8}
          desktopCollisionPadding={8}
          desktopContentClassName="w-auto p-0 bg-surface-raised border-border-muted"
          mobileContentClassName="w-auto max-w-[calc(100vw-2rem)] p-0 bg-transparent border-0 shadow-none [&>button]:hidden !duration-200 data-[state=open]:!slide-in-from-top-0 data-[state=closed]:!slide-out-to-top-0 data-[state=open]:!slide-in-from-left-0 data-[state=closed]:!slide-out-to-left-0 data-[state=open]:!zoom-in-100 data-[state=closed]:!zoom-out-100"
          trigger={
            <button
              className={`px-3 py-2 rounded-md border transition-colors duration-300 flex items-center gap-2 cursor-pointer ${
                isCustomDateTime
                  ? "border-yellow-500/40 bg-yellow-500/5 text-yellow-400 hover:bg-yellow-500/10"
                  : "border-border-subtle bg-surface-input text-primary hover:border-border-strong"
              }`}
              aria-label="Select date and time"
            >
              <CalendarClock
                className={`h-4 w-4 ${isCustomDateTime ? "text-yellow-400" : "text-secondary"}`}
              />
              <span className="text-sm whitespace-nowrap">
                {isCurrentDateTime
                  ? "Now"
                  : moment(selectedDateTime)
                      .tz("America/New_York")
                      .format("M/D h:mm A")}
              </span>
            </button>
          }
        >
          <DateTimePicker
            initialDateTime={selectedDateTime}
            onDateTimeChange={(dateTime: Date) => {
              setSelectedDateTime(dateTime);
            }}
            closeContainer={() => setDateTimePickerOpen(false)}
            minDate={moment().tz("America/New_York").toDate()}
            maxDate={moment()
              .tz("America/New_York")
              .add(6, "months")
              .endOf("month")
              .toDate()}
          />
        </ResponsivePopover>

        <ResponsivePopover
          title="Filter Options"
          desktopAlign="end"
          desktopSideOffset={8}
          desktopCollisionPadding={8}
          desktopContentClassName="w-[min(20rem,calc(100vw-1rem))] max-h-[calc(100svh-5rem)] overflow-y-auto p-4 sm:p-3 rounded-lg bg-surface-raised border-border-muted text-zinc-200"
          mobileContentClassName="w-[min(20rem,calc(100vw-2rem))] max-w-[calc(100vw-2rem)] p-4 sm:p-3 rounded-lg bg-surface-raised border-border-muted text-zinc-200 [&>button]:top-3 [&>button]:right-3 !duration-200 data-[state=open]:!slide-in-from-top-0 data-[state=closed]:!slide-out-to-top-0 data-[state=open]:!slide-in-from-left-0 data-[state=closed]:!slide-out-to-left-0 data-[state=open]:!zoom-in-100 data-[state=closed]:!zoom-out-100"
          trigger={
            <button
              className={`px-3 py-2 rounded-md border transition-colors duration-300 flex items-center gap-2 cursor-pointer ${
                hasActiveFilter
                  ? "border-yellow-500/40 bg-yellow-500/5 text-yellow-400 hover:bg-yellow-500/10"
                  : "border-border-subtle bg-surface-input text-primary hover:border-border-strong"
              }`}
              aria-label="Filter options"
            >
              <ListFilter
                className={`h-4 w-4 ${hasActiveFilter ? "text-yellow-400" : "text-secondary"}`}
              />
              <span className="text-sm">Filter</span>
            </button>
          }
        >
          <div className="space-y-4">
            <h3 className="font-semibold text-foreground mb-3">More Filters</h3>

            {/* Available by this time */}
            <div className="space-y-2">
              <label className="text-sm font-medium text-primary">
                Available by this time
              </label>
              <div className="relative">
                <Clock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-secondary pointer-events-none z-10" />
                <Input
                  type="time"
                  value={startTime}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                    setStartTime(e.target.value)
                  }
                  className={`bg-surface-raised border-border-muted text-zinc-200 focus-visible:ring-zinc-600 pl-9 text-right cursor-pointer ${HIDE_TIME_PICKER_INDICATOR}`}
                />
              </div>
              {startTime && (
                <button
                  onClick={() => setStartTime("")}
                  className="text-xs text-zinc-400 hover:text-zinc-300 underline cursor-pointer"
                >
                  Clear
                </button>
              )}
            </div>

            {/* Available until this time */}
            <div className="space-y-2">
              <label className="text-sm font-medium text-primary">
                Available at least until this time today
              </label>
              <div className="relative">
                <Clock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-secondary pointer-events-none z-10" />
                <Input
                  type="time"
                  value={freeUntil}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                    setFreeUntil(e.target.value)
                  }
                  className={`bg-surface-raised border-border-muted text-zinc-200 focus-visible:ring-zinc-600 pl-9 text-right cursor-pointer ${HIDE_TIME_PICKER_INDICATOR}`}
                />
              </div>
              {freeUntil && (
                <button
                  onClick={() => setFreeUntil("")}
                  className="text-xs text-zinc-400 hover:text-zinc-300 underline cursor-pointer"
                >
                  Clear
                </button>
              )}
            </div>

            {/* Minimum Duration */}
            <div className="space-y-2">
              <label className="text-sm font-medium text-primary">
                Minimum Duration
              </label>
              <div className="flex gap-2">
                {[
                  { label: "30m", value: 30 },
                  { label: "1h", value: 60 },
                  { label: "2h", value: 120 },
                  { label: "4h", value: 240 },
                ].map(({ label, value }) => (
                  <button
                    key={value}
                    onClick={() =>
                      setMinDuration(minDuration === value ? "" : value)
                    }
                    className={`flex-1 px-3 py-2 rounded-md text-sm font-medium transition-colors cursor-pointer ${
                      minDuration === value
                        ? "bg-yellow-500/20 text-yellow-400 border border-yellow-500/40"
                        : "bg-surface-raised border border-border-muted text-zinc-300 hover:bg-surface-hover"
                    }`}
                  >
                    {label}
                  </button>
                ))}
              </div>
            </div>

            {/* Clear all filters */}
            {hasActiveFilter && (
              <button
                onClick={() => {
                  setStartTime("");
                  setFreeUntil("");
                  setMinDuration("");
                }}
                className="w-full mt-4 px-3 py-2 text-sm rounded-md border border-border-muted bg-surface-raised text-zinc-300 hover:bg-surface-hover transition-colors cursor-pointer"
              >
                Clear All Filters
              </button>
            )}
          </div>
        </ResponsivePopover>
      </div>

      {/* Building Cards Area  */}
      <div
        ref={scrollContainerRef}
        className={`flex-1 min-h-0 overflow-y-auto scrollbar-hide ${
          isFetching ? "flex items-center justify-center" : ""
        }`}
      >
        {isFetching ? (
          <LoadingSpinner />
        ) : facilityData ? (
          <>
            {Object.keys(filteredFacilities).length === 0 ? (
              <div className="text-center py-8">
                <p className="text-zinc-500 text-sm">
                  {searchQuery.trim()
                    ? "No buildings found matching your search."
                    : "No buildings available."}
                </p>
              </div>
            ) : (
              <Accordion
                type="multiple"
                value={expandedItems}
                onValueChange={setExpandedItems}
                className="space-y-2 border-none w-full"
              >
                {Object.values(filteredFacilities)
                  .sort((a, b) => a.id.localeCompare(b.id))
                  .map((facility) => {
                    const availableRooms = Object.entries(
                      facility.rooms,
                    ).filter(
                      ([, room]) =>
                        room.status === RoomStatus.AVAILABLE ||
                        room.status === RoomStatus.PASSING_PERIOD,
                    );
                    const occupiedRooms = Object.entries(facility.rooms).filter(
                      ([, room]) =>
                        room.status === RoomStatus.OCCUPIED ||
                        room.status === RoomStatus.OPENING_SOON,
                    );

                    return (
                      <AccordionItem
                        key={facility.id}
                        value={facility.id}
                        disabled={!facility.isOpen}
                        className="border-none"
                      >
                        <div
                          ref={(el) => {
                            buildingRefs.current[facility.id] = el;
                          }}
                          className="bg-surface rounded-lg overflow-hidden border border-border-subtle data-disabled:opacity-60 data-disabled:hover:border-border-subtle hover:border-border-strong transition-colors duration-300"
                          data-disabled={!facility.isOpen ? "" : undefined}
                          title={!facility.isOpen ? "Closed" : undefined}
                          aria-label={
                            !facility.isOpen
                              ? `${facility.name} (closed)`
                              : undefined
                          }
                        >
                          <AccordionTrigger
                            className="p-3 py-3 px-4 cursor-pointer data-disabled:cursor-not-allowed data-disabled:[&>svg]:hidden"
                            onClick={() => {
                              if (!facility.isOpen) return;
                              handleToggle(facility.id);
                            }}
                          >
                            <div className="flex justify-between items-center w-full mr-1 sm:mr-2 text-left">
                              <div className="font-normal flex flex-col sm:block min-w-0">
                                <span className="font-mono font-semibold text-[13px]">
                                  {facility.name}
                                </span>
                                {BUILDING_NAMES[facility.name] && (
                                  <>
                                    <span className="text-secondary/80 font-extralight mx-1 hidden sm:inline">
                                      -
                                    </span>
                                    <span className="text-sm text-secondary/90 sm:text-primary">
                                      {BUILDING_NAMES[facility.name]}
                                    </span>
                                  </>
                                )}
                              </div>
                              <Badge
                                variant={getBadgeVariant(
                                  facility.roomCounts.available,
                                  facility.roomCounts.total,
                                  facility.isOpen,
                                )}
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
                                <h4 className="text-[10px] font-bold text-secondary uppercase tracking-widest mb-1 px-3">
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
                                        }),
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
                                            roomNumber,
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
                                <h4 className="text-[10px] font-bold text-secondary uppercase tracking-widest mb-1 px-3">
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
                                        }),
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
                                            roomNumber,
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
          </>
        ) : null}
      </div>
      <FeedbackDialog
        open={feedbackDialogOpen}
        onOpenChange={setFeedbackDialogOpen}
      />
    </div>
  );
}
