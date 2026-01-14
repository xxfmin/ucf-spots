"use client";

import { useQuery } from "@tanstack/react-query";
import { RoomScheduleBlock } from "@/types";
import HourlyTimeBlocks from "./HourlyTimeBlocks";

interface RoomScheduleLoaderProps {
  buildingId: string;
  roomNumber: string;
  buildingHours: {
    open: string;
    close: string;
  };
}

async function fetchRoomSchedule(
  buildingId: string,
  roomNumber: string
): Promise<RoomScheduleBlock[]> {
  const params = new URLSearchParams({
    buildingId,
    roomNumber,
  });

  const response = await fetch(`/api/room-schedule?${params}`);

  if (!response.ok) {
    throw new Error("Failed to fetch room schedule");
  }

  return response.json();
}

export default function RoomScheduleLoader({
  buildingId,
  roomNumber,
  buildingHours,
}: RoomScheduleLoaderProps) {
  const { data, isLoading, error } = useQuery({
    queryKey: ["room-schedule", buildingId, roomNumber],
    queryFn: () => fetchRoomSchedule(buildingId, roomNumber),
    staleTime: 60 * 1000, // Cache for 1 minute
    retry: 1,
  });

  if (isLoading) {
    return (
      <div className="w-full">
        <div className="flex gap-0.5 animate-pulse">
          {Array.from({ length: 12 }).map((_, i) => (
            <div
              key={i}
              className="h-8 sm:h-10 flex-1 min-w-0 bg-zinc-800 rounded-sm"
            />
          ))}
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <p className="text-xs text-zinc-500 italic">
        Unable to load schedule
      </p>
    );
  }

  return <HourlyTimeBlocks schedule={data} buildingHours={buildingHours} />;
}
