import { NextResponse } from "next/server";
import { createClient } from "@supabase/supabase-js";
import moment from "moment-timezone";
import {
  FacilityStatus,
  Facility,
  FacilityType,
  RoomStatus,
  AcademicRoom,
  ClassInfo,
} from "@/types";

// Force dynamic rendering (no caching)
export const dynamic = "force-dynamic";

// UCF timezone
const TIMEZONE = "America/New_York";

// Minimum duration (in minutes) for a room to be considered "usefully available"
const MIN_USEFUL_MINUTES = 30;

// Minutes threshold for "opening soon" status
const OPENING_SOON_THRESHOLD = 20;

/**
 * Raw building data from Supabase RPC
 */
interface RawBuildingData {
  name: string;
  coordinates: {
    latitude: number;
    longitude: number;
  };
  hours: {
    open: string;
    close: string;
  };
  rooms: Record<
    string,
    {
      status: "available" | "occupied";
      passingPeriod?: boolean;
      currentClass?: ClassInfo | null;
      nextClass?: ClassInfo | null;
      availableAt?: string | null;
      availableFor?: number | null;
      availableUntil?: string | null;
    }
  >;
  isOpen: boolean;
  roomCounts: {
    available: number;
    total: number;
  };
}

/**
 * Checks if a room will be available soon (within threshold minutes)
 */
function isOpeningSoon(
  availableAt: string,
  targetMoment: moment.Moment
): boolean {
  // Parse the availableAt time (HH:mm:ss format)
  const availableTime = moment.tz(
    `${targetMoment.format("YYYY-MM-DD")} ${availableAt}`,
    "YYYY-MM-DD HH:mm:ss",
    TIMEZONE
  );

  // If the available time is before the target moment, it's already passed
  if (availableTime.isBefore(targetMoment)) {
    return false;
  }

  const diffInMinutes = availableTime.diff(targetMoment, "minutes");

  // Check if it's opening within the threshold (inclusive of 0)
  return diffInMinutes <= OPENING_SOON_THRESHOLD && diffInMinutes >= 0;
}

/**
 * Transforms raw Supabase data into the frontend Facility format
 */
function transformBuildingData(
  buildingId: string,
  buildingData: RawBuildingData,
  targetMoment: moment.Moment
): Facility {
  const facility: Facility = {
    id: buildingId,
    name: buildingData.name,
    type: FacilityType.ACADEMIC,
    coordinates: buildingData.coordinates,
    hours: buildingData.hours,
    isOpen: buildingData.isOpen,
    roomCounts: buildingData.roomCounts || { available: 0, total: 0 },
    rooms: {},
  };

  // Transform each room
  Object.entries(buildingData.rooms || {}).forEach(([roomNumber, roomData]) => {
    let status: RoomStatus;

    if (roomData.status === "available") {
      // Available room - check if it's just a passing period
      if (roomData.passingPeriod) {
        status = RoomStatus.PASSING_PERIOD;
      } else {
        status = RoomStatus.AVAILABLE;
      }
    } else {
      // Occupied room - check if it's opening soon
      if (
        roomData.availableAt &&
        isOpeningSoon(roomData.availableAt, targetMoment) &&
        roomData.availableFor &&
        roomData.availableFor >= MIN_USEFUL_MINUTES
      ) {
        status = RoomStatus.OPENING_SOON;
      } else {
        status = RoomStatus.OCCUPIED;
      }
    }

    const room: AcademicRoom = {
      status,
      currentClass: roomData.currentClass || undefined,
      nextClass: roomData.nextClass || undefined,
      passingPeriod: roomData.passingPeriod,
      availableAt: roomData.availableAt || undefined,
      availableFor:
        roomData.availableFor != null
          ? Math.max(0, roomData.availableFor)
          : undefined,
      availableUntil: roomData.availableUntil || undefined,
    };

    facility.rooms[roomNumber] = room;
  });

  return facility;
}

/**
 * Fetches building data from Supabase
 */
async function fetchBuildingData(
  targetMoment: moment.Moment
): Promise<Record<string, Facility>> {
  const facilities: Record<string, Facility> = {};

  // Validate environment variables
  // Support both naming conventions
  const supabaseUrl =
    process.env.SUPABASE_URL || process.env.NEXT_PUBLIC_SUPABASE_URL;
  const supabaseKey =
    process.env.SUPABASE_KEY || process.env.SUPABASE_SERVICE_ROLE_KEY;

  if (!supabaseUrl || !supabaseKey) {
    throw new Error("Missing Supabase environment variables");
  }

  const supabase = createClient(supabaseUrl, supabaseKey);

  // Call the cached spots RPC function
  const { data, error } = await supabase.rpc("get_cached_spots", {
    check_time_param: targetMoment.format("HH:mm:ss"),
    check_date_param: targetMoment.format("YYYY-MM-DD"),
    min_minutes_param: MIN_USEFUL_MINUTES,
  });

  if (error) {
    console.error("Supabase RPC error:", error);
    throw new Error(`Database error: ${error.message}`);
  }

  // Transform each building
  if (data?.buildings) {
    Object.entries(data.buildings).forEach(([buildingId, buildingData]) => {
      facilities[buildingId] = transformBuildingData(
        buildingId,
        buildingData as RawBuildingData,
        targetMoment
      );
    });
  }

  return facilities;
}

/**
 * GET /api/facilities
 *
 * Query parameters:
 * - date: YYYY-MM-DD (optional, defaults to current date in ET)
 * - time: HH:mm:ss (optional, defaults to current time in ET)
 *
 * Returns: FacilityStatus JSON
 */
export async function GET(request: Request) {
  try {
    const url = new URL(request.url);
    const dateParam = url.searchParams.get("date");
    const timeParam = url.searchParams.get("time");

    // Determine the target moment
    let targetMoment: moment.Moment;

    if (dateParam && timeParam) {
      // Validate the date/time format
      const parsed = moment.tz(
        `${dateParam} ${timeParam}`,
        "YYYY-MM-DD HH:mm:ss",
        true,
        TIMEZONE
      );

      if (parsed.isValid()) {
        targetMoment = parsed;
      } else {
        console.warn(
          `Invalid date/time parameters: date=${dateParam}, time=${timeParam}. Using current time.`
        );
        targetMoment = moment().tz(TIMEZONE);
      }
    } else if (dateParam) {
      // Date provided but no time - use current time for that date
      const parsed = moment.tz(dateParam, "YYYY-MM-DD", true, TIMEZONE);
      if (parsed.isValid()) {
        const now = moment().tz(TIMEZONE);
        targetMoment = parsed
          .hour(now.hour())
          .minute(now.minute())
          .second(now.second());
      } else {
        targetMoment = moment().tz(TIMEZONE);
      }
    } else {
      // Default to current time in ET
      targetMoment = moment().tz(TIMEZONE);
    }

    // Fetch building data
    const facilities = await fetchBuildingData(targetMoment);

    // Build response
    const response: FacilityStatus = {
      timestamp: targetMoment.toISOString(),
      facilities,
    };

    return NextResponse.json(response);
  } catch (error) {
    console.error("Error in /api/facilities:", error);

    const errorMessage =
      error instanceof Error ? error.message : "Failed to fetch facilities";

    return NextResponse.json({ error: errorMessage }, { status: 500 });
  }
}
